"""SQLite transacional: eventos, reservas e recebimentos de demonstração.

Sem autenticação e sem integrações externas: somente uso local em loopback.
Valores de dinheiro em centavos. Quantidades inteiras na unidade do ingrediente.
"""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from .settings import SQLITE, PRODUCTS, INGREDIENTS, RECIPES


class Conflict(ValueError):
    pass


def now():
    return datetime.now(timezone.utc).isoformat()


def positive(n, label):
    if type(n) is not int or n <= 0:
        raise Conflict(f'{label}: use inteiro positivo')


class Store:
    def __init__(self, path=SQLITE):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as c:
            c.executescript('''
            CREATE TABLE IF NOT EXISTS ingredients(id TEXT PRIMARY KEY,name TEXT,unit TEXT,opening INTEGER,reorder_level INTEGER);
            CREATE TABLE IF NOT EXISTS products(id TEXT PRIMARY KEY,name TEXT,category TEXT,price_cents INTEGER,cost_cents INTEGER);
            CREATE TABLE IF NOT EXISTS recipes(product_id TEXT,ingredient_id TEXT,quantity INTEGER,PRIMARY KEY(product_id,ingredient_id));
            CREATE TABLE IF NOT EXISTS orders(id TEXT PRIMARY KEY,created_at TEXT,updated_at TEXT,channel TEXT,status TEXT,items TEXT,total_cents INTEGER);
            CREATE TABLE IF NOT EXISTS movements(id INTEGER PRIMARY KEY,created_at TEXT,ingredient_id TEXT,physical_delta INTEGER,reserved_delta INTEGER,reason TEXT,source TEXT);
            CREATE TABLE IF NOT EXISTS receipts(id TEXT PRIMARY KEY,created_at TEXT,ingredient_id TEXT,quantity INTEGER,unit_cost_cents INTEGER,status TEXT,note TEXT);
            CREATE TABLE IF NOT EXISTS commands(key TEXT PRIMARY KEY,payload TEXT,result TEXT);
            CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT,kind TEXT,payload TEXT);
            ''')
            c.executemany('INSERT OR IGNORE INTO ingredients VALUES(:id,:name,:unit,:opening,:reorder)', INGREDIENTS)
            c.executemany('INSERT OR IGNORE INTO products VALUES(:id,:name,:category,:price_cents,:cost_cents)', PRODUCTS)
            c.executemany('INSERT OR IGNORE INTO recipes VALUES(?,?,?)', [(p,i,q) for p,r in RECIPES.items() for i,q in r.items()])

    @contextmanager
    def connection(self, write=False):
        c = sqlite3.connect(self.path, timeout=10)
        c.row_factory = sqlite3.Row
        c.execute('PRAGMA foreign_keys=ON')
        try:
            if write:
                c.execute('BEGIN IMMEDIATE')
            yield c
            c.commit()
        except Exception:
            c.rollback()
            raise
        finally:
            c.close()

    @staticmethod
    def _inventory(c):
        return [dict(r) for r in c.execute('''SELECT i.id,i.name,i.unit,i.reorder_level,
        i.opening+COALESCE(SUM(m.physical_delta),0) physical,
        COALESCE(SUM(m.reserved_delta),0) reserved,
        i.opening+COALESCE(SUM(m.physical_delta-m.reserved_delta),0) available
        FROM ingredients i LEFT JOIN movements m ON i.id=m.ingredient_id GROUP BY i.id ORDER BY i.id''')]

    @staticmethod
    def _event(c, kind, payload):
        c.execute('INSERT INTO events(created_at,kind,payload) VALUES(?,?,?)', (now(),kind,json.dumps(payload,ensure_ascii=False)))

    @staticmethod
    def _command(c, key, payload):
        if not isinstance(key,str) or not key.strip() or len(key)>128:
            raise Conflict('Chave de comando ausente ou longa')
        data=json.dumps(payload,sort_keys=True)
        old=c.execute('SELECT * FROM commands WHERE key=?',(key,)).fetchone()
        if old:
            if old['payload'] != data:
                raise Conflict('Chave de comando reutilizada com conteúdo diferente')
            return json.loads(old['result'])
        return None

    @staticmethod
    def _remember(c,key,payload,result):
        c.execute('INSERT INTO commands VALUES(?,?,?)',(key,json.dumps(payload,sort_keys=True),json.dumps(result,ensure_ascii=False)))
        return result

    def catalogue(self):
        with self.connection() as c:
            return [dict(r) for r in c.execute('SELECT * FROM products ORDER BY id')]

    def inventory(self):
        with self.connection() as c:
            return self._inventory(c)

    def order(self, key, order_id, items, channel='salao'):
        if not isinstance(order_id,str) or not order_id.strip() or len(order_id)>80:
            raise Conflict('Identificador de pedido inválido')
        if channel not in ('salao','retirada','entrega') or not items:
            raise Conflict('Canal ou itens inválidos')
        for q in items.values():
            positive(q,'Quantidade')
            if q>100: raise Conflict('Máximo 100 unidades por produto')
        payload={'action':'create','id':order_id,'items':items,'channel':channel}
        with self.connection(True) as c:
            existing=self._command(c,key,payload)
            if existing is not None: return existing
            if c.execute('SELECT id FROM orders WHERE id=?',(order_id,)).fetchone():
                raise Conflict('Pedido já existe')
            demand={}; total=0
            for p,q in items.items():
                product=c.execute('SELECT * FROM products WHERE id=?',(p,)).fetchone()
                if not product: raise Conflict(f'Produto desconhecido: {p}')
                total+=product['price_cents']*q
                for r in c.execute('SELECT * FROM recipes WHERE product_id=?',(p,)):
                    i=r['ingredient_id']; demand[i]=demand.get(i,0)+r['quantity']*q
            available={r['id']:r['available'] for r in self._inventory(c)}
            if any(q>available.get(i,0) for i,q in demand.items()): raise Conflict('Estoque insuficiente para reservar o pedido inteiro')
            t=now()
            c.execute('INSERT INTO orders VALUES(?,?,?,?,?,?,?)',(order_id,t,t,channel,'reservado',json.dumps(items),total))
            for i,q in demand.items():
                c.execute('INSERT INTO movements(created_at,ingredient_id,physical_delta,reserved_delta,reason,source) VALUES(?,?,?,?,?,?)',(t,i,0,q,'reserva',order_id))
            result={'id':order_id,'status':'reservado','total_cents':total}
            self._event(c,'pedido_criado',result)
            return self._remember(c,key,payload,result)

    def transition(self,key,order_id,target):
        payload={'action':'transition','id':order_id,'target':target}
        with self.connection(True) as c:
            existing=self._command(c,key,payload)
            if existing is not None: return existing
            o=c.execute('SELECT * FROM orders WHERE id=?',(order_id,)).fetchone()
            if not o: raise Conflict('Pedido não encontrado')
            allowed={'reservado':{'preparando','cancelado'},'preparando':{'concluido'},'concluido':set(),'cancelado':set()}
            if target not in allowed[o['status']]: raise Conflict(f'Transição inválida: {o["status"]} → {target}')
            if o['status']=='reservado':
                for r in c.execute('SELECT ingredient_id,SUM(reserved_delta) quantity FROM movements WHERE source=? GROUP BY ingredient_id',(order_id,)).fetchall():
                    q=r['quantity']; delta=-q if target=='preparando' else 0
                    c.execute('INSERT INTO movements(created_at,ingredient_id,physical_delta,reserved_delta,reason,source) VALUES(?,?,?,?,?,?)',(now(),r['ingredient_id'],delta,-q,target,order_id))
            c.execute('UPDATE orders SET status=?,updated_at=? WHERE id=?',(target,now(),order_id))
            result={'id':order_id,'status':target}
            self._event(c,'pedido_alterado',result)
            return self._remember(c,key,payload,result)

    def receive(self,key,receipt_id,ingredient_id,quantity,unit_cost_cents,note=''):
        positive(quantity,'Quantidade recebida'); positive(unit_cost_cents,'Custo por unidade-base em centavos')
        if not receipt_id.strip() or len(receipt_id)>80 or len(note)>500: raise Conflict('Identificador ou observação inválida')
        payload={'action':'receive','id':receipt_id,'ingredient':ingredient_id,'quantity':quantity,'cost':unit_cost_cents,'note':note}
        with self.connection(True) as c:
            old=self._command(c,key,payload)
            if old is not None: return old
            if not c.execute('SELECT id FROM ingredients WHERE id=?',(ingredient_id,)).fetchone(): raise Conflict('Ingrediente desconhecido')
            if c.execute('SELECT id FROM receipts WHERE id=?',(receipt_id,)).fetchone(): raise Conflict('Recebimento já existe')
            c.execute('INSERT INTO receipts VALUES(?,?,?,?,?,?,?)',(receipt_id,now(),ingredient_id,quantity,unit_cost_cents,'pendente',note))
            result={'id':receipt_id,'status':'pendente'}
            self._event(c,'recebimento_pendente',result)
            return self._remember(c,key,payload,result)

    def approve(self,key,receipt_id):
        payload={'action':'approve','id':receipt_id}
        with self.connection(True) as c:
            old=self._command(c,key,payload)
            if old is not None: return old
            r=c.execute('SELECT * FROM receipts WHERE id=?',(receipt_id,)).fetchone()
            if not r: raise Conflict('Recebimento não encontrado')
            if r['status']!='pendente': raise Conflict('Recebimento já aprovado')
            c.execute('INSERT INTO movements(created_at,ingredient_id,physical_delta,reserved_delta,reason,source) VALUES(?,?,?,?,?,?)',(now(),r['ingredient_id'],r['quantity'],0,'recebimento',receipt_id))
            c.execute('UPDATE receipts SET status=? WHERE id=?',('aprovado',receipt_id))
            result={'id':receipt_id,'status':'aprovado'}
            self._event(c,'recebimento_aprovado',result)
            return self._remember(c,key,payload,result)

    def snapshot(self):
        with self.connection() as c:
            orders=[dict(r) for r in c.execute('SELECT * FROM orders ORDER BY created_at DESC LIMIT 500')]
            for o in orders: o['items']=json.loads(o['items'])
            return {'synthetic':True,'orders':orders,'inventory':self._inventory(c),
                    'receipts':[dict(r) for r in c.execute('SELECT * FROM receipts ORDER BY created_at DESC LIMIT 500')],
                    'seq':c.execute('SELECT COALESCE(MAX(seq),0) FROM events').fetchone()[0],
                    'summary':dict(c.execute("SELECT COUNT(*) total_orders,COALESCE(SUM(CASE WHEN status!='cancelado' THEN total_cents ELSE 0 END),0) booked_cents,SUM(status='reservado') waiting FROM orders").fetchone())}

    def events(self,after=0):
        with self.connection() as c:
            return [{**dict(r),'payload':json.loads(r['payload'])} for r in c.execute('SELECT * FROM events WHERE seq>? ORDER BY seq LIMIT 500',(after,))]
