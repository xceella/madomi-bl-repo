#!/usr/bin/env python3
import csv
import json
import re
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
TITLES = ROOT / "glossary_titles.json"
OUT_DIR = ROOT / "results"
OUT_JSON = OUT_DIR / "full_glossary.json"
OUT_CSV = OUT_DIR / "full_glossary.csv"
OUT_MD = OUT_DIR / "full_glossary.md"

TIMEOUT = 15
UA = "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/129 Safari/537.36 XBL-Glossary/1.0"
MAX_WORKERS = 8

SOURCES = [
    {"id":"bodinhoyaoi","name":"Bodinho Yaoi","lang":"pt-BR","type":"bodinho","base":"https://bodinhoyaoi.com"},
    {"id":"bryaoi","name":"BR Yaoi","lang":"pt-BR","type":"bryaoi","base":"https://bryaoi.com"},
    {"id":"covenscan","name":"Coven Scan","lang":"pt-BR","type":"madara","base":"https://covendasbruxonas.com"},
    {"id":"fleurblanche","name":"Fleur Blanche","lang":"pt-BR","type":"madara","base":"https://fbsquadx.com"},
    {"id":"portalyaoi","name":"Portal Yaoi","lang":"pt-BR","type":"madara","base":"https://portalyaoi.com"},
    {"id":"xxxyaoi","name":"XXX Yaoi","lang":"pt-BR","type":"madara","base":"https://3xyaoi.com"},
    {"id":"mangago","name":"Mangago","lang":"en","type":"mangago","base":"https://www.mangago.me"},
    {"id":"mangak","name":"MangaK","lang":"en","type":"mangak","base":"https://mangak.io"},
    {"id":"yaoiscan","name":"YaoiScan","lang":"en","type":"madara","base":"https://yaoiscan.com"},
    {"id":"yaoihub","name":"Yaoihub","lang":"en","type":"madara","base":"https://yaoihub.org"},
    {"id":"orchisasia","name":"Orchisasia","lang":"en","type":"madara","base":"https://www.orchisasia.org"},
    {"id":"mangaparktv","name":"MangaPark.tv","lang":"en","type":"madara","base":"https://mangapark.tv"},
    {"id":"manhwazone","name":"ManhwaZone","lang":"en","type":"manhwazone","base":"https://manhwazone.com"},
    {"id":"mangadex-en","name":"MangaDex","lang":"en","type":"mangadex","base":"https://mangadex.org","md_lang":"en"},
    {"id":"mangadex-pt","name":"MangaDex","lang":"pt-BR","type":"mangadex","base":"https://mangadex.org","md_lang":"pt-br"}
]

def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().replace("&", " and ")
    return re.sub(r"[^a-z0-9]+", " ", s).strip()

def title_queries(item):
    vals = [item["title"]] + item.get("aliases", [])
    if "/" in item["title"]:
        vals += [x.strip() for x in item["title"].split("/") if x.strip()]
    out=[]; seen=set()
    for x in vals:
        n=norm(x)
        if n and n not in seen:
            seen.add(n); out.append(x)
    return out

def score_title(expected, candidate):
    e,c=norm(expected),norm(candidate)
    if not e or not c: return 0.0
    if e==c: return 1.0
    if e in c or c in e:
        short=min(len(e),len(c)); long=max(len(e),len(c))
        return 0.92 + 0.07*(short/long)
    return SequenceMatcher(None,e,c).ratio()

def best_candidate(item, candidates, min_score=0.72):
    if not candidates: return None
    best=None; best_s=0
    expected = [item["title"]] + item.get("aliases", [])
    if "/" in item["title"]:
        expected += [x.strip() for x in item["title"].split("/") if x.strip()]
    for cand in candidates:
        for e in expected:
            s=score_title(e,cand.get("title",""))
            if s>best_s:
                best_s=s; best=cand
    if best is not None and best_s>=min_score:
        best=dict(best); best["_score"]=round(best_s,4)
        return best
    return None

def parse_latest_number(text):
    if not text: return None
    nums = re.findall(r"(?<!\d)(\d+(?:\.\d+)?)(?!\d)", text.replace(",", "."))
    if not nums: return None
    try: return float(nums[0])
    except: return None

