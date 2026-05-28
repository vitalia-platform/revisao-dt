---
description: >
  Converte o plano técnico aprovado em uma checklist acionável no task.md para implementação rastreável.
---

# /spec-tasks — Geração de Tarefas

$ARGUMENTS

---

## Propósito

Converte o plano técnico (`-plan.md`) em uma checklist acionável, permitindo rastreabilidade e commits atômicos.

---

## Comportamento

1. O agente recebe o plano técnico aprovado.
2. Quebra a implementação em tarefas lógicas, independentes e testáveis.
3. Atualiza ou cria o `task.md` na raiz ou no diretório de contexto da AI.
4. Prepara o estado para que o comando `/spec-implement` possa atuar passo a passo.
