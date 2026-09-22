// Program-owned observation and freshness guard. No clicks, navigation or input values.
(request => {
  const q=request.policy;
  if(location.origin!==q.origin) throw Error('origin_changed');
  const visible=e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return r.width>0&&r.height>0&&s.display!=='none'&&s.visibility!=='hidden'&&!e.closest('[aria-hidden="true"],[inert]');};
  const label=e=>(e.getAttribute('aria-label')||[...(e.labels||[])].map(x=>x.innerText).join(' ')||e.getAttribute('placeholder')||e.innerText||e.getAttribute('title')||'').trim().slice(0,300);
  const section=e=>{const p=e.closest('section,form,dialog,[role="dialog"],nav,main');return (p?.getAttribute('aria-label')||p?.querySelector('h1,h2,h3,legend')?.innerText||'').trim().slice(0,160);};
  const enabled=e=>!e.matches(':disabled,[aria-disabled="true"]')&&!e.readOnly;
  const reachable=e=>{const r=e.getBoundingClientRect(),x=r.x+r.width/2,y=r.y+r.height/2;return x>=0&&y>=0&&x<innerWidth&&y<innerHeight&&e.contains(document.elementFromPoint(x,y));};
  const signature=e=>JSON.stringify([location.href,e.tagName,label(e),section(e),e.getAttribute('href'),enabled(e),e.getAttribute('type')]);
  const store=window.__jevContextLocator ||= new Map();
  if(request.op==='guard') {
    const cached=store.get(request.token),entry=cached?.entries.get(request.id),e=entry?.node;
    if(!entry||cached.scope!==q.scope||cached.origin!==q.origin) return {ok:false,reason:'stale_observation'};
    const scope=document.querySelector(q.scope);
    if(!e.isConnected||!scope?.contains(e)||!visible(e)||!enabled(e)||!reachable(e)||signature(e)!==entry.signature) return {ok:false,reason:'target_changed'};
    const key=request.token+'-'+request.id;
    e.setAttribute('data-jev-locator',key);
    return {ok:true,selector:'[data-jev-locator="'+key+'"]',verified_at:Date.now(),dom_id:e.id||null};
  }
  if(request.op!=='observe') throw Error('unknown_operation');
  const scopes=document.querySelectorAll(q.scope),scope=scopes[0];
  if(scopes.length>1) return {records:[],truncated:false,scope_ambiguous:true,url:location.href};
  if(!scope) return {records:[],truncated:false,scope_missing:true,url:location.href};
  const token=crypto.randomUUID(),entries=new Map(),records=[];
  let truncated=false;
  const selector='button,a,input,textarea,select,[role="button"],[role="tab"],[role="menuitem"]';
  for(const e of [...(scope.matches(selector)?[scope]:[]),...scope.querySelectorAll(selector)]) {
    if(e.matches('input[type="password"],input[type="hidden"],input[type="file"]')||!visible(e)||!reachable(e)) continue;
    if(records.length>=q.limit){truncated=true;break;}
    const id=String(records.length+1);
    entries.set(id,{node:e,signature:signature(e)});
    records.push({id,text:label(e),role:e.getAttribute('role')||e.tagName.toLowerCase(),section:section(e),enabled:enabled(e),href:e.getAttribute('href'),dom_id:e.id||null});
  }
  store.set(token,{entries,scope:q.scope,origin:q.origin});
  while(store.size>8)store.delete(store.keys().next().value);
  return {records,token,url:location.href,truncated,scope_missing:false,observed_at:Date.now()};
})
