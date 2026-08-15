#!/usr/bin/env python3
"""Generate the fully-static league storyboard (no JS needed for content)."""
import html

CSS = """
:root{--bg:#eceef0;--surface:#fff;--surface-2:#f4f6f8;--line:#dde1e6;--ink:#161a1f;--muted:#5c6570;--faint:#8a929c;
--gold:#a9781a;--gold-fill:#c8952a;--gold-soft:#eadfc4;--steel:#3c6f92;--espn:#b23a3a;--win:#2f8f5b;--loss:#c0554f;
--shadow:0 1px 2px rgba(20,24,30,.06),0 8px 24px rgba(20,24,30,.06);color-scheme:light;}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0f1319;--surface:#161c25;--surface-2:#1b232e;
--line:#28323f;--ink:#eef2f6;--muted:#9aa5b1;--faint:#6b7783;--gold:#e6ba4c;--gold-fill:#e0b246;--gold-soft:#3a3016;
--steel:#6aa0c4;--espn:#e07a76;--win:#5cbd83;--loss:#d97a72;--shadow:0 1px 2px rgba(0,0,0,.4),0 12px 30px rgba(0,0,0,.35);color-scheme:dark;}}
:root[data-theme="dark"]{--bg:#0f1319;--surface:#161c25;--surface-2:#1b232e;--line:#28323f;--ink:#eef2f6;--muted:#9aa5b1;
--faint:#6b7783;--gold:#e6ba4c;--gold-fill:#e0b246;--gold-soft:#3a3016;--steel:#6aa0c4;--espn:#e07a76;--win:#5cbd83;
--loss:#d97a72;--shadow:0 1px 2px rgba(0,0,0,.4),0 12px 30px rgba(0,0,0,.35);color-scheme:dark;}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
font-family:ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;line-height:1.5;-webkit-font-smoothing:antialiased}
.wrap{max-width:1000px;margin:0 auto;padding:clamp(20px,4vw,44px) clamp(16px,4vw,30px) 80px}
.num{font-variant-numeric:tabular-nums}
header.mast{border-bottom:2px solid var(--ink);padding-bottom:20px;position:relative}
.eyebrow{font-size:12px;letter-spacing:.24em;text-transform:uppercase;color:var(--gold);font-weight:700;margin:0 0 8px}
h1{font-size:clamp(34px,8vw,72px);line-height:.9;letter-spacing:-.03em;margin:0;font-weight:800}
.sub{margin:14px 0 0;color:var(--muted);font-size:15px}.sub b{color:var(--ink);font-weight:650}
.toggle{position:absolute;top:0;right:0;border:1px solid var(--line);background:var(--surface);color:var(--muted);
border-radius:999px;padding:8px 14px;font-size:13px;cursor:pointer;font-weight:600}
.toggle:hover{color:var(--ink);border-color:var(--faint)}.toggle:focus-visible{outline:2px solid var(--gold);outline-offset:2px}
.sec-label{display:flex;align-items:baseline;gap:12px;margin:52px 0 18px}
.sec-label h2{font-size:clamp(15px,2.6vw,20px);letter-spacing:-.01em;margin:0;font-weight:800;white-space:nowrap}
.sec-label .rule{height:1px;background:var(--line);flex:1}.sec-label .n{font-size:12px;color:var(--faint);font-weight:700}
.note{color:var(--muted);font-size:12.5px;margin:10px 2px 0}
.chapter{background:var(--surface);border:1px solid var(--line);border-radius:16px;box-shadow:var(--shadow);padding:22px clamp(18px,3vw,26px);margin-bottom:16px}
.chead{display:flex;gap:16px 20px;align-items:baseline;flex-wrap:wrap;margin-bottom:6px}
.yr{font-size:clamp(30px,5vw,44px);font-weight:800;letter-spacing:-.03em;line-height:1}
.plat{font-size:10.5px;font-weight:800;letter-spacing:.06em;text-transform:uppercase;padding:2px 7px;border-radius:6px;border:1px solid currentColor;margin-left:4px}
.plat.e{color:var(--espn)}.plat.s{color:var(--steel)}
.headline{margin:0;font-size:clamp(15px,2.3vw,18px);font-weight:600;color:var(--muted);flex:1;min-width:220px}
.crown{display:flex;gap:22px;flex-wrap:wrap;margin:14px 0 16px}.crown .unit{display:flex;align-items:center;gap:11px}
.crown .ic{font-size:24px}.crown .cl{font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--faint);font-weight:700}
.crown .cn{font-weight:750;font-size:17px}.crown .cr{font-size:13px;color:var(--muted);font-weight:600}.crown .champ .cn{color:var(--gold)}
.chips{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}
.chip{background:var(--surface-2);border:1px solid var(--line);border-radius:11px;padding:11px 13px}
.chip .ck{font-size:10px;letter-spacing:.08em;text-transform:uppercase;color:var(--faint);font-weight:700;display:block;margin-bottom:4px}
.chip .cv{font-weight:700;font-size:14.5px;display:block;line-height:1.25}.chip .cs{font-size:12px;color:var(--muted);display:block;margin-top:1px}
.card{background:var(--surface);border:1px solid var(--line);border-radius:14px;box-shadow:var(--shadow);overflow:hidden}
ol.rank{list-style:none;margin:0;padding:6px 0}
ol.rank li{display:grid;grid-template-columns:34px 1fr auto;align-items:center;gap:12px;padding:11px 18px;border-bottom:1px solid var(--line)}
ol.rank li:last-child{border-bottom:0}ol.rank li:hover{background:var(--surface-2)}
.rk{color:var(--faint);font-weight:800;font-size:14px;text-align:center}.rk.top{color:var(--gold)}
.nm{font-weight:650}.ns{font-size:12.5px;color:var(--muted);margin-top:1px}
.rv{font-weight:800;font-size:17px;letter-spacing:-.02em;text-align:right}.rv small{font-size:.62em;color:var(--muted);font-weight:600}
.rivals{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px}
.rival{background:var(--surface);border:1px solid var(--line);border-radius:13px;box-shadow:var(--shadow);padding:15px 16px}
.rival .who{font-weight:750;font-size:15px}.rival .plays{font-size:12.5px;color:var(--muted);margin-top:3px}.rival .plays b{color:var(--ink);font-weight:700}
.rival .foot{display:flex;justify-content:space-between;align-items:baseline;margin-top:11px;gap:10px}
.rival .rec{font-weight:800;font-size:16px}
.rival .tag{font-size:11px;font-weight:700;padding:2px 8px;border-radius:99px;border:1px solid var(--line);color:var(--muted)}
.rival .tag.lead{color:var(--gold);border-color:var(--gold-fill)}.rival .tag.trail{color:var(--loss)}
.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;min-width:660px;font-size:14px}
thead th{font-size:10.5px;letter-spacing:.06em;text-transform:uppercase;color:var(--faint);font-weight:700;text-align:right;padding:13px 10px;border-bottom:1px solid var(--line);background:var(--surface)}
thead th.l{text-align:left}tbody td{padding:10px 10px;border-bottom:1px solid var(--line);text-align:right}
tbody tr:last-child td{border-bottom:0}tbody tr:hover{background:var(--surface-2)}td.l{text-align:left}
.owner{font-weight:700}.wl-w{color:var(--win);font-weight:650}.wl-l{color:var(--loss)}
.trophy{color:var(--gold);font-weight:800}.sacko{color:var(--loss);font-weight:700}.dim{color:var(--faint)}
.closer{margin-top:56px;text-align:center;padding:30px;border:1px dashed var(--line);border-radius:16px}
.closer .big{font-size:clamp(22px,4vw,32px);font-weight:800;letter-spacing:-.02em}.closer .small{color:var(--muted);margin-top:8px;font-size:14px}
footer{margin-top:30px;padding-top:18px;border-top:1px solid var(--line);color:var(--faint);font-size:12.5px;text-align:center}
"""

