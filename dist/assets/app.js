const state={token:"",sessions:[],selected:null,timer:null};
const $=selector=>document.querySelector(selector);
const escapeHtml=value=>String(value??"").replace(/[&<>'"]/g,char=>({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[char]));
const format=value=>value?new Date(value).toLocaleString():"—";

async function api(path,options={}){
  const response=await fetch(path,{...options,cache:"no-store",headers:{Accept:"application/json","X-API-Key":state.token,...(options.headers||{})}});
  const payload=await response.json().catch(()=>({ok:false,error:{message:"Invalid server response"}}));
  if(!response.ok)throw new Error(payload.error?.message||`HTTP ${response.status}`);
  return payload.data;
}

function connection(ok,label){const node=$("#connection");node.className=`status ${ok?"online":"offline"}`;node.textContent=label;}
function rows(items,render,empty){return items.length?items.map(render).join(""):`<p class="empty">${empty}</p>`;}

function renderSession(session){
  state.selected=session;
  $("#session-title").textContent=session?session.label:"No session selected";
  $("#simulation").hidden=!session?.simulated;
  $("#metric-telemetry").textContent=session?.telemetry.length||0;
  $("#metric-events").textContent=session?.events.length||0;
  $("#metric-evidence").textContent=session?.evidence.length||0;
  $("#telemetry").innerHTML=rows(session?.telemetry||[],item=>`<div class="data-card"><strong>${escapeHtml(item.deviceId)}</strong><time>${format(item.timestamp)}</time>${Object.entries(item.metrics).map(([key,value])=>`<p><span>${escapeHtml(key)}</span><b>${escapeHtml(value)}</b></p>`).join("")}</div>`,"No telemetry received.");
  $("#events").innerHTML=rows([...(session?.events||[])].reverse(),item=>`<div class="row"><span class="event ${escapeHtml(item.status)}">${escapeHtml(item.status)}</span><div><strong>${escapeHtml(item.type)}</strong><p>${escapeHtml(item.message)}</p></div><time>${format(item.timestamp)}</time></div>`,"No events.");
  $("#evidence").innerHTML=rows([...(session?.evidence||[])].reverse(),item=>`<div class="row"><div><strong>${escapeHtml(item.name)}</strong><p>${escapeHtml(item.kind)} · ${Number(item.sizeBytes||0).toLocaleString()} bytes</p></div><time>${format(item.timestamp)}</time></div>`,"No evidence metadata.");
  document.querySelectorAll(".led").forEach(node=>node.classList.remove("active","error"));
  Object.entries(session?.leds||{}).forEach(([color,value])=>{const node=document.querySelector(`.led.${color}`);if(node)node.classList.add(value.state==="error"?"error":"active")});
}

async function load(){
  try{
    const listing=await api("/api/sessions");state.sessions=listing.sessions;$("#metric-sessions").textContent=state.sessions.length;
    const select=$("#session-select"),previous=select.value;select.innerHTML=state.sessions.length?state.sessions.map(item=>`<option value="${escapeHtml(item.id)}">${escapeHtml(item.label)}${item.simulated?" [simulated]":""}</option>`).join(""):"<option>No sessions</option>";
    if(previous&&state.sessions.some(item=>item.id===previous))select.value=previous;
    const id=state.sessions.length?select.value:null;renderSession(id?await api(`/api/sessions/${encodeURIComponent(id)}`):null);
    const audit=await api("/api/audit");$("#audit-list").innerHTML=rows(audit.audit,item=>`<div class="row"><div><strong>${escapeHtml(item.action)}</strong><p>${escapeHtml(item.detail)}</p></div><time>${format(item.timestamp)}</time></div>`,"No audit entries.");
    connection(true,"Live");
  }catch(error){connection(false,"Connection error");$("#auth-error").textContent=error.message;}
}

$("#auth-form").addEventListener("submit",async event=>{event.preventDefault();state.token=$("#token").value;try{await api("/api/sessions");$("#auth").hidden=true;$("#dashboard").hidden=false;await load();state.timer=setInterval(load,5000)}catch(error){$("#auth-error").textContent=error.message}});
$("#session-select").addEventListener("change",async event=>renderSession(await api(`/api/sessions/${encodeURIComponent(event.target.value)}`)));
$("#refresh").addEventListener("click",load);
