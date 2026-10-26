# XBL Source Audit

Gerado em **2026-10-26T15:39:36+00:00**.

Esta auditoria procura obras que a busca pode descartar, capítulos que o parser pode deixar de indexar, duplicatas e sinais de paginação não percorrida.

| Fonte | Busca | Obra testada | Busca raw/parser | Caps declarados/raw/parser | Status |
|---|---|---|---:|---:|---|
| Bodinho Yaoi | `release` | - | - / - | - / - / - | **BLOCKED** |
| Bodinho Yaoi | `jinx` | - | - / - | - / - / - | **BLOCKED** |
| Bodinho Yaoi | `low tide` | - | - / - | - / - / - | **BLOCKED** |
| Bodinho Yaoi | `desire me if you can` | - | - / - | - / - / - | **BLOCKED** |
| BR Yaoi | `release` | Release Your Persona | 1 / 1 | - / 2 / 2 | **PASS** |
| BR Yaoi | `jinx` | Jinx | 2 / 2 | - / 109 / 109 | **PASS** |
| BR Yaoi | `desire me if you can` | Deseje-me se puder | 1 / 1 | - / 226 / 226 | **PASS** |
| ManhwaZone | `jinx` | Jinx | 2 / 2 | - / 100 / 100 | **PASS** |
| ManhwaZone | `low tide` | Low Tide in Twilight | 4 / 4 | - / 108 / 108 | **PASS** |
| Mangago | `jinx` | The Jinx's Lover | 1 / 1 | 96 / 96 / 96 | **PASS** |
| Mangago | `low tide` | The Blue Flows | 1 / 1 | 86 / 86 / 86 | **PASS** |
| Mangago | `desire me if you can` | Tell Me You Can Hear It | 1 / 1 | 32 / 32 / 32 | **PASS** |
| MangaK | `jinx` | Jinx | 24 / 24 | - / 198 / 198 | **PASS** |
| MangaK | `low tide` | Night by the sea | 24 / 24 | - / 176 / 176 | **PASS** |
| MangaK | `desire me if you can` | Desire Me if You Can | 24 / 24 | - / 37 / 37 | **PASS** |

## Achados

### Bodinho Yaoi — `release` — BLOCKED
- Falha/timeout de rede: 503 Server Error: Service Unavailable for url: https://bodinhoyaoi.com/sitemap.xml

### Bodinho Yaoi — `jinx` — BLOCKED
- Falha/timeout de rede: 503 Server Error: Service Unavailable for url: https://bodinhoyaoi.com/sitemap.xml

### Bodinho Yaoi — `low tide` — BLOCKED
- Falha/timeout de rede: 503 Server Error: Service Unavailable for url: https://bodinhoyaoi.com/sitemap.xml

### Bodinho Yaoi — `desire me if you can` — BLOCKED
- Falha/timeout de rede: 503 Server Error: Service Unavailable for url: https://bodinhoyaoi.com/sitemap.xml


## Legenda

- **PASS**: nenhum indício de perda na amostra.
- **WARN**: comportamento que merece inspeção, mas não prova perda de conteúdo.
- **BLOCKED**: o site/API impediu ou excedeu o tempo da auditoria.
- **FAIL**: discrepância concreta entre conteúdo retornado/declarado e o que o parser consegue indexar.
