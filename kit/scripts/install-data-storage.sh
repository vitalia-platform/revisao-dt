#!/usr/bin/env bash
# ==============================================================================
# install-data-storage.sh — Configura o repositório de dados da revisão
# Uso: bash kit/scripts/install-data-storage.sh
#
# Responsabilidades:
#   1. Verifica se .agent/data_storage/ já existe (idempotente)
#   2. Inicializa o repositório git de dados localmente
#   3. Cria a estrutura de pastas padrão com .gitkeep
#   4. Cria os symlinks na raiz do projeto
#   5. Conecta ao remoto informado pelo usuário (opcional)
# ==============================================================================
set -euo pipefail

# --- Localização ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DATA_DIR="$PROJECT_ROOT/.agent/data_storage"

echo "======================================================"
echo "📦 INSTALADOR DO STORAGE DE DADOS"
echo "======================================================"

# --- Passo 1: Criar e inicializar o repositório de dados ---
if [ -d "$DATA_DIR/.git" ]; then
    echo "ℹ️  .agent/data_storage já é um repositório git. Pulando inicialização."
else
    echo "📁 Criando .agent/data_storage e inicializando repositório git..."
    mkdir -p "$DATA_DIR"
    git -C "$DATA_DIR" init -b main
    echo "✅ Repositório inicializado."
fi

# --- Passo 2: Criar estrutura de pastas ---
echo ""
echo "📂 Criando estrutura de pastas padrão..."
FOLDERS=("amostra/biorxiv" "amostra/scopus" "amostra/webofscience" "exportacao" "fichamentos" "lotes" "saida/audit")
for folder in "${FOLDERS[@]}"; do
    mkdir -p "$DATA_DIR/$folder"
    touch "$DATA_DIR/$folder/.gitkeep"
done
echo "✅ Pastas criadas."

# --- Passo 3: Criar symlinks na raiz ---
echo ""
echo "🔗 Criando symlinks na raiz do projeto..."
SYMLINK_TARGETS=("amostra" "lotes" "saida" "exportacao" "fichamentos")
for target in "${SYMLINK_TARGETS[@]}"; do
    link_path="$PROJECT_ROOT/$target"
    if [ -L "$link_path" ]; then
        echo "   ↩️  $target (symlink já existe, ignorado)"
    elif [ -e "$link_path" ]; then
        echo "   ⚠️  $target já existe como diretório real. Movendo para o storage..."
        mv "$link_path" "$DATA_DIR/$target"
        ln -s ".agent/data_storage/$target" "$link_path"
        echo "   ✅ $target movido e symlink criado."
    else
        ln -s ".agent/data_storage/$target" "$link_path"
        echo "   ✅ $target → .agent/data_storage/$target"
    fi
done

# --- Passo 4: .gitignore na raiz ---
echo ""
echo "🔒 Verificando .gitignore da raiz..."
GITIGNORE="$PROJECT_ROOT/.gitignore"
if ! grep -q ".agent/data_storage/" "$GITIGNORE" 2>/dev/null; then
    cat >> "$GITIGNORE" <<'EOF'

# Ignorar storage de dados da revisão (repositório aninhado isolado)
.agent/data_storage/
.agent/data_storage/*
EOF
    echo "✅ .gitignore atualizado."
else
    echo "ℹ️  .gitignore já contém a entrada do data_storage."
fi

# --- Passo 5: Conectar ao remoto (opcional) ---
echo ""
read -rp "🌐 Informe a URL SSH do repositório de dados (Enter para pular): " REMOTE_URL
if [ -n "$REMOTE_URL" ]; then
    git -C "$DATA_DIR" remote add origin "$REMOTE_URL" 2>/dev/null || \
        git -C "$DATA_DIR" remote set-url origin "$REMOTE_URL"
    echo "✅ Remote configurado: $REMOTE_URL"
    echo ""
    echo "Para enviar os dados pela primeira vez:"
    echo "  cd .agent/data_storage && git add . && git commit -m 'chore: init data storage' && git push -u origin main"
else
    echo "ℹ️  Remote não configurado. Configure manualmente com:"
    echo "  cd .agent/data_storage && git remote add origin git@github.com:SEU_USUARIO/SEU_REPO_DADOS.git"
fi

echo ""
echo "======================================================"
echo "✅ Storage de dados configurado com sucesso!"
echo "======================================================"
