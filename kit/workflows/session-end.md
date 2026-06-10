---
description: >
  Encerra a sessão de trabalho em 4 fases estanques: avaliação proativa de melhorias,
  reflexão HITL da sessão, commit do repositório raiz e gravação do shard local.
  NÃO sincroniza o repositório de contexto com a nuvem — isso é responsabilidade do /session-consolidate.
---

<!-- kit/workflows/session-end.md | Atualizado em: 01-06-2026 21:26:30(GMT-04:00) -->

# /session-end — Encerramento de Sessão (Dual-Git)

$ARGUMENTS

---

## Propósito

**Responsabilidade única:** Reflexão, registro e commit local. Este workflow **NÃO faz push** do repositório de contexto.

Respeita a arquitetura de dois repositórios Git independentes:
- **Repositório Raiz** (`revisao-dt`): código, dados de auditoria, scripts, skills.
- **Repositório de Contexto** (`.agent/session/`): estado da sessão, shards, histórico.

> [!IMPORTANT]
> Este workflow termina com o shard salvo **localmente**. Para sincronizar com a nuvem e ver o dashboard de máquinas, rode `/session-consolidate` após o encerramento.

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
  - Escopo Global → kit/skills/<nome>/SKILL.md
→ Aguardar conclusão antes de avançar para a Fase 2.

Se nenhuma melhoria for aprovada:
→ Prosseguir diretamente para a Fase 2.
```

---

### 🪞 Fase 2 — Reflexão da Sessão (HITL)

Esta é a fase central do encerramento. A IA para, pensa e pergunta.

```
1. Ler o transcript.jsonl da conversa atual para extrair o contexto do trabalho realizado.

2. Se existir um task.md ativo na conversa, lê-lo para inferir o estado das etapas (ex: 3/5).

3. Com base na leitura, a IA propõe automaticamente o seguinte resumo ao usuário:

   ┌──────────────────────────────────────────────────────────────────┐
   │ 📋 Resumo da sessão — Identificado automaticamente               │
   │                                                                  │
   │ Tarefa:  [Nome inferido do foco central do dia]                  │
   │ Etapas:  [X/Y do task.md, ou "N/A" se não houver task]          │
   │ Status:  [Iniciando | Executando | Aguardando | Concluído]       │
   │                                                                  │
   │ Atividades desta sessão:                                         │
   │   • [Atividade 1 identificada no transcript]                     │
   │   • [Atividade 2 identificada no transcript]                     │
   │   • ...                                                          │
   │                                                                  │
   │ Próximo Passo (P0):                                              │
   │   [Item mais prioritário para a próxima sessão]                  │
   └──────────────────────────────────────────────────────────────────┘

   ✅ Aprova este resumo? Ajuste o que desejar antes de salvar.

4. AGUARDAR aprovação ou ajustes do usuário antes de prosseguir.
   A IA não escreve nada no disco até receber confirmação.
```

---

### 📦 Fase 3 — Commit do Repositório Raiz

```
1. [SEGURANÇA OBRIGATÓRIA] Executar o script de sanitização:
   $ bash scripts/sanitize_for_cloud.sh
   → Se o script falhar (IP exposto, .curadoria sem .gitignore): PARAR e alertar o usuário.
   → Se o script passar: autorização concedida para commit autônomo.

2. Fazer o commit e push do Repositório Raiz:
   $ git add .
   $ git commit -m "chore(session-end): [resumo aprovado na Fase 2]"
   $ git push
   NOTA: A pasta .agent/session/ é ignorada pelo .gitignore da raiz.
         Ela NÃO será incluída neste commit.
```

---

### 🗄️ Fase 3.5 — Sincronização de Dados (Storage)

```
1. Fazer o commit e push autônomo dos arquivos de dados (Tri-Git):
   $ bash kit/scripts/data-sync.sh --push
   → O script usará 'lsof' para garantir que os dados estão livres antes de subir.
```

---

### 🗂️ Fase 4 — Gravação do Shard Local

Com o resumo aprovado pelo usuário na Fase 2:

```
1. Obter o ID da máquina rodando:
   $ python3 .agent/scripts/lib_machine.py --get-id

2. Sobrescrever o shard da máquina local usando o template obrigatório:
   Arquivo: .agent/session/shards/[MACHINE_ID].md

   Template:
   ─────────────────────────────────────────────────
   # Shard: [Nome da máquina] ([MACHINE_ID])
   **Último sync:** [DD-MM-YYYY HH:MM:SS(GMT-04:00)]
   **Tarefa:** [aprovado na Fase 2]
   **Etapas:** [aprovado na Fase 2]
   **Status:** [aprovado na Fase 2]

   ## Atividade desta sessão
   - [lista aprovada na Fase 2]

   ## Próximo Passo (P0)
   [aprovado na Fase 2]
   ─────────────────────────────────────────────────

3. Commitar o shard localmente no repositório de contexto:
   $ cd .agent/session
   $ git add shards/[MACHINE_ID].md
   $ git commit -m "chore(shard): session registered [MACHINE_ID] [TIMESTAMP]"

   ⚠️ NÃO EXECUTAR git push aqui.
      O push é responsabilidade exclusiva do /session-consolidate.

4. Exibir a confirmação final ao usuário:

   ✅ Sessão registrada localmente com sucesso!
   
   📌 Shard [MACHINE_ID] salvo em .agent/session/shards/.
   📦 Repositório raiz: pushed ✅
   📡 Para sincronizar com a nuvem e ver o dashboard:
      → Rode /session-consolidate
```

---

## Exemplos de Uso

```
/session-end
/session-end --resumo="Calibração da Fase 0 concluída; query v4 expandida aprovada"
```
