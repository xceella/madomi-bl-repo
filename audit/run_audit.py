#!/usr/bin/env python3
import json
import re
import sys
import time
import unicodedata
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "config.json"
RESULTS = ROOT / "results"
TIMEOUT = 25
UA = "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/129 Safari/537.36 XBL-Audit/1.0"


@dataclass
class Check:
    source: str
    query: str
    title: str | None
    url: str | None
    search_raw: int | None = None
    search_parsed: int | None = None
    chapters_declared: int | None = None
    chapters_raw: int | None = None
    chapters_parsed: int | None = None
    duplicate_chapters: int | None = None
    pagination_detected: bool | None = None
    status: str = "PASS"
    notes: list[str] | None = None

    def add(self, note: str, status: str | None = None):
        if self.notes is None:
            self.notes = []
        self.notes.append(note)
        if status:
            order = {"PASS": 0, "WARN": 1, "BLOCKED": 2, "FAIL": 3}
            if order[status] > order[self.status]:
                self.status = status


def norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def get(session: requests.Session, url: str, **kwargs):
    return session.get(url, timeout=TIMEOUT, allow_redirects=True, **kwargs)


def unique_urls(elements, base_url: str):
    values = []
    for e in elements:
        href = e.get("href")
        if href:
            values.append(urljoin(base_url, href))
    return list(dict.fromkeys(values))


def declared_chapter_count(text: str) -> int | None:
    patterns = [
        r"(?:cap[ií]tulos?|chapters?)\s*\(\s*(\d+)\s*\)",
        r"(?:cap[ií]tulos?|chapters?)\s*[:\-]?\s*(\d+)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return int(match.group(1))
    return None


def pick_result(items, expect_title=None):
    if not items:
        return None
    if expect_title:
        target = norm(expect_title)
        exact = [x for x in items if norm(x.get("title", "")) == target]
        if exact:
            return exact[0]
        partial = [x for x in items if target in norm(x.get("title", "")) or norm(x.get("title", "")) in target]
        if partial:
            return partial[0]
        return None
    return items[0]


def audit_bodinho(session, source, test):
    base = source["baseUrl"]
    query = test["query"]
    expect = test.get("expectTitle")
    check = Check(source=source["name"], query=query, title=None, url=None)
    try:
        r = get(session, f"{base}/sitemap.xml")
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "xml")
        work_urls = [x.get_text(strip=True) for x in soup.select("loc") if "/obras/" in x.get_text() and "/capitulo/" not in x.get_text()]
        matches = []
        for url in dict.fromkeys(work_urls):
            slug = url.split("/obras/", 1)[1].split("/", 1)[0]
            title = " ".join(w.capitalize() for w in slug.split("-") if w)
            searchable = norm(slug.replace("-", " "))
            if norm(query) in searchable:
                matches.append({"title": title, "url": url})
        check.search_raw = len(matches)
        check.search_parsed = len(matches)
        chosen = pick_result(matches, expect)
        if expect and chosen is None:
            check.add(f"O sitemap contém obras, mas não encontrei o título esperado: {expect}.", "FAIL")
            return check
        if not chosen:
            check.add("Nenhuma obra encontrada para esta busca no sitemap.", "WARN")
            return check
        check.title, check.url = chosen["title"], chosen["url"]
        page = get(session, chosen["url"])
        page.raise_for_status()
        doc = BeautifulSoup(page.text, "html.parser")
        check.chapters_declared = declared_chapter_count(doc.get_text(" ", strip=True))
        raw = unique_urls(doc.select("a[href*='/capitulo/']"), base)
        parsed = unique_urls(doc.select("section[aria-labelledby='capitulos'] a[href*='/capitulo/']"), base)
        parsed = [u for u in parsed if doc.select_one(f"a[href='{u}'] span.block.truncate") is not None] if False else parsed
        check.chapters_raw = len(raw)
        check.chapters_parsed = len(parsed)
        check.duplicate_chapters = len(raw) - len(set(raw))
        check.pagination_detected = bool(doc.select("section[aria-labelledby='capitulos'] a[rel=next], section[aria-labelledby='capitulos'] .pagination"))
        if check.chapters_raw != check.chapters_parsed:
            check.add(f"Links de capítulos na página: {check.chapters_raw}; capturados pelo escopo atual: {check.chapters_parsed}.", "FAIL")
        if check.chapters_declared is not None and check.chapters_declared != check.chapters_parsed:
            check.add(f"A página declara {check.chapters_declared} capítulos, mas o parser encontra {check.chapters_parsed}.", "FAIL")
        if check.pagination_detected:
            check.add("Há sinais de paginação na área de capítulos; revisar se todos são carregados.", "WARN")
    except requests.RequestException as e:
        check.add(f"Falha/timeout de rede: {e}", "BLOCKED")
    except Exception as e:
        check.add(f"Erro de auditoria: {type(e).__name__}: {e}", "FAIL")
    return check


