from __future__ import annotations

import html
import json
import base64

from .motion_models import MotionTemplate, MotionTemplateInput


TEMPLATE_VERSION = "news-motion-v1"


def render_motion_html(spec: MotionTemplateInput, gsap_source: str) -> str:
    payload = base64.b64encode(json.dumps(spec.data, ensure_ascii=False).encode("utf-8")).decode("ascii")
    template = html.escape(spec.template.value)
    return f"""<!doctype html><html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width={spec.width},height={spec.height}"><style>
*{{box-sizing:border-box}}html,body{{margin:0;width:{spec.width}px;height:{spec.height}px;overflow:hidden;background:#071525;color:#f7fbff;font-family:Arial,sans-serif}}
#stage{{position:relative;width:100%;height:100%;padding:180px 72px 300px;display:flex;flex-direction:column;justify-content:center;background:radial-gradient(circle at 80% 15%,#173d68 0,#0b1d34 35%,#071525 78%)}}
#stage:before{{content:'';position:absolute;inset:0;background:linear-gradient(135deg,rgba(37,211,190,.11),transparent 48%,rgba(72,93,255,.12));pointer-events:none}}
.eyebrow{{font-size:34px;letter-spacing:7px;text-transform:uppercase;color:#63dfcb;font-weight:800;margin-bottom:28px}}h1{{font-size:112px;line-height:1.02;margin:0;letter-spacing:-3px;max-width:930px}}.sub{{font-size:48px;line-height:1.3;color:#a9bdd2;margin-top:36px}}
.accent{{color:#63dfcb}}.card{{background:rgba(12,35,59,.85);border:2px solid #244b69;border-radius:28px;padding:46px;box-shadow:0 24px 80px #0008}}
.stat{{font-size:220px;font-weight:900;color:#63dfcb;line-height:.9}}.bars{{display:flex;align-items:flex-end;gap:24px;height:650px;margin-top:50px}}.bar{{flex:1;background:linear-gradient(#63dfcb,#287b98);border-radius:14px 14px 0 0;min-height:20px;position:relative}}.bar span{{position:absolute;bottom:-70px;left:0;right:0;text-align:center;font-size:25px}}
.compare{{display:grid;grid-template-columns:1fr 1fr;gap:34px}}.compare .value{{font-size:92px;color:#63dfcb;font-weight:900}}.timeline{{border-left:6px solid #63dfcb;padding-left:44px;display:grid;gap:34px}}.item{{font-size:42px;position:relative}}.item:before{{content:'';position:absolute;width:24px;height:24px;border-radius:50%;background:#63dfcb;left:-59px;top:12px}}
.quote{{font-size:70px;line-height:1.25;font-weight:700}}.quote:before{{content:'“';font-size:180px;color:#63dfcb;line-height:0}}.source{{font-size:34px;color:#8ea8bf;margin-top:42px}}.outro{{text-align:center;align-items:center}}.rule{{height:6px;width:520px;background:linear-gradient(90deg,#63dfcb,#5865ff);margin:44px 0}}
</style><script>{gsap_source}</script></head><body><main id="stage" data-template="{template}"></main>
<script>const D=JSON.parse(new TextDecoder().decode(Uint8Array.from(atob('{payload}'),c=>c.charCodeAt(0))));const T={json.dumps(spec.template.value)};const stage=document.getElementById('stage');
const esc=s=>{{const e=document.createElement('span');e.textContent=String(s??'');return e.innerHTML}};
const list=(a,f)=>a.map(f).join('');
if(T==='hook')stage.innerHTML=`<div class="eyebrow">TIN NÓNG</div><h1>${{esc(D.headline)}}</h1><div class="sub">${{esc(D.subhead||'Cập nhật mới nhất')}}</div>`;
if(T==='headline')stage.innerHTML=`<div class="eyebrow">BẢN TIN</div><h1>${{esc(D.headline)}}</h1><div class="rule"></div><div class="sub">${{esc(D.subhead||'Thông tin đáng chú ý')}}</div>`;
if(T==='stat-hero')stage.innerHTML=`<div class="eyebrow">CON SỐ ĐÁNG CHÚ Ý</div><div class="stat">${{esc(D.value)}}</div><h1 style="font-size:62px">${{esc(D.label)}}</h1><div class="sub">${{esc(D.context||'')}}</div>`;
if(T==='chart'){{const values=D.data.map(x=>Number(x.value)||0),max=Math.max(...values,1);stage.innerHTML=`<div class="eyebrow">DỮ LIỆU</div><h1 style="font-size:64px">${{esc(D.title)}}</h1><div class="bars">${{list(D.data,(x,i)=>`<div class="bar" style="height:${{Math.max(8,(Number(x.value)||0)/max*100)}}%"><span>${{esc(x.label)}}</span></div>`)}}</div>`}}
if(T==='comparison')stage.innerHTML=`<div class="eyebrow">SO SÁNH</div><div class="compare"><div class="card"><div class="sub">${{esc(D.left.label)}}</div><div class="value">${{esc(D.left.value)}}</div></div><div class="card"><div class="sub">${{esc(D.right.label)}}</div><div class="value">${{esc(D.right.value)}}</div></div></div>`;
if(T==='timeline')stage.innerHTML=`<div class="eyebrow">DÒNG THỜI GIAN</div><div class="timeline">${{list(D.items,x=>`<div class="item"><b class="accent">${{esc(x.label||x.date)}}</b><br>${{esc(x.text)}}</div>`)}}</div>`;
if(T==='quote')stage.innerHTML=`<div class="quote">${{esc(D.quote)}}</div><div class="source">${{esc(D.author||D.source||'Nguồn bài viết')}}</div>`;
if(T==='outro'){{stage.classList.add('outro');stage.innerHTML=`<div class="eyebrow">SUPER VIDEO PRO</div><h1>${{esc(D.headline)}}</h1><div class="rule"></div><div class="sub">${{esc(D.source||'Theo dõi để xem thêm')}}</div>`}}
window.__newsvidPlay=()=>{{const tl=gsap.timeline();tl.from('#stage>*',{{opacity:0,y:80,duration:.65,stagger:.13,ease:'power3.out'}});if(T==='chart')tl.from('.bar',{{height:0,duration:1.1,stagger:.1,ease:'power2.out'}},.15);if(T==='timeline')tl.from('.item',{{x:-50,opacity:0,duration:.45,stagger:.16}},.1);if(T==='comparison')tl.from('.card',{{scale:.8,rotationY:12,duration:.7,stagger:.18}},.1);}};
</script></body></html>"""
