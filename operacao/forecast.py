"""Previsão com seleção em validação e teste cronológico separado.

Todos os dados são sintéticos. O conjunto de teste não escolhe o modelo.
"""
import json
import math
from datetime import timedelta
from pathlib import Path
import duckdb
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from .settings import WAREHOUSE, DATA

FEATURES=['weekday','month','lag7','previous7_mean']


def feature_frame(daily):
    d=daily.sort_values('day').copy()
    d['day']=pd.to_datetime(d.day)
    d['weekday']=d.day.dt.day_of_week
    d['month']=d.day.dt.month
    d['lag7']=d.orders.shift(7)
    d['previous7_mean']=d.orders.shift(1).rolling(7).mean()
    return d.dropna(subset=FEATURES).reset_index(drop=True)


def metrics(actual,predicted):
    a=np.asarray(actual,dtype=float); p=np.asarray(predicted,dtype=float)
    return {'mae':float(np.mean(abs(a-p))),'rmse':float(np.sqrt(np.mean((a-p)**2))),
            'wape':float(np.sum(abs(a-p))/np.sum(abs(a))) if np.sum(abs(a)) else None}


def run_forecast(database=WAREHOUSE,save=DATA/'forecast.json'):
    with duckdb.connect(str(database),read_only=True) as c:
        daily=c.execute('SELECT day,orders FROM mart_daily ORDER BY day').df()
        productivity=c.execute("""SELECT d.orders/sum(s.hours) rate FROM mart_daily d
        JOIN fact_shift s USING(day) WHERE s.role='cozinha' GROUP BY d.day,d.orders HAVING sum(s.hours)>0""").df()
    f=feature_frame(daily)
    if len(f)<50: raise ValueError('Previsão precisa de pelo menos 57 dias de histórico')
    a=int(len(f)*.65); b=int(len(f)*.82)
    train,validation,test=f.iloc[:a],f.iloc[a:b],f.iloc[b:]
    models={'semana_anterior':None,'media_sete_dias':None,'ridge':Ridge(alpha=10),
            'floresta':RandomForestRegressor(n_estimators=80,max_depth=6,min_samples_leaf=4,random_state=271)}
    def predict(name,model,frame):
        if name=='semana_anterior': return frame.lag7.to_numpy()
        if name=='media_sete_dias': return frame.previous7_mean.to_numpy()
        return np.maximum(0,model.predict(frame[FEATURES]))
    comparison=[]
    for name,model in models.items():
        if model is not None: model.fit(train[FEATURES],train.orders)
        score=metrics(validation.orders,predict(name,model,validation))
        comparison.append({'model':name,'validation':score})
    selected=min(comparison,key=lambda x:x['validation']['mae'])['model']
    # Congelar seleção e só então avaliar teste, com refit em treino+validação.
    for name,model in models.items():
        if model is not None: model.fit(f.iloc[:b][FEATURES],f.iloc[:b].orders)
        for row in comparison:
            if row['model']==name: row['test']=metrics(test.orders,predict(name,model,test))
    test_predictions=predict(selected,models[selected],test)
    history=[{'day':str(row.day.date()),'actual':int(row.orders),'predicted':round(float(p),2)} for row,p in zip(test.itertuples(),test_predictions)]
    # Refit final em todo histórico. Próximos sete passos usam as próprias previsões.
    model=models[selected]
    if model is not None: model.fit(f[FEATURES],f.orders)
    counts=daily.orders.astype(float).tolist(); last=pd.Timestamp(daily.day.iloc[-1]); future=[]
    capacity=float(productivity.rate.median()) if len(productivity) else 1.0
    capacity=max(capacity,.1)
    for step in range(1,8):
        day=last+timedelta(days=step)
        row=pd.DataFrame([{'weekday':day.day_of_week,'month':day.month,'lag7':counts[-7],'previous7_mean':float(np.mean(counts[-7:]))}])
        pred=float(predict(selected,model,row)[0]); counts.append(pred)
        future.append({'day':str(day.date()),'orders':round(pred,1),'kitchen_people_8h':math.ceil(pred/(capacity*8))})
    result={'synthetic':True,'selected':selected,'features':FEATURES,'selection':'menor MAE na validação, antes do teste',
            'split':{'train':len(train),'validation':len(validation),'test':len(test),'test_start':history[0]['day']},
            'evaluation':'previsão de um dia com histórico real anterior disponível; futuro de sete dias é recursivo',
            'comparison':comparison,'test_history':history,'future':future,
            'staffing_assumption':'pessoas = teto(pedidos previstos / (mediana histórica de pedidos por hora de cozinha × 8h)); não é escala real',
            'uncertainty':'Não há intervalo probabilístico calibrado. Erro de teste não é garantia para dias futuros.'}
    if save is not None:
        Path(save).parent.mkdir(parents=True,exist_ok=True)
        Path(save).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result

if __name__=='__main__':
    result=run_forecast(); print(json.dumps({k:v for k,v in result.items() if k!='test_history'},ensure_ascii=False,indent=2))