def normalize_status(text):
    n=norm(text)
    if not n: return "unknown"
    if any(x in n for x in ["completed","complete","completo","finalizado","finished","end"]): return "complete"
    if any(x in n for x in ["ongoing","on going","em andamento","andamento","updating"]): return "ongoing"
    if any(x in n for x in ["hiatus","on hold","pausado","hiato"]): return "hiatus"
    if any(x in n for x in ["cancelled","canceled","cancelado"]): return "cancelled"
    return "unknown"

def session():
    s=requests.Session()
    s.headers.update({"User-Agent":UA,"Accept-Language":"en-US,en;q=0.9,pt-BR;q=0.8","Referer":"https://google.com/"})
    return s

def request(s, method, url, **kwargs):
    return s.request(method, url, timeout=TIMEOUT, allow_redirects=True, **kwargs)

def details_common(status, chapters, latest, latest_num, notes=None):
    return {"site_status":status or "unknown","chapter_count":chapters,"latest_chapter":latest,"latest_number":latest_num,"notes":notes or ""}

def bodinho_search(s, item, src, cache):
    if "bodinho_sitemap" not in cache:
        r=request(s,"GET",src["base"]+"/sitemap.xml"); r.raise_for_status()
        soup=BeautifulSoup(r.text,"xml"); works=[]
        for loc in soup.select("loc"):
            u=loc.get_text(strip=True)
            if "/obras/" in u and "/capitulo/" not in u:
                slug=u.split("/obras/",1)[1].strip("/").split("/",1)[0]
                works.append({"title":slug.replace("-"," ").title(),"url":u,"slug":slug})
        cache["bodinho_sitemap"]=works
    cand=best_candidate(item,cache["bodinho_sitemap"],0.63)
    if not cand: return None
    r=request(s,"GET",cand["url"]); r.raise_for_status(); d=BeautifulSoup(r.text,"html.parser")
    og=d.select_one("meta[property='og:title']")
    matched=(og.get("content","") if og else cand["title"]).replace("Ler ","").split(" em PT-BR")[0].strip()
    status="unknown"
    for t in d.find_all(string=re.compile(r"Completo|Em andamento",re.I)):
        status=normalize_status(str(t))
        if status!="unknown": break
    links=[]; seen=set()
    for a in d.select("section[aria-labelledby='capitulos'] a[href*='/capitulo/']"):
        href=urljoin(src["base"],a.get("href")); sp=a.select_one("span.block.truncate")
        name=sp.get_text(" ",strip=True) if sp else a.get_text(" ",strip=True)
        if href not in seen: seen.add(href); links.append((href,name))
    latest=links[0][1] if links else None
    return {"matched_title":matched,"url":cand["url"],**details_common(status,len(links),latest,parse_latest_number(latest))}

def bryaoi_search(s,item,src,cache):
    candidates=[]
    for q in title_queries(item):
        r=request(s,"GET",src["base"]+"/yaoi/page/1",params={"s":q})
        if r.status_code>=400: continue
        d=BeautifulSoup(r.text,"html.parser")
        for a in d.select(".listagem .item a[href]"):
            h=a.select_one("h2")
            if h: candidates.append({"title":h.get_text(" ",strip=True),"url":urljoin(src["base"],a.get("href"))})
        if best_candidate(item,candidates,0.74): break
    cand=best_candidate(item,candidates,0.74)
    if not cand: return None
    r=request(s,"GET",cand["url"]); r.raise_for_status(); d=BeautifulSoup(r.text,"html.parser")
    links=[]; seen=set()
    for a in d.select(".capitulos a[href]"):
        href=urljoin(src["base"],a.get("href")); name=a.get_text(" ",strip=True)
        if href not in seen: seen.add(href); links.append((href,name))
    text=d.get_text(" ",strip=True)
    m=re.search(r"(?:Status|Estado)\s*[:\-]?\s*(Completo|Em andamento|Ongoing|Completed|Hiatus)",text,re.I)
    status=normalize_status(m.group(1) if m else "")
    latest=links[0][1] if links else None
    return {"matched_title":cand["title"],"url":cand["url"],**details_common(status,len(links),latest,parse_latest_number(latest))}