seasons = [
 (2018,"e","Dustin Geissert","8–5","Seth Miller","3–10","Where it began — Dustin Geissert is the inaugural champion.",
  ("Jeff Heitzman","2,532"),("Steve Clausing","1,773"),("210.8","Jeff Heitzman","Wk 11"),("Jeff Heitzman","Steve Clausing","+104.6")),
 (2019,"e","Nick Vgts","7–6","Micah Swank","3–10","Nick Vgts sneaks in at 7–6 and captures his first ring.",
  ("Nick Vgts","2,325"),("Kolby Moddelmog","1,665"),("202.6","Nick Vgts","Wk 3"),("Steve Clausing","Kolby Moddelmog","+109.6")),
 (2020,"e","Seth Miller","10–2","Micah Swank","2–11","Seth Miller's 10–2 juggernaut ends in a title.",
  ("Seth Miller","2,684"),("Kolby Moddelmog","1,876"),("221.8","Jeff Heitzman","Wk 12"),("Jeff Heitzman","Alex Clausing","+161.2")),
 (2021,"e","Alex Otte","8–6","Matthew Hermann","3–11","Alex Otte takes the crown.",
  ("Dylan Geissert","2,481"),("Jeff Heitzman","2,075"),("219.6","Alex Otte","Wk 5"),("Matthew Hermann","Jeff Heitzman","+120.8")),
 (2022,"e","Jeff Heitzman","7–7","Alex Clausing","5–9","A 7–7 Cinderella — Jeff Heitzman breaks through for the title.",
  ("Matthew Hermann","2,439"),("Alex Otte","2,053"),("219.6","Dylan Geissert","Wk 5"),("Dylan Geissert","Micah Swank","+104.0")),
 (2023,"e","Alex Clausing","7–7","Kolby Moddelmog","3–11","Alex Clausing wins it all at 7–7 — while Dylan piled up points without a ring.",
  ("Dylan Geissert","2,628"),("Kolby Moddelmog","1,920"),("238.8","Alex Clausing","Wk 4"),("Alex Clausing","Kolby Moddelmog","+186.6")),
 (2024,"e","Micah Swank","9–5","Jacob Berkley","4–10","The final ESPN season — Micah Swank rides a league-record 256.7 to the title.",
  ("Nick Vgts","2,644"),("Alex Otte","1,998"),("256.7","Micah Swank","Wk 17"),("Micah Swank","Anthony Otte","+114.8")),
 (2025,"s","Nick Vgts","11–3","Alex Clausing","3–11","The Sleeper era opens — Nick Vgts goes 11–3 and wins his second ring.",
  ("Nick Vgts","2,589"),("Alex Otte","2,041"),("211.8","Jacob Berkley","Wk 16"),("Jacob Berkley","Micah Swank","+141.8")),
]
scoring = [("Seth Miller","2020","2,684"),("Nick Vgts","2024","2,644"),("Dylan Geissert","2023","2,628"),
 ("Nick Vgts","2025 · Sleeper","2,589"),("Alex Clausing","2020","2,574"),("Jeff Heitzman","2018","2,532"),
 ("Micah Swank","2024","2,521"),("Dylan Geissert","2021","2,481"),("Jeff Heitzman","2025 · Sleeper","2,461"),("Alex Otte","2021","2,450")]
