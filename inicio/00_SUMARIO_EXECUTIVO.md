# Sumário Executivo — Revisão Integrativa da Literatura

**Versão:** 1.0  
**Data:** 2026-05-28  
**Status:** AGUARDANDO AMOSTRA DE CALIBRAÇÃO

---

## Identificação do Estudo

| Campo | Conteúdo |
|---|---|
| **Título provisório** | Design Thinking aplicado à Saúde Positiva: Ecossistemas de Movimento, Lazer e Sono para a Manutenção da Saúde e Prevenção de DCNTs (2010-2026) |
| **Tipo de estudo** | Revisão Integrativa da Literatura |
| **Método** | Mendes, Silveira e Galvão (2008) — 6 etapas |
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

## Estado Atual do Corpus Documental (PRISMA)

| Etapa PRISMA | Quantidade |
|---|---|
| Arquivo Bruto Exportado (WoS/Scopus) | [A depositar] |
| Amostra de Calibração (Fase 0) | [A depositar na pasta de amostra] |
| Após Screening Fase 1 (título + resumo) | — |
| Após leitura na íntegra (Fase 2) | — |
| **Artigos incluídos na revisão** | **0 (Estaca Zero)** |
| Fichamentos concluídos | 0 |
