# XBL — Desire Me If You Can

Auditoria pontual executada em 2026-10-16 para verificar presença da obra, cobertura de capítulos e possíveis falhas de indexação nas cinco fontes da primeira bateria.

| Fonte | Obra encontrada no site | Encontrada pela lógica atual da extensão | Conteúdo/capítulos observados | Resultado |
|---|---|---|---|---|
| Bodinho Yaoi | Sim — `Desire Me If You Can` | Sim | 21 capítulos de manhwa, Cap. 01–21 | PASS |
| BR Yaoi | Sim — `Deseje-me se puder` (alias: `Desire me if you can`) | Sim | A fonte expõe centenas de entradas; amostra verificada é conteúdo em prosa/novel, não páginas do manhwa | PASS com ressalva |
| ManhwaZone | Não localizado | Não | A busca por `desire me if you can` retorna 24 títulos, mas nenhum é a obra de Grayson Miller/Dane Striker | NOT FOUND |
| Mangago | Sim — `Desire Me if You Can (Yaoi)` | **Não pela busca atual da extensão** | Página direta tem 47 linhas de release, 31 labels únicos, do Ch.0 ao Ch.30; duplicatas são versões/scanlators | **SEARCH_MISS** |
| MangaK | Sim — `Desire Me if You Can` | Sim | API retorna 35 entradas indexáveis: capítulos até Ch.30, incluindo Ch.1.1, 2 notices e 1 promo | PASS |

## Achado principal

### Mangago — SEARCH_MISS

O site retorna `DesireMeifYouCan` na busca e a página direta existe em:

`https://www.mangago.me/read-manga/desire_me_if_you_can/`

Porém, a lógica atual da extensão usa os seletores de cards `.updatesli, .pic_list > li` + `.thm-effect`. Na auditoria automatizada da mesma consulta, apenas um resultado foi montado pelo parser, e era um título diferente. Portanto, esta é uma falha real de indexação de obra na busca da extensão: o BL existe no Mangago, mas pode não aparecer no Madomi pela pesquisa normal.

A página direta da obra possui 47 linhas de release e 31 capítulos/labels únicos, com o capítulo mais alto em Ch.30. Os itens duplicados correspondem principalmente a versões/scanlators diferentes.

## Cobertura por idioma

- Bodinho Yaoi: PT-BR, 21 capítulos do manhwa.
- BR Yaoi: PT-BR, mas a obra encontrada corresponde a conteúdo em prosa/novel; não deve ser tratada como equivalente ao manhwa para comparação de capítulos.
- ManhwaZone: obra não encontrada nesta consulta.
- Mangago: EN, até Ch.30 no momento do teste.
- MangaK: EN, até Ch.30 no momento do teste.

## Conclusão

Para o manhwa `Desire Me If You Can`, as melhores fontes desta amostra são:

1. **MangaK** — encontra a obra e indexa o conteúdo disponível até Ch.30.
2. **Mangago** — também tem até Ch.30, mas a busca da extensão precisa ser corrigida para a obra aparecer normalmente.
3. **Bodinho Yaoi** — melhor opção PT-BR da amostra, mas está em Ch.21.

O caso do Mangago confirma o tipo de problema que motivou a auditoria: uma obra pode existir no site e ficar invisível na extensão por causa do parser de busca.
