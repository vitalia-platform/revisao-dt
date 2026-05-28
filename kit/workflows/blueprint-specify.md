---
description: >
  Inicia a fase de Transposição Pedagógica (SDD aplicado ao Ensino). Coleta o tema e o contexto e gera a especificação.
---

# /blueprint-specify — Especificação Pedagógica

$ARGUMENTS

---

## Propósito

Inicia a fase de Transposição Pedagógica (SDD aplicado ao Ensino). Coleta o tema e o contexto, e gera o `[modulo].blueprint.spec.md` definindo os objetivos e restrições da aula/módulo.

---

## Comportamento

1. Aciona o agente `curriculum-designer`.
2. Mapeia o contexto, a audiência (alunos/profissionais de Saúde, Esporte e Lazer), e o problema a ser ensinado.
3. INFERE a Taxonomia de Bloom apropriada (conhecimento, compreensão, aplicação, etc) baseando-se no objetivo final do módulo.
4. Gera o documento de Especificação Pedagógica a partir do template `blueprint.spec.md`.
5. Aguarda validação do usuário ou do `academic-rigor-expert` antes de passar para o `/blueprint-plan`.
