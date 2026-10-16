# XBL Source Audit

Gerado em **2026-10-16T01:10:24+00:00**.

Esta auditoria procura obras que a busca pode descartar, capítulos que o parser pode deixar de indexar, duplicatas e sinais de paginação não percorrida.

| Fonte | Busca | Obra testada | Busca raw/parser | Caps declarados/raw/parser | Status |
|---|---|---|---:|---:|---|
| Bodinho Yaoi | `release` | Release Your Persona | 1 / 1 | 19 / 19 / 19 | **PASS** |
| Bodinho Yaoi | `jinx` | Jinx | 2 / 2 | 108 / 108 / 108 | **PASS** |
| Bodinho Yaoi | `low tide` | Low Tide In Twilight | 1 / 1 | 118 / 118 / 118 | **PASS** |
| BR Yaoi | `release` | Release Your Persona | 1 / 1 | 0 / 2 / 2 | **FAIL** |
| BR Yaoi | `jinx` | Jinx | 2 / 2 | 1 / 109 / 109 | **FAIL** |
| ManhwaZone | `jinx` | Jinx | 2 / 2 | 84 / 100 / 100 | **FAIL** |
| ManhwaZone | `low tide` | Low Tide in Twilight | 4 / 4 | 69 / 108 / 108 | **FAIL** |
| Mangago | `jinx` | The Jinx's Lover | 1 / 1 | 96 / 96 / 96 | **PASS** |
| Mangago | `low tide` | The Blue Flows | 1 / 1 | 85 / 85 / 85 | **PASS** |
| MangaK | `jinx` | Jinx | 24 / 24 | - / 198 / 198 | **PASS** |
| MangaK | `low tide` | Night by the sea | 24 / 24 | - / 176 / 176 | **PASS** |

## Achados

### BR Yaoi — `release` — FAIL
- A página declara 0 capítulos, mas `.capitulos a` encontra 2.
- Obra analisada: https://bryaoi.com/yaoi/release-your-persona-online/

### BR Yaoi — `jinx` — FAIL
- A página declara 1 capítulos, mas `.capitulos a` encontra 109.
- Obra analisada: https://bryaoi.com/yaoi/jinx-online/

### ManhwaZone — `jinx` — FAIL
- A página declara 84 capítulos; Livewire entregou 100 indexáveis.
- Obra analisada: https://manhwazone.com/series/jinx-p22r2

### ManhwaZone — `low tide` — FAIL
- A página declara 69 capítulos; Livewire entregou 108 indexáveis.
- Obra analisada: https://manhwazone.com/series/low-tide-in-twilight-z460x


## Legenda

- **PASS**: nenhum indício de perda na amostra.
- **WARN**: comportamento que merece inspeção, mas não prova perda de conteúdo.
- **BLOCKED**: o site/API impediu ou excedeu o tempo da auditoria.
- **FAIL**: discrepância concreta entre conteúdo retornado/declarado e o que o parser consegue indexar.
