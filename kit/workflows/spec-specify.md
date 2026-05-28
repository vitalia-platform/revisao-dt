---
description: >
  Traduz o pedido do usuário em requisitos formais e histórias de usuário, criando um artefato .spec.md.
---

# /spec-specify — Especificação de Requisitos

$ARGUMENTS

---

## Propósito

Traduz o pedido do usuário (o "O quê" e o "Por quê") em requisitos formais e histórias de usuário, criando um artefato `.spec.md` baseado no `software.spec.md`, ANTES de qualquer planejamento técnico ou codificação.

---

## Comportamento

1. O agente recebe a descrição da funcionalidade ou sistema.
2. Analisa a viabilidade e aderência à Constituição do Arquiteto.
3. Se houver ambiguidades, interage com o usuário para esclarecer.
4. Gera o arquivo de especificação (`[funcionalidade].spec.md`) contendo:
   - Requisitos Funcionais e Não-Funcionais
   - Histórias de Usuário (User Stories)
   - Critérios de Aceite
   - Escopo Negativo (Fora do Escopo)
5. Aguarda a aprovação do usuário no arquivo de Spec antes de permitir o avanço para `/spec-plan`.
