---
description: >
  Executa rigorosamente a checklist de tarefas aprovada, escrevendo e modificando código fonte passo a passo.
---

# /spec-implement — Execução de Implementação

$ARGUMENTS

---

## Propósito

Executa rigorosamente a checklist de tarefas aprovada, escrevendo e modificando código fonte.

---

## Comportamento

1. O agente lê a checklist (`task.md`) e os documentos base (`.spec.md` e `-plan.md`).
2. Executa cada item sistematicamente (escrevendo arquivos, refatorando código, etc).
3. Após cada bloco lógico, sugere commits atômicos ou validações.
4. Atualiza o `task.md` à medida que progride, finalizando apenas quando os critérios de aceite forem atingidos e testados.
