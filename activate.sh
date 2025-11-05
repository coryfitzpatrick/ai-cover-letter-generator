#!/bin/bash
# Quick activation script for cover-letter-ai-gen

cd "$(dirname "$0")"
source venv/bin/activate

echo "✓ Virtual environment activated"
echo ""
echo "Available commands:"
echo "  prepare-data      - Process PDFs and CSVs to build vector database"
echo "  cover-letter-cli  - Generate cover letters from job descriptions"
echo "  deactivate        - Exit virtual environment"
echo ""
