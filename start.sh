#!/bin/bash

echo "🚀 Starting TikTok Deputy Verification Application"
echo ""

# Check if database exists
if [ ! -f "tiktok_verification.db" ]; then
    echo "📊 Initializing database..."
    python load_data.py
    echo ""
fi

echo "🌐 Starting server at http://localhost:8000"
echo "Press Ctrl+C to stop the server"
echo ""

python main.py

