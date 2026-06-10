---
description: >
  Consolida os shards das máquinas e constrói o README.md do contexto, gerenciando a concorrência estrita na nuvem.
  Pode ser invocado a qualquer momento para ver o estado global do projeto entre máquinas.
---

<!-- kit/workflows/session-consolidate.md | Atualizado em: 01-06-2026 21:26:30(GMT-04:00) -->

# /session-consolidate — Consolidação Descentralizada e Dashboard

$ARGUMENTS

---

## Propósito

**Responsabilidade única:** Rede, lock distribuído, tabulação semântica e push para a nuvem.

Este workflow assume que os shards já foram escritos e commitados localmente pelo `/session-end`.
Pode ser invocado a qualquer momento — inclusive no meio de uma sessão — para obter uma visão
atual do trabalho de todas as máquinas participantes do projeto.

> [!IMPORTANT]
> Este workflow **não escreve o shard da máquina local**. Se você rodá-lo sem ter rodado
> o `/session-end` antes, o shard estará desatualizado e o dashboard refletirá a última
> sessão registrada, não o turno atual.

---

## Comportamento

### Passo 1: Identificação

```
1. Obter o ID da máquina local:
   $ python3 .agent/scripts/lib_machine.py --get-id

2. Registrar a data/hora atual no formato: DD-MM-YYYY HH:MM:SS(GMT-04:00)
```

---

### Passo 1.5: Validação de Shard Local (Evitar Stale Data)

```
1. Compare a hora atual do sistema com a data do 'Último sync' no seu shard local (`shards/[SEU_MACHINE_ID].md`).
2. Se a diferença for considerável (ex: mais de 1 hora) e houver atividades na conversa atual ainda não salvas:
   ⚠️ EXIBA ESTE AVISO E PAUSE:
   "⚠️ **Nota:** Seu shard local parece desatualizado em relação a este turno de trabalho. Para salvar seu progresso antes de consolidar, rode `/session-end`."
   (Aguarde o usuário confirmar se deseja prosseguir assim mesmo ou se vai rodar o session-end).
```

---

### Passo 2: Sincronização com a Nuvem

```
No diretório .agent/session:

1. Se houver mudanças locais não commitadas no repo de contexto, commitar antes:
   $ git add .
   $ git commit -m "chore: auto-save before consolidate pull"

2. Fazer pull priorizando a nuvem:
   $ git pull origin main --rebase
```

---

### Passo 3: Verificação de Lock (Controle de Concorrência)

```
1. Ler o arquivo .agent/session/CONSOLIDATION_LOG.md.
2. Verificar a ÚLTIMA linha da tabela.
3. Se a última linha contiver STATUS "CONSOLIDANDO" e o MACHINE_ID for DIFERENTE do seu:

   ⚠️ PARAR IMEDIATAMENTE. Exibir ao usuário:

   "⏸️ Consolidação bloqueada.
    A máquina [MACHINE_ID_OUTRO] adquiriu o lock às [TIMESTAMP_DO_LOG].
    Aguarde a conclusão ou rode /session-consolidate novamente em alguns minutos."

   Não prosseguir além deste passo.

4. Se o último registro for "CONSOLIDADO" ou for da própria máquina → prosseguir.
```

---

### Passo 4: Aquisição do Lock (Push Imediato)

```
1. Adicionar uma nova linha no final da tabela do CONSOLIDATION_LOG.md:
   | [TIMESTAMP] | [SEU_MACHINE_ID] | CONSOLIDANDO |

2. IMEDIATAMENTE commitar e empurrar para a nuvem para efetivar o lock:
   $ cd .agent/session
   $ git add CONSOLIDATION_LOG.md
   $ git commit -m "chore: acquire consolidation lock [MACHINE_ID]"
   $ git push origin main

3. Se o git push FALHAR (rejeitado — outra máquina fez push antes):
   → Desfazer o commit local: git reset HEAD~1 --hard
   → Avisar o usuário: "Lock perdido para outra máquina. Tente novamente."
   → PARAR.
```

---

### Passo 5: Leitura Semântica dos Shards

```
Com o lock confirmado na nuvem, você está seguro para consolidar:

1. Listar todos os arquivos .md dentro de .agent/session/shards/.
2. Ler o conteúdo de cada shard, extraindo:
   - Nome da máquina e Machine ID
   - Tarefa atual
   - Etapas
   - Status
   - Último sync
   - Atividades desta sessão
   - Próximo Passo (P0)

3. Incluir os dados do shard da própria máquina (9a7881ea.md ou equivalente).
```

---

### Passo 6: Reconstrução dos Artefatos

```
Com todos os dados dos shards em mãos:

A) Reconstruir README.md:
   Substituir completamente o conteúdo com o seguinte template didático para exibição no Github:

   <!-- .agent/session/README.md | Atualizado em: [TIMESTAMP] -->
   
   <div align="center">
     <h1>🛰️ Centro de Comando (Contexto)</h1>
     <p><b>Repositório Raiz:</b> <a href="https://github.com/vitalia-platform/revisao-dt">vitalia-platform/revisao-dt</a></p>
     <p>Este repositório atua como o cérebro distribuído da IA. Ele mantém o estado global, o histórico de sessões e o lock de sincronia entre as máquinas físicas do projeto.</p>
   </div>

   <br/>

   ## Painel de Máquinas (Shards) Horário Local (GMT-04:00)

   | Máquina | Tarefa Atual | Etapas | Status | Último Sync |
   | :--- | :--- | :--- | :--- | :--- |
   | [dados de cada shard (sem fuso na coluna)] |

B) Atualizar CONTEXT.md:
   - Atualizar o cabeçalho com o novo timestamp.
   - Atualizar o campo "Próximo passo (P0)" com o P0 mais prioritário entre os shards.
   - Não remover constraints, agentes ou outras seções estruturais.

C) Inserir no topo de SESSION_HISTORY.md (Cronologia Reversa — Regra P4):
   Para cada shard com atividades novas desta sessão, inserir um bloco no TOPO:

   ## ✅ Sessão Encerrada em [TIMESTAMP do shard]
   **Máquina:** [Machine Name] ([MACHINE_ID])
   **Tarefa:** [Tarefa do shard]
   **Atividades:**
   - [lista do shard]
   **Próxima sessão começa em:** [P0 do shard]
```

---

### Passo 7: Liberação do Lock e Push Final

```
1. Adicionar a linha de liberação no CONSOLIDATION_LOG.md:
   | [TIMESTAMP] | [SEU_MACHINE_ID] | CONSOLIDADO |

2. Commitar todos os artefatos reconstruídos e fazer push:
   $ cd .agent/session
   $ git add .
   $ git commit -m "chore: session consolidated — dashboard updated [TIMESTAMP]"
   $ git push origin main

3. Atualizar o lock de sincronia local para refletir o push da nuvem:
   $ python3 ../scripts/lib_sync_guard.py --action update --session-dir .
```

---

### Passo 8: Exibição do Dashboard

```
Exibir o conteúdo completo do README.md ao usuário no chat.
Encerrar com a mensagem:

   ✅ Consolidação concluída!
   🗓️  [TIMESTAMP]
   📊 Dashboard atualizado com [N] máquina(s).
   📡 Contexto sincronizado na nuvem.
```

---

## Exemplos de Uso

```
/session-consolidate
/session-consolidate   ← pode ser chamado a qualquer momento para ver o estado global
```
