# Roteiro de Busca Estruturada (Portal de Periódicos CAPES)
**Acesso:** Institucional via Comunidade Acadêmica Federada (CAFe) - UFMT

Este roteiro é um **Template** projetado para extrair o máximo potencial do seu acesso institucional (via RNP/CAFe), obtendo dados massivos e confiáveis para alimentar o processo automatizado de triagem (PRISMA Log Total) da nossa Revisão Integrativa. Durante o processo de `/integrative-review`, as marcações abaixo serão preenchidas.

## Passo 1: Autenticação (Acesso CAFe)
1. Acesse: [Portal de Periódicos da CAPES](https://www-periodicos-capes-gov-br.ezl.periodicos.capes.gov.br/) (ou vá na página inicial e clique em "Acesso CAFe").
2. Na lista de instituições, selecione **UFMT - Universidade Federal de Mato Grosso**.
3. Insira suas credenciais institucionais. Você verá no topo do site: *"Acesso provido por Universidade Federal de Mato Grosso"*.

## Passo 2: Acesso à Base de Dados Indexada (Web of Science / Scopus)
A barra principal da CAPES é apenas um agregador genérico. Para a exportação estruturada exigida pela IA, você deve acessar bases específicas. Usaremos primariamente a **Web of Science (Clarivate)** ou a **Scopus (Elsevier)**.
1. No menu principal da CAPES, vá em **Acervo > Lista de bases**.
2. Digite **Web of Science** (ou Scopus) e clique no link. Uma nova aba se abrirá já autenticada.

## Passo 3: Execução da "Search String"
Para abranger o nosso foco atualizado (Engajamento, Gamificação, Redes Sociais) e manter o rigor das tecnologias vestíveis, utilizaremos uma busca por Tópico (Topic Search ou TS):
1. Selecione o campo como **"Topic"** (WoS) ou **"Article title, Abstract, Keywords"** (Scopus).
2. Cole a seguinte string booleana:
   ```text
   ("physical activity" OR "exercise" OR "physical training" OR "rehabilitation" OR "physical exercise" OR "physical education" OR "sports") AND ("wearable*" OR "smartphone" OR "mobile app*" OR "mHealth" OR "artificial intelligence" OR "gamification" OR "serious game*" OR "engagement" OR "adherence" OR "social media" OR "social network*" OR "peer support" OR "digital technology" OR "telemetry" OR "wearables")
   ```
3. Pressione **Search**.

## Passo 4: Filtros Padrão (PRISMA)
No painel esquerdo, aplique os filtros:
1. **Year (Ano de Publicação):** 2018 até 2026.
2. **Document Type:** Article e Review Articles (rejeite capítulos de livros e resumos de conferências).
3. **Language:** English, Portuguese, Spanish.
4. Clique em **Refine / Limit to**.

## Passo 5: Exportação Estruturada (O Essencial)
Para não sobrecarregar a janela de contexto da IA com arquivos CSV de dezenas de megabytes, exportaremos apenas as colunas estritamente necessárias.
1. Clique em **Export** > **Excel** ou **Text file (CSV/TSV)**.
2. Nas opções de registro (Record Content / Custom selection), marque **apenas** estes campos essenciais:
   - **Author(s)**
   - **Article Title**
   - **Source Title (Journal)**
   - **Abstract** (CRÍTICO para o screening da fase 1)
   - **Author Keywords / Keywords Plus**
   - **DOI**
   - **Publication Year**
3. Clique em **Export**.

## Próximo Passo
Mova o arquivo baixado (ex: `savedrecs.csv`) para o novo repositório limpo e forneça o caminho do arquivo para o Agente IA, utilizando o *ROTEIRO_IA_REVISAO.md* como seu comando de inicialização.
