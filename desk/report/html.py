"""Render a check result as one self-contained HTML page (no network needed)."""
from __future__ import annotations

import html
import json
from pathlib import Path

TEMPLATE = r"""<!doctype html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
:root{--bg:#fbfaf7;--fg:#1d1b18;--muted:#6b665d;--rule:#ddd8ce;--panel:#ffffff;
--flag:#b3261e;--border:#b26a00;--note:#2f5d9e;--unver:#6a4c93;--watch:#1f7a6d;--ok:#4a7a2a;
--dlg:#f1ece0;--int:#eef1f6;--code:#f3f0ea}
@media (prefers-color-scheme: dark){:root:not([data-theme=light]){--bg:#161513;--fg:#ece8e1;--muted:#a59f94;
--rule:#38352f;--panel:#1f1d1a;--flag:#ff8a80;--border:#ffb74d;--note:#90b4ff;--unver:#c9a7ff;--watch:#6fd6c4;
--ok:#9ccc65;--dlg:#26231e;--int:#1e222a;--code:#2a2722}}
:root[data-theme=dark]{--bg:#161513;--fg:#ece8e1;--muted:#a59f94;--rule:#38352f;--panel:#1f1d1a;--flag:#ff8a80;
--border:#ffb74d;--note:#90b4ff;--unver:#c9a7ff;--watch:#6fd6c4;--ok:#9ccc65;--dlg:#26231e;--int:#1e222a;--code:#2a2722}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 Georgia,"Iowan Old Style",serif}
header,main{max-width:1180px;margin:0 auto;padding:0 16px}
header{padding-top:24px}
h1{font-size:1.5rem;margin:.2em 0}
h2{font-size:1.15rem;margin:1.6em 0 .4em;border-bottom:1px solid var(--rule);padding-bottom:.2em}
h3{font-size:1rem;margin:1.2em 0 .3em}
.caveat{border-left:4px solid var(--border);padding:.5em .8em;background:var(--panel)}
.meta{color:var(--muted);font-size:.9rem}
nav{position:sticky;top:0;background:var(--bg);border-bottom:1px solid var(--rule);z-index:5}
nav div{max-width:1180px;margin:0 auto;padding:6px 16px;display:flex;gap:14px;flex-wrap:wrap;font-size:.9rem}
nav a{color:var(--fg)}
table{border-collapse:collapse;width:100%;font-size:.92rem}
th,td{border-bottom:1px solid var(--rule);padding:4px 6px;text-align:left;vertical-align:top}
th{font-weight:600}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums}
.badge{display:inline-block;font:600 .72rem/1.6 system-ui,sans-serif;padding:0 .45em;border-radius:3px;
color:#fff;letter-spacing:.02em;white-space:nowrap}
.b-FLAG{background:var(--flag)}.b-BORDERLINE{background:var(--border)}.b-NOTE{background:var(--note)}
.b-UNVERIFIED{background:var(--unver)}.b-WATCH{background:var(--watch)}.b-OK{background:var(--ok)}
.tag{display:inline-block;font:500 .72rem/1.6 system-ui,sans-serif;padding:0 .4em;border:1px solid var(--muted);
border-radius:3px;color:var(--muted);white-space:nowrap}
.item{cursor:pointer}
.item:hover td{background:var(--code)}
.text p{margin:.5em 0;max-width:46em}
.text p .pn{color:var(--muted);font:.75rem system-ui,sans-serif;margin-right:.5em;user-select:none}
.text p.h{font-weight:700}
.st-dialogue{background:var(--dlg)}
.st-interior{background:var(--int);font-style:italic}
.hl{cursor:pointer;text-decoration-thickness:2px;text-underline-offset:3px}
.s-FLAG{text-decoration:underline solid var(--flag);color:var(--flag)}
.s-UNVERIFIED{text-decoration:underline dotted var(--unver);color:var(--unver)}
.s-BORDERLINE{text-decoration:underline dashed var(--border)}
.s-NOTE{text-decoration:underline dotted var(--note)}
.s-WATCH{text-decoration:underline wavy var(--watch)}
.legend span{margin-right:1em}
#panel{position:fixed;right:0;top:0;bottom:0;width:min(460px,100%);background:var(--panel);
border-left:1px solid var(--rule);padding:14px 16px 40px;overflow:auto;transform:translateX(105%);
transition:transform .15s;z-index:10;font-size:.92rem;box-shadow:-4px 0 18px rgba(0,0,0,.08)}
#panel.open{transform:none}
#panel .x{float:right;cursor:pointer;border:1px solid var(--rule);background:none;color:var(--fg);
border-radius:3px;padding:0 .5em}
.kwic{font:.85rem/1.45 "Iowan Old Style",Georgia,serif;background:var(--code);padding:.4em .55em;margin:.35em 0;
border-radius:3px}
.kwic b{color:var(--flag)}
.kwic .src{display:block;color:var(--muted);font:.72rem system-ui,sans-serif;margin-top:.2em}
.hist{display:flex;align-items:flex-end;gap:2px;height:46px;margin:.4em 0 1.2em}
.hist div{background:var(--note);width:9px;position:relative}
.hist div.before{background:var(--ok)}
.hist div span{position:absolute;bottom:-1.25em;left:-4px;font:9px system-ui;color:var(--muted)}
.small{font-size:.82rem;color:var(--muted)}
.wl{border-left:3px solid var(--watch);padding-left:.6em;margin:.5em 0}
@media (max-width:700px){body{font-size:15px}td,th{padding:3px 4px}}
</style>
</head>
<body>
<header>
<h1>Period-language check: __FILE__</h1>
<p class="meta" id="settings"></p>
<p class="caveat" id="caveat"></p>
<p class="meta" id="corpus"></p>
</header>
<nav><div><a href="#summary">Summary</a><a href="#s-narration">Narration</a><a href="#s-dialogue">Dialogue</a>
<a href="#s-interior">Interior</a><a href="#other">Interjections, punctuation, phrases</a>
<a href="#romani">Romani and cant</a><a href="#latinate">Latin/French share</a><a href="#text">Text</a></div></nav>
<main>
<section id="summary"><h2>Summary</h2><div id="sumtable"></div>
<p class="legend small"><span><span class="badge b-FLAG">FLAG</span> first printed after the window</span>
<span><span class="badge b-BORDERLINE">BORDERLINE</span> first printed in the year or the window after</span>
<span><span class="badge b-NOTE">NOTE</span> printed before the year, thinly</span>
<span><span class="badge b-UNVERIFIED">UNVERIFIED</span> not in the corpus</span>
<span><span class="badge b-WATCH">WATCH</span> watch-list entry</span></p>
<p class="small">Evidence tags: <b>DOCUMENTED</b> rests on a cited dated text or source;
<b>REASONABLE INFERENCE</b> is drawn from evidence that does not state it directly (a spelling variant,
a lemma, a statistical test); <b>CONTESTED</b> means the evidence conflicts (an earlier conjecturally
dated text, or corpus against watch list); <b>UNVERIFIED</b> means no evidence either way.</p>
</section>
<section id="streams"></section>
<section id="other"><h2>Interjections, punctuation and phrases</h2><div id="othertable"></div></section>
<section id="romani"><h2>Romani and cant</h2>
<p class="small">Every token not resolved as English (not in the period corpus as English, and not a
Wiktionary English headword), and every watch-list Romani or cant entry. The desk does not adjudicate
Romani words.</p><div id="romanitable"></div></section>
<section id="latinate"><h2>Latin/French share by paragraph</h2><p class="small" id="latlabel"></p>
<div id="lattable"></div></section>
<section id="text"><h2>Text</h2>
<p class="small">Shading: <span class="st-dialogue">dialogue</span>, <span class="st-interior">interior thought</span>,
plain = narration. Click a marked word for its evidence.</p><div class="text" id="textbody"></div></section>
</main>
<aside id="panel" aria-live="polite"><button class="x" onclick="closePanel()" aria-label="Close">×</button><div id="pbody"></div></aside>
<script id="data" type="application/json">__DATA__</script>
<script>
const R = JSON.parse(document.getElementById('data').textContent);
const S = R.settings, Y = S.year;
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const fmt = n => (n ?? 0).toLocaleString('en-GB');
const badge = s => `<span class="badge b-${s}">${s}</span>`;
const tag = t => `<span class="tag">${esc(t)}</span>`;
const STREAMS = ['narration','dialogue','interior'];
const ORDER = {FLAG:0,UNVERIFIED:1,BORDERLINE:2,NOTE:3,WATCH:4,OK:5};
document.getElementById('settings').textContent =
  `Setting year ${Y} · borderline window ${S.window} years · NOTE below ${S.note_min} texts · ` +
  `watch list ${S.watchlist ? 'on' : 'off'} · dialogue quotes: ${S.quote_style} · generated ${R.generated}`;
document.getElementById('caveat').textContent = R.caveat;
const C = R.corpus;
document.getElementById('corpus').textContent =
  `Corpus: EEBO-TCP Phases I and II and ECCO-TCP, EarlyPrint regularised edition. About ${fmt(C.texts_before)} texts ` +
  `(${fmt(C.words_before)} words) printed before ${Y}; ${fmt(C.texts_total)} texts (${fmt(C.words_total)} words) in all. ` +
  `Index built ${C.built}; ${C.holdout} texts held out for testing.`;

function firstDate(ev, it){
  if(!ev) return '';
  if(it && it.type==='watch' && (ev.first_firm||ev.first_any)) return '<span class="small">form: </span>' + firstDate(ev);
  const f = ev.first_firm, a = ev.first_any;
  let s = f ? `${f.year} (${esc(f.tcp)})` : '';
  if(a && (!f || a.year < f.year)) s += `${s?'; ':''}<span class="small">${a.year}? ${esc(a.tcp)} — ${esc(a.date_kind)}</span>`;
  return s;
}
// ---------- summary
(function(){
  const t = R.summary.occurrences, ty = R.summary.types;
  let h = '<table><thead><tr><th>Status</th>' + STREAMS.map(s=>`<th class="n">${s}</th>`).join('') +
          '<th class="n">all</th></tr></thead><tbody>';
  for(const st of ['FLAG','BORDERLINE','NOTE','UNVERIFIED','WATCH']){
    const row = t[st]; let tot=0;
    h += `<tr><td>${badge(st)}</td>` + STREAMS.map(s=>{tot+=row[s]; return `<td class="n">${row[s]} <span class="small">(${ty[st][s]})</span></td>`}).join('') +
         `<td class="n"><b>${tot}</b></td></tr>`;
  }
  const w = R.streams_words;
  h += `<tr><td class="small">words in stream</td>` + STREAMS.map(s=>`<td class="n small">${fmt(w[s])}</td>`).join('') +
       `<td class="n small">${fmt(STREAMS.reduce((a,s)=>a+w[s],0))}</td></tr></tbody></table>` +
       `<p class="small">Occurrences, with distinct items in brackets.</p>` +
       (Object.keys(R.accepted||{}).length ? `<p class="small">Accepted by you in the watch list, not flagged: ${Object.entries(R.accepted).map(([k,n])=>esc(k)+(n>1?' ×'+n:'')).join(', ')}.</p>` : '');
  document.getElementById('sumtable').innerHTML = h;
})();
// ---------- per-stream lists
(function(){
  const items = Object.values(R.items);
  let h = '';
  for(const st of STREAMS){
    const rows = items.filter(it => (it.type==='word'||it.type==='watch') && it.occurrences.some(o=>o.stream===st))
                      .sort((a,b)=>(ORDER[a.status]-ORDER[b.status])||a.text.localeCompare(b.text));
    h += `<h2 id="s-${st}">${st[0].toUpperCase()+st.slice(1)} <span class="small">(${rows.length} items)</span></h2>`;
    if(!rows.length){ h += '<p class="small">Nothing to report.</p>'; continue; }
    h += '<table><thead><tr><th>Status</th><th>Word</th><th>Tag</th><th>Earliest firm-dated print</th><th class="n">here</th><th>Basis / reason</th></tr></thead><tbody>';
    for(const it of rows){
      const n = it.occurrences.filter(o=>o.stream===st).length;
      h += `<tr class="item" onclick="openItem('${esc(it.id)}')"><td>${badge(it.status)}</td><td>${esc(it.text)}</td>` +
           `<td>${tag(it.tag)}</td><td>${firstDate(it.evidence, it)}</td><td class="n">${n}</td>` +
           `<td class="small">${esc(it.reason)}${it.evidence && it.evidence.note ? ' — '+esc(it.evidence.note):''}</td></tr>`;
    }
    h += '</tbody></table>';
  }
  document.getElementById('streams').innerHTML = h;
  const other = items.filter(it => it.type==='interjection'||it.type==='punct'||it.type==='phrase');
  let o = '';
  if(!other.length) o = '<p class="small">Nothing to report.</p>';
  else {
    o = '<table><thead><tr><th>Status</th><th>Kind</th><th>Text</th><th>Tag</th><th>Earliest firm-dated print</th><th>Streams</th><th>Reason</th></tr></thead><tbody>';
    for(const it of other.sort((a,b)=>ORDER[a.status]-ORDER[b.status])){
      const sts = [...new Set(it.occurrences.map(x=>x.stream))].join(', ');
      o += `<tr class="item" onclick="openItem('${esc(it.id)}')"><td>${badge(it.status)}</td><td>${it.type}</td>` +
           `<td>${esc(it.text)}</td><td>${tag(it.tag)}</td><td>${firstDate(it.evidence)}</td><td>${sts}</td>` +
           `<td class="small">${esc(it.reason)}${it.evidence && it.evidence.note ? ' — '+esc(it.evidence.note):''}</td></tr>`;
    }
    o += '</tbody></table>';
  }
  document.getElementById('othertable').innerHTML = o;
})();
// ---------- romani
(function(){
  const rows = R.romani;
  if(!rows.length){ document.getElementById('romanitable').innerHTML = '<p class="small">No such tokens.</p>'; return; }
  let h = '<table><thead><tr><th>Token</th><th class="n">n</th><th>Paragraphs</th><th>Streams</th><th>Watch list</th><th>Corpus</th></tr></thead><tbody>';
  for(const r of rows){
    const wl = r.watch ? `${esc(r.watch.reason)} ${tag(r.watch.tag)}` : '<i>unplaced — for the consultant</i>';
    h += `<tr><td>${esc(r.token)}</td><td class="n">${r.count}</td><td>${r.paragraphs.join(', ')}</td>` +
         `<td>${r.streams.join(', ')}</td><td>${wl}</td><td class="small">${esc(r.corpus||'')}</td></tr>`;
  }
  document.getElementById('romanitable').innerHTML = h + '</tbody></table>';
})();
// ---------- latinate
(function(){
  const L = R.latinate;
  document.getElementById('latlabel').textContent = L.label + (L.baseline ? ` Compared with Henry's own passages in ${L.baseline.file} (${L.baseline.paragraphs} paragraphs, mean ${(L.baseline.mean*100).toFixed(0)}%).` : ' No samples/baseline.md, so no comparison is made.');
  let h = '<table><thead><tr><th class="n">¶</th><th class="n">content words</th><th class="n">classified</th><th class="n">Latin/French</th><th class="n">share</th>' + (L.baseline?'<th class="n">vs baseline</th>':'') + '</tr></thead><tbody>';
  for(const p of R.paragraphs){
    const l = p.latinate;
    h += `<tr><td class="n"><a href="#p${p.i}">${p.i+1}</a></td><td class="n">${l.content_words}</td><td class="n">${l.classified}</td>` +
         `<td class="n">${l.latin_french}</td><td class="n">${l.share==null?'—':(l.share*100).toFixed(0)+'%'}</td>` +
         (L.baseline?`<td class="n">${l.vs_baseline==null?'—':(l.vs_baseline>0?'+':'')+(l.vs_baseline*100).toFixed(0)+' pts'}${l.z!=null?' <span class="small">(z '+l.z+')</span>':''}</td>`:'') + '</tr>';
  }
  document.getElementById('lattable').innerHTML = h + '</tbody></table><p class="small">Share shown only where at least 5 content words are classified.</p>';
})();
// ---------- text
(function(){
  let h = '';
  for(const p of R.paragraphs){
    const T = p.text, cuts = new Set([0, T.length]);
    p.spans.forEach(s=>{cuts.add(s.start); cuts.add(s.end)});
    p.stream_ranges.forEach(r=>{cuts.add(r[0]); cuts.add(r[1])});
    const pts = [...cuts].sort((a,b)=>a-b);
    let out = '';
    for(let k=0;k<pts.length-1;k++){
      const a=pts[k], b=pts[k+1]; if(a>=b) continue;
      const seg = esc(T.slice(a,b));
      const sr = p.stream_ranges.find(r=>r[0]<=a && a<r[1]);
      const cov = p.spans.filter(s=>s.start<=a && b<=s.end);
      let cls = sr && sr[2]!=='narration' ? `st-${sr[2]}` : '';
      if(cov.length){
        const its = cov.map(s=>R.items[s.item]).filter(Boolean).sort((x,y)=>ORDER[x.status]-ORDER[y.status]);
        const ids = [...new Set(its.map(i=>i.id))];
        out += `<span class="hl s-${its[0].status} ${cls}" data-items="${esc(ids.join('|'))}" onclick="openItems(this)" title="${esc(its.map(i=>i.status+': '+i.text).join('; '))}">${seg}</span>`;
      } else out += cls ? `<span class="${cls}">${seg}</span>` : seg;
    }
    h += `<p id="p${p.i}" class="${p.heading?'h':''}"><span class="pn">${p.i+1}</span>${out}</p>`;
  }
  document.getElementById('textbody').innerHTML = h;
})();
// ---------- evidence panel
function citeLine(c){
  if(!c) return '—';
  const link = `https://texts.earlyprint.org/works/${encodeURIComponent(c.tcp)}.xml`;
  const au = c.author && c.author !== 'n/a' ? ' ('+esc(c.author).slice(0,60)+')' : '';
  return `<b>${c.year}</b> — ${esc(c.title).slice(0,160)}${au} ` +
         `[<a href="${link}" target="_blank" rel="noopener">${esc(c.tcp)}</a>] <span class="small">imprint: ${esc(c.date_raw)} · ${esc(c.date_kind)}</span>`;
}
function hist(dec){
  const ks = Object.keys(dec||{}).map(Number).sort((a,b)=>a-b);
  if(!ks.length) return '';
  const lo = Math.min(ks[0], Math.floor(Y/10)*10), hi = Math.max(ks[ks.length-1], Math.floor(Y/10)*10);
  const max = Math.max(...ks.map(k=>dec[k]));
  let h = '<div class="hist" title="distinct texts per decade">';
  for(let d=lo; d<=hi; d+=10){
    const v = dec[d]||0, ht = v? Math.max(2, Math.round(40*Math.sqrt(v/max))) : 0;
    h += `<div class="${d+10<=Y?'before':''}" style="height:${ht}px" title="${d}s: ${v} texts">${(d%50===0)?'<span>'+d+'</span>':''}</div>`;
  }
  return h + '</div>';
}
function kwics(list){
  return (list||[]).map(k=>`<div class="kwic">${esc(k.left)} <b>${esc(k.kw)}</b> ${esc(k.right)}<span class="src">${k.year||''} · ${esc(k.tcp||'')} · ${esc((k.title||'').slice(0,90))}${k.date_kind&&k.date_kind!=='firm'?' · date '+esc(k.date_kind):''}</span></div>`).join('');
}
function itemHtml(it){
  const ev = it.evidence||{};
  let h = `<h3>${esc(it.text)} ${badge(it.status)} ${tag(it.tag)}</h3>`;
  h += `<p class="small">${esc(it.type)} · key <code>${esc(it.key)}</code></p>`;
  if(it.reason) h += `<p>${esc(it.reason)}</p>`;
  if(ev.basis && ev.basis!==it.reason && ev.basis!=='exact') h += `<p class="small">Basis: ${esc(ev.basis)}${ev.matched && ev.matched!==it.key ? ' → '+esc(ev.matched):''}</p>`;
  if(ev.note) h += `<p>${esc(ev.note)}</p>`;
  for(const w of (it.watch||[])){
    h += `<div class="wl"><b>Watch list</b>: ${esc(w.reason)} ${tag(w.tag)}${w.source?'<br><span class="small">source: '+esc(w.source)+'</span>':''}` +
         `${w.from_year?'<br><span class="small">recorded from '+w.from_year+'</span>':''}${w.corpus?'<br><span class="small">corpus: '+esc(w.corpus)+'</span>':''}</div>`;
  }
  if(ev.first_firm || ev.first_any){
    if(it.type==='watch') h += `<p class="small"><b>Corpus evidence for the form</b> (it may be another word or sense - see the contexts)${ev.status?': on the corpus alone '+badge(ev.status)+' '+tag(ev.tag):''}</p>`;
    h += `<p><b>Earliest firm-dated print</b><br>${citeLine(ev.first_firm)}</p>`;
    if(ev.first_any) h += `<p><b>Earlier, date not firm</b><br>${citeLine(ev.first_any)}</p>`;
    h += `<p class="small">Texts before ${Y}: ${ev.n_before}${ev.n_before_approx?' (decade resolution)':''} · texts in all: ${fmt(ev.ntexts)}${ev.expected_before!=null?' · expected before '+Y+' at the later rate: '+ev.expected_before:''}</p>`;
    h += hist(ev.decades);
  } else if(ev.foreign){
    h += `<p><b>As a foreign-language word</b><br>${citeLine(ev.foreign.first_firm||ev.foreign.first_any)}<br><span class="small">${ev.foreign.ntexts} texts</span></p>`;
  }
  if(ev.kwic && ev.kwic.length) h += `<p><b>Earliest printed contexts</b> <span class="small">(printed spelling)</span></p>` + kwics(ev.kwic);
  if(ev.lemma_note) h += `<p class="small">MorphAdorner lemma(s) for this form: ${esc(ev.lemma_note)}</p>`;
  const occ = it.occurrences.map(o=>`<a href="#p${o.para}">¶${o.para+1}</a> ${o.stream}`).join(', ');
  h += `<p class="small">In this scene: ${occ}</p>`;
  return h;
}
function openItem(id){ const it = R.items[id]; if(!it) return; document.getElementById('pbody').innerHTML = itemHtml(it); document.getElementById('panel').classList.add('open'); }
function openItems(el){ const ids = el.dataset.items.split('|'); document.getElementById('pbody').innerHTML = ids.map(i=>R.items[i]).filter(Boolean).map(itemHtml).join('<hr>'); document.getElementById('panel').classList.add('open'); }
function closePanel(){ document.getElementById('panel').classList.remove('open'); }
document.addEventListener('keydown', e=>{ if(e.key==='Escape') closePanel(); });
</script>
</body>
</html>
"""


def render(result: dict, title_file: str) -> str:
    data = json.dumps(result, ensure_ascii=False, default=str).replace("</", "<\\/")
    return (TEMPLATE.replace("__TITLE__", html.escape(f"Period check: {title_file} ({result['settings']['year']})"))
            .replace("__FILE__", html.escape(title_file))
            .replace("__DATA__", data))


def write(result: dict, html_path: Path, json_path: Path | None = None) -> None:
    html_path = Path(html_path)
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(render(result, Path(result.get("source", "scene")).name), encoding="utf-8")
    if json_path:
        Path(json_path).write_text(json.dumps(result, ensure_ascii=False, indent=1, default=str),
                                   encoding="utf-8")
