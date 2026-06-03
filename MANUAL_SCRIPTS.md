<!-- MANUAL_SCRIPTS.md | Atualizado em: 03-06-2026 -->
# Manual do Pipeline de Revisão Integrativa 📖

Este manual documenta o funcionamento, invocação e opções dos scripts do pipeline automatizado da plataforma Vitalia.

## 🏗️ Como os Dados Fluem no Sistema (Arquitetura Dual-Git e API-First)

A arquitetura foi projetada para ser **tolerante a falhas**, **interrompível** e utilizar **Armazenamento de Dados Isolado**. Todos os dados da revisão são manipulados de forma isolada na pasta `.agent/data_storage/` com symlinks na raiz.

1. **Ingestão Direta (`run_ingestion_api.py`)**: O pipeline busca automaticamente os artigos diretamente via API no PubMed e OpenAlex, criando o Log PRISMA inicial de forma centralizada e sem intervenção manual com CSVs brutos (embora os CSVs convencionais ainda possam ser importados por script secundário).
2. **`saida/PRISMA_LOG_MASTER.csv` (O Coração do Sistema)**: O script de ingestão cria esta planilha mestre consolidando e deduplicando os dados. Ela contém a coluna `Status`, que dita qual será a próxima ação.
3. **`saida/audit/` (O Cérebro da Auditoria)**: Para cada artigo processado, um arquivo JSON (shard) contendo o prompt usado, a resposta do LLM, os metadados do artigo e a performance (latência) é gerado para auditoria rigorosa.
4. **Dashboard de Progresso (`generate_progress.py`)**: Script autônomo que compila os logs do PRISMA em um painel HTML interativo (`PROGRESS.html`).

---

## 💻 Os Scripts Core (Localizados na pasta `scripts/`)

### 1. `scripts/review_pipeline/run_ingestion_api.py` (Ingestão Automática via API)
**O que faz:** Busca nas bases configuradas (como PubMed e OpenAlex) de acordo com os termos de busca, aplica lógica de deduplicação e atualiza ou cria o `PRISMA_LOG_MASTER.csv`.
**Como invocar:** `python scripts/review_pipeline/run_ingestion_api.py`

### 2. `scripts/review_pipeline/run_fase1.py` (Triagem / Screening Fase 1)
**O que faz:** Lê artigos marcados como `"Aguardando Triagem Fase 1"` no Master Log. Analisa Título e Resumo para aplicar critérios. Utiliza a classe `LLMRouter` (híbrido Nuvem/Local) para inferência e apresenta um *RichDashboard* dinâmico no terminal.
**Como invocar (Opções):**
- `python scripts/review_pipeline/run_fase1.py` : Modo normal interativo. Em caso de erros, o processo entra em modo de segurança e exibe um menu (Retry, Skip, Pause).
- `python scripts/review_pipeline/run_fase1.py --overnight` : Modo autônomo (Overnight). Se um artigo falhar, ele pula automaticamente para o próximo sem pausar o terminal (indicado para rodar de madrugada).

### 3. `scripts/generate_progress.py` (Visualização)
**O que faz:** Processa os dados do log mestre e da pasta de auditoria para gerar o arquivo `.agent/data_storage/PROGRESS.html` contendo os gráficos do funil e as métricas do LLM.
**Como invocar:** `python scripts/generate_progress.py` (o browser abrirá automaticamente).

### 4. `scripts/review_pipeline/run_fase2_extraction.py` (Extração em Profundidade)
**O que faz:** Lê artigos marcados como `"Incluído (Fase 1)"`. Lê o texto completo (PDF ou HTML) e extrai todas as variáveis (População, Intervenção, Resultados) configuradas.

### 5. `scripts/review_pipeline/run_pdf_download.py` (Obtenção de Texto Completo)
**O que faz:** Busca e baixa o texto completo dos artigos aprovados na triagem, utilizando OpenAccess, Unpaywall, ou fontes institucionais configuradas.

---

## 🛡️ Dicas de Segurança e Boas Práticas

1. **Nunca edite o `PRISMA_LOG_MASTER.csv` manualmente com o Excel enquanto um script estiver rodando.** Isso causará conflito de IO e os resultados da IA podem ser corrompidos.
2. **Uso de Variáveis de Ambiente:** Qualquer credencial, URL da API ou IP de servidor local deve residir no arquivo `.env`. Nunca preencha informações sensíveis no `criteria_config.yaml`.
3. **Acompanhamento de Erros:** O novo RichDashboard interceptará falhas no TUI. Para relatórios detalhados das inferências, consulte os payloads salvos em `saida/audit/`.
