# Madomi BL Repo

Repositório personalizado para o Madomi focado em BL/manhwa, com fontes em inglês e PT-BR.

## Índice principal — Keiyoushi filtrado

URL:
`https://raw.githubusercontent.com/xceella/madomi-bl-repo/main/index.pb`

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

O MangaDex permanece no mesmo pacote e inclui fontes EN e PT-BR.

Os APKs/JARs dessas fontes continuam sendo baixados dos releases oficiais do Keiyoushi; o índice raiz segue usando a assinatura oficial do projeto enquanto nossa infraestrutura própria é desenvolvida.

## Nova infraestrutura — Xceella BL Extensions

Estamos migrando gradualmente para extensões compiladas e assinadas por uma chave própria, para podermos manter fontes vindas de projetos diferentes sob a mesma identidade de assinatura e criar extensões novas quando necessário.

Primeiro teste: **Comix**.

O índice de testes é:
`https://raw.githubusercontent.com/xceella/madomi-bl-repo/main/owned/index.pb`

A automação está em `.github/workflows/build-owned-comix.yml` e a configuração está documentada em `OWNED-EXTENSIONS-SETUP.md`.

O índice próprio (`/owned/index.pb`) é separado do índice principal para que os testes não quebrem o catálogo estável.

## Índice legado de teste — Comix externo

URL:
`https://raw.githubusercontent.com/xceella/madomi-bl-repo/main/comix/index.pb`

Esse índice antigo aponta para a build externa do MHRepo/MarBou e foi mantido apenas como registro do teste anterior. A meta agora é substituir isso por builds nossas, assinadas por nossa própria chave.

## Fontes para usar pelo Madomi Web Reader

Por enquanto, sem extensão Mihon/Madomi atual confirmada:
- DesireScans — `https://desirescans.com/`
- SpringToons — `https://springtoons.com/`
- QToon — `https://qtoon.org/`
- Bodinho Yaoi — `https://bodinhoyaoi.com/`

O Bodinho Yaoi já possui pedido de fonte no Keiyoushi, mas ainda não há extensão pronta confirmada. Ele é candidato para uma extensão própria futura.

## Licenças e atribuições

Consulte `THIRD_PARTY.md` para os projetos de código aberto usados como base/referência.
