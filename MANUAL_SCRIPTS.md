<!-- MANUAL_SCRIPTS.md | Atualizado em: 10-06-2026 -->
# Manual do Pipeline de Revisão Integrativa 📖

Este manual documenta o funcionamento, invocação e opções dos scripts do pipeline automatizado da plataforma Vitalia.

## 🏗️ Como os Dados Fluem no Sistema (Arquitetura Dual-Git e API-First)

A arquitetura foi projetada para ser **tolerante a falhas**, **interrompível** e utilizar **Armazenamento de Dados Isolado**. Todos os dados da revisão são manipulados de forma isolada na pasta `.agent/data_storage/` com symlinks na raiz.

1. **Ingestão Direta (`run_ingestion_api.py`)**: O pipeline busca automaticamente os artigos diretamente via API no PubMed e OpenAlex, criando o Log PRISMA inicial de forma centralizada e sem intervenção manual com CSVs brutos.
2. **`saida/PRISMA_LOG_MASTER.csv` (O Coração do Sistema)**: Planilha mestre consolidada com a coluna `Status`, que dita qual será a próxima ação.
3. **`saida/auditoria/` (O Cérebro da Auditoria)**: Cada fase gera shards JSON (`1717800000_audit.json`) isolados por subpastas (ex: `fase1_screening`, `fase2a_download`). Eles contêm prompts, respostas do LLM, metadados e performance (latência, tokens) para auditoria rigorosa financeira e de raciocínio.

---

## 🛠️ Kit de Ferramentas Shell (Operações e DevOps)
Localizados na pasta `scripts/`, estes utilitários em bash (.sh) gerenciam a infraestrutura da esteira:

### `scripts/reset.sh` (O Orquestrador de Limpeza)
O canivete suíço para gerenciar os dados em cache e iniciar rodadas limpas. Sempre invocado no terminal: `bash scripts/reset.sh [opção]`
- `--soft` (ou `-s`): **Uso mais comum.** Preserva o Master Log (a Ingestão não é perdida), mas "rebobina" o Status de todos os artigos para "Aguardando Triagem". Apaga as extrações das Fases 1 a 3. Ideal para testar novos Prompts.
- `--hard` (ou `-h`): Destruição total. Apaga todo o diretório `saida` e `fichamentos`. Usado para iniciar um estudo inteiramente do zero.
- `--ui-only`: Apenas apaga e recria os arquivos HTML (PROGRESS e LIVE_PROGRESS) caso algo trave no cache do navegador.
- `--start` (ou `-a`): Flag auxiliar. Se anexada ao comando, o script irá emendar o reset e já iniciar a próxima etapa automaticamente (Ingestão se `--hard`, Triagem se `--soft`).

### `scripts/run_pipeline.sh` (O Modo Autônomo "Produção")
Roda o funil inteiro de ponta a ponta na sequência metodológica correta: Ingestão ➔ Triagem ➔ Download ➔ Síntese. Ele monitora falhas de sistema e para automaticamente se uma fase quebrar.

### `scripts/status_cli.sh` (Radar de Terminal)
Se você não quiser abrir a página Web, rode este script no terminal. Ele lerá o arquivo CSV de forma rápida e cuspirá um resumo na tela preta (Total na Base, Incluídos, Excluídos e Pendentes).

### `scripts/backup_experiment.sh` (Snapshot de Segurança)
Zipa todo o conteúdo da pasta `saida/` colocando a data e hora no nome do arquivo `.zip`. Indispensável antes de mudar drásticamente a "Constituição" ou os critérios de exclusão do arquivo `.spec.md`.

---

## 💻 Motor de Inferência e Revisão (Python Scripts)

### `scripts/review_pipeline/run_fase1.py` (Triagem / Screening Fase 1)
Lê artigos `Aguardando Triagem Fase 1`. Analisa Título e Resumo para aplicar critérios utilizando a classe `LLMRouter` (híbrido Nuvem/Local).
- `python scripts/review_pipeline/run_fase1.py` : Modo normal.
- `python scripts/review_pipeline/run_fase1.py --overnight` : Modo autônomo, não pausa o terminal caso um arquivo apresente erro de API, seguindo para o próximo da fila.
> **Nota:** Ao terminar a execução, a Fase 1 aciona automaticamente em background a geração do `PROGRESS.html`.

### `scripts/review_pipeline/run_fase2_extraction.py` & `run_pdf_download.py`
Baixa os textos completos (PDFs) e extrai dados granulares (População, Intervenções) apenas dos artigos aprovados na Triagem.

---

## 📊 Dashboards e UI

### `scripts/generate_progress.py` (Auditoria Estática)
**O que faz:** Lê varre todas as subpastas em `saida/auditoria/`, soma os Tokens Gastos e o tempo de Latência, e compila junto ao Log do Prisma um painel financeiro e de sucesso rigoroso (`.agent/data_storage/PROGRESS.html`).
**Como invocar:** `python scripts/generate_progress.py`

### `scripts/generate_live_dashboard.py` (Live Tracker Time-Machine)
**O que faz:** Monitora dinamicamente a execução dos scripts. Constrói o `LIVE_PROGRESS.html` que possui o "Mapa do Metrô".
- O Metrô calcula em tempo real o **Tempo Decorrido (Duração)** de cada Fase e apresenta um cronômetro global ao longo da esteira medindo o tempo de ponta-a-ponta, além da estimativa de fim (ETA) ajustada segundo a latência atual.

---

## 🛡️ Dicas de Segurança e Boas Práticas

1. **Nunca edite o `PRISMA_LOG_MASTER.csv` no Excel enquanto um script estiver rodando.** Isso trava o IO e o motor python irá falhar ao gravar.
2. Sempre realize um `bash scripts/backup_experiment.sh` antes de limpar a Fase 1 para recalibragem.
3. Se o "Metrô" parar de mover os nós no painel `LIVE_PROGRESS`, use o script `./scripts/reset.sh --ui-only` para soltar a trava do cache JSONP.
