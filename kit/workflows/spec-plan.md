---
description: >
  Lê um .spec.md já aprovado e propõe a arquitetura técnica, bibliotecas e decisões de engenharia necessárias.
---

# /spec-plan — Planejamento Técnico

$ARGUMENTS

---

## Propósito

Lê um `.spec.md` já aprovado e propõe a arquitetura técnica, bibliotecas e decisões de engenharia necessárias para implementá-lo.

---

## Comportamento

1. O agente carrega o `[funcionalidade].spec.md`.
2. Avalia a infraestrutura atual e a arquitetura do projeto.
3. Gera um plano técnico (`[funcionalidade]-plan.md` ou `implementation_plan.md`) que descreve:
   - Estrutura de Pastas e Arquivos (novos ou modificados)
   - Modelagem de Dados
   - APIs/Contratos
   - Dependências
4. Aguarda aprovação explícita do usuário antes de permitir a geração de tarefas (`/spec-tasks`) ou implementação (`/spec-implement`).
