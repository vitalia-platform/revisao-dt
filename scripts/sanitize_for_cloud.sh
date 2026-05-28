#!/bin/bash
# scripts/sanitize_for_cloud.sh | Última Atualização: 21-05-2026 11:31:00(GMT-04:00)
# Valida configurações sensíveis antes de pushs ou operações em nuvem.

echo "🔍 Verificando arquivos sensíveis e configurações locais..."

# 1. Checagem do .env
if [ ! -f .env ]; then
    echo "⚠️  AVISO: Arquivo .env não encontrado na raiz."
    echo "   Copie o .env.example para .env e preencha suas variáveis locais (IP, emails)."
fi

# 2. Checagem de Hardcoded IPs no config
if grep -q "192\.168\." criteria_config.yaml 2>/dev/null; then
    echo "❌ ERRO DE SEGURANÇA: Endereço IP local detectado no criteria_config.yaml."
    echo "   Por favor, remova esse IP do YAML e coloque-o no arquivo .env (OLLAMA_BASE_URL=...)"
    exit 1
fi

# 3. Checagem do diretório .curadoria
if [ -d ".curadoria" ]; then
    # Verifica se .curadoria está no .gitignore
    if ! grep -q "^\.curadoria" .gitignore; then
        echo "❌ ERRO DE PRIVACIDADE: A pasta '.curadoria' não está sendo ignorada pelo Git."
        echo "   Adicione '.curadoria/' ao seu .gitignore para evitar vazamento de lixo ou dados privados."
        exit 1
    else
        echo "✅ A pasta secreta '.curadoria' está devidamente isolada via .gitignore."
    fi
fi

echo "🚀 Validação concluída. Ambiente e configurações parecem limpos para cloud!"
exit 0
