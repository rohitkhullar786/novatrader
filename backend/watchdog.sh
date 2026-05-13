#!/bin/bash
# Watchdog script to keep the trading bot running
# Monitors: backend, frontend, AI reasoning health

BACKEND_DIR="/home/super/.openclaw/workspace/crypto-agent-v2/backend"
BACKEND_PORT=5181
FRONTEND_PORT=5180
LOG_FILE="$BACKEND_DIR/watchdog.log"
MAX_DECISION_AGE=300  # 5 minutes - if no new decision in 5 min, alert

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

restart_backend() {
    log "Restarting backend..."
    pkill -f "uvicorn main:app.*5181" 2>/dev/null
    sleep 2
    cd "$BACKEND_DIR"
    nohup python3 -m uvicorn main:app --host 0.0.0.0 --port $BACKEND_PORT >> /tmp/backend.log 2>&1 &
    sleep 4
    
    # Check if backend is responding
    if curl -s http://localhost:$BACKEND_PORT/api/balance > /dev/null 2>&1; then
        log "Backend restarted successfully"
        # Start auto-run
        curl -s -X POST http://localhost:$BACKEND_PORT/api/auto/start > /dev/null 2>&1
        log "Auto-run enabled"
        return 0
    else
        log "Backend restart failed, retrying in 30s..."
        sleep 30
        return 1
    fi
}

restart_frontend() {
    log "Restarting frontend..."
    pkill -f "vite.*5180" 2>/dev/null
    sleep 2
    cd "$BACKEND_DIR/../dashboard"
    nohup npx vite --host 0.0.0.0 --port $FRONTEND_PORT > /tmp/frontend.log 2>&1 &
    sleep 4
    
    if curl -s http://localhost:$FRONTEND_PORT > /dev/null 2>&1; then
        log "Frontend restarted successfully"
        return 0
    else
        log "Frontend restart failed, retrying in 30s..."
        sleep 30
        return 1
    fi
}

check_ai_reasoning() {
    # Check if decisions are being made regularly
    local last_decision=$(curl -s http://localhost:$BACKEND_PORT/api/decisions 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0]['timestamp'] if d else 'none')" 2>/dev/null)
    
    if [ "$last_decision" = "none" ] || [ -z "$last_decision" ]; then
        log "WARNING: No decisions found in history"
        return 1
    fi
    
    # Calculate age of last decision in seconds
    local decision_time=$(date -d "${last_decision:0:19}" +%s 2>/dev/null || echo "0")
    local now_time=$(date +%s)
    local age=$((now_time - decision_time))
    
    if [ $age -gt $MAX_DECISION_AGE ]; then
        log "WARNING: Last decision was ${age}s ago (max: ${MAX_DECISION_AGE}s) - AI reasoning may be stuck!"
        return 1
    fi
    
    return 0
}

log "========================================="
log "Watchdog started - monitoring backend, frontend, and AI reasoning"
log "========================================="

# Start services if not running
if ! pgrep -f "uvicorn main:app.*5181" > /dev/null 2>&1; then
    log "Backend not running, starting..."
    restart_backend
fi

if ! pgrep -f "vite.*5180" > /dev/null 2>&1; then
    log "Frontend not running, starting..."
    restart_frontend
fi

while true; do
    # Check backend
    if ! pgrep -f "uvicorn main:app.*5181" > /dev/null 2>&1; then
        log "Backend not running!"
        restart_backend
    else
        # Check if backend is responding
        if ! curl -s http://localhost:$BACKEND_PORT/api/balance > /dev/null 2>&1; then
            log "Backend not responding!"
            restart_backend
        fi
    fi
    
    # Check frontend
    if ! pgrep -f "vite.*5180" > /dev/null 2>&1; then
        log "Frontend not running!"
        restart_frontend
    else
        # Check if frontend is responding
        if ! curl -s http://localhost:$FRONTEND_PORT > /dev/null 2>&1; then
            log "Frontend not responding!"
            restart_frontend
        fi
    fi
    
    # Check AI reasoning health
    check_ai_reasoning
    
    log "Health check OK - Backend: $(pgrep -c -f "uvicorn main:app.*5181" 2>/dev/null || echo 0), Frontend: $(pgrep -c -f "vite.*5180" 2>/dev/null || echo 0)"
    
    sleep 60  # Check every minute
done