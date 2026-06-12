#!/bin/bash
# scripts/backup_experiment.sh - Cria um snapshot ZIP dos dados atuais

DATE_STR=$(date +"%d%b%y_%H%M%S")
BACKUP_DIR=".agent/backups"
ZIP_FILE="$BACKUP_DIR/backup_calibracao_$DATE_STR.zip"

mkdir -p "$BACKUP_DIR"

if [ -d ".agent/data_storage/saida" ]; then
    echo "📦 Compactando diretório de saída..."
    zip -r "$ZIP_FILE" .agent/data_storage/saida .agent/data_storage/fichamentos -q
    echo "✅ Backup criado com sucesso em: $ZIP_FILE"
else
    echo "❌ Diretório de saída não encontrado."
fi
