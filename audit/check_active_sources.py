#!/usr/bin/env python3
"""Lightweight availability audit for every active XBL catalog source."""
import json
from datetime import datetime, timezone
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
catalog = json.loads((ROOT / "index.json").read_text(encoding="utf-8"))
extensions = catalog["extensionList"]["extensions"]
rows = []
session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0 (compatible; XBLHealth/1.0)", "Accept-Language": "pt-BR,pt;q=0.9"})
for ext in extensions:
    for source in ext["sources"]:
        url = source["homeUrl"]
        item = {"name": source["name"], "url": url, "status": "UNKNOWN", "http": None, "note": ""}
        try:
            response = session.get(url, timeout=20, allow_redirects=True)
            item["http"] = response.status_code
            item["finalUrl"] = response.url
            body = response.text.lower()
            if response.status_code in (401, 402, 403, 429):
                item["status"] = "BLOCKED"
                item["note"] = "Acesso restrito, rate limit ou bloqueio"
            elif response.status_code >= 500:
                item["status"] = "DOWN"
                item["note"] = "Erro de servidor"
            elif response.status_code >= 400:
                item["status"] = "DOWN"
                item["note"] = "Erro HTTP"
            elif any(t in body for t in ("bloqueador detectado", "acesso não validado", "conteúdo bloqueado", "desative o bloqueador")):
                item["status"] = "RESTRICTED"
                item["note"] = "Página respondeu, mas contém bloqueio de leitura"
            elif "text/html" not in response.headers.get("content-type", "").lower() or len(body) < 200:
                item["status"] = "WARN"
                item["note"] = "Resposta curta ou conteúdo inesperado"
            else:
                item["status"] = "UP"
                item["note"] = "Página inicial acessível; leitura no Mihon não testada"
        except requests.RequestException as exc:
            item["status"] = "DOWN"
            item["note"] = type(exc).__name__ + ": " + str(exc)[:160]
        rows.append(item)
        print(f"{item['name']}: {item['status']} ({item['http']})", flush=True)

generated = datetime.now(timezone.utc).isoformat(timespec="seconds")
dest = ROOT / "audit" / "results"
dest.mkdir(parents=True, exist_ok=True)
(dest / "health.json").write_text(json.dumps({"generatedAt": generated, "checks": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
lines = ["# XBL — Disponibilidade das fontes ativas", "", f"Gerado em **{generated}**.", "", "Teste HTTP das páginas iniciais; não confirma busca, capítulos, imagens ou funcionamento no Mihon.", "", "| Fonte | HTTP | Estado | Observação |", "|---|---:|---|---|"]
for r in rows:
    note = r["note"].replace("|", "/").replace("\n", " ")
    lines.append(f"| {r['name']} | {r['http'] or '-'} | **{r['status']}** | {note} |")
(dest / "health.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
