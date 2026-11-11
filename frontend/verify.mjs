import { chromium } from '@playwright/test';
import {spawn} from 'node:child_process';
import fs from 'node:fs';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const root=fileURLToPath(new URL('..',import.meta.url)).replace(/[\\/]$/,'');
const python=process.env.PYTHON_BIN || path.join(root,'.venv',process.platform==='win32'?'Scripts/python.exe':'bin/python');
const processes=[];
function start(cmd,args,cwd){let p=spawn(cmd,args,{cwd,stdio:['ignore','pipe','pipe'],env:{...process.env,PYTHONUNBUFFERED:'1'}});processes.push(p);return p;}
async function wait(url){for(let i=0;i<100;i++){try{const r=await fetch(url);if(r.ok)return;}catch{}await new Promise(r=>setTimeout(r,200));}throw Error('Server unavailable '+url)}
let browser;
try{
 start(python,['-m','uvicorn','operacao.api:app','--host','127.0.0.1','--port','8000'],root);
 start('node',['node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','5173'],root+'/frontend');
 await Promise.all([wait('http://127.0.0.1:8000/api/health'),wait('http://127.0.0.1:5173')]);
 browser=await chromium.launch({...(process.env.CHROME_BIN?{executablePath:process.env.CHROME_BIN}:{}),headless:true});
 const page=await browser.newPage({viewport:{width:1280,height:900}});
 page.setDefaultTimeout(10000);
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:5173');await page.getByText('Conexão ativa',{exact:true}).waitFor();
 if(!process.env.SCREEN_ONLY){await page.getByRole('button',{name:'Reservar pedido'}).click();await page.getByText('Pedido reservado.',{exact:true}).waitFor();
 await page.getByRole('button',{name:'Preparar',exact:true}).first().click();await page.getByRole('button',{name:'Concluir',exact:true}).first().click();
 await page.getByRole('button',{name:'Abastecer'}).click();await page.getByRole('button',{name:'Registrar para conferência'}).click();await page.getByText('Recebimento pendente de aprovação.',{exact:true}).waitFor();
 page.once('dialog',d=>d.accept());await page.getByRole('button',{name:'Aprovar entrada'}).first().click();await page.getByText('Estoque atualizado uma vez.',{exact:true}).waitFor();
 await page.getByRole('button',{name:'Hoje',exact:false}).click();await page.getByRole('button',{name:'Iniciar simulação'}).click();await page.getByRole('button',{name:'Pausar simulação'}).waitFor();await new Promise(r=>setTimeout(r,3400));await page.getByRole('button',{name:'Pausar simulação'}).click();
 }
 fs.mkdirSync(root+'/docs/screenshots',{recursive:true});
 const labels=[['Hoje','Today'],['Investigar','Explore'],['Abastecer','Stock'],['Planejar','Plan'],['Conferir dados','Data checks'],['Sobre','About']];
 const overflow=[];
 for(const lang of (process.env.LANG_CAPTURE?[process.env.LANG_CAPTURE]:['pt','en'])){
  if(lang==='en')await page.getByRole('button',{name:'Switch language'}).click();
  for(const width of [1280,390,320]){
   await page.setViewportSize({width,height:900});
   for(let i=0;i<labels.length;i++){
    await page.locator('nav button').nth(i).click();
    if(i===1)await page.getByText(lang==='pt'?'Ritmo dos pedidos':'Order rhythm',{exact:true}).waitFor();
    if(i===3)await page.getByText(lang==='pt'?'Comparação de modelos':'Model comparison',{exact:true}).waitFor();
    if(i===1)await page.getByText('30826',{exact:true}).waitFor();
    if(i===4)await page.getByText('365',{exact:true}).waitFor();
    await page.evaluate(()=>{window.scrollTo(0,0);return document.fonts.ready});await page.screenshot({path:root+`/docs/screenshots/${lang}-${i}-${width}.png`,fullPage:true});
    const size=await page.evaluate(()=>({body:document.body.scrollWidth,viewport:innerWidth}));if(size.body>width)overflow.push({lang,i,width,size});
   }
  }
 }
 if(errors.length||overflow.length)throw Error(JSON.stringify({errors,overflow}));
 console.log(`${process.env.SCREEN_ONLY?'Read-only UI capture':'UI action flows passed'}; ${process.env.LANG_CAPTURE?18:36} responsive screenshots; no JS errors or body overflow.`);
 if(process.env.LANG_CAPTURE==='pt')await page.getByRole('button',{name:'Switch language'}).click();
 // Filtering and reset
 await page.setViewportSize({width:1280,height:900});await page.locator('nav button').nth(1).click();
 await page.getByLabel('From',{exact:true}).fill('2025-12-31');await page.getByLabel('To',{exact:true}).fill('2025-01-01');
 await page.getByText('No data in selected range',{exact:true}).waitFor();await page.getByRole('button',{name:'Reset',exact:true}).click();
 if(await page.getByLabel('From',{exact:true}).inputValue()!=='')throw Error('Filter reset failed');
 // Independent Streamlit surface
 start(python,['-m','streamlit','run','app/Home.py','--server.headless','true','--server.address','127.0.0.1','--server.port','8501','--browser.gatherUsageStats','false'],root);
 await wait('http://127.0.0.1:8501');await page.goto('http://127.0.0.1:8501');await page.getByRole('heading',{name:'Visão diária',exact:true}).waitFor();await page.locator('[data-testid=stMetric]').first().waitFor();await page.locator('[data-testid=stDataFrame]').first().waitFor();await page.waitForTimeout(1500);
 await page.screenshot({path:root+'/docs/screenshots/streamlit-1280.png',fullPage:true});
 for(let i=1;i<8;i++){await page.getByRole('combobox').first().click();await page.getByRole('option').nth(i).click();await page.locator('[data-testid=stDataFrame]').first().waitFor();await page.waitForTimeout(1200);if(await page.locator('[data-testid=stException]').count())throw Error('Streamlit exception in view '+i);await page.screenshot({path:root+`/docs/screenshots/streamlit-${i}-1280.png`,fullPage:true});}
 console.log('All eight Streamlit views loaded and screenshots captured.');
}finally{if(browser)await browser.close();await Promise.all(processes.map(p=>new Promise(resolve=>{p.once('exit',resolve);p.kill('SIGTERM');setTimeout(()=>{if(p.exitCode===null)p.kill('SIGKILL')},2000).unref()})));}
