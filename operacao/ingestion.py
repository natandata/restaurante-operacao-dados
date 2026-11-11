"""Importação validada e atômica do lote CSV completo para DuckDB.

Uma linha inválida rejeita o lote inteiro; relatório de rejeições fica fora do banco.
Repetir o mesmo conteúdo retorna duplicate, sem duplicar fatos.
"""
import hashlib
import json
import math
from pathlib import Path
import duckdb
import pandas as pd
from .settings import RAW, WAREHOUSE

TABLES=('products','ingredients','employees','context','orders','order_items','shifts','reviews','movements','receipts','suppliers')
REQUIRED={
 'products':{'id','name','category','price_cents','cost_cents'},
 'ingredients':{'id','name','unit','opening','reorder'},
 'employees':{'id','role','hourly_cents'},
 'context':{'date','weekday','temperature','rain','promotion','synthetic'},
 'orders':{'id','date','created_at','channel','status','cancel_reason','gross_cents','discount_cents','fee_cents','net_cents','food_cost_cents','prep_minutes','promised_minutes'},
 'order_items':{'order_id','product_id','quantity','gross_cents','food_cost_cents'},
 'shifts':{'date','employee_id','role','hours','cost_cents'},
 'reviews':{'id','order_id','date','rating','category'},
 'movements':{'date','ingredient_id','kind','quantity','source'},
 'receipts':{'id','date','ingredient_id','quantity','supplier_id'},
 'suppliers':{'id','name'},
}


class BatchRejected(ValueError):
    pass


def load_batch(folder=RAW,database=WAREHOUSE):
    folder=Path(folder); database=Path(database)
    errors=[]; frames={}; digest=hashlib.sha256()
    for name in TABLES:
        path=folder/f'{name}.csv'
        if not path.is_file(): errors.append({'table':name,'error':'arquivo ausente'}); continue
        digest.update(name.encode()); digest.update(path.read_bytes())
        try:
            frame=pd.read_csv(path,keep_default_na=False)
            if not REQUIRED[name].issubset(frame.columns): raise ValueError('colunas obrigatórias ausentes')
            if frame.empty: raise ValueError('tabela vazia')
            if 'id' in frame and (frame.id.astype(str).str.strip().eq('').any() or frame.id.duplicated().any()): raise ValueError('id vazio ou duplicado')
            if 'date' in frame: pd.to_datetime(frame['date'],format='%Y-%m-%d',errors='raise')
            for col in ('quantity','price_cents','cost_cents','opening','reorder','hours','gross_cents','discount_cents','fee_cents','net_cents','food_cost_cents','rating','hourly_cents'):
                if col not in frame: continue
                numbers=pd.to_numeric(frame[col],errors='raise')
                if not numbers.map(math.isfinite).all(): raise ValueError(f'{col}: número não finito')
                if col.endswith('_cents') or col in ('quantity','opening','reorder','rating'):
                    if not numbers.mod(1).eq(0).all(): raise ValueError(f'{col}: deve ser inteiro')
                if name!='movements' and numbers.lt(0).any(): raise ValueError(f'{col}: valor negativo')
                if col=='quantity' and name!='movements' and numbers.le(0).any(): raise ValueError('quantidade não positiva')
            frames[name]=frame
        except Exception as e: errors.append({'table':name,'error':str(e)})
    def relation(child,column,parent):
        if child in frames and parent in frames and not frames[child][column].isin(frames[parent].id).all():
            errors.append({'table':child,'error':f'{column}: referência inexistente em {parent}'})
    for child,column,parent in [('order_items','order_id','orders'),('order_items','product_id','products'),('reviews','order_id','orders'),('shifts','employee_id','employees'),('movements','ingredient_id','ingredients'),('receipts','ingredient_id','ingredients'),('receipts','supplier_id','suppliers')]: relation(child,column,parent)
    if 'reviews' in frames and not frames['reviews'].rating.between(1,5).all(): errors.append({'table':'reviews','error':'nota fora de 1 a 5'})
    if 'orders' in frames:
        o=frames['orders']
        if not o.channel.isin(['salao','retirada','entrega']).all() or not o.status.isin(['concluido','cancelado']).all(): errors.append({'table':'orders','error':'canal ou status inválido'})
        expected=(o.gross_cents-o.discount_cents-o.fee_cents).where(o.status=='concluido',0)
        if not o.net_cents.eq(expected).all(): errors.append({'table':'orders','error':'receita líquida não reconcilia'})
        if 'order_items' in frames:
            sums=frames['order_items'].groupby('order_id').gross_cents.sum()
            if not o.set_index('id').gross_cents.eq(sums.reindex(o.id).to_numpy()).all(): errors.append({'table':'order_items','error':'valor dos itens difere do pedido'})
    if errors:
        report=folder/'rejections.json'; report.write_text(json.dumps(errors,ensure_ascii=False,indent=2),encoding='utf-8')
        raise BatchRejected(f'Lote rejeitado: {len(errors)} erro(s). Relatório: {report}')
    key=digest.hexdigest(); database.parent.mkdir(parents=True,exist_ok=True)
    with duckdb.connect(str(database)) as c:
        c.execute('CREATE SCHEMA IF NOT EXISTS audit')
        c.execute('CREATE TABLE IF NOT EXISTS audit.batches(hash VARCHAR PRIMARY KEY,loaded_at TIMESTAMP,rows BIGINT)')
        c.execute('CREATE TABLE IF NOT EXISTS audit.current_snapshot(singleton INTEGER PRIMARY KEY,hash VARCHAR)')
        current=c.execute('SELECT hash FROM audit.current_snapshot WHERE singleton=1').fetchone()
        if current is None:
            current=c.execute('SELECT hash FROM audit.batches ORDER BY loaded_at DESC LIMIT 1').fetchone()
        if current and current[0]==key: return {'status':'duplicate','hash':key}
        c.execute('BEGIN')
        try:
            c.execute('CREATE SCHEMA IF NOT EXISTS raw')
            for name,frame in frames.items():
                c.register('incoming',frame)
                c.execute(f'CREATE OR REPLACE TABLE raw.{name} AS SELECT * FROM incoming')
                c.unregister('incoming')
            c.execute('INSERT OR REPLACE INTO audit.batches VALUES(?,current_timestamp,?)',[key,sum(len(f) for f in frames.values())])
            c.execute('INSERT OR REPLACE INTO audit.current_snapshot VALUES(1,?)',[key])
            c.execute('COMMIT')
        except Exception:
            c.execute('ROLLBACK'); raise
    return {'status':'loaded','hash':key,'rows':sum(len(f) for f in frames.values())}

if __name__=='__main__': print(load_batch())