def madara_candidates(s,src,q):
    form=[("action","madara_load_more"),("page","0"),("template","madara-core/content/content-archive"),("vars[paged]","1"),("vars[template]","archive"),("vars[posts_per_page]","25"),("vars[post_type]","wp-manga"),("vars[post_status]","publish"),("vars[manga_archives_item_layout]","big_thumbnail"),("vars[meta_query][0][key]","_wp_manga_chapter_type"),("vars[meta_query][0][value]","manga"),("vars[s]",q)]
    h={"X-Requested-With":"XMLHttpRequest","Referer":src["base"]+"/"}
    r=request(s,"POST",src["base"]+"/wp-admin/admin-ajax.php",headers=h,data=form)
    out=[]
    if r.status_code<400:
        d=BeautifulSoup(r.text,"html.parser")
        for e in d.select("div.page-item-detail, .manga__item, .c-tabs-item__content"):
            link=e.select_one(".post-title a[href]")
            if not link: continue
            pid=e.get("data-post-id") or (e.select_one("[data-post-id]").get("data-post-id") if e.select_one("[data-post-id]") else None)
            out.append({"title":link.get_text(" ",strip=True),"url":urljoin(src["base"],link.get("href")),"post_id":pid})
    if not out:
        r=request(s,"GET",src["base"]+"/",params={"s":q,"post_type":"wp-manga"})
        if r.status_code<400:
            d=BeautifulSoup(r.text,"html.parser")
            for e in d.select("div.page-item-detail, .manga__item, .c-tabs-item__content"):
                link=e.select_one(".post-title a[href]")
                if link:
                    pid=e.get("data-post-id") or (e.select_one("[data-post-id]").get("data-post-id") if e.select_one("[data-post-id]") else None)
                    out.append({"title":link.get_text(" ",strip=True),"url":urljoin(src["base"],link.get("href")),"post_id":pid})
    return out

def madara_status(d):
    for block in d.select("div.post-content_item"):
        txt=block.get_text(" ",strip=True)
        if re.search(r"\b(Status|Estado)\b",txt,re.I):
            val=block.select_one(".summary-content"); st=normalize_status(val.get_text(" ",strip=True) if val else txt)
            if st!="unknown": return st
    for el in d.select("div.summary-content"):
        st=normalize_status(el.get_text(" ",strip=True))
        if st!="unknown": return st
    return "unknown"

def madara_chapters(s,src,cand,d):
    def parse(doc):
        vals=[]; seen=set()
        for li in doc.select("li.wp-manga-chapter"):
            a=li.select_one("a[href]")
            if a:
                u=urljoin(src["base"],a.get("href")); n=a.get_text(" ",strip=True)
                if u not in seen: seen.add(u); vals.append((u,n))
        return vals
    vals=parse(d)
    if vals: return vals
    h={"X-Requested-With":"XMLHttpRequest","Referer":cand["url"]}
    try:
        r=request(s,"POST",cand["url"].rstrip("/")+"/ajax/chapters/",headers=h,data={})
        if r.status_code<400:
            vals=parse(BeautifulSoup(r.text,"html.parser"))
            if vals: return vals
    except requests.RequestException: pass
    pid=cand.get("post_id")
    if pid:
        try:
            r=request(s,"POST",src["base"]+"/wp-admin/admin-ajax.php",headers=h,data={"action":"manga_get_chapters","manga":pid})
            if r.status_code<400:
                vals=parse(BeautifulSoup(r.text,"html.parser"))
                if vals: return vals
        except requests.RequestException: pass
    return vals

def madara_search(s,item,src,cache):
    candidates=[]
    for q in title_queries(item):
        try: candidates.extend(madara_candidates(s,src,q))
        except requests.RequestException: continue
        if best_candidate(item,candidates,0.76): break
    uniq={c["url"]:c for c in candidates}; cand=best_candidate(item,list(uniq.values()),0.76)
    if not cand: return None
    r=request(s,"GET",cand["url"]); r.raise_for_status(); d=BeautifulSoup(r.text,"html.parser")
    te=d.select_one("div.post-title h3, div.post-title h1, #manga-title > h1")
    matched=te.get_text(" ",strip=True) if te else cand["title"]
    status=madara_status(d); ch=madara_chapters(s,src,cand,d); latest=ch[0][1] if ch else None
    return {"matched_title":matched,"url":cand["url"],**details_common(status,len(ch),latest,parse_latest_number(latest))}

