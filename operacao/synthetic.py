"""Dados inteiramente fictícios. O gerador é a regra do cenário, não um modelo do mundo."""
import argparse
import csv
import math
import random
from datetime import date, timedelta
from pathlib import Path
from .settings import RAW, PRODUCTS, INGREDIENTS, RECIPES, CHANNEL_FEES


def write_csv(path, rows):
    if not rows: raise ValueError('Tabela vazia')
    with open(path,'w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


def generate(out=RAW,days=365,seed=20261111,start='2025-01-01',daily_orders=80):
    if not 28<=days<=730 or not 1<=daily_orders<=1000: raise ValueError('Use 28 a 730 dias e 1 a 1000 pedidos/dia')
    out=Path(out)
    # Não sobrescrever silenciosamente dados já gerados.
    if out.exists() and any(out.iterdir()): raise ValueError(f'Destino não vazio: {out}. Escolha outra pasta.')
    out.mkdir(parents=True,exist_ok=True)
    rng=random.Random(seed); begin=date.fromisoformat(start)
    context=[]; orders=[]; lines=[]; shifts=[]; reviews=[]; inventory=[]; receipts=[]
    employees=[{'id':f'E{i:02}','role':'cozinha' if i<=4 else 'atendimento','hourly_cents':1800 if i<=4 else 1500} for i in range(1,8)]
    stock={i['id']:i['opening'] for i in INGREDIENTS}; order_no=0
    for d in range(days):
        day=begin+timedelta(days=d); ds=day.isoformat(); weekday=day.weekday()
        rain=round(max(0,rng.gauss(6,7)),1); temp=round(25+4*math.sin(d/365*math.tau)+rng.gauss(0,2),1)
        promo=int(rng.random()<.12)
        multiplier=(.8,.9,.95,1.0,1.2,1.4,1.1)[weekday]
        count=max(1,round(daily_orders*multiplier*(1+.15*promo)*max(.5,1-.003*rain)*rng.uniform(.8,1.2)))
        context.append({'date':ds,'weekday':weekday,'temperature':temp,'rain':rain,'promotion':promo,'synthetic':1})
        active=[]
        for e in employees:
            present=rng.random()>.08
            hours=8 if present else 0
            shifts.append({'date':ds,'employee_id':e['id'],'role':e['role'],'hours':hours,'cost_cents':hours*e['hourly_cents']})
            if present: active.append(e)
        kitchen=max(1,sum(e['role']=='cozinha' for e in active))
        # Recebimento diário parcialmente variável; se faltar, o pedido pode ser cancelado.
        for ing in INGREDIENTS:
            i=ing['id']; delivered=0
            if stock[i]<ing['reorder']*2 and rng.random()>.1:
                delivered=ing['opening']; stock[i]+=delivered
                receipts.append({'id':f'R{d:04}{i}','date':ds,'ingredient_id':i,'quantity':delivered,'supplier_id':'S01' if i in ('I01','I02') else 'S02'})
                inventory.append({'date':ds,'ingredient_id':i,'kind':'entrada','quantity':delivered,'source':f'R{d:04}{i}'})
        for _ in range(count):
            order_no+=1; oid=f'O{order_no:07}'
            channel=rng.choices(list(CHANNEL_FEES),[.5,.2,.3])[0]
            hour=rng.choices([11,12,13,14,18,19,20,21],[1,4,3,1,1,3,3,1])[0]
            minute=rng.randrange(60); created=f'{ds}T{hour:02}:{minute:02}:00-03:00'
            chosen=rng.sample(PRODUCTS,k=rng.choices([1,2,3],[6,3,1])[0])
            demand={}; item_rows=[]; gross=cost=0
            for p in chosen:
                qty=rng.choices([1,2,3],[8,2,1])[0]
                gross+=qty*p['price_cents']; cost+=qty*p['cost_cents']
                item_rows.append({'order_id':oid,'product_id':p['id'],'quantity':qty,'gross_cents':qty*p['price_cents'],'food_cost_cents':qty*p['cost_cents']})
                for ing,q in RECIPES[p['id']].items(): demand[ing]=demand.get(ing,0)+qty*q
            unavailable=any(stock[i]<q for i,q in demand.items())
            cancelled=unavailable or rng.random()<.025
            reason='sem_ingrediente' if unavailable else ('desistencia' if cancelled else '')
            prep=round(max(4,rng.gauss(12+count/kitchen*.16,4)),1)
            discount=round(gross*.05) if promo else 0
            fee=round((gross-discount)*CHANNEL_FEES[channel]); net=gross-discount-fee
            orders.append({'id':oid,'date':ds,'created_at':created,'channel':channel,'status':'cancelado' if cancelled else 'concluido','cancel_reason':reason,'gross_cents':gross,'discount_cents':discount,'fee_cents':fee,'net_cents':0 if cancelled else net,'food_cost_cents':0 if cancelled else cost,'prep_minutes':0 if cancelled else prep,'promised_minutes':25})
            lines.extend(item_rows)
            if not cancelled:
                for i,q in demand.items():
                    stock[i]-=q; inventory.append({'date':ds,'ingredient_id':i,'kind':'consumo','quantity':-q,'source':oid})
                if rng.random()<.25:
                    rating=max(1,min(5,round(5-max(0,prep-20)/12+rng.gauss(0,.65))))
                    category='espera' if rating<4 else 'satisfacao'
                    reviews.append({'id':f'V{oid}','order_id':oid,'date':ds,'rating':rating,'category':category})
        for ing in INGREDIENTS:
            i=ing['id']; waste=min(stock[i],round(stock[i]*rng.uniform(0,.012)))
            if waste: stock[i]-=waste; inventory.append({'date':ds,'ingredient_id':i,'kind':'perda','quantity':-waste,'source':f'W{d:04}{i}'})
    tables={'products':PRODUCTS,'ingredients':INGREDIENTS,'employees':employees,'context':context,'orders':orders,'order_items':lines,'shifts':shifts,'reviews':reviews,'movements':inventory,'receipts':receipts,'suppliers':[{'id':'S01','name':'Fornecedor fictício grãos'},{'id':'S02','name':'Fornecedor fictício hortifruti'}]}
    for name,rows in tables.items(): write_csv(out/f'{name}.csv',rows)
    import json
    (out/'manifest.json').write_text(json.dumps({'synthetic':True,'seed':seed,'days':days,'start':start,'daily_orders':daily_orders,'rows':{k:len(v) for k,v in tables.items()}},indent=2),encoding='utf-8')
    return {k:len(v) for k,v in tables.items()}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=RAW); parser.add_argument('--days',type=int,default=365)
    parser.add_argument('--seed',type=int,default=20261111); parser.add_argument('--start',default='2025-01-01')
    parser.add_argument('--daily-orders',type=int,default=80)
    print(generate(**vars(parser.parse_args())))
