from concurrent.futures import ThreadPoolExecutor
import csv
import json
import subprocess
import sys
from pathlib import Path
import duckdb
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from operacao.store import Store,Conflict
from operacao.api import create_app
from operacao.synthetic import generate
from operacao.ingestion import load_batch,BatchRejected
from operacao.forecast import feature_frame,metrics,run_forecast

@pytest.fixture
def store(tmp_path): return Store(tmp_path/'op.sqlite3')

def test_reserve_prepare_cancel(store):
    start=store.inventory()[0]
    store.order('create','A',{'P01':2})
    reserved=store.inventory()[0]
    assert reserved['physical']==start['physical']
    assert reserved['reserved']==320
    store.transition('prepare','A','preparando')
    consumed=store.inventory()[0]
    assert consumed['physical']==start['physical']-320
    assert consumed['reserved']==0
    assert consumed['available']==reserved['available']
    with pytest.raises(Conflict): store.transition('bad-cancel','A','cancelado')
    store.transition('complete','A','concluido')
    assert store.snapshot()['orders'][0]['status']=='concluido'

def test_cancel_releases_without_consuming(store):
    start=store.inventory()
    store.order('a','A',{'P02':3})
    store.transition('b','A','cancelado')
    assert store.inventory()==start

def test_command_is_idempotent(store):
    a=store.order('a','A',{'P01':2})
    before=store.inventory()
    assert store.order('a','A',{'P01':2})==a
    assert store.inventory()==before
    with pytest.raises(Conflict):store.order('a','A',{'P01':3})
    with pytest.raises(Conflict):store.order('newkey','A',{'P01':2})

def test_failed_order_leaves_no_rows(store):
    before=store.inventory()
    with pytest.raises(Conflict): store.order('a','A',{'P04':100})
    assert before==store.inventory()
    assert not store.snapshot()['orders']
    assert not store.events()

@pytest.mark.parametrize('quantity',[True,0,-1,2.3])
def test_invalid_quantity(store,quantity):
    with pytest.raises(Conflict): store.order('a','A',{'P01':quantity})

def test_receipt_needs_approval_and_cannot_duplicate(store):
    before=store.inventory()[0]['physical']
    r=store.receive('a','R','I01',1000,1)
    assert r['status']=='pendente'
    assert store.inventory()[0]['physical']==before
    store.approve('b','R'); store.approve('b','R')
    assert store.inventory()[0]['physical']==before+1000
    with pytest.raises(Conflict):store.approve('c','R')

def test_persistence_and_replay(store):
    store.order('a','A',{'P01':1})
    new=Store(store.path)
    assert len(new.snapshot()['orders'])==1
    assert new.events(0)[0]['seq']==1
    assert new.events(1)==[]

def test_concurrent_reservations_cannot_go_negative(store):
    def send(i):
        try:store.order(str(i),str(i),{'P01':20}); return True
        except Conflict:return False
    with ThreadPoolExecutor(max_workers=8) as pool: result=list(pool.map(send,range(20)))
    assert any(result) and not all(result)
    assert all(i['available']>=0 and i['physical']>=0 for i in store.inventory())

def test_api_commands_and_receipts(store):
    with TestClient(create_app(store)) as c:
        assert c.get('/api/health').json()['synthetic']
        a=c.post('/api/orders',json={'key':'k','id':'A','items':{'P01':1}})
        assert a.status_code==200
        assert c.post('/api/orders',json={'key':'k','id':'A','items':{'P01':1}}).status_code==200
        assert c.post('/api/orders',json={'key':'k','id':'A','items':{'P01':2}}).status_code==409
        assert c.post('/api/orders',json={'key':'j','id':'B','items':{'P01':True}}).status_code==422
        assert c.post('/api/receipts',json={'key':'r','id':'R','ingredient_id':'I01','quantity':500,'unit_cost_cents':1}).status_code==200
        assert c.post('/api/receipts/R/approve',json={'key':'approve'}).status_code==200
        assert c.post('/api/simulator/start',json={}).json()['running']
        assert not c.post('/api/simulator/stop',json={}).json()['running']

def test_foreign_origin_cannot_write(store):
    with TestClient(create_app(store)) as c:
        assert c.post('/api/simulator/start',json={},headers={'Origin':'https://not-local.invalid'}).status_code==403

