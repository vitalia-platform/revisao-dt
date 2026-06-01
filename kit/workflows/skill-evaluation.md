---
description: >
  Avalia, cuida e cria novas skills para o Kit de Agentes.
  Pipeline HITL completo: define escopo, método de invocação,
  trânsito de dados e risco de viés antes de acionar o workflow-skill-creator.
  Pode ser invocado diretamente pelo usuário ou sugerido pelo /session-end.
---
<!-- kit/workflows/skill-evaluation.md | Atualizado em: 01-06-2026 10:26:21(GMT-04:00) -->

# /skill-evaluation — Curadoria e Criação de Skills

$ARGUMENTS

---

## Propósito

Garantir que nenhuma skill seja criada de forma impulsiva, sem critério de rigor e sem considerar o impacto no pipeline científico do projeto. Este workflow é a **barreira de qualidade obrigatória** entre uma ideia de automação e a sua materialização como skill.

> [!IMPORTANT]
> Este workflow **não cria código por conta própria**. Ele conduz o pesquisador por um conjunto de perguntas estruturadas (HITL) e, somente após aprovação explícita de cada critério, aciona o `workflow-skill-creator`.

---

## Quando Usar

- Diretamente via chat: `/skill-evaluation` sempre que um processo manual repetitivo foi descoberto.
- Sugerido automaticamente pelo `/session-end` quando a sessão identificou padrões candidatos a automação.
- **Nunca chamar o `workflow-skill-creator` diretamente** sem passar por este workflow.

---

## Comportamento

### Fase 1: Inventário (Silencioso)

```
1. Ler CONTEXT.md e SESSION_HISTORY.md para identificar processos repetidos na sessão.
2. Se $ARGUMENTS contiver uma descrição de skill candidata, usá-la como ponto de partida.
3. Se invocado pelo /session-end, apresentar a lista de candidatas detectadas para o usuário escolher qual avaliar primeiro.
```

### Fase 2: Entrevista de Design (HITL — Perguntas Obrigatórias)

O agente conduz uma entrevista estruturada. Aguardar resposta do usuário a cada pergunta antes de prosseguir.

---

**Pergunta 1 — Descrição:**
> "Descreva com precisão o processo que você quer automatizar. Qual é o input? Qual é o output esperado?"

---

**Pergunta 2 — Escopo de Atuação:**
> "Esta skill deve funcionar para:
> (A) Apenas este projeto (revisão específica) → salvar em `.agent/skills/`
> (B) Todas as revisões futuras (global para todos os projetos Vitalia na sua máquina) → integrar ao `kit/skills/`"

---

**Pergunta 3 — Método de Invocação:**
> "Como esta skill será invocada?
> (A) Diretamente pelo usuário via chat (ex: `/minha-skill argumento`)
> (B) Chamada por outro agente ou workflow (ex: como sub-rotina do Passo 0 de calibração)
> (C) Ambas"

---

**Pergunta 4 — Trânsito de Dados:**
> "Como os dados entrarão e sairão desta skill?
> (A) Texto livre (input do usuário e output em markdown)
> (B) JSON estruturado (para integração com scripts Python e outros agentes)
> (C) Arquivos (leitura/escrita de CSVs, PDFs ou JSONs no disco)
> (D) Combinação — especifique"

---

**Pergunta 5 — Auditoria e Rastreabilidade (Constituição do Arquiteto — P4 e P10):**
> "Esta skill produz ou consome dados de pesquisa científica?
> Se sim: como garantiremos que ela gere um log de auditoria compatível com as diretrizes PRISMA-S/trAIce do projeto?"

---

**Pergunta 6 — Análise de Viés (Risco Científico):**
> "Esta automação pode introduzir algum viés no pipeline científico?
> Ex: critérios de inclusão/exclusão hardcoded, ordenação tendenciosa de resultados, descarte silencioso de evidências.
> Como mitigamos isso?"

---

### Fase 3: Decisão e Rota

Com base nas respostas, o agente apresenta:

```markdown
## 📋 Diagnóstico da Skill Candidata

**Nome proposto:** [nome-da-skill]
**Escopo:** [Local / Global]
**Invocação:** [direta / sub-rotina / ambas]
**Formato de dados:** [texto / JSON / arquivos]
**Auditoria:** [sim — como / não aplicável — justificativa]
**Risco de viés:** [baixo / médio / alto — mitigação proposta]

**Decisão recomendada:**
[ ] ✅ Criar skill — [caminho de destino]
[ ] ⏸️ Adiar — registrar no CONTEXT.md para revisão futura
[ ] ❌ Descartar — [justificativa]

Confirma? (S / N / Ajustar)
```

### Fase 4: Criação (Condicional)

```
Se o usuário aprovar:
→ Acionar `workflow-skill-creator` com os parâmetros definidos na entrevista.
→ O `workflow-skill-creator` gera o arquivo SKILL.md com:
   - Frontmatter YAML (name, description, scope, invocation, data_format)
   - Instruções detalhadas de uso
   - Exemplos de input/output
→ Salvar no caminho definido (`.agent/skills/` ou `kit/skills/`).
→ Atualizar CONTEXT.md com a nova skill criada.
→ Registrar no SESSION_HISTORY.md.
```

---

## Exemplos de Uso

```
/skill-evaluation
/skill-evaluation extração de Kernel Theories de PDFs de fichamento
/skill-evaluation geração automática de log de busca PRISMA-S
```

---

## Saídas Possíveis

| Resultado | Ação |
|---|---|
| Skill criada (local) | `.agent/skills/<nome-skill>/SKILL.md` |
| Skill criada (global) | `kit/skills/<nome-skill>/SKILL.md` |
| Skill adiada | Anotada em `CONTEXT.md` — campo "Skills Pendentes de Avaliação" |
| Skill descartada | Justificativa registrada no `SESSION_HISTORY.md` |
