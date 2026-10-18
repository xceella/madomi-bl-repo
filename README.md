# XBL — Mihon PT-BR

Repositório pessoal de extensões **exclusivamente em português brasileiro**, voltado à leitura de BL/manhwa no **Mihon**. Mantém o histórico técnico e a assinatura do antigo projeto Madomi, mas **não depende de Madomi nem de tradução automática**.

## Adicionar ao Mihon (atualizado)

Copie o endereço do nosso catálogo moderno:

```text
https://raw.githubusercontent.com/xceella/madomi-bl-repo/main/index.pb
```

No Mihon: **Mais → Configurações → Navegar → Repositórios de extensões → Adicionar**. Cole o endereço, depois entre em **Navegar → Extensões** e atualize a lista. O formato `index.pb` é destinado às versões atuais do Mihon (0.20.1 ou mais recentes).

**Importante:** o caminho antigo do GitHub (`madomi-bl-repo`) permanece por compatibilidade e histórico; o catálogo exibido passa a se chamar **XBL — Mihon PT-BR**.

## Fontes ativas — somente PT-BR

| Extensão | Implementação |
|---|---|
| Bodinho Yaoi | Extensão própria XBL, em `custom/pt/bodinhoyaoi/` |
| BR Yaoi | Base Keiyoushi |
| Coven Scan | Base Keiyoushi |
| Fleur Blanche | Base Keiyoushi |
| Portal Yaoi | Base Keiyoushi |
| XXX Yaoi | Base Keiyoushi |
| Nocturne Summer (Nocturne Fansub) | Base Keiyoushi |
| FlowerManga.net (Flower Mangas) | Base Keiyoushi |

As fontes antes em inglês (Mangago, MangaK, YaoiScan, Yaoihub, Orchisasia, MangaPark, ManhwaZone) e o MangaDex multilíngue **não integram mais o catálogo ativo**. Os artefatos e relatórios históricos ficam arquivados no GitHub; os releases antigos não são listados no índice atual.

## Instalação, assinatura e biblioteca

As extensões são **compiladas do código-fonte** (Keiyoushi ou extensão própria) e assinadas com a mesma chave privada XBL utilizada nas builds anteriores. Fingerprint SHA-256:

```text
7A:41:E1:29:8A:15:1D:48:F4:9A:A7:58:08:7E:9B:A3:F8:5E:C0:BF:57:EC:8B:2B:93:C7:54:87:81:D3:18:50
```

Caso a mesma extensão já esteja instalada por outro repositório com assinatura diferente, **faça antes um backup da biblioteca do Mihon**. Pode ser necessária a desinstalação da APK antiga para instalar a versão XBL. Não desinstale o Mihon nem apague seus dados. Ter o mesmo identificador de extensão não garante atualização direta entre assinaturas distintas.

## Build e validação

A seleção oficial está em [`catalog/sources.json`](catalog/sources.json) e o workflow em [`.github/workflows/build-xbl-catalog.yml`](.github/workflows/build-xbl-catalog.yml). Cada build baixa as extensões mantidas no Keiyoushi, compila as 8 escolhidas, assina e publica APKs/JARs em Releases e gera o catálogo `index.pb`, `index.json` e `repo.json` na raiz.

O workflow recusa módulos fora de `src/pt/` e metadados de fonte diferentes de `pt-BR`, para impedir a reintrodução acidental de fontes em inglês.

**Validação no dispositivo:** build e catálogo válidos não comprovam que buscas, capítulos e páginas carregam no Mihon. Cada fonte nova precisa de teste real de instalação, busca, contagem e leitura; Cloudflare e mudanças de domínio podem afetar o funcionamento.

## Auditorias e histórico

Os scripts em `audit/` e seus relatórios antigos foram preservados para histórico. Parte deles menciona sites em inglês, **mas isso não significa que essas fontes estejam disponíveis no Mihon via XBL**. Nosso foco atual é disponibilidade em PT-BR. Trabalhos experimentais anteriores (`comix/`, `comix-ws/`, `owned/`) não integram o catálogo ativo.

## Créditos e licença

As extensões importadas derivam de [Keiyoushi / extensions-source](https://github.com/keiyoushi/extensions-source). Consulte [`THIRD_PARTY.md`](THIRD_PARTY.md) para atribuições e licenças. O Mihon é independente deste repositório.
