---
description: >
  Encerra a sessão de trabalho em 3 fases estanques: avaliação proativa de melhorias,
  commit seguro do repositório raiz e sincronização do repositório de contexto.
  O commit do contexto é sempre o último passo.
---

<!-- kit/workflows/session-end.md | Atualizado em: 01-06-2026 14:30:00(GMT-04:00) -->

# /session-end — Encerramento de Sessão (Dual-Git)

$ARGUMENTS

---

## Propósito

Garante que nenhum aprendizado ou progresso se perca entre sessões, respeitando a arquitetura de dois repositórios Git independentes:

- **Repositório Raiz** (`revisao-dt`): código, dados de auditoria, scripts, skills.
- **Repositório de Contexto** (`.agent/session/`): estado da sessão, histórico, CONTEXT.md.

> [!IMPORTANT]
> O commit do Repositório de Contexto é **sempre o último passo**. A ordem das fases é obrigatória.

---

## Pipeline de Encerramento

### 🔍 Fase 1 — Avaliação e Refinamento Ativo

```
Executar imediatamente o diagnóstico proativo do /skill-evaluation:
1. Ler o transcript.jsonl da conversa atual.
2. Identificar: erros repetidos, correções feitas pelo usuário, processos manuais.
3. Apresentar o Cardápio de Diagnóstico ao usuário:
   - 🛠️ Melhorias Estruturais (rules, workflows, configs)
   - ⚡ Skills Candidatas com rascunho HITL pré-preenchido

Se o usuário aprovar alguma melhoria ou skill:
→ Escrever os arquivos gerados no destino correto:
  - Escopo Local  → .agent/skills/<nome>/SKILL.md
  - Escopo Global → kit/skills/<nome>/SKILL.md (futuramente separado do projeto)
→ Aguardar conclusão antes de avançar para a Fase 2.

Se nenhuma melhoria for aprovada:
→ Prosseguir diretamente para a Fase 2.
```

---

### 📦 Fase 2 — Conclusão do Diretório Raiz

```
1. Consolidar o progresso da sessão em 2-3 linhas (input do usuário ou inferência do log).

2. [SEGURANÇA OBRIGATÓRIA] Executar o script de sanitização:
   $ bash scripts/sanitize_for_cloud.sh
   → Se o script falhar (IP exposto, .curadoria sem .gitignore): PARAR e alertar o usuário.
   → Se o script passar: autorização concedida para commit autônomo.

3. Fazer o commit e push do Repositório Raiz:
   $ git add .
   $ git commit -m "chore(session-end): [resumo do progresso]"
   $ git push
   NOTA: A pasta .agent/session/ é ignorada pelo .gitignore da raiz.
         Ela NÃO será incluída neste commit.
```

---

### ☁️ Fase 3 — Sincronização do Repositório de Contexto (O Último Passo)

```
1. Escrever o resumo da sessão no CONTEXT.md local:
   - Estado Atual (O que foi concluído)
   - Constraints Ativos (se mudou)
   - Próximo passo (P0)

2. Annexar o bloco de encerramento ao SESSION_HISTORY.md:

   ## ✅ Sessão Encerrada em [data/hora]
   **Progresso**: [resumo de 3-5 linhas]
   **Próxima sessão começa em**: [P0]

3. Entrar no repositório de contexto e sincronizar com a nuvem:
   $ cd .agent/session

   3a. [REBASE — prioridade à nuvem]
       $ git pull origin main --rebase
       → Isso traz mudanças feitas em outras máquinas.
       → Em caso de conflito: pausar e alertar o usuário para resolver manualmente
         ou acionar o session-resolve.sh.

   3b. [CONSOLIDAÇÃO — mescla de contextos multi-máquina]
       Executar o script de consolidação:
       $ python3 ../kit/scripts/session-consolidate.py .

   3c. [COMMIT DO CONTEXTO]
       $ git add .
       $ git commit -m "chore: session end [data] — [resumo]"

   3d. [PUSH — o último passo real]
       $ git push origin main
```

---

## Confirmação Final

Após completar as 3 fases, apresentar:

```markdown
## ✅ Sessão Encerrada com Sucesso

**Repositório Raiz:** pushed ✅
**Repositório de Contexto:** synced ✅
**Skills/Melhorias geradas:** [lista ou "nenhuma"]
**Próxima sessão começa em:** [P0 — descrição]

Até a próxima. Use `/session-start` para retomar.
```

---

## Exemplos de Uso

```
/session-end
/session-end --resumo="Calibração da Fase 0 concluída; query v4 expandida aprovada"
```
