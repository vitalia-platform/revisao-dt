---
name: git-lock-recovery
description: Recupera o repositório de contexto de estados bloqueados ou rebases quebrados, destravando o CONSOLIDATION_LOG.md.
---

# /git-lock-recovery — Recuperação de Lock Distribuído

## Propósito
Esta skill deve ser invocada quando o usuário ou a IA detectar que a consolidação de contexto (`/session-consolidate`) falhou repetidamente devido a um lock ("CONSOLIDANDO") travado por uma máquina offline, ou quando o repositório `.agent/session` ficar preso em um estado de rebase quebrado.

## Instruções de Execução

1. **Abortar Rebase em Andamento (Se houver):**
   Execute no terminal para garantir que o repositório não está preso:
   ```bash
   cd .agent/session && git rebase --abort || true
   ```

2. **Hard Reset para a Nuvem:**
   Para limpar qualquer divergência local corrompida e forçar a máquina a espelhar a nuvem:
   ```bash
   cd .agent/session && git fetch origin main && git reset --hard origin/main
   ```

3. **Remoção de Lock Pendente (Destravamento Automático):**
   Analise as últimas linhas de `.agent/session/CONSOLIDATION_LOG.md`. Se a última linha terminar em `| CONSOLIDANDO |` e estiver travando a rede, adicione uma nova linha de liberação em nome do administrador:
   `| [DATA_ATUAL] | ADMIN_RECOVERY | CONSOLIDADO (FORCED UNLOCK) |`
   
4. **Commit e Push do Destravamento:**
   ```bash
   cd .agent/session
   git add CONSOLIDATION_LOG.md
   git commit -m "fix(lock): forced unlock by admin recovery"
   git push origin main
   ```

5. **Aviso Final:**
   Exiba ao usuário que o repositório de contexto foi recuperado e o lock foi destravado, instruindo-o a rodar `/session-consolidate` novamente.
