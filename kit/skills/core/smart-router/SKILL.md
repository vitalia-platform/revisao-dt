---
name: smart-router
description: >
  Roteamento contextual automático. Analisa qualquer solicitação e seleciona
  o agente especialista ideal sem que o usuário precise nomeá-lo. Ativo em
  todo contexto. Triggers: qualquer solicitação de trabalho.
version: 1.0.0
trigger: always_on
---
<!-- kit/skills/core/smart-router/SKILL.md | Atualizado em: 28-05-2026 14:04:00(GMT-04:00) -->

# Smart Router — Roteamento Contextual Automático

> O usuário nunca precisa nomear um agente. Este skill analisa o contexto e aciona o especialista certo.

---

## Como Funciona

### Análise Silenciosa (antes de cada resposta)

```
Solicitação do usuário
       ↓
[1] Detectar DOMÍNIOS (tech? científico? meta?)
       ↓
[2] Avaliar COMPLEXIDADE (simples / moderado / complexo)
       ↓
[3] Selecionar AGENTE(S)
       ↓
[4] Informar brevemente qual expertise está sendo aplicada
       ↓
Resposta especializada
```

---

## Tabela de Roteamento

### Domínio: Desenvolvimento

| Intenção detectada | Palavras-chave / Padrões | Agente |
|--------------------|--------------------------|--------|
| Continuar código existente | "continue", "retome", "próximo passo", "implemente", "adicione ao", "extenda", referência a arquivo .py/.ts/.js | `coder` |
| Pair programming | "pair", "vamos trabalhar juntos", "em pares" | `coder` (modo pair) |
| Bug / erro | "erro", "bug", "não funciona", "quebrou", "exception", stack trace | `coder` |
| Code review | "revise", "review", "verifique o código", "está correto?" | `reviewer` |
| Testes | "teste", "TDD", "cobertura", "unit test", "e2e", "vitest", "jest", "pytest" | `tester` |
| Deploy / release | "deploy", "publicar", "release", "produção", "CI/CD", "docker push" | `shipper` |
| Múltiplos domínios / arquitetura | "full stack", "arquitetura", "planeje", "como deveria ser", "toda a feature" | `conductor` |

### Domínio: Ciência & Saúde

| Intenção detectada | Palavras-chave / Padrões | Agente |
|--------------------|--------------------------|--------|
| Biologia geral, fisiologia, anatomia | "fisiologia", "anatomia", "homeostase", "células", "tecido", "sistema nervoso", "biologia" | `biologist` |
| Endocrinologia | "hormônio", "cortisol", "insulina", "testosterona", "tireoide", "metabolismo", "endócrino" | `endocrinologist` |
| Nutrição | "nutrição", "dieta", "proteína", "carboidrato", "suplemento", "vitamina", "calorias", "alimentação" | `nutritionist` |
| Psicologia / saúde mental clínica | "ansiedade", "estresse", "hábito", "psicologia", "saúde mental", "mindfulness", "burnout" | `psychologist` |
| Revisão de conteúdo de saúde | "revise o conteúdo", "válido clinicamente?", "science-review", "validar claim" | `conductor` → aciona científico relevante |

### Domínio: Extensão Acadêmica (Esporte, Saúde & Lazer)

| Intenção detectada | Palavras-chave / Padrões | Agente |
|--------------------|--------------------------|--------|
| Rigor epistemológico DSR, enquadramento metodológico | "DSR", "design science", "rigor acadêmico", "enquadramento metodológico", "wicked problem", "Herbert Simon", "Schön", "Buchanan", "valide o problema", "filtro de rigor" | `academic-rigor-expert` |
| Análise comportamental, esporte, lazer, práticas corporais | "análise comportamental", "mudança de comportamento", "esporte", "lazer", "práticas corporais", "adesão ao exercício", "motivação esportiva", "BJ Fogg", "SDT", "Prochaska", "modelo transteórico", "transposição comportamental" | `behavioral-health-expert` |
| Transposição pedagógica, currículo, pedagogia do esporte | "transposição pedagógica", "pedagogia do esporte", "design instrucional", "currículo", "ABP", "ABD", "Bloom", "pós-graduação", "extensão universitária", "blueprint pedagógico", "módulo de aprendizagem", "gestão do lazer" | `curriculum-designer` |

### Domínio: Meta-Trabalho

| Intenção detectada | Palavras-chave / Padrões | Agente |
|--------------------|--------------------------|--------|
| Contexto / sessão | "onde parei", "última sessão", "o que foi feito", "contexto", "session-start" | `session-manager` |
| Aprender / capturar padrão | "aprendi", "memorize", "extraia padrão", "crie um agente", "adicione à coleção" | `knowledge-curator` |
| Novo projeto | "novo projeto", "inicializar", "do zero", "bootstrap", "criar repositório" | `bootstrapper` |

---

## Regras de Seleção

### Simples (1 domínio) → 1 agente direto
```
"Adiciona validação de email no serializer Django"
→ tech + código existente → coder
```

### Moderado (2 domínios relacionados) → sequência
```
"Implementa o endpoint de biometria e garante que os ranges estão corretos"
→ tech + endocrinologia → coder + endocrinologist (em sequência)
→ endocrinologist valida primeiro → coder implementa com constraints
```

### Complexo (3+ domínios / arquitetural) → conductor
```
"Cria a feature completa de plano de saúde personalizado com IA"
→ múltiplos domínios → conductor orquestra o time
```

### Subgrupo Academic Extension — Filtro DSR Obrigatório (Opção B)

```
QUERY COMPLEXA (padrão — filtro ativo):
  Detecta palavras: "analise", "mapeie", "sintetize", "crie módulo",
  "blueprint", "transponha", "mapa comportamental", "estrutura pedagógica",
  "categorias emergentes", "draft", "escreva", "elabore"
  → Sequência: academic-rigor-expert PRIMEIRO → agente alvo

QUERY SIMPLES (bypass do filtro):
  Detecta palavras: "o que é", "explique", "defina", "consulta", "confirme"
  → Agente alvo DIRETAMENTE (sem filtro DSR)

OVERRIDE sempre disponível:
  @behavioral-health-expert, @curriculum-designer → bypassa filtro automaticamente
```

---

## Formato de Resposta ao Acionar

```markdown
🤖 Aplicando expertise de `[agente]`...

[resposta especializada]
```

Para múltiplos agentes:
```markdown
🤖 Orquestrando: `[agente-1]` + `[agente-2]`...

[síntese das perspectivas]
```

---

## Override Manual

O usuário sempre pode forçar um agente específico:
```
"Use o @biologist para revisar isto" → ignora roteamento automático
"Como @coder, implemente..." → usa coder diretamente
```

---

## Casos Especiais

| Situação | Ação |
|----------|------|
| Pergunta genérica / conceitual | Responde diretamente, sem acionar agente |
| Solicitação muito vaga | Faz 1-2 perguntas de clarificação antes de rotear |
| Conflito de domínios (mobile vs web) | Pergunta antes de rotear |
| Conteúdo médico para usuário final | Aciona HITL independente do agente |
