# Xceella BL Repo

Repositório próprio para Madomi/Mihon focado em BL/manhwa, com extensões em inglês e PT-BR compiladas e assinadas pela nossa chave.

## Índice principal

`https://raw.githubusercontent.com/xceella/madomi-bl-repo/main/index.pb`

O catálogo raiz usa builds publicadas nos Releases deste repositório com a assinatura própria do Xceella BL Repo. Fontes upstream são recompiladas por nós e fontes exclusivas podem ser implementadas diretamente no projeto.

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
- Bodinho Yaoi — extensão própria XBL

O MangaDex inclui múltiplos idiomas, entre eles EN e PT-BR.

## Bodinho Yaoi

O Bodinho Yaoi é a primeira extensão criada diretamente para o Xceella BL Repo.

Código:
`custom/pt/bodinhoyaoi/`

Implementação inicial:
- populares pela Biblioteca;
- atualizações recentes;
- busca por título/autor usando `/busca?q=`;
- detalhes básicos da obra;
- lista de capítulos;
- leitura das imagens hospedadas em `media.bodinhoyaoi.com`;
- paginação da Biblioteca.

Como é uma implementação nova, validar no Madomi a navegação real, busca, capítulos e páginas antes de considerá-la estável.

## Assinatura própria

Fingerprint SHA-256 do repositório:

`7A:41:E1:29:8A:15:1D:48:F4:9A:A7:58:08:7E:9B:A3:F8:5E:C0:BF:57:EC:8B:2B:93:C7:54:87:81:D3:18:50`

Como os package names das fontes portadas são preservados, uma extensão instalada anteriormente com outra assinatura precisa ser desinstalada uma vez antes de instalar a nossa build. Depois disso, atualizações XBL usam a mesma assinatura própria.

## Build e manutenção

A lista oficial de fontes está em:

`catalog/sources.json`

O workflow principal está em:

`.github/workflows/build-xbl-catalog.yml`

Ele:
1. baixa a base atual do Keiyoushi;
2. sobrepõe módulos próprios de `custom/` quando existirem;
3. valida os módulos selecionados;
4. compila todas as extensões com nossa keystore;
5. gera APK e JAR assinados por nós;
6. publica os artefatos nos Releases deste repositório;
7. gera `index.json`, `index.pb` e `repo.json` próprios;
8. valida dinamicamente a quantidade de extensões;
9. só substitui o catálogo raiz quando todo o processo termina com sucesso.

Alterações no catálogo, nas extensões próprias ou no tooling principal disparam nova build automaticamente. O workflow também pode ser executado manualmente pelo GitHub Actions.

## Próximas extensões próprias em observação

- DesireScans — `https://desirescans.com/`
- SpringToons — `https://springtoons.com/`
- QToon — `https://qtoon.org/`

## Testes antigos de Comix

As pastas `comix/`, `comix-ws/` e `owned/` registram experimentos anteriores com Comix e com a infraestrutura de assinatura. Elas não são o índice raiz oficial.

## Licenças e atribuições

Consulte `THIRD_PARTY.md`. Código derivado de projetos externos deve preservar as licenças e atribuições correspondentes.
