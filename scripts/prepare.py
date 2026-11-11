"""Preparação local reproduzível sem sobrescrever arquivos gerados existentes."""
import json
import subprocess
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from operacao.settings import RAW, ROOT
from operacao.synthetic import generate
from operacao.ingestion import load_batch
from operacao.forecast import run_forecast
if __name__=='__main__':
    if not (RAW/'manifest.json').exists(): print(generate())
    else: print('Dados existentes preservados:', RAW)
    print(load_batch())
    executable=Path(sys.executable).parent/'dbt'
    subprocess.run([str(executable),'build','--project-dir',str(ROOT/'warehouse'),'--profiles-dir',str(ROOT/'warehouse')],cwd=ROOT,check=True)
    f=run_forecast(); print('Previsão concluída:',f['selected'])