def mangago_search(s,item,src,cache):
    candidates=[]
    for q in title_queries(item):
        r=request(s,"GET",src["base"]+"/r/l_search/",params={"name":q,"page":1})
        if r.status_code>=400: continue
        d=BeautifulSoup(r.text,"html.parser")
        for e in d.select(".updatesli, .pic_list > li"):
            a=e.select_one(".thm-effect")
            if a and a.get("title"): candidates.append({"title":a.get("title").strip(),"url":urljoin(src["base"],a.get("href"))})
        if best_candidate(item,candidates,0.76): break
    cand=best_candidate(item,candidates,0.76)
    if not cand: return None
    r=request(s,"GET",cand["url"]); r.raise_for_status(); d=BeautifulSoup(r.text,"html.parser")
    status="unknown"
    for el in d.select("#information li, #information tr, .manga_info li, .manga_right tr"):
        txt=el.get_text(" ",strip=True)
        if txt.lower().startswith("status"): status=normalize_status(txt); break
    rows=d.select(":is(table#raws_table, table#chapter_table) > tbody > tr, table.uk-table > tbody > tr")
    vals=[]
    for row in rows:
        a=row.select_one("a.chico")
        if a and a.get_text(" ",strip=True): vals.append((urljoin(src["base"],a.get("href")),a.get_text(" ",strip=True)))
    latest=vals[0][1] if vals else None
    return {"matched_title":cand["title"],"url":cand["url"],**details_common(status,len(vals),latest,parse_latest_number(latest),"chapter_count = releases/versions on Mangago")}

def mangak_search(s,item,src,cache):
    api="https://api.mangak.io"; candidates=[]
    for q in title_queries(item):
        r=request(s,"GET",api+"/titles/search",params={"page":1,"limit":24,"q":q})
        if r.status_code>=400: continue
        p=r.json(); d=p.get("data",p); its=d.get("items",[]) if isinstance(d,dict) else []
        for x in its:
            if x.get("id") and x.get("name"): candidates.append({"title":x["name"],"url":urljoin(src["base"],x.get("url","")),"id":x["id"]})
        if best_candidate(item,candidates,0.76): break
    cand=best_candidate(item,candidates,0.76)
    if not cand: return None
    status="unknown"; count=None; latest=None; notes=""
    try:
        r=request(s,"GET",api+f"/titles/{cand['id']}")
        if r.status_code<400:
            p=r.json(); d=p.get("data",p)
            if isinstance(d,dict): status=normalize_status(str(d.get("status",""))); count=d.get("chapters_count")
    except: pass
    r=request(s,"GET",api+f"/titles/{cand['id']}/chapters",params={"cv":int(time.time()*1000)})
    if r.status_code<400:
        p=r.json(); d=p.get("data",p); ch=d.get("chapters",[]) if isinstance(d,dict) else []
        valid=[x for x in ch if x.get("url") and x.get("name")]
        if count is None: count=len(valid)
        if valid: latest=valid[0].get("name")
        if any("notice" in norm(x.get("name","")) or "promo" in norm(x.get("name","")) for x in valid): notes="count includes notice/promo entries"
    return {"matched_title":cand["title"],"url":cand["url"],**details_common(status,count,latest,parse_latest_number(latest),notes)}

def manhwazone_chapters(s,base,d):
    target=None
    for div in d.find_all("div"):
        if div.has_attr("wire:snapshot") and div.has_attr("wire:id") and div.get("wire:init")=="bootLoad": target=div; break
    if not target: return []
    csrf=d.select_one("meta[name=csrf-token]"); token=csrf.get("content","") if csrf else ""
    payload={"_token":token,"components":[{"snapshot":target.get("wire:snapshot"),"updates":{},"calls":[{"path":"","method":"bootLoad","params":[]}]}]}
    h={"Accept":"application/json","Content-Type":"application/json","X-Livewire":"true","Referer":base+"/"}
    r=request(s,"POST",base+"/livewire/update",headers=h,json=payload); r.raise_for_status()
    data=r.json(); snap=(data.get("components") or [{}])[0].get("snapshot")
    if not snap: return []
    sd=json.loads(snap); ct=((sd.get("data") or {}).get("chapters") or []); vals=ct[0] if isinstance(ct,list) and ct else []; out=[]
    for x in vals:
        if isinstance(x,list) and x and isinstance(x[0],dict): out.append(x[0])
    return out

