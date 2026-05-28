# ADR 001: Rigor Metodológico e Prevenção de Viés ("Log Total PRISMA")

## Status
Aceito e Estabelecido (Maio de 2026)

## Contexto
O fluxo anterior do desenvolvimento da Revisão Integrativa sobre uso de tecnologias digitais no exercício físico sofreu desvios graves de neutralidade. O agente de IA e os documentos de consolidação estavam enviesados por um propósito mercadológico (validar lógicas de produto, nomeadamente os "Motores Kim e Keytel" da Plataforma Vitalia), além da utilização de métodos de rastreio frágeis que resultaram em "links quebrados" e falsa extração de dados. Para fins de publicação em periódicos científicos qualificados, uma revisão sistemática ou integrativa precisa ser agnóstica e estritamente atrelada à sua Pergunta Norteadora.

## Decisão
Foi instituído que o novo repositório de revisão operará como uma "Sala Limpa" (Clean Room), orientada pelas seguintes normativas inegociáveis:

1. **Acesso Estruturado Oficial (RNP):**
   A extração de registros será feita exclusivamente via exportação direta (.csv ou .ris) por acesso humano autenticado no Portal de Periódicos CAPES (CAFe), focando em bases como Scopus e Web of Science. Scripts autônomos de raspagem e downloads baseados em links genéricos estão proibidos para evitar *paywalls* ocultos e falsos positivos.

2. **Rastreabilidade "Log Total" (PRISMA):**
   O agente IA não pode omitir ou suprimir exclusões. Todo registro originado no `.csv` base passará por triagem com justificativa gerada. Para a leitura de Título e Resumo (Fase 1), a IA construirá uma tabela contendo o motivo exato pelo qual o artigo não atende aos critérios da Pergunta Norteadora. 

3. **Neutralidade Estrita de Produto:**
   É terminantemente proibida a menção da "Plataforma Vitalia", "Motores Kim e Keytel" ou qualquer terminologia comercial dentro dos resultados e das discussões do *draft* acadêmico. A revisão deverá se sustentar por seu mérito clínico/fisiológico geral. As categorias de análise emergirão indutivamente do texto dos estudos incluídos, não dos interesses da plataforma.

## Consequências
- **Acréscimo de Transparência:** Maior aceitação em avaliação por pares; facilidade na criação de um "Apêndice de Exclusão" irrefutável.
- **Mudança de Fluxo (HITL):** O usuário deve atuar obrigatoriamente na fase de *Search* (autenticação CAFe) e prover o dataset; o agente IA assume a fase de *Screening* de alto volume de forma assíncrona.
- **Isolamento de Domínio:** O resultado deste repositório será um Artigo Acadêmico puro. O reuso dessas descobertas para engenharia de software da plataforma ocorrerá em um repositório apartado no futuro.
