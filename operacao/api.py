"""Serviço local da demonstração. Vincular a 127.0.0.1; não expor na internet."""
import asyncio
import json
import random
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
import duckdb
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, StrictInt
from .settings import WAREHOUSE, DATA
from .store import Store, Conflict

MARTS={'daily':'mart_daily','menu':'mart_menu','channel':'mart_channel','service':'mart_service','labour':'mart_labour','inventory':'mart_inventory','experience':'mart_experience'}


class NewOrder(BaseModel):
    key: str=Field(min_length=1,max_length=128)
    id: str=Field(min_length=1,max_length=80)
    items: dict[str,StrictInt]
    channel: Literal['salao','retirada','entrega']='salao'


class Change(BaseModel):
    key: str=Field(min_length=1,max_length=128)
    target: Literal['preparando','concluido','cancelado']


class Receipt(BaseModel):
    key: str=Field(min_length=1,max_length=128)
    id: str=Field(min_length=1,max_length=80)
    ingredient_id: str
    quantity: StrictInt=Field(gt=0,le=10000000)
    unit_cost_cents: StrictInt=Field(gt=0,le=1000000)
    note: str=Field(default='',max_length=500)


class Approval(BaseModel):
    key: str=Field(min_length=1,max_length=128)


def analytics(name,database=WAREHOUSE):
    if name not in MARTS: raise Conflict('Indicador desconhecido')
    if not Path(database).is_file(): raise Conflict('Warehouse ainda não preparado. Rode a preparação de dados.')
    with duckdb.connect(str(database),read_only=True) as c:
        frame=c.execute(f'SELECT * FROM {MARTS[name]}').df()
    return json.loads(frame.to_json(orient='records',date_format='iso'))


def create_app(store=None,database=WAREHOUSE,forecast_path=DATA/'forecast.json'):
    store=store or Store()
    state={'simulate':False,'task':None,'rejected':0}
    async def simulate():
        rng=random.Random(331)
        while True:
            await asyncio.sleep(3)
            if not state['simulate']: continue
            token='SIM-'+uuid.uuid4().hex[:10]
            product=rng.choice(store.catalogue())
            try:
                store.order(token,token,{product['id']:rng.randint(1,2)},rng.choice(['salao','retirada','entrega']))
                store.transition(token+'-prep',token,'preparando')
                store.transition(token+'-done',token,'concluido')
            except Conflict: state['rejected']+=1
    @asynccontextmanager
    async def lifespan(app):
        state['task']=asyncio.create_task(simulate())
        yield
        state['task'].cancel()
        try: await state['task']
        except asyncio.CancelledError: pass
    app=FastAPI(title='Restaurante fictício - estudo independente',lifespan=lifespan)
    app.state.store=store
    app.add_middleware(CORSMiddleware,allow_origins=['http://127.0.0.1:5173','http://localhost:5173','http://127.0.0.1:4173'],allow_methods=['GET','POST'],allow_headers=['Content-Type'])
    @app.middleware('http')
    async def local_only(request:Request,call_next):
        if request.method=='POST':
            origin=request.headers.get('origin')
            if origin and origin not in ('http://127.0.0.1:5173','http://localhost:5173','http://127.0.0.1:4173'):
                return JSONResponse(status_code=403,content={'detail':'Origem não permitida'})
        return await call_next(request)
    @app.exception_handler(Conflict)
    async def handle(request,exc): return JSONResponse(status_code=409,content={'detail':str(exc)})
    @app.get('/api/health')
    def health(): return {'status':'ok','synthetic':True,'warehouse_ready':Path(database).is_file()}
    @app.get('/api/catalogue')
    def catalogue(): return store.catalogue()
    @app.get('/api/state')
    def snapshot(): return {**store.snapshot(),'simulator':{'running':state['simulate'],'rejected':state['rejected']}}
    @app.get('/api/events')
    def events(after:int=0): return store.events(max(0,after))
    @app.post('/api/orders')
    def order(body:NewOrder): return store.order(body.key,body.id,body.items,body.channel)
    @app.post('/api/orders/{order_id}/transition')
    def transition(order_id:str,body:Change): return store.transition(body.key,order_id,body.target)
    @app.post('/api/receipts')
    def receive(body:Receipt): return store.receive(body.key,body.id,body.ingredient_id,body.quantity,body.unit_cost_cents,body.note)
    @app.post('/api/receipts/{receipt_id}/approve')
    def approve(receipt_id:str,body:Approval): return store.approve(body.key,receipt_id)
    @app.post('/api/simulator/{action}')
    def simulator(action:Literal['start','stop']):
        state['simulate']=action=='start'
        return {'running':state['simulate']}
    @app.get('/api/analytics/{name}')
    def mart(name:str): return {'synthetic':True,'rows':analytics(name,database),'scope':'dataset completo; estoque é saldo final do histórico sintético, separado da operação ao vivo'}
    @app.get('/api/forecast')
    def forecast():
        if not Path(forecast_path).is_file(): raise Conflict('Previsão ainda não calculada')
        return json.loads(Path(forecast_path).read_text(encoding='utf-8'))
    @app.websocket('/ws')
    async def stream(websocket:WebSocket,after:int=0):
        origin=websocket.headers.get('origin')
        if origin and origin not in ('http://127.0.0.1:5173','http://localhost:5173','http://127.0.0.1:4173'):
            await websocket.close(code=1008); return
        await websocket.accept()
        cursor=max(0,after)
        try:
            await websocket.send_json({'type':'snapshot','data':store.snapshot()})
            while True:
                rows=store.events(cursor)
                if rows:
                    cursor=rows[-1]['seq']
                    await websocket.send_json({'type':'events','data':rows,'seq':cursor})
                else: await websocket.send_json({'type':'heartbeat','seq':cursor})
                await asyncio.sleep(1)
        except (WebSocketDisconnect,RuntimeError): pass
    return app

app=create_app()
