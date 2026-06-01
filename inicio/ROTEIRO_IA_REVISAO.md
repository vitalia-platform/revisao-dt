<!-- inicio/ROTEIRO_IA_REVISAO.md | Atualizado em: 01-06-2026 10:19:28(GMT-04:00) -->
# Roteiro de Trabalho da IA na Revisão Integrativa

**Uso:** Este arquivo descreve o papel da IA em cada fase da revisão. O agente deve lê-lo na primeira sessão de trabalho e referenciar os parâmetros do arquivo de configuração ativo do projeto, nunca hardcoded. O usuário informa em que Passo estamos a cada interação.

---

## DIRETRIZ MACRO DE COMPORTAMENTO

A IA atua como Assistente Científico e Revisor Acadêmico. É proibido citar plataformas, produtos ou motores proprietários nos resultados, análises e no draft final. O foco é estritamente a Pergunta Norteadora. Todas as decisões no funil de seleção devem ser rastreáveis via *Log Total* (PRISMA como Reporting Standard).

**Regra de Zero Hardcoding:** A IA NUNCA assume valores para caminhos, endpoints ou nomes de modelo. Antes de qualquer ação, ela lê o arquivo `criteria_config.yaml` presente na raiz do projeto. Se o arquivo não existir, a IA instrui o usuário a rodar o workflow `/integrative-review` para gerá-lo.

**Premissa Metodológica (Pivot 01-06-2026):**  
Este projeto utiliza uma **Estratégia Híbrida**:
- **Análise e Síntese:** Revisão Integrativa (Mendes, Silveira e Galvão, 2008) + Síntese DSR (vom Brocke et al., 2015).
- **Reporting Standard:** PRISMA 2020 / PRISMA-ScR — usado *exclusivamente* para demonstrar a transparência e rastreabilidade da triagem (fluxograma e log), não como amarra metodológica quantitativa.
- **Implicação prática:** A IA aceita artigos teóricos, qualitativos e literatura cinzenta com o mesmo peso de ensaios empíricos, desde que a pertinência à Pergunta Norteadora seja explícita e auditável.

---

## PASSO 0: Calibração da Amostra (HITL + Busca Automatizada via API)

**Pré-condição:** `criteria_config.yaml` deve existir. Se não existir, parar e pedir `/integrative-review`.

**Ação da IA (busca e auditoria):**
1. Lê `criteria_config.yaml` para obter a `study.query_string`, o `audit_logging.enabled`, `paths.audit_payloads` e as bases habilitadas.
2. Para cada base habilitada, aciona a skill correspondente para coletar a amostra de calibração:
   - `pubmed-database` → para artigos indexados em bases biomédicas (MEDLINE)
   - `literature-search-europepmc` → para artigos de acesso aberto (literatura cinzenta e periódicos internacionais)
   - `literature-search-biorxiv` → **exclusivamente para preprints** (literatura cinzenta no domínio de ciências da vida e saúde)
3. **Trilha de Auditoria Obrigatória (PRISMA-S / PRISMA-trAIce):** Para cada chamada de API, a IA grava automaticamente dois artefatos na pasta `paths.audit_payloads`:
   - `LOG_BUSCA_<base>_<timestamp>.csv` — contendo: data/hora (ISO 8601), endpoint, query string exata, número total de hits retornados.
   - `PAYLOAD_<base>_<timestamp>.json` — o payload JSON bruto completo retornado pela API. Esta é a evidência incontestável para revisão por pares e não pode ser omitida.
4. Mapeia os temas recorrentes na amostra completa.
5. Se `criteria.high_value_domains` estiver configurado, mapeia especificamente quais conceitos aparecem nesse contexto.
6. Gera ativamente sugestões de **Inclusão** e **Exclusão** com base na Revisão Integrativa e apresenta ao usuário.

**Ação do Humano (HITL):** Revisa e aprova os critérios e a amostra coletada. Autoriza o avanço para o Passo 1. **Nenhuma fase avança sem "De Acordo" explícito.**

---

## PASSO 1: Deduplicação e Preparação dos Lotes

**Ação da IA:**
1. Lê `criteria_config.yaml` para obter `paths.lote_pool` e `processing.batch_size`.
2. Aciona o `@data-librarian` para processar todos os CSVs na pasta de lotes usando a skill `academic-id-resolver`.
3. Garante a deduplicação entre fontes cruzadas (mesmo artigo em WoS, Scopus, PubMed e preprints).
4. Gera o `LOG_PRISMA_FASE1.csv` vazio usando o template do projeto.

**Ação do Humano:** Confirma a contagem total de registros únicos antes de iniciar o screening.

---

## PASSO 2: Screening Fase 1 (Título e Resumo — Processamento em Lote Local)

