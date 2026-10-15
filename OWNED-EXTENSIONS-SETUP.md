# Xceella BL Extensions — configuração inicial

Este arquivo documenta a migração do repositório filtrado para extensões compiladas e assinadas por nós.

## Objetivo

- manter uma única identidade de assinatura para extensões próprias;
- poder portar extensões abertas de outros projetos compatíveis;
- poder criar fontes novas quando não existir extensão pronta;
- publicar APK/JAR em GitHub Releases;
- gerar `index.pb` compatível com Mihon/Madomi.

## Situação atual

O índice raiz (`/index.pb`) continua funcionando com as 8 fontes filtradas do Keiyoushi.

A infraestrutura própria está sendo criada separadamente em `/owned/index.pb` para não quebrar o que já funciona. Quando todas as fontes importantes forem migradas para a nossa assinatura, o índice próprio poderá substituir o índice raiz.

## Primeira extensão própria

Comix (`https://comix.to`) será a primeira extensão de teste.

O workflow manual está em:

`.github/workflows/build-owned-comix.yml`

Ele:
1. baixa o código aberto do Comix;
2. compila a extensão;
3. assina APK/JAR com a nossa chave;
4. publica os arquivos em GitHub Releases;
5. gera `/owned/index.pb` com a nossa assinatura;
6. salva o índice automaticamente no repositório.

## Segredos necessários no GitHub

Em **Settings → Secrets and variables → Actions → Repository secrets**, criar exatamente estes quatro secrets:

- `SIGNING_KEY`
- `KEY_STORE_PASSWORD`
- `ALIAS`
- `KEY_PASSWORD`

Nunca adicionar esses valores em commits, README, Issues ou arquivos públicos.

## Chave pública/fingerprint

Fingerprint SHA-256 da chave criada para este projeto:

`7A:41:E1:29:8A:15:1D:48:F4:9A:A7:58:08:7E:9B:A3:F8:5E:C0:BF:57:EC:8B:2B:93:C7:54:87:81:D3:18:50`

O índice grava a forma normalizada sem `:` automaticamente.

## Depois dos secrets

Executar manualmente em **Actions → Build owned Comix → Run workflow**.

Se o build passar, o novo índice será:

`https://raw.githubusercontent.com/xceella/madomi-bl-repo/main/owned/index.pb`

Esse índice terá somente extensões assinadas por nossa própria chave.

## Migração futura

Depois de validar o Comix:

1. migrar YaoiScan;
2. migrar Yaoihub;
3. migrar Mangago;
4. migrar Orchisasia;
5. migrar MangaK;
6. migrar MangaDex;
7. migrar MangaPark.tv;
8. migrar ManhwaZone;
9. desenvolver fontes novas para DesireScans, SpringToons e QToon quando viável.

Durante a migração, o índice antigo continua intacto como fallback.
