# Roteiro de Trabalho da IA na Revisão Integrativa
**Uso:** Este arquivo descreve o papel da IA em cada fase da revisão. O agente deve lê-lo na primeira sessão de trabalho e referenciar os parâmetros do arquivo de configuração ativo do projeto, nunca hardcoded. O usuário informa em que Passo estamos a cada interação.

---

## DIRETRIZ MACRO DE COMPORTAMENTO

A IA atua como Assistente Científico e Revisor Acadêmico. É proibido citar plataformas, produtos ou motores proprietários nos resultados, análises e no draft final. O foco é estritamente a Pergunta Norteadora. Todas as decisões no funil de seleção devem ser rastreáveis via *Log Total* (PRISMA).

**Regra de Zero Hardcoding:** A IA NUNCA assume valores para caminhos, endpoints ou nomes de modelo. Antes de qualquer ação, ela lê o arquivo `criteria_config.yaml` presente na raiz do projeto. Se o arquivo não existir, a IA instrui o usuário a rodar o workflow `/integrative-review` para gerá-lo.

---

## PASSO 0: Calibração da Amostra (Análise Profunda)

**Pré-condição:** `criteria_config.yaml` deve existir. Se não existir, parar e pedir `/integrative-review`.

**Ação da IA:**
1. Lê `criteria_config.yaml` para obter `paths.sample_root` e subpastas de origem.
2. Para cada sub-pasta de origem encontrada:
   - CSVs: extrai título, abstract, keywords, DOI, ano.
   - PDFs: extrai texto completo.
3. Mapeia os temas recorrentes na amostra completa.
4. Se `criteria.high_value_domains` estiver configurado, mapeia especificamente quais tecnologias aparecem nesse contexto.
5. Gera ativamente sugestões de **Inclusão** e **Exclusão** e as propõe ao usuário no painel `review_setup.md`.

**Ação do Humano:** Revisa e aprova os critérios. Autoriza o avanço para o Passo 1.

---

## PASSO 1: Deduplicação e Preparação dos Lotes

**Ação da IA:**
1. Lê `criteria_config.yaml` para obter `paths.lote_pool` e `processing.batch_size`.
2. Aciona o `@data-librarian` para processar todos os CSVs na pasta de lotes usando a skill `academic-id-resolver`.
3. Garante a deduplicação entre fontes cruzadas (mesmo artigo em WoS e Scopus).
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
3. Executa o script e reporta ao usuário o balanço ao final: Total → Excluídos → Aprovados para Fase 2.

**Ação do Humano:** Audita amostra do Log Total. Aprova avanço para o Passo 3.

---

## PASSO 3: Recuperação de Full-Texts (Multi-Fonte)

**Ação da IA:**
1. Extrai a lista de DOIs aprovados na Fase 1 do `LOG_PRISMA_FASE1.csv`.
2. Gera (ou usa se já existir) o script `multi_source_downloader.py`. O script itera em loop por cada DOI, tentando sequencialmente as fontes abaixo até obter sucesso, sem hardcoded — as URLs base das APIs são lidas do `criteria_config.yaml`:
   - **Fonte 1:** Unpaywall API (`api.unpaywall.org`)
   - **Fonte 2:** PubMed Central (PMC) OA API (`eutils.ncbi.nlm.nih.gov`)
   - **Fonte 3:** Europe PMC (`europepmc.org/api`)
   - **Fonte 4:** Crossref (`api.crossref.org`)
3. Salva PDFs recuperados em `paths.output_fichamentos` (lido do config).
4. Gera relatório final: *"Recuperados N PDFs."*
5. **Relatório Ativo de Falhas:** O Agente gera uma lista com links clicáveis diretos (ex: `https://doi.org/[DOI]`) para todos os DOIs não localizados, acelerando a verificação manual pelo pesquisador.

**Ação do Humano:** Baixa manualmente via CAFe/RNP os PDFs não recuperados automaticamente e avisa a IA.

**Verificação Pós-Download (Ação da IA):** Assim que o humano anexar os PDFs manuais, a IA executará um script de verificação para:
1. Confirmar se a nomenclatura dos arquivos segue o padrão definido no projeto.
2. Ler a primeira página do PDF para confirmar que o Título do artigo bate com o esperado, atestando a validade do anexo.

---

## PASSO 4: Extração Sistemática (Fichamentos)

**Ação da IA:**
Para cada PDF validado, cria um arquivo markdown individual em `paths.output_fichamentos`, seguindo o `TEMPLATE_FICHAMENTO.md` do projeto.

**Ação do Humano:** Revisa os fichamentos. Como se trata de dados para publicação (HITL), o humano confere ativamente parâmetros e dosagens citadas.

---

## PASSO 5: Síntese Cruzada, Categorias e Draft

**Ação da IA:**
Com todos os fichamentos prontos, cria a Matriz de Extração e identifica as categorias emergentes organicamente (análise indutiva). Gera o mapa de `TRENDING_TOPICS` para os domínios de alto valor configurados.
**Dossiê de Reasoning:** A IA produzirá um documento contendo o racional explícito da construção dessas categorias (citando quais artigos embasam cada categoria e o nível de confiança). Esse dossiê subsidiará a discussão do conselho científico.

**Ação do Humano:** Revisa o dossiê e as categorias propostas (consenso do conselho científico) e autoriza a redação do Draft Acadêmico Neutro do artigo final.
