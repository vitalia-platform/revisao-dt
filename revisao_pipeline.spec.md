# Especificação e Organograma Visual do Pipeline (Revisão DT) - Modo API-First

Este documento mapeia o fluxo real atualizado do sistema. A grande mudança arquitetural é a eliminação do trabalho braçal de baixar CSVs: o sistema agora opera via APIs conectadas diretamente às bases científicas.

---

## 1. Organograma Metodológico (Macro Fluxo Real)

Abaixo está o diagrama exato da jornada de um artigo científico no nosso sistema, focado na ingestão automatizada via API.

```mermaid
flowchart TD
    %% Fase Inicial
    subgraph ideacao [Ideação & Configuração]
        direction LR
        A[Usuário usa /integrative-review] --> B[Geração de Search Strings]
        B --> C[Salva `query_string`]
        C -->|Configura parâmetros| D(criteria_config.yaml)
    end

    %% Fase 0
    subgraph fase0 [Fase 0: Ingestão API-First]
        direction LR
        E[run_ingestion_api.py] -->|Lê query_string| D
        E -->|eSearch & eFetch| F((PubMed API))
        E -->|REST API| G((OpenAlex API))
        F --> H[Normalização & Deduplicação]
        G --> H
        H -->|Gera Master Log| I[(PRISMA_LOG_MASTER.csv)]
        I -.->|Status inicial| J([Todos como 'Aguardando Triagem Fase 1'])
    end

    %% Fase 1
    subgraph fase1 [Fase 1: Triagem]
        direction LR
        I -->|Puxa pendentes| K[run_fase1.py]
        K -->|Aplica LLM| L{Critérios de Inclusão/Exclusão}
        L -->|Sim| M([Status: Incluído Fase 1])
        L -->|Não| N([Status: Excluído Fase 1])
        M --> O[(Atualiza PRISMA_LOG)]
        N --> O
    end

    %% Fase Auditoria
    subgraph auditoria [Auditoria Visual]
        direction LR
        O -->|Lê CSV e JSONs| P[generate_progress.py]
        P -->|Gera| Q[PROGRESS.html Dashboard]
        Q -.->|Human-in-the-Loop| R{Auditor Humano Aprova?}
        R -->|Ajustes no Prompt| K
        R -->|Aprovado| S[Avançar para Extração]
    end

    %% Fase 2
    subgraph fase2 [Fase 2: Extração]
        direction LR
        S --> T[run_fase2_extraction.py]
        T -->|Busca PDFs / XMLs| U[Extração Estruturada via LLM]
        U --> V[(Fichamento JSON)]
    end

    %% Fase 3
    subgraph fase3 [Fase 3: Síntese]
        direction LR
        V --> W[Scripts de Síntese]
        W --> X([Relatório/Artigo Final])
    end

    style ideacao fill:#f3f4f6,stroke:#9ca3af,stroke-width:2px
    style fase0 fill:#e0e7ff,stroke:#6366f1,stroke-width:2px
    style fase1 fill:#dcfce7,stroke:#22c55e,stroke-width:2px
    style auditoria fill:#fef3c7,stroke:#f59e0b,stroke-width:2px
    style fase2 fill:#fce7f3,stroke:#ec4899,stroke-width:2px
    style fase3 fill:#f3e8ff,stroke:#a855f7,stroke-width:2px
```

---

## 2. Detalhamento Técnico das Fases (A Jornada do Dado)

### Ideação & Configuração (O Fim do Download Manual)
<!-- BEGIN FASE_IDEACAO -->
Você definiu a `query_string` no arquivo `criteria_config.yaml`.
Não há mais a necessidade de acessar os sites, exportar CSVs e colocá-los na pasta `exportacao`. O sistema agora é autônomo.
<!-- END FASE_IDEACAO -->

### Fase 0: Ingestão API-First (O Nascimento dos Artigos)
<!-- BEGIN FASE0 -->
- **Script Alvo:** `scripts/review_pipeline/run_ingestion_api.py`
- **O que faz:** Ele lê a `query_string` do seu YAML e faz requisições diretas via rede para as APIs do **PubMed** e **OpenAlex**.
- **Processamento:** Ele padroniza as colunas e remove artigos duplicados usando o DOI dinamicamente.
- **Saída:** Ele cria e popula diretamente o arquivo mestre `.agent/data_storage/saida/PRISMA_LOG_MASTER.csv`. 
- **Conceito Chave:** Todo artigo recém-baixado da API entra com o status `"Aguardando Triagem Fase 1"`.
<!-- END FASE0 -->

### Fase 1: Triagem (Screening via trAIce)
<!-- BEGIN FASE1 -->
- **Script Alvo:** `scripts/review_pipeline/run_fase1.py`
- **O que faz:** Lê o arquivo mestre, filtra quem está "Aguardando", envia para o Ollama local aplicar os critérios do YAML, gera o Raciocínio (Reasoning) com CoT e atualiza o status de volta no CSV para Incluído ou Excluído.
<!-- END FASE1 -->

### Fase 1.5: Auditoria & HITL (Human-in-the-Loop)
<!-- BEGIN FASE_AUDITORIA -->
- **Script Alvo:** `scripts/generate_progress.py`
- **O que faz:** Renderiza os resultados da triagem em um Dashboard HTML interativo. Permite auditar exatamente as justificativas da IA para refinar os prompts ou critérios antes da fase pesada de leitura de PDFs.
<!-- END FASE_AUDITORIA -->

### Fase 2: Fichamento / Extração 
<!-- BEGIN FASE2 -->
- **Script Alvo:** `scripts/review_pipeline/run_fase2_extraction.py`
- **O que faz:** Atua exclusivamente sobre os artigos aprovados na Fase 1. Lê o PDF ou XML completo e solicita ao LLM a extração de dados estruturados em JSON respondendo a perguntas metodológicas específicas.
<!-- END FASE2 -->

### Fase 3: Síntese (Finalização)
<!-- BEGIN FASE3 -->
- Consome todos os dados da Fase 2 para gerar os resumos finais, tabelas analíticas e os rascunhos do artigo científico final da revisão.
<!-- END FASE3 -->