top = [("Micah Swank","2024 · Wk 17 vs Anthony Otte","256.7"),("Alex Clausing","2023 · Wk 4 vs Kolby Moddelmog","238.8"),
 ("Nick Vgts","2024 · Wk 14 vs Cade Miller","231.2"),("Jeff Heitzman","2020 · Wk 12 vs Alex Clausing","221.8"),
 ("Alex Clausing","2020 · Wk 2 vs Dylan Geissert","221.5"),("Dylan Geissert","2022 · Wk 5 vs Micah Swank","219.6"),
 ("Alex Otte","2021 · Wk 5 vs Seth Miller","219.6"),("Anthony Otte","2024 · Wk 11 vs Nick Vgts","218.5"),
 ("Jacob Berkley","2025 · Wk 16 vs Micah Swank","211.8"),("Seth Miller","2020 · Wk 15 vs Alex Clausing","211.0")]
worst = [("Kolby Moddelmog","2019 · Wk 5 vs Steve Clausing","50.0"),("Kolby Moddelmog","2023 · Wk 4 vs Alex Clausing","52.2"),
 ("Jeff Heitzman","2019 · Wk 7 vs Alex Otte","53.6"),("Kolby Moddelmog","2019 · Wk 6 vs Dylan Geissert","54.4"),
 ("Kolby Moddelmog","2021 · Wk 10 vs Dylan Geissert","60.5"),("Kolby Moddelmog","2019 · Wk 10 vs Nick Vgts","60.5"),
 ("Alex Clausing","2020 · Wk 12 vs Jeff Heitzman","60.6"),("Alex Otte","2022 · Wk 9 vs Dylan Geissert","62.9"),
 ("Anthony Otte","2022 · Wk 1 vs Jeff Heitzman","63.4"),("Micah Swank","2025 · Wk 11 vs Nick Vgts","64.8")]
