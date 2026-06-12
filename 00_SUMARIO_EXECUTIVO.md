# Revisão DT: Sumário Executivo e Log PRISMA

Este documento consolida o estado final da Revisão Integrativa, refletindo o diagrama de fluxo metodológico e o rastreamento (auditabilidade) de todas as fases.

## 1. Fluxograma PRISMA Atualizado

```mermaid
flowchart TD
    A[Fase 0: Ingestão de API] -->|Identificados| B(N = 95)
    B --> C[Fase 1: Triagem LLM]
    C -->|Excluídos| D(N = 20)
    C -->|Aprovados| E(N = 75)
    E --> F[Fase 2a: Download de PDFs]
    F -->|Falha/Paywall| G(N = 32)
    F -->|Baixados| H(N = 43)
    H --> I[Fase 2b: Extração Profunda]
    I -->|Gap / Corrompidos| J(N = 6)
    I -->|Fichados com Sucesso| K(N = 37)
    K --> L[Fase 3: Síntese e Redação]
    L --> M([Draft Final Acadêmico])

    style A fill:#e0e7ff,stroke:#6366f1,stroke-width:2px
    style C fill:#dcfce7,stroke:#22c55e,stroke-width:2px
    style F fill:#fce7f3,stroke:#ec4899,stroke-width:2px
    style I fill:#fce7f3,stroke:#ec4899,stroke-width:2px
    style L fill:#f3e8ff,stroke:#a855f7,stroke-width:2px
    style K fill:#22c55e,color:white,font-weight:bold
```

## 2. N Final do Estudo
O *corpus* analítico aprovado para a Síntese Temática é composto por **37 estudos primários**.
Estes artigos passaram por 4 etapas rigorosas de filtros e validações, garantindo alinhamento total aos construtos definidos na ontologia da pesquisa.

## 3. Logs de Auditoria e Transparência
Todos os metadados de exclusões e inferências podem ser auditados no diretório `.agent/data_storage/saida/`:
- **PRISMA_LOG_MASTER.csv**: Detalhamento de cada inclusão/exclusão (Fase 1).
- **DOWNLOAD_MAP.csv**: Rastreamento de origem de cada arquivo físico PDF/XML obtido (Fase 2a).
- **EXTRACTION_LOG.csv**: Log de execução do VLM/LLM sobre os full-texts (Fase 2b).

## 4. Query de Busca Oficial
*(Carregada diretamente do `criteria_config.yaml` original)*
- A busca focou em bases que abordassem Metodologias Ativas e Design Thinking.