def audit_bryaoi(session, source, test):
    base = source["baseUrl"]
    query = test["query"]
    expect = test.get("expectTitle")
    check = Check(source=source["name"], query=query, title=None, url=None)
    try:
        r = get(session, f"{base}/yaoi/page/1", params={"s": query})
        r.raise_for_status()
        doc = BeautifulSoup(r.text, "html.parser")
        raw_cards = doc.select(".listagem .item a[href]")
        parsed = []
        for e in raw_cards:
            h2 = e.select_one("h2")
            if h2:
                parsed.append({"title": h2.get_text(" ", strip=True), "url": urljoin(base, e.get("href"))})
        raw_urls = unique_urls(raw_cards, base)
        parsed = list({x["url"]: x for x in parsed}.values())
        check.search_raw = len(raw_urls)
        check.search_parsed = len(parsed)
        if check.search_parsed < check.search_raw:
            check.add(f"A busca retornou {check.search_raw} links candidatos, mas o parser só conseguiu montar {check.search_parsed} obras.", "FAIL")
        chosen = pick_result(parsed, expect)
        if expect and chosen is None:
            check.add(f"Título esperado não indexado pela busca: {expect}.", "FAIL")
            return check
        if not chosen:
            check.add("Nenhum resultado utilizável para esta busca.", "WARN")
            return check
        check.title, check.url = chosen["title"], chosen["url"]
        page = get(session, chosen["url"])
        page.raise_for_status()
        detail = BeautifulSoup(page.text, "html.parser")
        raw = unique_urls(detail.select(".capitulos a[href]"), base)
        check.chapters_declared = declared_chapter_count(detail.get_text(" ", strip=True))
        check.chapters_raw = len(raw)
        check.chapters_parsed = len(raw)
        check.duplicate_chapters = 0
        check.pagination_detected = bool(detail.select(".capitulos .pagination, .capitulos a.next, .capitulos a.page-numbers"))
        if check.chapters_declared is not None and check.chapters_declared != check.chapters_parsed:
            check.add(f"A página declara {check.chapters_declared} capítulos, mas `.capitulos a` encontra {check.chapters_parsed}.", "FAIL")
        if check.pagination_detected:
            check.add("A área de capítulos contém paginação; a extensão atual não percorre páginas extras.", "WARN")
        if not raw:
            check.add("Nenhum capítulo foi capturado na página da obra.", "WARN")
    except requests.RequestException as e:
        check.add(f"Falha/timeout de rede: {e}", "BLOCKED")
    except Exception as e:
        check.add(f"Erro de auditoria: {type(e).__name__}: {e}", "FAIL")
    return check


def manhwazone_chapters(session, base, doc):
    target = None
    for div in doc.find_all("div"):
        if div.has_attr("wire:snapshot") and div.has_attr("wire:id") and div.get("wire:init") == "bootLoad":
            target = div
            break
    if target is None:
        return None, "wire:snapshot/bootLoad não encontrado"
    csrf = doc.select_one("meta[name=csrf-token]")
    token = csrf.get("content", "") if csrf else ""
    payload = {
        "_token": token,
        "components": [{
            "snapshot": target.get("wire:snapshot"),
            "updates": {},
            "calls": [{"path": "", "method": "bootLoad", "params": []}],
        }],
    }
    headers = {"Accept": "application/json", "Content-Type": "application/json", "X-Livewire": "true", "Referer": base + "/"}
    response = session.post(base + "/livewire/update", json=payload, headers=headers, timeout=TIMEOUT)
    response.raise_for_status()
    data = response.json()
    snapshot = (data.get("components") or [{}])[0].get("snapshot")
    if not snapshot:
        return None, "Livewire não retornou snapshot"
    snap = json.loads(snapshot)
    chapters_tuple = ((snap.get("data") or {}).get("chapters") or [])
    if not chapters_tuple:
        return [], None
    values = chapters_tuple[0] if isinstance(chapters_tuple, list) and chapters_tuple else []
    chapters = []
    for item in values:
        if isinstance(item, list) and item and isinstance(item[0], dict):
            chapters.append(item[0])
    return chapters, None


