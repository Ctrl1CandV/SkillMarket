// Static and mock-DOM checks only. This does not render a browser or prove accessibility.
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
const dir=path.dirname(fileURLToPath(import.meta.url));
class Element {
  constructor(){this.value='';this.hidden=false;this.children=[];this.attrs={};this.handlers={};this.textContent='';this.disabled=false;}
  append(...items){this.children.push(...items)}
  replaceChildren(...items){this.children=items}
  setAttribute(k,v){this.attrs[k]=v}
  getAttribute(k){return this.attrs[k]??null}
  addEventListener(k,f){this.handlers[k]=f}
  focus(){this.focused=true}
  async fire(k){return this.handlers[k]?.({currentTarget:this})}
}
let checks=0;
function ok(test){assert.ok(test);checks++}
function load(name){
  const html=fs.readFileSync(path.join(dir,name),'utf8');
  const ids=[...html.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]);ok(ids.length===new Set(ids).size);
  for(const m of html.matchAll(/href="#([^"]+)"/g))ok(ids.includes(m[1]));
  for(const m of html.matchAll(/(?:href|src)="([^"#:]+\.html)"/g))ok(fs.existsSync(path.join(dir,m[1])));
  ok(html.includes('name="viewport"'));ok(html.includes('lang="zh-CN"'));ok(!/<(?:script|link)[^>]+(?:src|href)="https?:/i.test(html));
  const elements=Object.fromEntries(ids.map(id=>[id,new Element()]));
  const document={getElementById:id=>elements[id],createElement:()=>new Element()};
  const context=vm.createContext({document,setTimeout});
  for(const m of html.matchAll(/<script>([\s\S]*?)<\/script>/g)){new vm.Script(m[1]); if(name==='workbench.html')elements.scope.value='all';if(name==='reading.html'){elements.reveal.setAttribute('aria-expanded','false');elements.answer.hidden=true}vm.runInContext(m[1],context)}
  return {elements,hash:crypto.createHash('sha256').update(html).digest('hex')};
}
const work=load('workbench.html'),w=work.elements;
ok(w.list.children.length===3);w.query.value='ReAct';await w.query.fire('input');ok(w.list.children.length===1);
w.query.value='完全无匹配';await w.query.fire('input');ok(w.list.children.length===0&&!w.empty.hidden);
await w.clear.fire('click');ok(w.list.children.length===3&&w.query.value==='');
w.scope.value='entry';await w.scope.fire('change');ok(w.list.children.length===2);
await w.fail.fire('click');ok(!w.error.hidden&&w.empty.hidden&&w.list.children.length===0);
const retry=w.retry.fire('click');ok(w.retry.disabled&&w.list.getAttribute('aria-busy')==='true');await retry;
ok(w.error.hidden&&w.list.children.length===2&&w.scope.value==='entry'&&!w.retry.disabled&&w.list.getAttribute('aria-busy')==='false');
const reading=load('reading.html'),r=reading.elements;
await r.reveal.fire('click');ok(!r.answer.hidden&&r.reveal.getAttribute('aria-expanded')==='true');await r.reveal.fire('click');ok(r.answer.hidden&&r.reveal.getAttribute('aria-expanded')==='false');
const root=path.resolve(dir,'../../../frontend-craft');
for(const file of [path.join(root,'SKILL.md'),...fs.readdirSync(path.join(root,'references')).map(n=>path.join(root,'references',n))]){
 const md=fs.readFileSync(file,'utf8');for(const m of md.matchAll(/\]\(([^)]+)\)/g)){if(!/^https?:/.test(m[1]))ok(fs.existsSync(path.resolve(path.dirname(file),m[1])))}
}
JSON.parse(fs.readFileSync(path.join(dir,'cases.json'),'utf8'));checks++;
console.log(JSON.stringify({kind:'static-and-mock-DOM-only',checks,status:'passed',hashes:{'workbench.html':work.hash,'reading.html':reading.hash},notTested:['browser rendering','real interactions','screenshots','responsive geometry','keyboard accessibility','screen reader','performance']},null,2));
