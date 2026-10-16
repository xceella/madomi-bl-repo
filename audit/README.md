# Auditoria de fontes XBL

Esta pasta verifica se uma fonte pode estar deixando obras ou capítulos de fora sem produzir erro visível no Madomi.

## Primeira bateria

- Bodinho Yaoi
- BR Yaoi
- ManhwaZone
- Mangago
- MangaK

## O que é verificado

1. **Cobertura da busca** — compara os cards/itens retornados pelo site ou API com os que o parser consegue transformar em obras.
2. **Cobertura de capítulos** — compara contagens declaradas, linhas/links/objetos brutos e capítulos realmente indexáveis.
3. **Duplicatas** — procura URLs de capítulos repetidas.
4. **Paginação não percorrida** — sinaliza quando o site/API indica continuação que a extensão pode não estar buscando.
5. **Timeout/bloqueio** — separa falha do site/Cloudflare de falha do parser.

## Resultados

O workflow grava sempre:

- `audit/results/latest.json`
- `audit/results/latest.md`

Status possíveis:

- `PASS`: nenhum indício de perda na amostra;
- `WARN`: suspeita que precisa de inspeção;
- `BLOCKED`: site/API impediu a verificação;
- `FAIL`: discrepância concreta de indexação.

A auditoria não substitui o teste final no Madomi. Ela serve para descobrir onde vale a pena testar manualmente.

## Execução

O GitHub Actions roda:

- manualmente (`workflow_dispatch`);
- quando `audit/config.json`, `audit/run_audit.py` ou o workflow forem alterados;
- toda segunda-feira às 09:00 UTC.

A primeira fase é amostral. Depois de validarmos os drivers, ampliaremos para todas as fontes do catálogo e para mais obras por fonte.
