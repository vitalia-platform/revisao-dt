#!/bin/bash
# scripts/status_cli.sh - Radar rápido de terminal

CSV_PATH=".agent/data_storage/saida/PRISMA_LOG_MASTER.csv"

if [ ! -f "$CSV_PATH" ]; then
    echo "❌ PRISMA_LOG_MASTER.csv não encontrado. Nenhuma Ingestão detectada."
    exit 1
fi

TOTAL=$(tail -n +2 "$CSV_PATH" | wc -l)
INCLUIDOS=$(grep -i "inclu" "$CSV_PATH" | wc -l)
EXCLUIDOS=$(grep -i "exclu" "$CSV_PATH" | wc -l)
PENDENTES_F1=$(grep -i "aguardando" "$CSV_PATH" | wc -l)

echo "=========================================="
echo "📊 STATUS DO PIPELINE VITALIA"
echo "=========================================="
echo "Total Ingerido (Fase 0): $TOTAL"
echo "Aguardando Triagem:      $PENDENTES_F1"
echo "Triados - Incluídos:     $INCLUIDOS"
echo "Triados - Excluídos:     $EXCLUIDOS"
echo "=========================================="
