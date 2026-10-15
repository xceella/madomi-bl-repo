# Xceella BL Repo — arquitetura de extensões próprias

Este arquivo documenta a infraestrutura atual do repositório próprio de extensões BL para Mihon/Madomi.

## Objetivo

- usar uma única identidade de assinatura controlada por nós;
- compilar e publicar nossos próprios APK/JAR;
- poder reaproveitar código aberto de projetos compatíveis sem depender da assinatura deles;
- manter um `index.pb` raiz próprio;
- adicionar novas fontes ao catálogo com o tempo;
- criar extensões do zero quando não existir implementação pronta.

## Estado atual

O catálogo raiz já foi migrado para a nossa assinatura.

Índice principal:

`https://raw.githubusercontent.com/xceella/madomi-bl-repo/main/index.pb`

As 13 extensões atuais são compiladas e assinadas pela nossa infraestrutura:

### EN
1. YaoiScan
2. Yaoihub
3. Mangago
4. Orchisasia
5. MangaK
6. MangaDex
7. MangaPark.tv (unoriginal)
8. ManhwaZone

### PT-BR
9. BR Yaoi
10. Coven Scan
11. Fleur Blanche
12. Portal Yaoi
13. XXX Yaoi

A fonte oficial do catálogo está em `catalog/sources.json`.

## Workflow principal

`.github/workflows/build-xbl-catalog.yml`

Fluxo:
1. clona `keiyoushi/extensions-source`;
2. confere se todos os módulos declarados existem;
3. prepara a nossa keystore;
4. compila os 13 módulos com a nossa assinatura;
5. publica APK/JAR em Releases deste repositório;
6. monta um catálogo temporário;
7. valida que as 13 extensões estão presentes;
8. só então promove `index.pb`, `index.json` e `repo.json` para a raiz.

Se alguma etapa falhar, o índice raiz anterior não é substituído.

## Segredos no GitHub

Os builds usam Repository Secrets:

- `SIGNING_KEY`
- `KEY_STORE_PASSWORD`
- `KEY_PASSWORD`

O alias é detectado automaticamente a partir da keystore. O secret `ALIAS` pode permanecer configurado por compatibilidade com workflows antigos, mas o workflow raiz não depende dele.

Nunca salvar a keystore, senhas ou conteúdo dos secrets em arquivos públicos, commits, Issues ou README.

## Chave pública / fingerprint

SHA-256:

`7A:41:E1:29:8A:15:1D:48:F4:9A:A7:58:08:7E:9B:A3:F8:5E:C0:BF:57:EC:8B:2B:93:C7:54:87:81:D3:18:50`

## Migração de instalações antigas

Os package names upstream são preservados. Isso mantém a identidade lógica das fontes, mas Android não aceita atualizar um APK assinado por outra chave.

Ao trocar uma extensão oficial/terceira pela versão XBL:
1. desinstalar a extensão antiga uma vez;
2. instalar a versão do Xceella BL Repo;
3. a partir daí, futuras atualizações XBL podem ser instaladas normalmente porque continuarão usando a mesma chave.

## Adicionando fontes existentes

Para uma extensão já existente no Keiyoushi, normalmente basta adicionar seu módulo a `catalog/sources.json`. O workflow recompila o catálogo com nossa assinatura.

Antes de adicionar, conferir:
- licença;
- compatibilidade atual;
- domínio/site funcional;
- valor real para nosso catálogo BL.

## Criando extensões próprias

Quando não existir módulo upstream, criaremos a implementação seguindo o padrão atual do Keiyoushi/Mihon e depois a incorporaremos ao mesmo catálogo e à mesma assinatura.

Primeiro candidato: **Bodinho Yaoi** (`https://bodinhoyaoi.com/`).

Outras fontes em observação: DesireScans, SpringToons e QToon.

## Legado

`owned/`, `comix/` e `comix-ws/` são registros dos testes que levaram à infraestrutura atual. Não são o índice raiz oficial.
