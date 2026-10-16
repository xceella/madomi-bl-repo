#!/usr/bin/env python3
import csv,json,re,time,unicodedata
from concurrent.futures import ThreadPoolExecutor
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parent
TITLES=ROOT/'glossary_titles.json'; OUT=ROOT/'results'; OUT.mkdir(exist_ok=True)
UA='Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/129 Safari/537.36 XBL-WebReader/1.0'
TIMEOUT=20

def norm(s):
 s=unicodedata.normalize('NFKD',s or ''); s=''.join(c for c in s if not unicodedata.combining(c)); s=s.lower().replace('&',' and '); return re.sub(r'[^a-z0-9]+',' ',s).strip()
def score(a,b):
 a,b=norm(a),norm(b)
 if not a or not b:return 0
 if a==b:return 1
 if a in b or b in a:return .92+.07*min(len(a),len(b))/max(len(a),len(b))
 return SequenceMatcher(None,a,b).ratio()
def aliases(x):
 vals=[x['title']]+x.get('aliases',[])
 if '/' in x['title']:vals += [a.strip() for a in x['title'].split('/')]
 return [a for a in vals if a]
def best(item,cands,cut=.72):
 hit=None; bs=0
 for c in cands:
  for a in aliases(item):
   sc=score(a,c['title'])
   if sc>bs:bs=sc;hit=c
 return dict(hit,score=bs) if hit and bs>=cut else None
def sess():
 s=requests.Session(); s.headers.update({'User-Agent':UA,'Accept-Language':'en-US,en;q=.9,pt-BR;q=.8'}); return s
def get(s,u,**kw):return s.get(u,timeout=TIMEOUT,allow_redirects=True,**kw)
def xml_locs(s,u):
 r=get(s,u); r.raise_for_status(); d=BeautifulSoup(r.text,'xml'); return [x.get_text(strip=True) for x in d.select('loc')]
def slug_title(slug):return re.sub(r'[-_]+',' ',slug).strip().title()
def num_from(s):
 m=re.search(r'(\d+(?:\.\d+)?)',s or ''); return float(m.group(1)) if m else None

def desires_catalog(s):
 series=xml_locs(s,'https://desirescans.com/series-sitemap-1.xml'); c=[]
 for u in series:
  m=re.search(r'/series/comic/([^/?#]+)',u)
  if m:c.append({'title':slug_title(m.group(1)),'url':u,'slug':m.group(1)})
 chapters={}
 for i in range(1,9):
  try: urls=xml_locs(s,f'https://desirescans.com/chapter-sitemap-{i}.xml')
  except: continue
  for u in urls:
   m=re.search(r'/series/comic/([^/]+)/chapter/([^/?#]+)',u)
   if m:chapters.setdefault(m.group(1),[]).append((u,m.group(2)))
 return c,chapters

def spring_catalog(s):
 urls=xml_locs(s,'https://springtoons.com/manga-sitemap.xml'); c=[]
 for u in urls:
  path=urlparse(u).path.strip('/'); slug=path.split('/')[-1]
  if slug:c.append({'title':slug_title(slug),'url':u,'slug':slug})
 return c

def qtoon_catalog(s):
 urls=xml_locs(s,'https://qtoon.org/sitemap-mangas.xml'); c=[]
 for u in urls:
  m=re.search(r'/manga/\d+/([^/?#]+)',u)
  if m:c.append({'title':slug_title(m.group(1)),'url':u,'slug':m.group(1)})
 return c

def parse_status_text(text):
 n=norm(text)
 if re.search(r'\b(completed|complete|completo|finished|finalizado)\b',n):return 'complete'
 if re.search(r'\b(ongoing|em andamento|w toku|releasing)\b',n):return 'ongoing'
 if re.search(r'\b(hiatus|hiato|on hiatus)\b',n):return 'hiatus'
 return 'unknown'

def detail_desire(s,item,cand,chapters):
 r=get(s,cand['url']); r.raise_for_status(); d=BeautifulSoup(r.text,'html.parser'); text=d.get_text(' ',strip=True)
 title=(d.select_one('h1').get_text(' ',strip=True) if d.select_one('h1') else cand['title']); st=parse_status_text(text)
 ch=chapters.get(cand['slug'],[]); vals=[]
 for u,label in ch:
  n=num_from(label); vals.append((n,label,u))
 nums=[x for x in vals if x[0] is not None]; latest=max(nums,key=lambda x:x[0]) if nums else (vals[-1] if vals else None)
 return {'matched_title':title,'url':cand['url'],'site_status':st,'chapter_count':len(ch),'latest_chapter':latest[1] if latest else None,'latest_number':latest[0] if latest else None,'language':'multi/EN','notes':'Web Reader; capítulos derivados do sitemap oficial do site'}
