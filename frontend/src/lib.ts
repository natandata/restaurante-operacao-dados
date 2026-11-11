export type Lang='pt'|'en';
export function money(n:number,lang:Lang='pt'){return new Intl.NumberFormat(lang==='pt'?'pt-BR':'en-US',{style:'currency',currency:'BRL'}).format(n/100)}
export function sum(rows:Record<string,any>[],key:string){return rows.reduce((a,r)=>a+(Number(r[key])||0),0)}
export function eventCursor(current:number,events:{seq:number}[]){return events.reduce((m,e)=>Math.max(m,e.seq),current)}
export function dateLabel(value:string,lang:Lang){return new Intl.DateTimeFormat(lang==='pt'?'pt-BR':'en-US',{day:'2-digit',month:'short',timeZone:'UTC'}).format(new Date(value))}
export const LABELS:Record<string,[string,string]>={
 reservado:['Reservado','Reserved'],preparando:['Em preparo','Preparing'],concluido:['Concluído','Completed'],cancelado:['Cancelado','Cancelled'],pendente:['Pendente','Pending'],aprovado:['Aprovado','Approved'],salao:['Salão','Dine-in'],retirada:['Retirada','Pickup'],entrega:['Entrega','Delivery'],
};
export const statusLabel=(s:string,l:Lang)=>LABELS[s]?.[l==='pt'?0:1]??s;