def audit_manhwazone(session, source, test):
    base = source["baseUrl"]
    query = test["query"]
    check = Check(source=source["name"], query=query, title=None, url=None)
    try:
        r = get(session, f"{base}/series", params={"page": 1, "keyword": query})
        r.raise_for_status()
        doc = BeautifulSoup(r.text, "html.parser")
        articles = doc.select("article.group")
        parsed = []
        for e in articles:
            title = e.select_one(".min-w-0 > a.font-semibold")
            link = e.select_one("a[href]")
            if title and link:
                parsed.append({"title": title.get_text(" ", strip=True), "url": urljoin(base, link.get("href"))})
        check.search_raw = len(articles)
        check.search_parsed = len(parsed)
        if len(parsed) < len(articles):
            check.add(f"A página trouxe {len(articles)} cards, mas {len(articles)-len(parsed)} não puderam ser indexados pelos seletores atuais.", "FAIL")
        chosen = pick_result(parsed, test.get("expectTitle")) or (parsed[0] if parsed else None)
        if not chosen:
            check.add("Nenhum resultado utilizável para esta busca.", "WARN")
            return check
        check.title, check.url = chosen["title"], chosen["url"]
        page = get(session, chosen["url"])
        page.raise_for_status()
        detail = BeautifulSoup(page.text, "html.parser")
        check.chapters_declared = declared_chapter_count(detail.get_text(" ", strip=True))
        chapters, err = manhwazone_chapters(session, base, detail)
        if err:
            check.add(f"Não consegui reproduzir o carregamento Livewire de capítulos: {err}.", "WARN")
            return check
        urls = [c.get("web_url") for c in chapters if c.get("web_url")]
        check.chapters_raw = len(chapters)
        check.chapters_parsed = len(urls)
        check.duplicate_chapters = len(urls) - len(set(urls))
        if len(urls) != len(chapters):
            check.add(f"Livewire retornou {len(chapters)} capítulos, mas {len(chapters)-len(urls)} vieram sem web_url e seriam descartados.", "FAIL")
        if check.duplicate_chapters:
            check.add(f"Foram detectadas {check.duplicate_chapters} URLs de capítulos duplicadas.", "FAIL")
        if check.chapters_declared is not None and check.chapters_declared != check.chapters_parsed:
            check.add(f"A página declara {check.chapters_declared} capítulos; Livewire entregou {check.chapters_parsed} indexáveis.", "FAIL")
    except requests.RequestException as e:
        check.add(f"Falha/timeout de rede: {e}", "BLOCKED")
    except Exception as e:
        check.add(f"Erro de auditoria: {type(e).__name__}: {e}", "FAIL")
    return check