def manhwazone_search(s,item,src,cache):
    candidates=[]
    for q in title_queries(item):
        r=request(s,"GET",src["base"]+"/series",params={"page":1,"keyword":q})
        if r.status_code>=400: continue
        d=BeautifulSoup(r.text,"html.parser")
        for e in d.select("article.group"):
            t=e.select_one(".min-w-0 > a.font-semibold"); a=e.select_one("a[href]")
            if t and a: candidates.append({"title":t.get_text(" ",strip=True),"url":urljoin(src["base"],a.get("href"))})
        if best_candidate(item,candidates,0.76): break
    cand=best_candidate(item,candidates,0.76)
    if not cand: return None
    r=request(s,"GET",cand["url"]); r.raise_for_status(); d=BeautifulSoup(r.text,"html.parser")
    status="unknown"
    for el in d.find_all(string=re.compile(r"Completed|Ongoing|Hiatus|Complete",re.I)):
        st=normalize_status(str(el))
        if st!="unknown": status=st; break
    ch=manhwazone_chapters(s,src["base"],d); latest=None
    if ch: latest=str(ch[0].get("name") or ch[0].get("title") or ch[0].get("chapter_number") or "")
    return {"matched_title":cand["title"],"url":cand["url"],**details_common(status,len(ch),latest,parse_latest_number(latest))}

def mangadex_search(s,item,src,cache):
    api="https://api.mangadex.org"; candidates=[]
    for q in title_queries(item):
        r=request(s,"GET",api+"/manga",params=[("title",q),("limit","10"),("includes[]","cover_art")])
        if r.status_code>=400: continue
        p=r.json()
        for x in p.get("data",[]):
            a=x.get("attributes",{}); tt=a.get("title",{}); title=tt.get("en") or next(iter(tt.values()),""); alt=[]
            for obj in a.get("altTitles",[]): alt += list(obj.values())
            candidates.append({"title":title,"alts":alt,"id":x.get("id"),"url":"https://mangadex.org/title/"+str(x.get("id")),"attrs":a})
        expanded=[]
        for c in candidates:
            expanded.append(c)
            for alt in c.get("alts",[]): expanded.append({**c,"title":alt})
        if best_candidate(item,expanded,0.76): break
    expanded=[]
    for c in candidates:
        expanded.append(c)
        for alt in c.get("alts",[]): expanded.append({**c,"title":alt})
    hit=best_candidate(item,expanded,0.76)
    if not hit: return None
    cand=next((c for c in candidates if c["id"]==hit["id"]),hit); status=normalize_status(str(cand.get("attrs",{}).get("status",""))); lang=src["md_lang"]
    total=0; latest=None; offset=0
    while True:
        params=[("translatedLanguage[]",lang),("limit","100"),("offset",str(offset)),("order[chapter]","desc"),("order[volume]","desc"),("includeFutureUpdates","0")]
        r=request(s,"GET",api+f"/manga/{cand['id']}/feed",params=params)
        if r.status_code>=400: break
        p=r.json()
        if offset==0:
            total=p.get("total",0)
            if p.get("data"): a=p["data"][0].get("attributes",{}); latest=a.get("chapter") or a.get("title")
        if offset+len(p.get("data",[]))>=p.get("total",0): break
        offset += len(p.get("data",[]))
        if offset>2000: break
    return {"matched_title":cand["title"],"url":cand["url"],**details_common(status,total,latest,parse_latest_number(latest),f"MangaDex language={lang}")}

HANDLERS={"bodinho":bodinho_search,"bryaoi":bryaoi_search,"madara":madara_search,"mangago":mangago_search,"mangak":mangak_search,"manhwazone":manhwazone_search,"mangadex":mangadex_search}

