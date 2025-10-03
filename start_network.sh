#!/bin/bash

echo "🌐 Starting TikTok Deputy Verification Application (Network Access)"
echo ""

# Check if database exists
if [ ! -f "tiktok_verification.db" ]; then
    echo "📊 Initializing database..."
    python load_data.py
    echo ""
fi

# Get local IP address
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "IP not found")
else
    # Linux
    LOCAL_IP=$(hostname -I | awk '{print $1}')
fi

echo "🖥️  Local access: http://localhost:8000"
echo "🌐 Network access: http://${LOCAL_IP}:8000"
echo ""
echo "Share the network URL with others on your WiFi/network!"
echo "Press Ctrl+C to stop the server"
echo ""
echo "═══════════════════════════════════════════════════════════"
echo ""

python main.py

