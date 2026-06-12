#!/bin/bash
# scripts/run_pipeline.sh - Orquestrador Autônomo das Fases

echo "=========================================="
echo "🚀 INICIANDO PIPELINE COMPLETA VITALIA"
echo "=========================================="

echo "[1/4] Fase 0: Ingestão API-First..."
.venv/bin/python scripts/review_pipeline/run_ingestion_api.py
if [ $? -ne 0 ]; then echo "❌ Erro na Ingestão. Abortando."; exit 1; fi

echo "[2/4] Fase 1: Triagem (Screening)..."
.venv/bin/python scripts/review_pipeline/run_fase1.py
if [ $? -ne 0 ]; then echo "❌ Erro na Triagem. Abortando."; exit 1; fi

echo "[3/4] Fase 2a: Download de PDFs..."
.venv/bin/python scripts/review_pipeline/run_pdf_download.py
if [ $? -ne 0 ]; then echo "❌ Erro no Download. Abortando."; exit 1; fi

echo "[4/4] Fase 2b: Extração Analítica..."
.venv/bin/python scripts/review_pipeline/run_fase2_extraction.py
if [ $? -ne 0 ]; then echo "❌ Erro na Extração. Abortando."; exit 1; fi

echo "=========================================="
echo "✅ PIPELINE CONCLUÍDA COM SUCESSO!"
echo "Abra .agent/data_storage/PROGRESS.html para ver o relatório final."
