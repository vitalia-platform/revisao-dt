#!/bin/bash
# scripts/reset.sh - Orquestrador de Limpeza do Pipeline HITL

MODE="soft"
UI_ONLY=0
START_NEXT=0

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --hard|-h) MODE="hard" ;;
        --soft|-s) MODE="soft" ;;
        --ui-only) UI_ONLY=1 ;;
        --start|-a) START_NEXT=1 ;;
        *) echo "Parâmetro desconhecido: $1"; exit 1 ;;
    esac
    shift
done

echo "==================================="
echo "🧹 VITALIA RESET ($MODE)"
echo "==================================="

if [ "$UI_ONLY" -eq 1 ]; then
    echo "[*] Limpando apenas a interface (UI-Only)..."
    rm -f .agent/data_storage/LIVE_PROGRESS.html
    rm -f .agent/data_storage/LIVE_PROGRESS_STATE.js
    rm -f .agent/data_storage/PROGRESS.html
else
    if [ "$MODE" = "hard" ]; then
        echo "[*] Limpeza HARD: Destruindo TODOS os dados (incluindo Ingestão)..."
        rm -rf .agent/data_storage/saida
        rm -rf .agent/data_storage/fichamentos
    else
        echo "[*] Limpeza SOFT: Restaurando CSV e limpando Fases 1-3..."
        rm -rf .agent/data_storage/saida/auditoria/fase1_screening
        rm -rf .agent/data_storage/saida/auditoria/fase2a_download
        rm -rf .agent/data_storage/saida/auditoria/fase2b_extraction
        rm -rf .agent/data_storage/saida/auditoria/fase3_synthesis
        rm -rf .agent/data_storage/fichamentos
        
        # Resetar o PRISMA_LOG_MASTER via mini-script python in-line
        if [ -f ".agent/data_storage/saida/PRISMA_LOG_MASTER.csv" ]; then
            .venv/bin/python -c "
import csv, os
p = '.agent/data_storage/saida/PRISMA_LOG_MASTER.csv'
try:
    with open(p, 'r', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r['Status'] = 'Aguardando Triagem (API)'
        for key in ['Reasoning', 'CoT_Tags', 'Evidence_Quote']:
            if key in r: r[key] = ''
    if rows:
        with open(p, 'w', encoding='utf-8', newline='') as f:
            w = csv.DictWriter(f, fieldnames=rows[0].keys())
            w.writeheader()
            w.writerows(rows)
except Exception as e: print(f'Erro no soft reset: {e}')"
        fi
    fi
    
    echo "[*] Destruindo painéis em cache..."
    rm -f .agent/data_storage/LIVE_PROGRESS.html
    rm -f .agent/data_storage/LIVE_PROGRESS_STATE.js
    rm -f .agent/data_storage/PROGRESS.html
    
    echo "[*] Recriando estrutura de pastas base..."
    mkdir -p .agent/data_storage/saida/auditoria
    mkdir -p .agent/data_storage/fichamentos/pdfs
    mkdir -p .agent/data_storage/fichamentos/xmls
fi

echo "[*] Regerando painéis zerados..."
.venv/bin/python scripts/generate_live_dashboard.py
.venv/bin/python scripts/generate_progress.py

if [ "$START_NEXT" -eq 1 ]; then
    if [ "$MODE" = "hard" ]; then
        echo "[*] Iniciando Fase 0 (Ingestão)..."
        .venv/bin/python scripts/review_pipeline/run_ingestion_api.py
    else
        echo "[*] Iniciando Fase 1 (Triagem)..."
        .venv/bin/python scripts/review_pipeline/run_fase1.py
    fi
fi

echo "✅ Limpeza concluída!"
