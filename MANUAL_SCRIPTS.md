<!-- MANUAL_SCRIPTS.md | Atualizado em: 21-05-2026 11:31:00(GMT-04:00) -->
# Manual do Pipeline de Revisão Integrativa 📖

Este manual documenta o funcionamento, invocação e opções dos scripts do pipeline automatizado da plataforma Vitalia.

## 🏗️ Como os Dados Fluem no Sistema

A arquitetura foi projetada para ser **tolerante a falhas** e **interrompível**. Você pode parar qualquer fase (Ctrl+C) e o pipeline retomará exatamente de onde parou.

1. **`amostra/` (Seu ponto de partida)**: Você joga os CSVs brutos extraídos do PubMed, Scopus, etc., nesta pasta.
2. **`PRISMA_LOG.csv` (O Coração do Sistema)**: O script de ingestão lê os arquivos da amostra e cria esta planilha mestre. Ela contém a coluna `Status`, que dita qual será a próxima ação para cada artigo.
3. **`saida/auditoria/` (O Cérebro)**: Para cada artigo processado (Fase 1 ou 2), um arquivo JSON (shard) é salvo aqui contendo o prompt usado, a resposta do LLM, os metadados do artigo e a versão da configuração usada. Esta é sua **prova de auditoria metodológica**.
4. **`fichamentos/` (O Produto Final)**: Onde os arquivos extraídos em profundidade na Fase 2 são guardados de forma organizada para a redação da sua revisão.

---

## 💻 Os Scripts Core (Localizados em `scripts/review_pipeline/`)

### 1. `run_fase1.py` (Triagem / Screening)
**O que faz:** Lê artigos marcados como `"Aguardando Fase 1"` no `PRISMA_LOG.csv`. Analisa Título e Resumo para aplicar critérios de inclusão/exclusão.

**Como invocar (Opções):**
- `python scripts/review_pipeline/run_fase1.py` : Modo normal interativo. Pausa em falhas graves e pede sua decisão.
- `python scripts/review_pipeline/run_fase1.py --overnight` : **Modo autônomo (Overnight)**. Se um artigo falhar, ele pula automaticamente para o próximo sem pausar o terminal. Ideal para processar lotes de milhares de artigos de madrugada.
- `python scripts/review_pipeline/run_fase1.py --force-restart` : Força a limpeza e reinicia o status dos artigos pendentes para forçar o reprocessamento da fase.

### 2. `run_fase2_extraction.py` (Extração em Profundidade)
**O que faz:** Lê artigos `"Aprovado Fase 1"`. Lê o texto completo (PDF ou HTML) e extrai todas as variáveis (População, Intervenção, Resultados, Vieses) configuradas no `criteria_config.yaml`.

**Como invocar (Opções):**
- `python scripts/review_pipeline/run_fase2_extraction.py` : Modo normal.
- `python scripts/review_pipeline/run_fase2_extraction.py --overnight` : Mesma lógica da Fase 1, opera sem interrupções manuais.

### 3. `run_pdf_download.py` (Obtenção de Texto Completo)
**O que faz:** Busca e baixa o texto completo dos artigos aprovados na triagem, utilizando OpenAccess, Unpaywall, ou métodos diretos definidos.

**Configuração Importante:** Certifique-se de que o `.env` possui o e-mail cadastrado na variável `UNPAYWALL_EMAIL` para não receber bloqueios de acesso.

---

## 🎛️ Orquestração Avançada

### `run_pipeline.py` (Orquestrador Central - Automático)
Ao invés de chamar cada fase manualmente, você pode apenas rodar o orquestrador:
`python scripts/review_pipeline/run_pipeline.py`

Ele lerá as estatísticas do `PRISMA_LOG.csv` e executará automaticamente a fase que tem a maior fila de pendências, orquestrando todo o processo de ponta a ponta.

---

## 🛡️ Dicas de Segurança e Boas Práticas

1. **Nunca edite o `PRISMA_LOG.csv` manualmente com o Excel enquanto um script estiver rodando.** Isso causará conflito de permissões e os resultados da IA serão perdidos.
2. **Uso de Variáveis de Ambiente:** Qualquer credencial ou IP de servidor local deve residir no arquivo `.env` (oculto). Nunca preencha informações sensíveis no `criteria_config.yaml`, pois ele vai para o repositório público (nuvem).
3. **Acompanhamento de Erros:** Se a execução travar misteriosamente ou der falhas consecutivas, acesse `saida/auditoria/logs_execucao/` para ler relatórios legíveis para humanos descrevendo o motivo das interrupções.