blow = [("Alex Clausing def. Kolby Moddelmog","2023 · Wk 4","+186.6"),("Jeff Heitzman def. Alex Clausing","2020 · Wk 12","+161.2"),
 ("Jacob Berkley def. Micah Swank","2025 · Wk 16","+141.8"),("Matthew Hermann def. Jeff Heitzman","2021 · Wk 15","+120.8"),
 ("Micah Swank def. Anthony Otte","2024 · Wk 17","+114.8"),("Alex Clausing def. Dylan Geissert","2020 · Wk 2","+114.1"),
 ("Steve Clausing def. Kolby Moddelmog","2019 · Wk 5","+109.6"),("Dylan Geissert def. Alex Otte","2023 · Wk 17","+106.6"),
 ("Jeff Heitzman def. Steve Clausing","2018 · Wk 11","+104.6"),("Dylan Geissert def. Micah Swank","2022 · Wk 5","+104.0")]
bench = [("Seth Miller","2025 · Sleeper","538"),("Nick Vgts","2022","520"),("Micah Swank","2019","504"),
 ("Alex Clausing","2023","499"),("Dylan Geissert","2019","499"),("Steve Clausing","2019","480"),
 ("Jeff Heitzman","2020","476"),("Nick Vgts","2023","473"),("Steve Clausing","2020","457"),("Jeff Heitzman","2023","453")]
rivals = [("Nick Vgts","Micah Swank",19,14,5),("Dylan Geissert","Nick Vgts",18,12,6),("Jeff Heitzman","Alex Clausing",16,10,6),
 ("Seth Miller","Alex Clausing",19,12,7),("Alex Clausing","Seth Miller",21,8,13),("Alex Otte","Micah Swank",17,11,6),
 ("Micah Swank","Nick Vgts",19,5,14),("Kolby Moddelmog","Seth Miller",13,8,4),("Anthony Otte","Jeff Heitzman",11,4,7),
 ("Dustin Geissert","Nick Vgts",7,3,4),("Jacob Berkley","Seth Miller",9,5,4),("Cade Miller","Alex Clausing",6,4,2),
 ("Matthew Hermann","Jeff Heitzman",6,3,3),("Steve Clausing","Seth Miller",7,4,3)]
mgr = [("Nick Vgts",2,3,7,8,75,58,1,"56.0","135.8",0),("Dustin Geissert",1,2,3,3,33,15,0,"68.8","135.3",0),
 ("Jeff Heitzman",1,2,6,8,77,57,0,"57.5","130.3",0),("Seth Miller",1,1,2,8,63,70,1,"47.0","128.1",1),
 ("Alex Otte",1,1,4,8,63,71,0,"47.0","125.9",0),("Alex Clausing",1,2,5,8,62,72,0,"46.3","128.4",2),
 ("Micah Swank",1,1,5,8,57,77,0,"42.5","125.0",2),("Dylan Geissert",0,1,7,8,83,51,0,"61.9","134.8",0),
 ("Anthony Otte",0,1,2,5,40,46,0,"46.5","126.9",0),("Cade Miller",0,1,2,2,16,19,0,"45.7","132.6",0),
 ("Matthew Hermann",0,0,1,2,16,18,0,"47.1","135.6",1),("Jacob Berkley",0,0,1,3,23,29,0,"44.2","127.2",1),
 ("Steve Clausing",0,1,1,3,22,26,0,"45.8","112.9",0),("Kolby Moddelmog",0,0,2,6,41,56,2,"41.4","116.2",1)]

e = html.escape
def label(n, t): return f'<div class="sec-label"><span class="n">{n}</span><h2>{t}</h2><span class="rule"></span></div>'

def chip(k, v, s): return f'<div class="chip"><span class="ck">{k}</span><span class="cv">{v}</span><span class="cs">{e(s)}</span></div>'

def chapter(s):
    y,p,champ,crec,last,lrec,h,most,least,best,bl = s
    plat = "ESPN" if p == "e" else "Sleeper"
    return f'''<article class="chapter">
 <div class="chead"><div class="yr num">{y}<span class="plat {p}">{plat}</span></div><p class="headline">{e(h)}</p></div>
 <div class="crown">
  <div class="unit champ"><span class="ic">🏆</span><span><span class="cl">Champion</span><br><span class="cn">{e(champ)}</span> <span class="cr num">{crec}</span></span></div>
  <div class="unit"><span class="ic">💩</span><span><span class="cl">Last Place</span><br><span class="cn">{e(last)}</span> <span class="cr num">{lrec}</span></span></div>
 </div>
 <div class="chips">{chip("Most Points",e(most[0]),most[1]+" pts")}{chip("Fewest Points",e(least[0]),least[1]+" pts")}{chip("Highest Score",best[0],best[1]+" · "+best[2])}{chip("Biggest Blowout",e(bl[0])+" "+bl[2],"over "+bl[1])}</div>
</article>'''