def audit_mangago(session, source, test):
    base = source["baseUrl"]
    query = test["query"]
    check = Check(source=source["name"], query=query, title=None, url=None)
    try:
        r = get(session, f"{base}/r/l_search", params={"name": query, "page": 1})
        r.raise_for_status()
        doc = BeautifulSoup(r.text, "html.parser")
        containers = doc.select(".updatesli, .pic_list > li")
        parsed = []
        for e in containers:
            link = e.select_one(".thm-effect")
            title = link.get("title", "").strip() if link else ""
            if link and title:
                parsed.append({"title": title, "url": urljoin(base, link.get("href"))})
        check.search_raw = len(containers)
        check.search_parsed = len(parsed)
        if len(parsed) < len(containers):
            check.add(f"A busca retornou {len(containers)} cards, mas {len(containers)-len(parsed)} seriam descartados pelo parser atual.", "FAIL")
        chosen = pick_result(parsed, test.get("expectTitle")) or (parsed[0] if parsed else None)
        if not chosen:
            check.add("Nenhum resultado utilizável para esta busca.", "WARN")
            return check
        check.title, check.url = chosen["title"], chosen["url"]
        page = get(session, chosen["url"])
        page.raise_for_status()
        detail = BeautifulSoup(page.text, "html.parser")
        rows = detail.select("table#raws_table > tbody > tr, table#chapter_table > tbody > tr, table.uk-table > tbody > tr")
        parsed_rows = []
        for row in rows:
            link = row.select_one("a.chico")
            if link and link.get_text(" ", strip=True):
                parsed_rows.append(urljoin(base, link.get("href")))
        check.chapters_declared = declared_chapter_count(detail.get_text(" ", strip=True))
        check.chapters_raw = len(rows)
        check.chapters_parsed = len(parsed_rows)
        check.duplicate_chapters = len(parsed_rows) - len(set(parsed_rows))
        check.pagination_detected = bool(detail.select("#chapter_table + .pagination, .chapter_list .pagination, .pagination a[rel=next]"))
        if len(parsed_rows) < len(rows):
            check.add(f"A tabela possui {len(rows)} linhas, mas {len(rows)-len(parsed_rows)} não têm link `a.chico` utilizável.", "FAIL")
        if check.duplicate_chapters:
            check.add(f"Foram detectadas {check.duplicate_chapters} URLs duplicadas na lista de capítulos.", "FAIL")
        if check.chapters_declared is not None and check.chapters_declared != check.chapters_parsed:
            check.add(f"A página declara {check.chapters_declared} capítulos; o parser encontra {check.chapters_parsed}.", "FAIL")
        if check.pagination_detected:
            check.add("Há paginação associada à lista de capítulos; revisar cobertura total.", "WARN")
    except requests.RequestException as e:
        check.add(f"Falha/timeout de rede: {e}", "BLOCKED")
    except Exception as e:
        check.add(f"Erro de auditoria: {type(e).__name__}: {e}", "FAIL")
    return check


def audit_mangak(session, source, test):
    base = source["baseUrl"]
    api = "https://api." + base.split("//", 1)[1].strip("/")
    query = test["query"]
    check = Check(source=source["name"], query=query, title=None, url=None)
    try:
        r = get(session, f"{api}/titles/search", params={"page": 1, "limit": 24, "q": query})
        r.raise_for_status()
        payload = r.json()
        data = payload.get("data") or {}
        items = data.get("items") or []
        check.search_raw = len(items)
        check.search_parsed = sum(1 for x in items if all(k in x for k in ("id", "name", "cover", "url")))
        if check.search_parsed < check.search_raw:
            check.add(f"A API retornou {check.search_raw} itens, mas {check.search_raw-check.search_parsed} não têm todos os campos exigidos pelo DTO atual.", "FAIL")
        candidates = [{"title": x.get("name", ""), "url": urljoin(base, x.get("url", "")), "id": x.get("id")} for x in items if x.get("id") and x.get("name")]
        chosen = pick_result(candidates, test.get("expectTitle")) or (candidates[0] if candidates else None)
        if not chosen:
            check.add("Nenhum resultado utilizável para esta busca.", "WARN")
            return check
        check.title, check.url = chosen["title"], chosen["url"]
        chapters_resp = get(session, f"{api}/titles/{chosen['id']}/chapters", params={"cv": int(time.time() * 1000)})
        chapters_resp.raise_for_status()
        chapter_payload = chapters_resp.json()
        chapter_data = chapter_payload.get("data") or {}
        chapters = chapter_data.get("chapters") or []
        valid = [x for x in chapters if x.get("url") and x.get("name")]
        urls = [x.get("url") for x in valid]
        check.chapters_raw = len(chapters)
        check.chapters_parsed = len(valid)
        check.duplicate_chapters = len(urls) - len(set(urls))
        if len(valid) < len(chapters):
            check.add(f"A API retornou {len(chapters)} capítulos, mas {len(chapters)-len(valid)} não têm nome/URL e seriam parcialmente inúteis.", "WARN")
        if check.duplicate_chapters:
            check.add(f"Foram detectadas {check.duplicate_chapters} URLs de capítulos duplicadas na API.", "FAIL")
        for key in ("total", "count", "total_count"):
            if isinstance(chapter_data.get(key), int):
                check.chapters_declared = chapter_data[key]
                break
        if check.chapters_declared is not None and check.chapters_declared != check.chapters_raw:
            check.add(f"A API declara {check.chapters_declared} capítulos, mas devolveu {check.chapters_raw} nesta chamada única.", "FAIL")
        pagination = chapter_data.get("pagination") or {}
        check.pagination_detected = bool(pagination.get("has_next") or pagination.get("hasNext") or chapter_data.get("has_next"))
        if check.pagination_detected:
            check.add("A API informa página seguinte para capítulos, mas a extensão faz apenas uma chamada.", "FAIL")
    except requests.RequestException as e:
        check.add(f"Falha/timeout de rede: {e}", "BLOCKED")
    except Exception as e:
        check.add(f"Erro de auditoria: {type(e).__name__}: {e}", "FAIL")
    return check


