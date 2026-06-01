#!/usr/bin/env bash
# .agent/scripts/session-sync.sh | Atualizado em: 01-06-2026 14:30:00(GMT-04:00)
#
# RESPONSABILIDADE EXCLUSIVA: Repositório de Contexto (.agent/session/)
# Este script NÃO toca o repositório raiz do projeto (revisao-dt).
# O commit do repositório raiz é feito pela Fase 2 do workflow /session-end.
#
# Fluxo (Fase 3 do /session-end):
#   1. [REBASE]        git pull origin main --rebase   → prioriza mudanças de outras máquinas
#   2. [CONSOLIDA]     session-consolidate.py           → mescla contextos multi-máquina
#   3. [COMMIT]        git add . && git commit
#   4. [PUSH]          git push origin main             → último passo real

set -e

KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.."/.. >/dev/null 2>&1 && pwd)/kit"
SESSION_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." >/dev/null 2>&1 && pwd)/session"
CONSOLIDATE_SCRIPT="${KIT_DIR}/scripts/session-consolidate.py"
COMMIT_MSG="${1:-"chore: session end [$(date +'%Y-%m-%d %H:%M')]"}"

# Validação: este diretório deve ser um repositório Git isolado
if [ ! -d "${SESSION_DIR}/.git" ]; then
    echo "❌ Erro: .agent/session/ não é um repositório Git."
    echo "   Configure o repositório de contexto separado antes de usar este script."
    exit 1
fi

cd "${SESSION_DIR}"

echo "🔄 [1/4] Puxando atualizações da Nuvem (prioridade à nuvem)..."
HAS_REMOTE=$(git ls-remote --heads origin main 2>/dev/null | wc -l | tr -d ' ')
if [ "${HAS_REMOTE}" -gt "0" ]; then
    git pull origin main --rebase || {
        echo "❌ Conflito de rebase detectado."
        echo "   Resolva os conflitos manualmente ou acione o session-resolve.sh."
        exit 1
    }
else
    echo "   ℹ️  Remoto sem histórico (repositório vazio). Pulando pull."
fi

echo "🧩 [2/4] Consolidando contextos de todas as máquinas..."
if [ -f "${CONSOLIDATE_SCRIPT}" ]; then
    python3 "${CONSOLIDATE_SCRIPT}" "${SESSION_DIR}"
else
    echo "   ⚠️  session-consolidate.py não encontrado em ${CONSOLIDATE_SCRIPT}. Pulando consolidação."
fi

echo "💾 [3/4] Salvando estado consolidado localmente..."
git add .
if ! git diff --staged --quiet; then
    git commit -m "${COMMIT_MSG}"
else
    echo "   (Nenhuma mudança nova para commitar)"
fi

echo "⬆️  [4/4] Enviando contexto para a Nuvem..."
if git push origin main; then
    echo "✅ Repositório de Contexto sincronizado com sucesso!"
    # Atualiza o lock de controle de concorrência
    if [ -f "${KIT_DIR}/scripts/lib_sync_guard.py" ]; then
        python3 "${KIT_DIR}/scripts/lib_sync_guard.py" --action update --session-dir "${SESSION_DIR}"
    fi
else
    echo "❌ Falha no Push. Verifique suas permissões e conexão SSH."
    exit 1
fi
