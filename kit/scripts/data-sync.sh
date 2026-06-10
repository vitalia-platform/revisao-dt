#!/usr/bin/env bash
# kit/scripts/data-sync.sh | Atualizado em: 10-06-2026
#
# RESPONSABILIDADE EXCLUSIVA: Sincronizar o repositório de dados (.agent/data_storage)
#

set -e

ACTION="${1:-"--push"}"
DATA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." >/dev/null 2>&1 && pwd)/.agent/data_storage"
COMMIT_MSG="chore(data): auto-sync [$(date +'%Y-%m-%d %H:%M')]"

echo "🔄 [Data Storage] Iniciando sincronização ($ACTION)..."

# 1. Validação: verifica se é um repositório configurado
if [ ! -d "${DATA_DIR}/.git" ]; then
    echo "   ℹ️  .agent/data_storage/ não é um repositório Git. Pulando sincronização de dados."
    exit 0
fi

# 2. Trava de Segurança (Lock Guard): Verifica arquivos abertos via lsof
if command -v lsof >/dev/null 2>&1; then
    # lsof +D retorna 0 se achar arquivos, 1 se não achar
    if lsof +D "${DATA_DIR}" >/dev/null 2>&1; then
        echo "❌ ERRO DE CONCORRÊNCIA: Há processos manipulando arquivos em .agent/data_storage/"
        echo "   Processos ativos detectados via 'lsof'. Isso pode corromper o PRISMA_LOG_MASTER.csv."
        echo "   Por favor, aguarde a conclusão da extração/LLM ou feche os arquivos, e tente novamente."
        exit 1
    fi
fi

cd "${DATA_DIR}"

if [ "$ACTION" = "--pull" ]; then
    echo "⬇️  Puxando atualizações do Storage na nuvem..."
    HAS_REMOTE=$(git ls-remote --heads origin main 2>/dev/null | wc -l | tr -d ' ')
    if [ "${HAS_REMOTE}" -gt "0" ]; then
        git pull origin main --rebase || {
            echo "❌ Conflito detectado ao puxar o data_storage."
            echo "   Resolva manualmente em .agent/data_storage e rode o comando novamente."
            exit 1
        }
        echo "✅ Data Storage atualizado com sucesso."
    else
        echo "   ℹ️  Repositório remoto de dados ainda vazio."
    fi

elif [ "$ACTION" = "--push" ]; then
    echo "⬇️  [1/3] Puxando atualizações mais recentes (rebase)..."
    HAS_REMOTE=$(git ls-remote --heads origin main 2>/dev/null | wc -l | tr -d ' ')
    if [ "${HAS_REMOTE}" -gt "0" ]; then
        git pull origin main --rebase || {
            echo "❌ Conflito de rebase detectado no data_storage."
            echo "   Resolva os conflitos de CSV antes de enviar."
            exit 1
        }
    fi

    echo "💾 [2/3] Salvando estado local do Storage..."
    git add .
    if ! git diff --staged --quiet; then
        git commit -m "${COMMIT_MSG}"
    else
        echo "   ℹ️  Nenhuma alteração de dados nova para comitar."
        exit 0
    fi

    echo "⬆️  [3/3] Enviando dados para a nuvem..."
    if git push origin main; then
        echo "✅ Repositório de Data Storage sincronizado com sucesso!"
    else
        echo "❌ Falha no Push do Data Storage. Verifique suas permissões."
        exit 1
    fi
else
    echo "Ação inválida: $ACTION. Use --pull ou --push."
    exit 1
fi