DRIVERS = {
    "bodinho": audit_bodinho,
    "bryaoi": audit_bryaoi,
    "manhwazone": audit_manhwazone,
    "mangago": audit_mangago,
    "mangak": audit_mangak,
}


def markdown(report):
    lines = [
        "# XBL Source Audit",
        "",
        f"Gerado em **{report['generatedAt']}**.",
        "",
        "Esta auditoria procura obras que a busca pode descartar, capítulos que o parser pode deixar de indexar, duplicatas e sinais de paginação não percorrida.",
        "",
        "| Fonte | Busca | Obra testada | Busca raw/parser | Caps declarados/raw/parser | Status |",
        "|---|---|---|---:|---:|---|",
    ]
    for c in report["checks"]:
        search = f"{c['search_raw'] if c['search_raw'] is not None else '-'} / {c['search_parsed'] if c['search_parsed'] is not None else '-'}"
        caps = f"{c['chapters_declared'] if c['chapters_declared'] is not None else '-'} / {c['chapters_raw'] if c['chapters_raw'] is not None else '-'} / {c['chapters_parsed'] if c['chapters_parsed'] is not None else '-'}"
        title = (c.get("title") or "-").replace("|", "\\|")
        lines.append(f"| {c['source']} | `{c['query']}` | {title} | {search} | {caps} | **{c['status']}** |")
    lines += ["", "## Achados", ""]
    any_notes = False
    for c in report["checks"]:
        if c.get("notes"):
            any_notes = True
            lines.append(f"### {c['source']} — `{c['query']}` — {c['status']}")
            for note in c["notes"]:
                lines.append(f"- {note}")
            if c.get("url"):
                lines.append(f"- Obra analisada: {c['url']}")
            lines.append("")
    if not any_notes:
        lines.append("Nenhuma discrepância foi encontrada nesta bateria.")
    lines += [
        "",
        "## Legenda",
        "",
        "- **PASS**: nenhum indício de perda na amostra.",
        "- **WARN**: comportamento que merece inspeção, mas não prova perda de conteúdo.",
        "- **BLOCKED**: o site/API impediu ou excedeu o tempo da auditoria.",
        "- **FAIL**: discrepância concreta entre conteúdo retornado/declarado e o que o parser consegue indexar.",
    ]
    return "\n".join(lines) + "\n"


def main():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8"})
    checks = []
    for source in config["sources"]:
        driver = DRIVERS[source["driver"]]
        for test in source.get("tests", []):
            print(f"[audit] {source['name']}: {test['query']}", flush=True)
            checks.append(driver(session, source, test))
    generated = datetime.now(timezone.utc).isoformat(timespec="seconds")
    report = {"generatedAt": generated, "checks": [asdict(c) for c in checks]}
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "latest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (RESULTS / "latest.md").write_text(markdown(report), encoding="utf-8")
    summary = {s: sum(1 for c in checks if c.status == s) for s in ("PASS", "WARN", "BLOCKED", "FAIL")}
    print(json.dumps(summary, ensure_ascii=False))
    # Auditoria não derruba o workflow por diferenças de site: queremos sempre publicar o relatório.
    return 0


if __name__ == "__main__":
    sys.exit(main())
