# Madomi BL Repo

Repositório personalizado para o Madomi focado em BL/manhwa em inglês.

## Índice principal — Keiyoushi filtrado

URL:
`https://raw.githubusercontent.com/xceella/madomi-bl-repo/main/index.pb`

Fontes incluídas:
- YaoiScan
- Yaoihub
- Mangago
- Orchisasia
- MangaK
- MangaDex
- MangaPark.tv (unoriginal)
- ManhwaZone

Os APKs/JARs dessas fontes continuam sendo baixados dos releases oficiais do Keiyoushi; este índice continua intacto enquanto a infraestrutura própria é testada.

## Nova infraestrutura — Xceella BL Extensions

Estamos migrando gradualmente para extensões compiladas e assinadas por uma chave própria, para podermos manter fontes vindas de projetos diferentes sob a mesma identidade de assinatura.

Primeiro teste: **Comix**.

Quando o primeiro build próprio for concluído, o índice de testes será:

`https://raw.githubusercontent.com/xceella/madomi-bl-repo/main/owned/index.pb`

A automação está em `.github/workflows/build-owned-comix.yml` e a configuração está documentada em `OWNED-EXTENSIONS-SETUP.md`.

Depois de validar o Comix, as 8 fontes atuais serão migradas uma a uma. Só então o índice próprio substituirá o índice raiz.

## Índice legado de teste — Comix externo

URL:
`https://raw.githubusercontent.com/xceella/madomi-bl-repo/main/comix/index.pb`

Esse índice antigo aponta para a build externa do MHRepo/MarBou e foi mantido apenas como registro do teste anterior. A meta agora é substituir isso por uma build nossa, assinada por nossa própria chave.

## Fontes para usar pelo Madomi Web Reader

Por enquanto, sem extensão Mihon/Madomi atual confirmada:
- DesireScans — `https://desirescans.com/`
- SpringToons — `https://springtoons.com/`
- QToon — `https://qtoon.org/`

O QToon possui extensões legadas antigas, mas não entrou no repo porque não há uma implementação atual que valha a pena manter agora.

## Licenças e atribuições

Consulte `THIRD_PARTY.md` para os projetos de código aberto usados como base/referência.