def probe_one(item,src,cache):
    s=session(); base={"title_id":item["id"],"title":item["title"],"user_status":item["user_status"],"source":src["name"],"source_id":src["id"],"language":src["lang"],"found":False,"matched_title":None,"url":None,"site_status":"unknown","chapter_count":None,"latest_chapter":None,"latest_number":None,"notes":""}
    try:
        res=HANDLERS[src["type"]](s,item,src,cache)
        if res: base.update(res); base["found"]=True
    except requests.RequestException as e: base["notes"]="NETWORK/BLOCKED: "+str(e)[:180]
    except Exception as e: base["notes"]=f"ERROR {type(e).__name__}: {str(e)[:180]}"
    finally: s.close()
    return base

def choose_best(matches):
    if not matches: return None
    def score(r):
        lang_bonus=10 if r["language"]=="pt-BR" else 0
        source_bonus={"Bodinho Yaoi":4,"BR Yaoi":3,"MangaK":2,"MangaDex":1}.get(r["source"],0)
        latest=r.get("latest_number"); coverage=(latest if latest is not None else (r.get("chapter_count") or 0)/10); status_bonus=1 if r.get("site_status")=="complete" else 0
        return (coverage,lang_bonus,source_bonus,status_bonus)
    return max(matches,key=score)

def write_outputs(titles,rows):
    OUT_DIR.mkdir(parents=True,exist_ok=True); payload={"generated_at":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"titles":titles,"matches":rows}; OUT_JSON.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    fields=["title_id","title","user_status","source","source_id","language","found","matched_title","site_status","chapter_count","latest_chapter","latest_number","url","notes"]
    with OUT_CSV.open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); [w.writerow({k:r.get(k) for k in fields}) for r in rows]
    found=[r for r in rows if r["found"]]; by={}
    for r in found: by.setdefault(r["title_id"],[]).append(r)
    lines=["# XBL — Glossário completo de BLs","",f"Gerado em **{payload['generated_at']}**.","",f"Títulos pesquisados: **{len(titles)}** · Fontes/idiomas testados: **{len(SOURCES)}**.","","| # | Título | Status do Lucas | Melhor fonte | Cap./último | Status site | Outras fontes |","|---:|---|---|---|---|---|---|"]
    for item in titles:
        ms=by.get(item["id"],[]); best=choose_best(ms)
        if best:
            cap=best.get("latest_chapter") or (str(best.get("chapter_count")) if best.get("chapter_count") is not None else "—"); others=", ".join(f"{m['source']} ({m['language']})" for m in ms if m is not best) or "—"; lines.append(f"| {item['id']} | {item['title']} | {item['user_status']} | {best['source']} ({best['language']}) | {cap} | {best['site_status']} | {others} |")
        else: lines.append(f"| {item['id']} | {item['title']} | {item['user_status']} | — | — | — | não localizado |")
    lines += ["","## Detalhes por fonte","","| Título | Fonte | Idioma | Match | Capítulos/entradas | Último | Status | URL |","|---|---|---|---|---:|---|---|---|"]
    for r in found: lines.append(f"| {r['title']} | {r['source']} | {r['language']} | {r['matched_title'] or ''} | {r['chapter_count'] if r['chapter_count'] is not None else '—'} | {r['latest_chapter'] or '—'} | {r['site_status']} | {r['url'] or ''} |")
    OUT_MD.write_text("\n".join(lines),encoding="utf-8")

def main():
    titles=json.loads(TITLES.read_text(encoding="utf-8")); cache={}; rows=[]; jobs=[]
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        for src in SOURCES:
            for item in titles: jobs.append(ex.submit(probe_one,item,src,cache))
        for i,f in enumerate(as_completed(jobs),1):
            rows.append(f.result())
            if i%100==0: print(f"{i}/{len(jobs)} checks")
    rows.sort(key=lambda r:(r["title_id"],r["language"]!="pt-BR",r["source"])); write_outputs(titles,rows); found=sum(1 for r in rows if r["found"]); covered=len({r["title_id"] for r in rows if r["found"]}); print(f"Done: {found} source matches across {covered}/{len(titles)} titles"); return 0

if __name__=="__main__": raise SystemExit(main())