def detail_spring(s,item,cand):
 r=get(s,cand['url']); r.raise_for_status(); d=BeautifulSoup(r.text,'html.parser'); text=d.get_text(' ',strip=True)
 h=d.select_one('h1'); title=h.get_text(' ',strip=True) if h else cand['title']; st=parse_status_text(text)
 labels=[]
 for a in d.select('a'):
  tx=a.get_text(' ',strip=True)
  if re.search(r'\b(Chapter|Ch\.|Side Story|Epilogue|Special)\b',tx,re.I): labels.append(tx)
 labels=list(dict.fromkeys(labels)); nums=[(num_from(x),x) for x in labels if num_from(x) is not None]; latest=max(nums,key=lambda x:x[0]) if nums else (None,labels[0] if labels else None)
 return {'matched_title':title,'url':cand['url'],'site_status':st,'chapter_count':len(labels) if labels else None,'latest_chapter':latest[1],'latest_number':latest[0],'language':'EN','notes':'Web Reader; contagem baseada nos links de capítulos da página da obra'}
def detail_qtoon(s,item,cand):
 r=get(s,cand['url']); r.raise_for_status(); d=BeautifulSoup(r.text,'html.parser'); text=d.get_text(' ',strip=True)
 h=d.select_one('h1'); title=h.get_text(' ',strip=True) if h else cand['title']; st=parse_status_text(text)
 labels=[]
 for t in d.find_all(string=re.compile(r'(?:EP\.|Chapter|Cap[ií]tulo|Odcinek)\s*\d+',re.I)):
  tx=' '.join(str(t).split())
  if tx and len(tx)<160: labels.append(tx)
 labels=list(dict.fromkeys(labels)); nums=[(num_from(x),x) for x in labels if num_from(x) is not None]; latest=max(nums,key=lambda x:x[0]) if nums else (None,labels[0] if labels else None)
 m=re.search(r'(\d+)\s+(?:Episodes|Epis[oó]dios|Odcinki|Rozdzia)',text,re.I); count=int(m.group(1)) if m else (len(labels) if labels else None)
 langs=[]
 for code in ['PT','EN','ES','FR']:
  if re.search(rf'\b{code}\b',text):langs.append(code)
 return {'matched_title':title,'url':cand['url'],'site_status':st,'chapter_count':count,'latest_chapter':latest[1],'latest_number':latest[0],'language':'/'.join(langs) if langs else 'multi','notes':'Web Reader; Qtoon reúne idiomas por episódio'}

def main():
 titles=json.loads(TITLES.read_text(encoding='utf-8')); s=sess(); catalogs={}; rows=[]; dch={}; unavailable=[]
 try:
  print('Loading DesireScans sitemap...'); dc,dch=desires_catalog(s); catalogs['DesireScans']=dc
 except Exception as e: unavailable.append({'source':'DesireScans','error':f'{type(e).__name__}: {e}'})
 try:
  print('Loading SpringToons sitemap...'); sc=spring_catalog(s); catalogs['SpringToons']=sc
 except Exception as e: unavailable.append({'source':'SpringToons','error':f'{type(e).__name__}: {e}'})
 try:
  print('Loading Qtoon sitemap...'); qc=qtoon_catalog(s); catalogs['Qtoon']=qc
 except Exception as e: unavailable.append({'source':'Qtoon','error':f'{type(e).__name__}: {e}'})
 jobs=[]
 with ThreadPoolExecutor(max_workers=10) as ex:
  for item in titles:
   for source,cat in catalogs.items():
    cand=best(item,cat,.70)
    if not cand:continue
    if source=='DesireScans': fut=ex.submit(detail_desire,s,item,cand,dch)
    elif source=='SpringToons': fut=ex.submit(detail_spring,s,item,cand)
    else:fut=ex.submit(detail_qtoon,s,item,cand)
    jobs.append((item,source,fut))
  for item,source,f in jobs:
   try:r=f.result(); r.update({'title_id':item['id'],'title':item['title'],'user_status':item['user_status'],'source':source,'source_type':'Web Reader','found':True}); rows.append(r)
   except Exception as e: rows.append({'title_id':item['id'],'title':item['title'],'user_status':item['user_status'],'source':source,'source_type':'Web Reader','found':False,'notes':f'{type(e).__name__}: {e}'})
 s.close(); rows.sort(key=lambda x:(x['title_id'],x['source']))
 payload={'generated_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'unavailable_sources':unavailable,'matches':rows}; (OUT/'webreader_glossary.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
 fields=['title_id','title','user_status','source','source_type','found','matched_title','language','site_status','chapter_count','latest_chapter','latest_number','url','notes']
 with (OUT/'webreader_glossary.csv').open('w',newline='',encoding='utf-8-sig') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();[w.writerow({k:r.get(k) for k in fields}) for r in rows]
 lines=['# XBL — Web Reader glossary','',f"Generated: {payload['generated_at']}",'']
 if unavailable:
  lines += ['## Fontes bloqueadas na execução','']+[f"- **{x['source']}**: {x['error']}" for x in unavailable]+['']
 lines += ['| Title | Source | Language | Status | Count | Latest | URL |','|---|---|---|---|---:|---|---|']
 for r in rows:
  if r.get('found'):lines.append(f"| {r['title']} | {r['source']} | {r.get('language','—')} | {r.get('site_status','unknown')} | {r.get('chapter_count') if r.get('chapter_count') is not None else '—'} | {r.get('latest_chapter') or '—'} | {r.get('url','')} |")
 (OUT/'webreader_glossary.md').write_text('\n'.join(lines),encoding='utf-8'); print(f'Done: {sum(1 for r in rows if r.get("found"))} positive matches; blocked={len(unavailable)}')
if __name__=='__main__': main()
