#!/bin/bash
# ZeroGuard — Start Drone 2 and Drone 3 ArduCopter + MAVLink routing
# Run this once after docker compose up for both drones.
# Drone 1 starts automatically via web UI (http://localhost:8000).

set -e

echo "============================================="
echo " ZeroGuard — Drone 2 & 3 Startup Script"
echo "============================================="

# ── Helper ────────────────────────────────────────────────────────────────────
start_drone() {
    local DRONE_ID=$1
    local FC_CONTAINER=$2
    local CC_CONTAINER=$3
    local GCS_IP=$4
    local HOST_PORT=$5
    local LAT=$6
    local LON=$7

    echo ""
    echo "[Drone $DRONE_ID] Starting ArduCopter in $FC_CONTAINER..."
    docker exec -d "$FC_CONTAINER" bash -c "
        cd /ardupilot && \
        python Tools/autotest/sim_vehicle.py \
            -v ArduCopter \
            --add-param-file drone.parm \
            --custom-location ${LAT},${LON},137,340 \
            -f quad \
            --no-rebuild \
            --no-mavproxy \
            -A --serial0=uart:/dev/ttyACM0:57600 \
            > /tmp/arducopter.log 2>&1
    "
    echo "[Drone $DRONE_ID] Waiting 20s for ArduCopter to boot..."
    sleep 20

    # Check it started
    if docker exec "$FC_CONTAINER" ps aux | grep -q "[a]rducopter"; then
        echo "[Drone $DRONE_ID] ✅ ArduCopter running"
    else
        echo "[Drone $DRONE_ID] ❌ ArduCopter failed to start — check /tmp/arducopter.log"
        return 1
    fi

    echo "[Drone $DRONE_ID] Starting MAVLink router → host:$HOST_PORT..."
    docker exec "$CC_CONTAINER" pkill mavlink-routerd 2>/dev/null || true
    sleep 1
    docker exec -d "$CC_CONTAINER" bash -c "
        mavlink-routerd -r -l /var/log/mavlink-router \
            --tcp-port 576${DRONE_ID} \
            /dev/ttyUSB0:57600 \
            -e 127.0.0.1:14540 \
            -e ${GCS_IP}:14550 \
            -e 172.17.0.1:${HOST_PORT} \
            > /tmp/mavlink.log 2>&1
    "
    sleep 3

    if docker exec "$CC_CONTAINER" ps aux | grep -q "[m]avlink-routerd"; then
        echo "[Drone $DRONE_ID] ✅ MAVLink router running on host port $HOST_PORT"
    else
        echo "[Drone $DRONE_ID] ❌ MAVLink router failed"
    fi
}

# ── Drone 2 ───────────────────────────────────────────────────────────────────
start_drone 2 \
    "flight-controller-lite-2" \
    "companion-computer-lite-2" \
    "10.14.0.4" \
    14560 \
    "37.242500" "-115.797500"

# ── Drone 3 (uncomment when you have drone3 docker setup) ─────────────────────
# start_drone 3 \
#     "flight-controller-lite-3" \
#     "companion-computer-lite-3" \
#     "10.15.0.4" \
#     14570 \
#     "37.243000" "-115.798000"

echo ""
echo "============================================="
echo " Done! Verify with:"
echo "   python3 ~/multi_listner.py"
echo ""
echo " Then open 3 terminals:"
echo "   Terminal 1: cd ~/zero-gaurd/src && python3 cli_dashboard.py"
echo "   Terminal 2: python3 attack_gps_spoof.py 2       # attack drone 2"
echo "   Terminal 3: python3 attack_battery_spoof.py 1   # attack drone 1"
echo "============================================="