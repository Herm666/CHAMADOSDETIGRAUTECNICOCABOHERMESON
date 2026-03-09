#!/bin/bash
# TI Suporte — Script de inicialização
echo ""
echo "  ╔══════════════════════════════════════╗"
echo "  ║   TI Suporte — Iniciando sistema     ║"
echo "  ╚══════════════════════════════════════╝"
echo ""

# Verifica Python3
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 não encontrado. Por favor instale o Python 3.8+."
    exit 1
fi

# Pasta do script
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Inicia o backend em background
echo "  🚀 Iniciando backend na porta 5000..."
python3 "$DIR/backend/server.py" &
BACKEND_PID=$!
echo "  ✅ Backend rodando (PID: $BACKEND_PID)"
sleep 1

# Tenta abrir o navegador
echo ""
echo "  📂 Abrindo portal do solicitante..."
PORTAL="$DIR/frontend/solicitante.html"

if command -v xdg-open &> /dev/null; then
    xdg-open "$PORTAL"
elif command -v open &> /dev/null; then
    open "$PORTAL"
else
    echo "  ⚠️  Abra manualmente:"
    echo "      $PORTAL"
fi

echo ""
echo "  🌐 Portal Solicitante: file://$DIR/frontend/solicitante.html"
echo "  🔧 Painel Técnico:     file://$DIR/frontend/tecnico.html"
echo "  📡 API Backend:        http://localhost:5000/api/chamados"
echo ""
echo "  Pressione Ctrl+C para parar o servidor."
echo ""

# Aguarda o backend
wait $BACKEND_PID