def test_websocket_snapshot_and_replay(store):
    store.order('a','A',{'P01':1})
    with TestClient(create_app(store)) as c:
        with c.websocket_connect('/ws?after=0') as ws:
            assert ws.receive_json()['type']=='snapshot'
            events=ws.receive_json();assert events['type']=='events' and events['seq']==1
        with c.websocket_connect('/ws?after=1') as ws:
            ws.receive_json();assert ws.receive_json()['type']=='heartbeat'

def test_feature_lags_do_not_see_future():
    frame=pd.DataFrame({'day':pd.date_range('2025-01-01',periods=20),'orders':range(20)})
    a=feature_frame(frame)
    frame.loc[19,'orders']=90000
    b=feature_frame(frame)
    pd.testing.assert_frame_equal(a.iloc[:-1],b.iloc[:-1])
    assert b.iloc[-1].lag7==12
    assert b.iloc[-1].previous7_mean==15

def test_metrics_handle_zero():
    assert metrics([0,0],[1,2])['wape'] is None
    assert metrics([1,2],[1,2])['mae']==0

@pytest.fixture(scope='module')
def warehouse(tmp_path_factory):
    root=tmp_path_factory.mktemp('pipeline'); raw=root/'raw'; db=root/'test.duckdb'
    generate(raw,days=100,daily_orders=8)
    assert load_batch(raw,db)['status']=='loaded'
    env=__import__('os').environ.copy();env['RESTAURANTE_WAREHOUSE']=str(db)
    result=subprocess.run([__import__('shutil').which('dbt'),'build','--project-dir','warehouse','--profiles-dir','warehouse'],env=env,capture_output=True,text=True)
    # dbt's supported executable entry point is the installed CLI.
    if result.returncode or not db.exists(): raise AssertionError(result.stdout+result.stderr)
    with duckdb.connect(str(db)) as c:
        assert c.execute('select count(*) from mart_daily').fetchone()[0]==100
    return root,raw,db

def test_full_pipeline_and_forecast(warehouse):
    root,raw,db=warehouse
    assert load_batch(raw,db)['status']=='duplicate'
    f=run_forecast(db,root/'forecast.json')
    assert len(f['future'])==7
    assert len(f['comparison'])==4
    assert all(r['orders']>=0 for r in f['future'])
    assert f['split']['test']>0
    with TestClient(create_app(Store(root/'ops.sqlite3'),db,root/'forecast.json')) as c:
        for mart in ('daily','menu','channel','service','labour','inventory','experience'):
            assert c.get('/api/analytics/'+mart).json()['rows']
        assert c.get('/api/forecast').json()['selected']==f['selected']

def test_invalid_batch_atomic(warehouse,tmp_path):
    root,raw,db=warehouse
    copied=tmp_path/'bad';__import__('shutil').copytree(raw,copied)
    path=copied/'order_items.csv';f=pd.read_csv(path);f.loc[0,'order_id']='MISSING';f.to_csv(path,index=False)
    with duckdb.connect(str(db)) as c:before=c.execute('select count(*) from raw.orders').fetchone()[0]
    with pytest.raises(BatchRejected):load_batch(copied,db)
    with duckdb.connect(str(db)) as c:assert c.execute('select count(*) from raw.orders').fetchone()[0]==before
    assert (copied/'rejections.json').exists()

def test_same_seed_same_files(tmp_path):
    a=tmp_path/'a';b=tmp_path/'b'
    generate(a,days=28,daily_orders=5);generate(b,days=28,daily_orders=5)
    assert (a/'orders.csv').read_bytes()==(b/'orders.csv').read_bytes()
    with pytest.raises(ValueError):generate(a,days=28)


def test_previous_batch_can_replace_current_snapshot(tmp_path):
    a=tmp_path/'a'; b=tmp_path/'b'; db=tmp_path/'snapshots.duckdb'
    generate(a,days=28,daily_orders=8,seed=7)
    generate(b,days=29,daily_orders=8,seed=9)
    assert load_batch(a,db)['status']=='loaded'
    with duckdb.connect(str(db)) as c: original=c.execute('select count(*) from raw.orders').fetchone()[0]
    assert load_batch(b,db)['status']=='loaded'
    assert load_batch(a,db)['status']=='loaded'
    with duckdb.connect(str(db)) as c: assert c.execute('select count(*) from raw.orders').fetchone()[0]==original
    assert load_batch(a,db)['status']=='duplicate'
