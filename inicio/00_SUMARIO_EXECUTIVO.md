# Sumário Executivo — Revisão Integrativa da Literatura

**Versão:** Template  
**Data:** [A definir via `/integrative-review`]  
**Status:** [AGUARDANDO CONFIGURAÇÃO]

> **Este documento é um template.** Os campos abaixo serão preenchidos durante a execução do workflow `/integrative-review`. Mantenha-o no controle de versão do seu repositório de trabalho como registro da identidade da revisão.

---

## Identificação do Estudo

| Campo | Conteúdo |
|---|---|
| **Título provisório** | [A definir via `/integrative-review`] |
| **Tipo de estudo** | Revisão Integrativa da Literatura |
| **Método** | Mendes, Silveira e Galvão (2008) — 6 etapas |
| **Período de busca** | [A definir] |
| **Bases de dados** | [A definir — ex: Web of Science / Scopus] |
| **Idioma primário** | [A definir] |
| **Periódico alvo** | [A definir] |

---

## Pergunta Norteadora

> *[A definir via `/integrative-review` — Fase Exploratória (PICO/PCC)]*

---

## Configuração Dinâmica do Projeto

> [!IMPORTANT]
> **Zero Hardcoding:** Todos os parâmetros operacionais (nomes de pastas, endpoints, modelos, critérios de elegibilidade) são definidos em `criteria_config.yaml`. Esse arquivo é gerado interativamente pelo workflow `/integrative-review` e aprovado pelo pesquisador antes de qualquer processamento em lote.

### Pastas de Trabalho

Os nomes de todas as pastas são definidos durante o preenchimento do painel `/integrative-review`:

| Finalidade | Pasta |
|---|---|
| CSV bruto exportado da base de dados | [A definir no painel] |
| Amostra de calibração — PDFs (Scopus) | [A definir no painel] |
| Amostra de calibração — CSV (WoS) | [A definir no painel] |
| Pool de lotes para triagem em massa | [A definir no painel] |
| Saída do PRISMA (logs e resultados) | [A definir no painel] |
| Fichamentos (leitura integral) | [A definir no painel] |

### Domínios de Alto Valor

{{HIGH_VALUE_DOMAINS}}

Artigos nos domínios de alto valor receberão classificação `TRENDING_TOPIC` no Log PRISMA, permitindo análise isolada de tendências emergentes.

---

## Critérios de Elegibilidade

> [!NOTE]
> Os critérios abaixo serão definidos e aprovados pelo pesquisador durante a análise da amostra de calibração. O workflow `/integrative-review` sugere critérios ativamente com base na amostra depositada.

### Critérios de Inclusão

{{INCLUSION_CRITERIA}}

### Critérios de Exclusão

{{EXCLUSION_CRITERIA}}

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

---

## Próximos Marcos

| Marco | Responsável | Status |
|---|---|---|
| Criar repositório de trabalho e configurar remote | Usuário | PENDENTE |
| Criar e configurar repositório de contexto de sessão | Usuário | PENDENTE |
| Depositar amostra nas pastas de calibração | Usuário | PENDENTE |
| Executar `/integrative-review` e preencher painel | Usuário + IA | PENDENTE |
| Gerar `criteria_config.yaml` e aprovar critérios | Usuário | PENDENTE |
| Screening PRISMA Fase 1 (lotes via Ollama local) | IA (Ollama local) | AGUARDANDO CONFIG |
| Download PDFs aprovados (Unpaywall, PMC, EuropePMC) | IA + Usuário | — |
| Fichamentos (leitura integral) | IA + Revisor Humano | — |
| Síntese e Draft do Artigo | IA + Conselho | — |
