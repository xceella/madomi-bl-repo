# XBL Source Audit

Gerado em **2026-10-16T01:45:18+00:00**.

Esta auditoria procura obras que a busca pode descartar, capítulos que o parser pode deixar de indexar, duplicatas e sinais de paginação não percorrida.

| Fonte | Busca | Obra testada | Busca raw/parser | Caps declarados/raw/parser | Status |
|---|---|---|---:|---:|---|
| Bodinho Yaoi | `kiss me liar` | Kiss Me Liar | 1 / 1 | - / 80 / 80 | **PASS** |
| BR Yaoi | `kiss me liar` | Kiss Me Liar | 4 / 4 | - / 80 / 80 | **PASS** |
| BR Yaoi | `amber alert` | Amber Alert | 2 / 2 | - / 46 / 46 | **PASS** |
| Mangago | `kiss me liar` | Kiss me, Liar | 1 / 1 | 140 / 140 / 140 | **PASS** |
| Mangago | `dead man's switch` | Dead man Switch | 1 / 1 | 93 / 93 / 93 | **PASS** |
| Mangago | `amber alert` | Amber Alert | 1 / 1 | 140 / 140 / 140 | **PASS** |
| MangaK | `kiss me liar` | Kiss me, Liar | 24 / 24 | - / 98 / 98 | **PASS** |
| MangaK | `dead man's switch` | Dead Man's Switch | 24 / 24 | - / 68 / 68 | **PASS** |
| MangaK | `amber alert` | Amber Alert | 24 / 24 | - / 72 / 72 | **PASS** |

## Achados

Nenhuma discrepância foi encontrada nesta bateria.

## Legenda

- **PASS**: nenhum indício de perda na amostra.
- **WARN**: comportamento que merece inspeção, mas não prova perda de conteúdo.
- **BLOCKED**: o site/API impediu ou excedeu o tempo da auditoria.
- **FAIL**: discrepância concreta entre conteúdo retornado/declarado e o que o parser consegue indexar.
