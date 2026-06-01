<!-- inicio/00_SUMARIO_EXECUTIVO.md | Atualizado em: 01-06-2026 10:19:28(GMT-04:00) -->
# Sumário Executivo — Revisão Integrativa da Literatura

**Versão:** 2.0  
**Data:** 2026-06-01  
**Status:** AGUARDANDO AMOSTRA DE CALIBRAÇÃO

---

## Identificação do Estudo

| Campo | Conteúdo |
|---|---|
| **Título provisório** | Design Thinking aplicado à Saúde Positiva: Ecossistemas de Movimento, Lazer e Sono para a Manutenção da Saúde e Prevenção de DCNTs (2010-2026) |
| **Tipo de estudo** | Revisão Integrativa da Literatura com Síntese Orientada a Design Science Research (DSR) |
| **Método de Análise** | Mendes, Silveira e Galvão (2008) — 6 etapas + Síntese DSR de vom Brocke et al. (2015) |
| **Reporting Standard** | PRISMA 2020 / PRISMA-ScR (Transparência e Rastreabilidade da Triagem) |
| **Período de busca** | 2010-2026 |
| **Bases de dados** | Scopus, Web of Science, PubMed (Recomendada), SPORTDiscus (Recomendada) |
| **Idioma primário** | Todos |
| **Periódico alvo** | A definir |

---

## Pergunta Norteadora (Framework PCC)

- **População**: Praticantes e comunidades em três eixos: Urbano (espaços públicos), Digital (ecossistemas de wellness) e Institucional (escolas/ambientes corporativos).
- **Conceito**: Metodologias de Design Thinking, Service Design e Prototipagem Rápida aplicadas como solução para Wicked Problems em saúde.
- **Contexto**: Promoção da Saúde Positiva e Bem-Estar, com foco em exercício físico, lazer e higiene do sono, fundamentados na Teoria da Autodeterminação (SDT) para adesão a longo prazo.

**Estratégia de Busca (String Técnica)**:
`("Design Thinking" OR "Human-Centered Design" OR "Service Design" OR "Prototyping") AND ("Physical Activity" OR "Sport" OR "Leisure" OR "Sleep Hygiene" OR "Rest") AND ("Self-Determination Theory" OR "Intrinsic Motivation" OR "Autonomy") AND ("Positive Health" OR "Well-being" OR "NCD Prevention")`

---

## Configuração Dinâmica do Projeto

> [!IMPORTANT]
> **Zero Hardcoding:** Todos os parâmetros operacionais (nomes de pastas, endpoints, modelos, critérios de elegibilidade) são definidos em `criteria_config.yaml`.

### Pastas de Trabalho

| Finalidade | Pasta |
|---|---|
| CSV bruto exportado da base de dados | `exportacao` |
| Amostra de calibração — PDFs (Scopus) | `amostra/scopus` |
| Amostra de calibração — CSV (WoS) | `amostra/webofscience` |
| Pool de lotes para triagem em massa | `lotes` |
| Saída do PRISMA (logs e resultados) | `saida` |
| Fichamentos (leitura integral) | `fichamentos` |

### Domínios de Alto Valor

- Design Thinking
- Teoria da Autodeterminação (SDT)
- Salutogênese
- Saúde Positiva
- Wellness

Artigos nos domínios de alto valor receberão classificação `TRENDING_TOPIC` no Log PRISMA.

---

## Critérios de Elegibilidade

### Critérios de Inclusão

- C1 (Temporal): Publicações entre 2010 e 2026.
- C2 (Metodológico): Uso do Design como método de co-criação e resolução de problemas complexos.
- C3 (Interdisciplinar): Cruzamento entre Design e Comportamento/Saúde/Esporte.
- C4 (Condicionalidade de Dieta): Se o estudo focar em dieta, deve ter intervenção conjunta de exercício físico.

### Critérios de Exclusão

- Estudos puramente nutricionais (sem exercício físico).
- Estudos fora do recorte temporal 2010-2026.
- Estudos sem aplicação de métodos de Design para a resolução de problemas de saúde.

---

## Estado Atual do Corpus Documental (PRISMA como Reporting Standard)

> [!NOTE]
> O fluxograma PRISMA é utilizado neste projeto **exclusivamente como ferramenta de transparência e rastreabilidade** da triagem (Reporting Standard), conforme PRISMA 2020 e PRISMA-ScR. A metodologia de **análise e síntese** segue a Revisão Integrativa (Mendes et al.) com orientação DSR (vom Brocke et al.).

| Etapa PRISMA (Reporting) | Quantidade |
|---|---|
| Arquivo Bruto Exportado (API/WoS/Scopus) | [A depositar] |
| Amostra de Calibração (Fase 0 — HITL) | [A coletar via PubMed/EuropePMC/bioRxiv] |
| Após Screening Fase 1 (título + resumo) | — |
| Após leitura na íntegra (Fase 2) | — |
| **Artigos incluídos na revisão** | **0 (Estaca Zero)** |
| Fichamentos concluídos | 0 |
