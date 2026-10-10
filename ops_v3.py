OPS_V3 = r"""<!doctype html>
<html lang="id"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>9Router — peta jaringan</title><meta name='theme-color' content='#090C11'>
<link href="https://fonts.googleapis.com/css2?family=Archivo:wght@400;600;800&family=DM+Mono:wght@400;500&family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0&display=swap" rel="stylesheet">
<style>
:root{--bg:#F5F4EF;--bg2:#ECEAE2;--panel:#fff;--ink:#14181F;--mute:#667085;--line:#E3E1D9;--ok:#0F8A55;--warn:#B26B00;--bad:#C2410C;--l1:#E4002B;--l2:#0072CE;--acc:#B8893B;--acc2:#E9C57A;--on-acc:#1b1405;--shadow:0 1px 2px rgba(20,24,31,.04),0 8px 24px -8px rgba(20,24,31,.12);--glass:rgba(245,244,239,.78);--grid:rgba(20,24,31,.07)}
@media(prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#090C11;--bg2:#0E131A;--panel:#111821;--ink:#EDF1F5;--mute:#8896A5;--line:#212B37;--ok:#3CCB8C;--warn:#F5B93D;--bad:#FF8A5B;--l1:#FF4D6A;--l2:#4DA3FF;--acc:#D9B26A;--acc2:#F3DCA6;--shadow:0 1px 0 rgba(255,255,255,.04) inset,0 12px 32px -10px rgba(0,0,0,.6);--glass:rgba(9,12,17,.75);--grid:rgba(255,255,255,.06)}}
:root[data-theme="dark"]{--bg:#090C11;--bg2:#0E131A;--panel:#111821;--ink:#EDF1F5;--mute:#8896A5;--line:#212B37;--ok:#3CCB8C;--warn:#F5B93D;--bad:#FF8A5B;--l1:#FF4D6A;--l2:#4DA3FF;--acc:#D9B26A;--acc2:#F3DCA6;--shadow:0 1px 0 rgba(255,255,255,.04) inset,0 12px 32px -10px rgba(0,0,0,.6);--glass:rgba(9,12,17,.75);--grid:rgba(255,255,255,.06)}
html{-webkit-text-size-adjust:100%}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);background-attachment:fixed;color:var(--ink);font:15px/1.55 Archivo,system-ui,sans-serif;-webkit-font-smoothing:antialiased;min-height:100vh}
button{font:inherit;color:inherit;cursor:pointer;transition:transform .15s,background .2s,border-color .2s}
button:active{transform:scale(.97)}
.top{position:sticky;top:0;z-index:20;display:flex;justify-content:space-between;align-items:center;gap:14px;flex-wrap:wrap;padding:14px clamp(16px,3vw,40px);background:var(--glass);backdrop-filter:saturate(1.4) blur(18px);-webkit-backdrop-filter:saturate(1.4) blur(18px);border-bottom:1px solid var(--line)}
.brand{display:flex;align-items:center;gap:12px}
.brand::before{content:"";width:34px;height:34px;border-radius:10px;background:linear-gradient(135deg,var(--acc2),var(--acc) 55%,#7a5a22);box-shadow:0 6px 16px -4px rgba(184,137,59,.6),inset 0 1px 0 rgba(255,255,255,.5)}
.brand b{font-size:22px;font-weight:800;letter-spacing:-.04em}
.brand span{color:var(--mute);font-size:12px;letter-spacing:.16em;text-transform:uppercase;font-weight:600;margin-left:2px;padding-left:12px;border-left:1px solid var(--line)}
.seg{display:flex;gap:2px;border:1px solid var(--line);border-radius:999px;background:var(--panel);padding:4px;overflow-x:auto;max-width:100%;scrollbar-width:none;box-shadow:var(--shadow)}
.seg::-webkit-scrollbar{display:none}
.seg button{flex:none;background:none;border:0;padding:7px 16px;border-radius:999px;font-weight:600;font-size:14px;color:var(--mute);min-height:38px}
.seg button[aria-current=true]{background:linear-gradient(135deg,var(--acc2),var(--acc));color:var(--on-acc);box-shadow:0 4px 14px -4px rgba(184,137,59,.7)}
main{padding:26px clamp(16px,3vw,40px) 56px;max-width:1220px;margin:auto}
section:not([hidden]){animation:in .45s cubic-bezier(.2,.7,.2,1)}
@keyframes in{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
.strip{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-bottom:22px}
.strip span{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:16px 20px;color:var(--mute);font-size:13px;box-shadow:var(--shadow);position:relative;overflow:hidden}
.strip span::after{content:"";position:absolute;inset:0 0 auto 0;height:2px;background:linear-gradient(90deg,var(--acc),transparent)}
.strip b{display:block;color:var(--ink);font-size:30px;font-weight:800;letter-spacing:-.04em;line-height:1.15}
.ann{border:1px solid var(--warn);background:linear-gradient(90deg,rgba(178,107,0,.12),var(--panel));padding:12px 16px;border-radius:14px;margin:0 0 18px;box-shadow:var(--shadow)}
.ann[hidden]{display:none}
.chips{display:flex;gap:8px;margin-bottom:14px;flex-wrap:wrap}
.chip{border:1px solid var(--line);background:var(--panel);border-radius:999px;padding:6px 16px;font-weight:600;font-size:14px;min-height:38px}
.chip::before{content:"";display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--c);margin-right:8px}
.chip[aria-pressed=true]{background:var(--c);color:#fff;border-color:var(--c)}
.chip[aria-pressed=true]::before{background:#fff}
.stage{display:grid;grid-template-columns:1fr 330px;gap:22px;align-items:start}
svg#mp{width:100%;height:auto;border:1px solid var(--line);border-radius:22px;display:block;box-shadow:var(--shadow);background:radial-gradient(circle at 1px 1px,var(--grid) 1px,transparent 0) 0 0/22px 22px,linear-gradient(160deg,var(--panel),var(--bg2))}
.sheet{background:var(--panel);border:1px solid var(--line);padding:22px;box-shadow:var(--shadow);border-radius:20px}
.sheet h2{margin:0;font-size:22px;letter-spacing:-.03em}
.sheet p{margin:4px 0 14px;color:var(--mute)}
.bar{height:8px;border-radius:5px;background:var(--line);margin:8px 0 16px;overflow:hidden}.bar i{display:block;height:100%;border-radius:5px;transition:width .5s}
.kv{display:flex;justify-content:space-between;gap:12px;padding:12px 0;border-top:1px solid var(--line);align-items:center}
.btn{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:9px 18px;min-height:42px;font-weight:600}
.btn.p{background:linear-gradient(135deg,var(--acc2),var(--acc));color:var(--on-acc);border-color:transparent}
.in{background:var(--bg);border:1px solid var(--line);border-radius:12px;padding:9px 14px;min-height:42px;color:var(--ink);font:inherit;min-width:0}
.ln{stroke-linecap:round;stroke-linejoin:round;fill:none;stroke-width:12;transition:opacity .25s}
.st{cursor:pointer}.st:hover circle:first-child{filter:brightness(1.1)}
.lbl{font:700 18px Archivo,sans-serif;fill:var(--ink);paint-order:stroke;stroke:var(--panel);stroke-width:5px;stroke-linejoin:round}.lb2{font:500 14px "DM Mono",monospace;fill:var(--mute)}
.board{background:linear-gradient(180deg,#14110a,#0b0b0b);border:1px solid #2c2515;color:#FFB000;font:13px/1 "DM Mono",monospace;padding:6px 0;max-height:66vh;overflow:auto;box-shadow:0 0 40px -18px #FFB000;border-radius:20px;text-shadow:0 0 8px rgba(255,176,0,.35)}
.board .r{display:grid;grid-template-columns:80px 1fr 100px 110px;gap:8px;padding:13px 18px;border-bottom:1px solid #251f10}
.board .h{color:#9b7a22;position:sticky;top:0;background:#14110a;letter-spacing:.14em;text-transform:uppercase;font-size:11px}
.board .x{color:#ff6b4a}.board .w{color:#fff}
.tick{display:grid;grid-template-columns:1fr auto;background:var(--panel);border:1px solid var(--line);margin-bottom:14px;max-width:660px;box-shadow:var(--shadow);border-radius:20px;overflow:hidden}
.tick .m{padding:16px 20px;min-width:0}.tick h3{margin:0 0 2px;font-size:18px}
.tick code{font:13px "DM Mono",monospace;color:var(--acc)}
.tick .act{position:relative;border-left:2px dashed var(--line);padding:14px 16px;display:flex;flex-direction:column;gap:8px;justify-content:center}
.row{display:flex;gap:10px;flex-wrap:wrap;align-items:center}
.code{font:13px "DM Mono",monospace;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:11px 14px;overflow-x:auto;flex:1;min-width:0;color:var(--acc)}
.toast{position:fixed;left:50%;transform:translateX(-50%);bottom:24px;background:var(--ink);color:var(--bg);padding:10px 20px;border-radius:999px;z-index:30;font-weight:600;box-shadow:0 12px 30px -8px rgba(0,0,0,.4)}
.toast[hidden]{display:none}
table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:12px 8px;border-bottom:1px solid var(--line)}tr:last-child td{border-bottom:0}th{color:var(--mute);font-weight:600;font-size:11px;letter-spacing:.12em;text-transform:uppercase}
.ust{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:16px 0}.ust div{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:16px;box-shadow:var(--shadow)}.ust b{display:block;font-size:26px;letter-spacing:-.04em}.ust span{color:var(--mute);font-size:13px}
.cgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:16px}
.termwrap{height:calc(100vh - 210px)}
.termwrap iframe{width:100%;height:100%;border:1px solid var(--line);border-radius:20px;background:#000}
.badge{font-size:11px;padding:3px 10px;border-radius:99px;border:1px solid var(--line);color:var(--mute)}
@media(max-width:820px){.strip{gap:8px}.strip span{padding:12px;font-size:11px}.strip b{font-size:22px}.ust{grid-template-columns:1fr 1fr}.stage{grid-template-columns:1fr}.brand span{display:none}.board .r{grid-template-columns:70px 1fr 90px}.board .r span:nth-child(3){display:none}.tick{grid-template-columns:1fr}.tick .act{border-left:0;border-top:2px dashed var(--line);flex-direction:row}.termwrap{height:calc(100vh - 240px)}}
</style></head><body>
<header class="top"><div class="brand"><b>9Router</b><span>Peta jaringan</span></div>
<div class='seg'><button data-v='pt' aria-current='true'>Peta</button><button data-v='pp'>Papan</button><button data-v='md'>Model</button><button data-v='us'>Pemakaian</button><button data-v='tk'>Tiket</button><button data-v='ct'>Tool CLI</button><button data-v='tm'>Terminal</button></div></header>
<main>
<p class="ann" id="an" hidden></p>
<div class="strip"><span><b id="k1">—</b>perjalanan kemarin</span><span><b id="k2">—</b>token terpakai</span><span><b id="k3">—</b>cache hemat</span></div>
<section id="pt"><div class="chips" id="ch"></div><div class="stage"><svg id="mp" viewBox="40 60 660 320" role="group" aria-label="Peta jaringan provider"></svg><aside class="sheet" id="sh"></aside></div></section>
<section id="pp" hidden><div class="board" id="bd"></div></section>
<section id="md" hidden><div class="sheet" style="overflow-x:auto"><h2>Per model (kemarin)</h2><table id="mt"><thead><tr><th>Model</th><th>Provider</th><th>Req</th><th>Prompt</th><th>Cached</th><th>Hit</th><th>Cost</th></tr></thead><tbody></tbody></table></div>
<div class="sheet" style="margin-top:16px"><h2>Cachewatch proxy</h2><table id="cw"><thead><tr><th>Model</th><th>Req</th><th>Prompt</th><th>Cached</th><th>Hit</th></tr></thead><tbody></tbody></table></div></section>
<section id="us" hidden><div class="ust"><div><b id="u1"></b><span>Perjalanan 7 hari</span></div><div><b id="u2"></b><span>Token</span></div><div><b id="u3"></b><span>Cached</span></div><div><b id="u4"></b><span>Biaya</span></div></div><div class="sheet" style="overflow-x:auto"><table id="ut"></table></div></section>
<section id="tk" hidden>
<p style="color:var(--mute);margin-top:0">Satu tiket untuk satu tool. Salin untuk dipakai.</p>
<div class="row" style="margin-bottom:18px;max-width:640px"><div class="code" id="eu">http://127.0.0.1:20130/v1</div><button class="btn" id="ec">Salin alamat</button></div>
<div id="kl"></div>
</section>
<section id="ct" hidden><p style='color:var(--mute);margin-top:0'>Salin konfigurasi ke tool yang kamu pakai. Endpoint via cachewatch.</p><div class='cgrid' id="cg"></div></section>
<section id="tm" hidden>
<div class="termwrap" style="display:flex;flex-direction:column;align-items:center;justify-content:center;gap:18px;text-align:center;padding:24px">
  <span class="material-symbols-outlined" style="font-size:56px;color:var(--gold)">terminal</span>
  <div>
    <h2 style="margin:0 0 6px">Terminal VPS</h2>
    <p style="color:var(--mute);margin:0;max-width:420px">Terminal dibuka di tab baru biar prompt login-nya muncul (Chrome Android kadang blok prompt di dalam iframe).</p>
  </div>
  <button class="btn" id="tmbtn" style="font-size:16px;padding:14px 28px">Buka Terminal ↗</button>
  <p style="color:var(--mute);font-size:12px;margin:0">Login: <b>admin</b> + password ttyd</p>
</div>
</section>
</main>
<div class="toast" id="ts" hidden></div>
<script>
const $=id=>document.getElementById(id);
function toast(m){const t=$('ts');t.textContent=m;t.hidden=false;clearTimeout(toast.h);toast.h=setTimeout(()=>t.hidden=true,1800)}
const copy=async s=>{try{await navigator.clipboard.writeText(s)}catch(e){}toast('Disalin')};
document.querySelectorAll('.seg button').forEach(b=>b.onclick=()=>{['pt','pp','md','us','tk','ct','tm'].forEach(k=>$(k).hidden=k!==b.dataset.v);document.querySelectorAll('.seg button').forEach(x=>x.setAttribute('aria-current',x===b))});
$('tmbtn').onclick=()=>window.open('/term/','_blank');
const base=location.pathname.replace(/\/(ops|home|v2|v3|map|panel|dashboard|live)\/?$/,'/');
async function jget(u){
  for(let i=0;i<3;i++){
    try{const r=await fetch(base+u,{cache:'no-store',headers:{'ngrok-skip-browser-warning':'1'}});const t=await r.text();if(t.trim().startsWith('{'))return JSON.parse(t);}catch(e){}
    await new Promise(r=>setTimeout(r,700));
  }
  throw new Error('offline');
}
function fmt(n){return n>=1e6?(n/1e6).toFixed(1).replace('.',',')+' jt':n>=1e3?(n/1e3).toFixed(1).replace('.',',')+' rb':String(n)}
function money(n){return '$'+n.toFixed(2)}
let A=null,sel=0;
function stationColor(p){
  if(p.error&&p.error.includes('429'))return 'var(--warn)';
  if(p.status==='active')return 'var(--ok)';
  if(p.status==='unavailable')return 'var(--bad)';
  return 'var(--mute)';
}
function statusLabel(p){
  if(p.error&&p.error.includes('429'))return 'KUOTA HABIS';
  if(p.status==='active')return 'SEHAT';
  if(p.status==='unavailable')return 'GANGGUAN';
  return 'IDLE';
}
function map(){
  const P=(A.providers||[]);
  const H=320, y0=110, gap=Math.min(120, 240/Math.max(P.length-1,1));
  let s='';
  // routes: hub -> each provider
  P.forEach((p,i)=>{
    const y=y0+i*gap;
    const col=p.active?stationColor(p):'var(--mute)';
    s+=`<path class="ln" d="M150 210 C 260 210, 300 ${y}, 430 ${y}" style="stroke:${col};opacity:${p.active?1:.25}"/>`;
    if(p.active)s+=`<circle r="7" fill="var(--panel)" stroke="${col}" stroke-width="5"><animateMotion dur="${6+i*2}s" repeatCount="indefinite" path="M150 210 C 260 210, 300 ${y}, 430 ${y}"/></circle>`;
  });
  s+=`<circle cx="110" cy="210" r="32" fill="var(--ink)"/><text x="110" y="217" text-anchor="middle" font-weight="800" font-size="18" fill="var(--bg)" font-family="Archivo">9R</text><text class="lb2" x="110" y="265" text-anchor="middle">Pusat</text>`;
  P.forEach((p,i)=>{
    const y=y0+i*gap, c=stationColor(p), dim=p.active?1:.45;
    s+=`<g class="st" data-i="${i}" style="opacity:${dim}"><circle cx="470" cy="${y}" r="20" fill="var(--panel)" stroke="${c}" stroke-width="6"/>`+
       (p.active?`<circle cx="470" cy="${y}" r="6" fill="${c}"/>`:`<path d="M465 ${y-5}l10 10m0-10l-10 10" stroke="var(--mute)" stroke-width="3"/>`)+
       `<text class="lbl" x="470" y="${y-32}" text-anchor="middle">${p.provider}</text><text class="lb2" x="470" y="${y+42}" text-anchor="middle">${statusLabel(p)}</text></g>`;
  });
  $('mp').innerHTML=s;
  $('ch').innerHTML=P.map((p,i)=>`<button class="chip" style="--c:${stationColor(p)}" onclick="sel=${i};sheet()">${p.provider} · ${p.name}</button>`).join('');
}
function sheet(){
  const P=(A.providers||[]), p=P[sel];if(!p)return;
  $('sh').innerHTML=`<h2>${p.provider}</h2><p>${p.name} · ${p.auth}</p>
  <div class="kv"><span>Status</span><b>${statusLabel(p)}</b></div>
  <div class="kv"><span>Prioritas</span><b>#${p.priority}</b></div>
  <div class="kv"><span>Aktif</span><b>${p.active?'Ya':'Tidak'}</b></div>
  ${p.error?`<div class="kv"><span>Error terakhir</span></div><p style="font:11px 'DM Mono',monospace;color:var(--bad);word-break:break-all">${p.error.slice(0,180)}</p>`:''}`;
}
function board(){
  const logs=(A.logs||[]).slice(0,30);
  $('bd').innerHTML='<div class="r h"><span>Waktu</span><span>Tujuan</span><span>Status</span><span>Biaya</span></div>'+
    logs.map(l=>{
      const st=l.status==='ok'?'BERANGKAT':'GAGAL';
      const cl=l.status==='ok'?'':'x';
      return `<div class="r"><span>${l.ts}</span><span>${l.provider} · ${l.model}</span><span class="${cl}">${st}</span><span>${money(l.cost)}</span></div>`;
    }).join('')||'<div class="r"><span>—</span><span>belum ada perjalanan</span><span></span><span></span></div>';
}
function render(){
  const s=A.summary;
  $('k1').textContent=fmt(s.requests);
  $('k2').textContent=fmt(s.tokens);
  $('k3').textContent=fmt(s.cached_tokens||s.cached||0);
  // announcement: provider with 429
  const bad=(A.providers||[]).find(p=>p.error&&p.error.includes('429'));
  const an=$('an');
  if(bad){an.hidden=false;an.innerHTML=`<b>Pengumuman.</b> Stasiun ${bad.provider} (${bad.name}) kuotanya habis — perjalanan dialihkan otomatis ke stasiun sehat.`}
  else an.hidden=true;
  map();sheet();board();
  const mtb=document.querySelector('#mt tbody');
  mtb.innerHTML=(A.models||[]).map(m=>`<tr><td>${m.model}</td><td>${m.provider}</td><td>${m.requests}</td><td>${fmt(m.prompt)}</td><td>${fmt(m.cached)}</td><td>${m.hit_pct}%</td><td>${money(m.cost||0)}</td></tr>`).join('')||'<tr><td colspan="7">belum ada data hari ini</td></tr>';
  document.querySelector('#cw tbody').innerHTML=(A.cw||[]).filter(m=>m.prompt>0).map(m=>`<tr><td>${m.model}</td><td>${m.requests}</td><td>${fmt(m.prompt)}</td><td>${fmt(m.cached)}</td><td>${m.hit_pct}%</td></tr>`).join('')||'<tr><td colspan="5">belum ada data</td></tr>';
  const days=A.days||[], totR=days.reduce((a,d)=>a+d.requests,0), totT=days.reduce((a,d)=>a+d.tokens,0), totC=days.reduce((a,d)=>a+d.cached,0), totM=days.reduce((a,d)=>a+d.cost,0);
  $('u1').textContent=fmt(totR);$('u2').textContent=fmt(totT);$('u3').textContent=fmt(totC);$('u4').textContent=money(totM);
  document.querySelector('#ut tbody').innerHTML=days.map(d=>`<tr><td>${d.date}</td><td>${d.requests}</td><td>${fmt(d.tokens)}</td><td>${fmt(d.cached)}</td><td>${money(d.cost)}</td></tr>`).join('');
  $('kl').innerHTML=(A.keys||[]).map(k=>`<div class="tick"><div class="m"><h3>${k.name}</h3><code>${k.key}</code><br><span style="color:var(--mute);font-size:13px">Berlaku untuk semua jalur · sejak ${k.created}</span></div><div class="act"><button class="btn" onclick="copy('${k.key}')">Salin</button></div></div>`).join('');
  const u='http://127.0.0.1:20130/v1';
  const k=(A.keys&&A.keys[0])?A.keys[0].key:'(lihat tab Tiket)';
  const T=[['Claude Code',`ANTHROPIC_BASE_URL=${u}\nANTHROPIC_AUTH_TOKEN=${k}`],['Codex',`OPENAI_BASE_URL=${u}/v1\nOPENAI_API_KEY=${k}`],['Cline',`Provider: OpenAI Compatible\nBase URL: ${u}/v1\nAPI key: ${k}`],['Hermes',`provider: custom\nbase_url: ${u}`]];
  $('cg').innerHTML=T.map((t,i)=>`<div class='sheet'><div class='row' style='justify-content:space-between'><h2 style='font-size:18px;margin:0'>${t[0]}</h2><button class='btn' onclick="copy(\`${t[1].replace(/`/g,'')}\`)">Salin</button></div><div class='code' style='margin-top:10px'><pre style='margin:0;font:inherit;white-space:pre-wrap'>${t[1]}</pre></div></div>`).join('');
}
async function tick(){
  try{
    A=await jget('data/all?'+Date.now());
    try{render()}catch(e){$('k1').textContent='render err';console.error(e)}
  }catch(e){$('k1').textContent='gagal ambil data';$('k2').textContent='—';$('k3').textContent='—'}
}
$('ec').onclick=()=>copy($('eu').textContent);
tick();setInterval(tick,10000);
</script></body></html>
"""
