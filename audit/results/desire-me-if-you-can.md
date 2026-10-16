# XBL — Desire Me If You Can

Auditoria pontual executada em 2026-10-16 para verificar presença da obra, cobertura de capítulos e possíveis falhas de indexação nas cinco fontes da primeira bateria.

| Fonte | Obra encontrada no site | Encontrada pela lógica atual da extensão | Conteúdo/capítulos observados | Resultado |
|---|---|---|---|---|
| Bodinho Yaoi | Sim — `Desire Me If You Can` | Sim | 21 capítulos de manhwa, Cap. 01–21 | PASS |
| BR Yaoi | Sim — `Deseje-me se puder` (alias: `Desire me if you can`) | Sim | A fonte expõe centenas de entradas; a amostra verificada corresponde a conteúdo em prosa/novel, não às páginas do manhwa | PASS com ressalva |
| ManhwaZone | Não localizado | Não | A busca por `desire me if you can` retorna títulos relacionados, mas nenhum é a obra de Grayson Miller/Dane Stryker | NOT FOUND |
| Mangago | Sim — `Desire Me if You Can` | **Sim** | Página direta tem 47 linhas de release, 31 labels únicos, do Ch.0 ao Ch.30; duplicatas são versões/scanlators | **PASS** |
| MangaK | Sim — `Desire Me if You Can` | Sim | API retorna entradas até Ch.30, incluindo Ch.1.1, notices e promo | PASS |

## Correção do achado anterior

A primeira leitura da auditoria marcou o Mangago como `SEARCH_MISS`, mas isso foi um falso positivo do próprio auditor.

O HTML ao vivo da busca do Mangago contém explicitamente o card:

`<a class="thm-effect" title="Desire Me if You Can" href="https://www.mangago.me/read-manga/desire_me_if_you_can/">`

A extensão atual usa exatamente os seletores `.updatesli, .pic_list > li` e, dentro do card, `.thm-effect`, lendo o atributo `title`. Portanto, **o parser atual do Mangago deve indexar Desire Me If You Can normalmente**.

O erro estava na configuração do teste: para esse caso `expectTitle` estava nulo, então o auditor escolheu automaticamente o primeiro resultado da busca (`Tell Me You Can Hear It`) e o relatório anterior interpretou isso incorretamente como se a obra desejada tivesse sido descartada.

## Cobertura por idioma

- Bodinho Yaoi: PT-BR, 21 capítulos do manhwa.
- BR Yaoi: PT-BR, mas a obra encontrada corresponde a conteúdo em prosa/novel; não deve ser tratada como equivalente ao manhwa para comparação de capítulos.
- ManhwaZone: obra não encontrada nesta consulta.
- Mangago: EN, até Ch.30 no momento do teste.
- MangaK: EN, até Ch.30 no momento do teste.

## Conclusão

Para o manhwa `Desire Me If You Can`, as melhores fontes desta amostra são:

1. **MangaK** — encontra a obra e indexa o conteúdo disponível até Ch.30.
2. **Mangago** — também possui a obra até Ch.30 e o parser atual é compatível com o card real da busca.
3. **Bodinho Yaoi** — melhor opção PT-BR da amostra, mas está em Ch.21.

Não há, neste momento, evidência de que a extensão Mangago precise de correção para esta obra. A parte que precisa ser endurecida é o auditor, para exigir correspondência exata do título quando estivermos testando uma obra específica.
