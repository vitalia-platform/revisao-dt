<!-- inicio/ADR-002-Identity-Revisao-DT.md | Criado em: 28-05-2026 14:04:00(GMT-04:00) -->
# ADR 002: Identidade e Escopo do Projeto revisao-dt

## Status
Aceito e Estabelecido (Maio de 2026)

## Contexto

Este repositório foi inicializado a partir do clone de `revisao-integrativa`, um template genérico de revisão da literatura construído como reação a um episódio de viés de produto (documentado no ADR-001). Embora o template seja reutilizado, o projeto `revisao-dt` tem identidade, objetivos e escopo próprios e distintos. Este ADR formaliza essa diferenciação e serve como referência de identidade para todos os agentes e para o `00_SUMARIO_EXECUTIVO.md`.

---

## Decisão

### Identidade deste Projeto

| Campo | Valor |
|-------|-------|
| **Nome** | revisao-dt |
| **Tipo** | Revisão Integrativa da Literatura + Transposição Pedagógica |
| **Epistemologia central** | Design Science Research (DSR) |
| **Tema transversal** | Esporte, Saúde e Lazer |
| **Método de transposição** | Design Thinking e Metodologias Ativas |
| **Produto esperado** | (1) Artigo acadêmico de revisão integrativa + (2) Blueprint pedagógico para programas de extensão universitária em nível de pós-graduação |

### Escopo Temático

O projeto investiga as intersecções entre:
- **Esporte** — práticas esportivas educacionais, iniciação esportiva, esporte comunitário, esporte e lazer
- **Saúde** — promoção da saúde via práticas corporais, comportamento em saúde, fatores fisiológicos e educacionais
- **Lazer** — lazer ativo como direito social, gestão de espaços de lazer, animação cultural, políticas públicas

### Subgrupo de Agentes Exclusivo deste Projeto

| Agente | Papel |
|--------|-------|
| `academic-rigor-expert` | Filtro DSR — enquadramento epistemológico (Herbert Simon, Nigel Cross, Schön, Buchanan) |
| `behavioral-health-expert` | Análise comportamental em Esporte, Saúde & Lazer (Fogg, Deci/Ryan, Prochaska) |
| `curriculum-designer` | Transposição pedagógica (ABP, ABD, Bloom, Pedagogia do Esporte, Gestão do Lazer) |

**Localização:** `kit/agents/academic_extension/`

### Skill Exclusiva

| Skill | Propósito |
|-------|-----------|
| `instructional-design` | Encapsula Bloom, ABP, ABD, Chevallard, Pedagogia do Esporte e Gestão do Lazer |

**Localização:** `kit/skills/science/instructional-design/`

### O que foi herdado do Template e Adaptado

| Componente | Adaptação |
|------------|-----------|
| Pipeline PRISMA | Mantido — metodologicamente correto para qualquer revisão |
| Arquitetura Clean Room | Mantida — neutralidade é universal |
| `methodology-auditor.md` | Bias terms atualizados para contexto pedagógico/institucional/esportivo |
| `chief-reviewer.md` | Periódicos alvo atualizados para Educação, Esporte e Lazer |
| Smart-router | Novo domínio "Extensão Acadêmica" + Filtro DSR Obrigatório (Opção B) |
| ADR-001 | Permanece como registro histórico do template de origem |

### Periódicos Alvo

| Periódico | Área |
|-----------|------|
| Movimento (UFRGS) | Educação Física e Esportes |
| Licere (UFMG) | Lazer e Humanidades |
| RBCE — Revista Brasileira de Ciências do Esporte | Esporte |
| Revista Brasileira de Educação | Educação |
| Cadernos de Pesquisa (FCC) | Educação |
| Interface — Comunicação, Saúde, Educação (UNESP) | Saúde Coletiva |

---

## Consequências

1. **O ADR-001** permanece válido como registro histórico do template de origem. Este ADR (002) define a identidade específica deste projeto.
2. **O workflow `/integrative-review`** preencherá a Pergunta Norteadora específica no `00_SUMARIO_EXECUTIVO.md` — esse é o passo seguinte após o bootstrap.
3. **Todo novo agente, skill ou regra** criado exclusivamente para este projeto deve ser documentado aqui como adendo.
4. **A dimensão de Esporte, Saúde e Lazer** deve guiar tanto a construção dos critérios de elegibilidade (no painel `/integrative-review`) quanto a análise dos domínios comportamentais e a estruturação pedagógica do blueprint final.
