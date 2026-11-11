"""Painel histórico complementar à operação React, sem escrever no banco."""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import streamlit as st
from operacao.api import analytics
from operacao.settings import DATA
import pandas as pd

st.set_page_config(page_title='Restaurante fictício | data with natan',layout='wide')
st.markdown('''<style>.stApp{background:#fbfbfa;color:#161514}h1,h2,h3{letter-spacing:-.03em!important}div[data-testid="stMetric"]{background:white;border:1px solid #e9e8e4;padding:20px;border-radius:18px}.stButton button{border-radius:30px;color:#3f3cd8}a{color:#3f3cd8}</style>''',unsafe_allow_html=True)
lang=st.sidebar.radio('Idioma / Language',['PT','EN'],horizontal=True)
def t(pt,en): return pt if lang=='PT' else en
st.sidebar.markdown('## data with natan')
sections=[t('Visão diária','Daily overview'),t('Cardápio','Menu'),t('Canais','Channels'),t('Atendimento','Service'),t('Equipe','Team'),t('Estoque','Inventory'),t('Avaliações','Reviews'),t('Previsão','Forecast')]
page=st.sidebar.selectbox(t('Análise','Analysis'),sections)
st.caption(t('DADOS SINTÉTICOS · HISTÓRICO COMPLETO','SYNTHETIC DATA · COMPLETE HISTORY'))
st.title(page)
st.info(t('Dados históricos fictícios. O estado da operação ao vivo fica separado no app React. Valores em centavos nas tabelas brutas.','Fictional historical data. Live operations state is separate in the React app. Raw table money fields are in cents.'))
@st.cache_data(ttl=30)
def load(n):
    frame=pd.DataFrame(analytics(n))
    if 'day' in frame: frame['day']=pd.to_datetime(frame['day'])
    return frame
try:
    if page==sections[0]:
        frame=load('daily').sort_values('day'); frame['day']=pd.to_datetime(frame.day)
        bounds=st.date_input(t('Período','Period'),value=(frame.day.min().date(),frame.day.max().date()))
        if len(bounds)==2: frame=frame[(frame.day.dt.date>=bounds[0])&(frame.day.dt.date<=bounds[1])]
        a,b,c=st.columns(3); a.metric(t('Pedidos','Orders'),int(frame.orders.sum())); b.metric(t('Receita líquida (R$)','Net revenue (BRL)'),f'{frame.net_cents.sum()/100:,.2f}'); c.metric(t('Cancelados','Cancelled'),int(frame.cancelled.sum()))
        st.line_chart(frame.set_index('day')[['orders','completed','cancelled']])
        st.dataframe(frame,hide_index=True)
    elif page==sections[1]:
        frame=load('menu'); st.bar_chart(frame.set_index('name')['units']); st.dataframe(frame,hide_index=True)
        selected=st.selectbox(t('Produto para detalhar','Product detail'),frame.name)
        st.write(frame[frame.name==selected])
        st.caption(t('Margem antes de descontos/taxas; não é lucro líquido.','Margin before discounts/fees; not net profit.'))
    elif page==sections[2]:
        frame=load('channel'); chart=frame.set_index('channel')[['net_cents','contribution_cents']]/100; chart.columns=[t('Receita líquida (R$)','Net revenue (BRL)'),t('Contribuição (R$)','Contribution (BRL)')]; st.bar_chart(chart,stack=False); st.dataframe(frame,hide_index=True)
    elif page==sections[3]:
        frame=load('service'); weighted=frame.assign(total_minutes=frame.prep_minutes*frame.orders).groupby('day')[['total_minutes','orders']].sum(); st.line_chart((weighted.total_minutes/weighted.orders).rename(t('Preparo médio ponderado (min)','Weighted preparation time (min)'))); st.dataframe(frame,hide_index=True)
        st.caption(t('O gráfico pondera o preparo pela quantidade de pedidos em cada canal.','Chart weights preparation time by the number of orders in each channel.'))
    elif page==sections[4]:
        frame=load('labour'); st.line_chart(frame.set_index('day')['orders_per_hour']); st.dataframe(frame,hide_index=True)
        st.caption(t('Produtividade sintética; não avalia pessoas reais.','Synthetic productivity; does not assess real employees.'))
    elif page==sections[5]:
        frame=load('inventory'); st.dataframe(frame,hide_index=True)
        for unit,group in frame.groupby('unit'):
            st.subheader(t('Unidade: ','Unit: ')+unit); st.bar_chart(group.set_index('name')[['closing','waste']],stack=False)
        st.caption(t('Saldo no fim do dataset. Ingredientes podem ter unidades diferentes; não somar entre eles.','Closing stock at dataset end. Ingredient units may differ; do not sum across ingredients.'))
    elif page==sections[6]:
        frame=load('experience'); weighted=frame.assign(total_rating=frame.rating*frame.reviews).groupby('day')[['total_rating','reviews']].sum(); st.line_chart((weighted.total_rating/weighted.reviews).rename(t('Nota média ponderada (1–5)','Weighted average rating (1–5)'))); st.dataframe(frame,hide_index=True)
        st.caption(t('Notas geradas por regras, não avaliações reais.','Rule-generated ratings, not real reviews.'))
    else:
        f=json.loads((DATA/'forecast.json').read_text())
        st.metric(t('Modelo escolhido na validação','Model selected on validation'),f['selected'])
        st.dataframe([{'model':m['model'],'validation_mae':m['validation']['mae'],'test_mae':m['test']['mae'],'test_rmse':m['test']['rmse'],'test_wape':m['test']['wape']} for m in f['comparison']],hide_index=True)
        history=pd.DataFrame(f['test_history']); history['day']=pd.to_datetime(history['day']); st.line_chart(history.set_index('day')[['actual','predicted']])
        st.dataframe(f['future'],hide_index=True)
        st.warning(t('Sem intervalo calibrado. Resultado sintético não comprova desempenho real. Datas são futuras em relação ao dataset, não a hoje.','No calibrated interval. Synthetic results do not prove real performance. Dates are future relative to the dataset, not today.'))
except Exception as error:
    st.error(t('Dados ainda não preparados ou falha ao ler o warehouse. Veja a preparação no README.','Data not prepared or warehouse read failed. See preparation in README.'))
    st.code(str(error))
st.caption(t('Demonstração local de estudo com assistência de IA. Não expor à internet.','Local AI-assisted learning demonstration. Do not expose to the internet.'))