def rank_list(items, small=False):
    lis = []
    for i,(n,s,v) in enumerate(items):
        vv = f'{v} <small>pts</small>' if small else v
        top = " top" if i < 3 else ""
        lis.append(f'<li><div class="rk{top}">{i+1}</div><div><div class="nm">{e(n)}</div><div class="ns">{e(s)}</div></div><div class="rv">{vv}</div></li>')
    return f'<div class="card"><ol class="rank">{"".join(lis)}</ol></div>'

def rival_card(r):
    o,ri,g,w,l = r
    tag = '<span class="tag">dead even</span>' if w==l else (f'<span class="tag lead">leads</span>' if w>l else '<span class="tag trail">trails</span>')
    return f'''<div class="rival"><div class="who">{e(o)}</div><div class="plays">most plays <b>{e(ri)}</b> · {g} meetings</div>
 <div class="foot"><span class="rec num"><span class="wl-w">{w}</span>–<span class="wl-l">{l}</span></span>{tag}</div></div>'''

def mgr_row(m):
    n,c,fi,po,se,w,l,t,win,ppg,last = m
    trophy = "🏆"*c if c else '<span class="dim">—</span>'
    fin = str(fi) if fi else '<span class="dim">0</span>'
    tie = f'–{t}' if t else ''
    sack = f'<span class="sacko">{"💩"*last}</span>' if last else '<span class="dim">—</span>'
    return f'''<tr><td class="l owner">{e(n)}</td><td class="trophy">{trophy}</td><td>{fin}</td>
 <td>{po}<span class="dim">/{se}</span></td><td class="l"><span class="wl-w">{w}</span>–<span class="wl-l">{l}</span>{tie}</td>
 <td>{win}</td><td>{ppg}</td><td>{sack}</td></tr>'''

chapters = "".join(chapter(s) for s in reversed(seasons))
rivals_html = "".join(rival_card(r) for r in rivals)
mgr_html = "".join(mgr_row(m) for m in mgr)

DOC = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>There Can Only Be ONE</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
 <header class="mast">
  <button class="toggle" id="tg" type="button" aria-label="Toggle theme">◐ Theme</button>
  <p class="eyebrow">The Squad · Est. 2018</p>
  <h1>There Can<br>Only Be ONE</h1>
  <p class="sub"><b>8 seasons</b> · <b>15 managers</b> · <b>1,340 games</b> — ESPN (2018–24) → Sleeper (2025–)</p>
 </header>
 {label("01","Season by Season")}{chapters}
 {label("02","Best Scoring Seasons")}{rank_list(scoring)}<p class="note">Total points scored in a season, including playoffs.</p>
 {label("03","Top 10 Performances")}{rank_list(top)}
 {label("04","Worst 10 Performances")}{rank_list(worst)}<p class="note">Regular season only — consolation/losers-bracket games excluded.</p>
 {label("05","Biggest Blowouts")}{rank_list(blow)}<p class="note">Point differential in head-to-head games; playoff byes excluded.</p>
 {label("06","Points Left on the Bench")}{rank_list(bench, small=True)}<p class="note">Points a manager could have scored with their optimal lineup, minus what they actually started — by season.</p>
 {label("07","Every Manager's Rival")}<div class="rivals">{rivals_html}</div><p class="note">The opponent each manager has faced most, all-time (playoffs included). Record from that manager's side.</p>
 {label("08","The Managers")}<div class="card"><div class="scroll"><table class="num"><thead><tr>
  <th class="l">Manager</th><th>🏆</th><th>Finals Made</th><th>Playoffs</th><th class="l">Record</th><th>Win %</th><th>PPG</th><th>💩</th>
 </tr></thead><tbody>{mgr_html}</tbody></table></div></div>
 <p class="note">🏆 championships won · Finals Made = title-game appearances · Playoffs = seasons reaching the postseason · 💩 last-place finishes (worst regular-season record).</p>
 <div class="closer"><div class="big">2026 is loading…</div><div class="small">There can only be ONE.</div></div>
 <footer>Built from the league's full ESPN + Sleeper history.</footer>
</div>
<script>
(function(){{var r=document.documentElement,b=document.getElementById('tg');
var m=matchMedia('(prefers-color-scheme:dark)').matches?'dark':'light';
b.addEventListener('click',function(){{m=m==='dark'?'light':'dark';r.setAttribute('data-theme',m);}});}})();
</script>
</body>
</html>'''

with open("/home/user/espnfflhistory/docs/index.html", "w") as f:
    f.write(DOC)
print("wrote docs/index.html", len(DOC), "bytes")
