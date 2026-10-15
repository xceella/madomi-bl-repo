# Xceella BL Repo

Repositório próprio para Madomi/Mihon focado em BL/manhwa, com extensões em inglês e PT-BR compiladas e assinadas pela nossa chave.

## Índice principal

`https://raw.githubusercontent.com/xceella/madomi-bl-repo/main/index.pb`

O catálogo raiz não aponta mais para APK/JAR oficiais de terceiros. As extensões abaixo são compiladas a partir do código aberto upstream e publicadas nos Releases deste repositório com a assinatura própria do Xceella BL Repo.

### Fontes em inglês
- YaoiScan
- Yaoihub
- Mangago
- Orchisasia
- MangaK
- MangaDex
- MangaPark.tv (unoriginal)
- ManhwaZone

### Fontes em PT-BR
- BR Yaoi
- Coven Scan
- Fleur Blanche
- Portal Yaoi
- XXX Yaoi

O MangaDex inclui múltiplos idiomas, entre eles EN e PT-BR.

## Assinatura própria

Fingerprint SHA-256 do repositório:

`7A:41:E1:29:8A:15:1D:48:F4:9A:A7:58:08:7E:9B:A3:F8:5E:C0:BF:57:EC:8B:2B:93:C7:54:87:81:D3:18:50`

Como os package names são preservados para manter compatibilidade com as fontes originais, uma extensão instalada anteriormente com a assinatura do Keiyoushi/terceiro precisa ser desinstalada uma vez antes de instalar a nossa build. Depois disso, atualizações futuras do XBL usam a mesma assinatura própria.

## Build e manutenção

A lista oficial de fontes está em:

`catalog/sources.json`

O workflow principal está em:

`.github/workflows/build-xbl-catalog.yml`

Ele:
1. baixa o código atual do Keiyoushi;
2. valida os módulos selecionados;
3. compila todas as extensões com nossa keystore;
4. gera APK e JAR assinados por nós;
5. publica os artefatos nos Releases deste repositório;
6. gera `index.json`, `index.pb` e `repo.json` próprios;
7. só substitui o catálogo raiz quando todo o processo termina com sucesso.

Alterações no catálogo ou no tooling principal disparam uma nova build automaticamente. O workflow também pode ser executado manualmente pelo GitHub Actions.

## Extensões próprias futuras

Quando uma fonte útil não existir em um projeto upstream, ela pode ser implementada diretamente para este repositório seguindo a arquitetura atual do Keiyoushi/Mihon.

Primeiros candidatos:
- Bodinho Yaoi — `https://bodinhoyaoi.com/`
- DesireScans — `https://desirescans.com/`
- SpringToons — `https://springtoons.com/`
- QToon — `https://qtoon.org/`

O Bodinho Yaoi já possui pedido de fonte no Keiyoushi, mas ainda não há extensão pronta confirmada; por isso é o candidato principal para nossa primeira extensão criada do zero.

## Testes antigos de Comix

As pastas `comix/`, `comix-ws/` e `owned/` registram experimentos anteriores com Comix e com a infraestrutura de assinatura. Elas não são o catálogo raiz atual.

## Licenças e atribuições

Consulte `THIRD_PARTY.md`. Código derivado de projetos externos deve preservar as licenças e atribuições correspondentes.
