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
    subgraph fase0 [Fase 0: Ingestão & Calibração]
        direction LR
        E[run_ingestion_api.py] -->|Lê query_string| D
        E -->|Modo Calibração (50 artigos)| F((APIs Acadêmicas))
        F --> H[Normalização & Deduplicação]
        H -->|Gera Master Log Temporário| I[(PRISMA_LOG_MASTER.csv)]
        I -.->|Status inicial| J([Todos como 'Aguardando Triagem Fase 1'])
    end

    %% Fase 1
    subgraph fase1 [Fase 1: Triagem Automatizada]
        direction LR
        I -->|Puxa pendentes| K[run_fase1.py]
        K -->|Aplica LLM local| L{Critérios de Inclusão/Exclusão}
        L -->|Sim| M([Status: Incluído Fase 1])
        L -->|Não| N([Status: Excluído Fase 1])
        M --> O[(Atualiza PRISMA_LOG)]
        N --> O
    end

    %% Fase Auditoria e Loop de Calibração HITL
    subgraph auditoria [Fase 0.5: Auditoria & Loop de Calibração HITL]
        direction LR
        O -->|Lê CSV e JSONs| P[generate_progress.py]
        P -->|Gera visualização| Q[PROGRESS.html Dashboard]
        Q -.->|Pesquisador avalia precisão (HITL)| R{Amostra está precisa?}
        R -->|Não: Exporta Feedback JSON| S[IA ajusta prompts no YAML]
        S -->|Reinicia ciclo limpando logs| E
        R -->|Sim: Aprovado| T[Muda Ingestão para Modo Principal = 1000]
        T -->|Ingere base final e roda Triagem real| K
    end

    %% Fase 2
    subgraph fase2 [Fase 2: Extração]
        direction LR
        auditoria --> U[run_fase2_extraction.py]
        U -->|Busca PDFs / XMLs| V[Extração Estruturada via LLM]
        V --> W[(Fichamento JSON)]
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

### Fase 0: Ingestão API-First & Calibração Iterativa
<!-- BEGIN FASE0 -->
**O Nascimento dos Dados e a Prova de Conceito (PoC)**

Nesta fase inicial, o sistema não tenta ler milhares de artigos de uma vez. O script `run_ingestion_api.py` opera inicialmente em **Modo de Calibração**, consultando as bases científicas (PubMed, OpenAlex, etc.) de forma controlada para trazer apenas os primeiros 50 artigos mais relevantes de cada fonte.

- **Por que fazemos isso?** Se os critérios de inclusão (prompts) não estiverem perfeitamente alinhados à sua Pergunta Norteadora, rodar milhares de artigos custaria tempo computacional e geraria "lixo" acadêmico.
- **O que acontece sob o capô:** A IA consome sua `query_string` e faz requisições dinâmicas às APIs, pulando o trabalho braçal de exportar e importar arquivos CSV. Tudo cai em um arquivo unificado chamado `PRISMA_LOG_MASTER.csv`. Cada vez que rodamos esta calibração, o arquivo anterior é limpo para garantir que resíduos não poluam a nova análise.
<!-- END FASE0 -->

### Fase 1: Triagem (Screening Inteligente)
<!-- BEGIN FASE1 -->
**A Peneira de Títulos e Resumos (Screening via LLM Local)**

Com a base amostral pronta, o script `run_fase1.py` entra em ação. Ele pega cada artigo "Aguardando Triagem" e o envia para o modelo de inteligência artificial (LLM).

- **O Motor de Decisão (Chain of Thought):** O modelo é forçado a refletir sobre cada pergunta do seu `criteria_config.yaml`. Ele pensa alto (razão) antes de cravar um SIM ou NÃO. Isso se chama cadeia de raciocínio.
- Se o artigo passar em todas as regras mandatárias, seu status muda para *Incluído Fase 1*. Senão, *Excluído*. O log no PRISMA é imediato.
<!-- END FASE1 -->

### Fase 1.5: Auditoria Visual e Loop HITL (Onde você está agora)
<!-- BEGIN FASE_AUDITORIA -->
**A Hora da Verdade: O Feedback Humano no Loop (Human-in-the-Loop)**

Este **Dashboard Interativo** que você está visualizando foi gerado pelo `generate_progress.py`. O objetivo não é apenas mostrar números bonitos, mas sim auditar as decisões da máquina.

- **Sua Ação Necessária (Calibração):** Abra a lista de incluídos ou excluídos. Se notar que a IA tomou uma decisão errada, use os botões **[👍 Incluir]** ou **[👎 Excluir]** ao lado do artigo e escreva uma breve justificativa (ex: "Excluiu errado pois o artigo falava sobre crianças indiretamente").
- **Retroalimentação:** Ao terminar de revisar a amostra, clique no botão **[📤 Copiar Feedback para IA]** no topo do modal. Cole esse JSON no chat para o agente. A IA usará seus ajustes para reescrever as regras no `criteria_config.yaml`.
- **Avançando:** Apenas quando a IA acertar quase 100% da amostra calibração, nós ativaremos o "Modo Principal" (Ingestão em Massa, ex: 1000 artigos) para realizar a triagem real definitiva.
<!-- END FASE_AUDITORIA -->

### Fase 2: Fichamento / Extração 
<!-- BEGIN FASE2 -->
**Mergulho Profundo: A Leitura Integral**

- Somente os artigos sobreviventes chegam aqui.
- A máquina usa rastreadores acadêmicos (Unpaywall, PMC, Crossref) para tentar realizar o download automático dos PDFs originais.
- Um modelo de visão (Vision-Language Model) mais avançado é ativado para ler o documento inteiro e preencher uma matriz de extração JSON (Fichamento Automático), focado nos construtos de *Design Science Research* e *Contexto Pedagógico*.
<!-- END FASE2 -->

### Fase 3: Síntese (Finalização)
<!-- BEGIN FASE3 -->
**Conclusão e Elaboração Científica**

Aqui os fichamentos isolados são unidos. Padrões emergem. Categorias temáticas (como as de Bardin ou Thematic Analysis) são sugeridas e cruzadas com a sua ontologia. Nasce o rascunho do estado da arte da sua revisão.
<!-- END FASE3 -->