**Ação da IA:**
1. Lê `criteria_config.yaml`: `ollama.base_url`, `ollama.model`, `criteria.inclusion`, `criteria.exclusion`, `criteria.high_value_domains`.
2. Gera (ou usa se já existir) o script `local_chunk_screening.py`. O script:
   - Lê a lista de lotes a partir de `paths.lote_pool` (nenhum caminho fixo no código).
   - Processa `processing.batch_size` artigos por chamada à API do Ollama em `ollama.base_url`.
   - Para cada artigo: aplica os critérios de Inclusão/Exclusão lidos do config. Registra a decisão e justificativa no `LOG_PRISMA_FASE1.csv`.
   - Marca artigos de `high_value_domains` com a tag `TRENDING_TOPIC`.
   - **Aceita artigos teóricos e conceituais** se pertinentes à Pergunta Norteadora (critério DSR).
3. Executa o script e reporta ao usuário o balanço ao final: Total → Excluídos → Aprovados para Fase 2.

**Ação do Humano:** Audita amostra do Log Total. Aprova avanço para o Passo 3.

---

## PASSO 3: Recuperação de Full-Texts (Multi-Fonte, Baseada na Origem)

**Ação da IA:**
1. Extrai a lista de DOIs aprovados na Fase 1 do `LOG_PRISMA_FASE1.csv`.
2. Gera (ou usa se já existir) o script `multi_source_downloader.py`. O script itera por cada DOI com lógica de prioridade baseada na **base de origem do artigo**, lendo as URLs da API do `criteria_config.yaml`:
   - Se origem **PubMed/MEDLINE:** tenta **PubMed Central (PMC) OA API** primeiro, depois Unpaywall, EuropePMC, Crossref.
   - Se origem **EuropePMC/preprint:** tenta **EuropePMC API** primeiro, depois PMC, Unpaywall, Crossref.
   - Se origem **bioRxiv:** tenta **bioRxiv API** diretamente.
3. Salva PDFs recuperados em `paths.output_fichamentos` (lido do config).
4. Gera relatório final: *"Recuperados N PDFs."*
5. **Relatório Ativo de Falhas:** Gera lista com links clicáveis diretos (`https://doi.org/[DOI]`) para todos os DOIs não localizados.

**Ação do Humano:** Baixa manualmente via CAFe/RNP os PDFs não recuperados automaticamente e avisa a IA.

**Verificação Pós-Download (Ação da IA):** Assim que o humano anexar os PDFs manuais, a IA executará um script de verificação para:
1. Confirmar se a nomenclatura dos arquivos segue o padrão definido no projeto.
2. Ler a primeira página do PDF para confirmar que o Título do artigo bate com o esperado.

---

## PASSO 4: Extração Sistemática (Fichamentos — Orientação DSR)

**Ação da IA:**
Para cada PDF validado, cria um arquivo markdown individual em `paths.output_fichamentos`, seguindo o `TEMPLATE_FICHAMENTO.md`. O foco do fichamento é **duplo**:

1. **Dados bibliométricos padrão:** Autores, ano, base, metodologia, amostra, resultados.
2. **Extração orientada a DSR (vom Brocke et al.):** A IA deverá extrair e destacar explicitamente:
   - **Kernel Theories** — Teorias e frameworks teóricos que embasam o estudo (ex: SDT, Salutogênese, Design Thinking).
   - **Design Principles** — Princípios de design identificados ou testados no estudo.
   - **Wicked Problems** — Problemas complexos identificados que o estudo tenta resolver.
   - **Artefatos de Design** — Produtos, protótipos, metodologias criadas.
   - **Gaps Identificados** — Lacunas explícitas apontadas pelos autores.

**Ação do Humano:** Revisa os fichamentos. Como se trata de dados para publicação (HITL), o humano confere ativamente os dados extraídos, especialmente as Kernel Theories e Design Principles.

---

## PASSO 5: Síntese Cruzada, Categorias Emergentes e Dossiê DSR

**Ação da IA (Síntese Integrativa + DSR):**
Com todos os fichamentos prontos, executa dois processos em paralelo:

**5a. Síntese Integrativa (Mendes et al.):**
- Cria a Matriz de Extração e identifica as categorias emergentes de forma indutiva.
- Gera o mapa de `TRENDING_TOPICS` para os domínios de alto valor configurados.

**5b. Dossiê de Síntese DSR (vom Brocke et al.):**
- Consolida o mapa de **Kernel Theories** transversais a múltiplos estudos (hierarquia de frequência e relevância).
- Identifica **Design Principles** recorrentes que podem guiar o artefato pedagógico.
- Mapeia as **Lacunas de Design** — o "espaço em branco" que justifica a construção do Blueprint Pedagógico.
- Produz o **Dossiê de Reasoning**: documento com o racional explícito da construção de categorias (citando artigos, nível de confiança e alinhamento às teorias nucleares). Este dossiê subsidiará a discussão do conselho científico.

**Ação do Humano:** Revisa o dossiê e as categorias propostas (consenso do conselho científico) e autoriza a redação do Draft Acadêmico Neutro do artigo final + o início do Blueprint Pedagógico.
