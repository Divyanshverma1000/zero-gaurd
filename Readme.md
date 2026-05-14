# ZeroGuard — Zero Trust Drone Security System

## Architecture

```
[Drone 1] ArduCopter → MAVLink → port 14550 ─┐
[Drone 2] ArduCopter → MAVLink → port 14560 ──┼─→ listener.py → detector.py → cli_dashboard.py
[Drone 3] ArduCopter → MAVLink → port 14570 ─┘
```

## Detection

- **Rule-based**: GPS jump, altitude spike, yaw rate, voltage drop, battery drop
- **ML**: Isolation Forest trained live on first 60 samples per drone
- **Zero Trust**: trust score starts at 100%, drops on anomaly, drone quarantined at <35%

---

## Setup & Run (2-hour presentation flow)

### Step 1 — Start Docker containers

```bash
cd ~/drone1 && docker compose -f docker-compose-lite.yaml up -d
cd ~/drone2 && docker compose -f docker-compose-lite.yaml up -d
```

### Step 2 — Start Drone 1 via web UI

Open http://localhost:8000 → click through Stage 1 → Stage 2 → drone flies

### Step 3 — Start Drone 2 (and optionally Drone 3)

```bash
cd ~ && bash zero-gaurd/start_drones.sh
```

### Step 4 — Verify both drones sending telemetry

```bash
python3 ~/multi_listner.py
# Should show drone1 and drone2 logging rows
# Ctrl+C after confirming
```

### Step 5 — Open CLI Dashboard (Terminal 1)

```bash
cd ~/zero-gaurd/src
python3 cli_dashboard.py
```

Wait ~60 seconds — ML model will train automatically per drone.

---

## Attacks (run in separate terminals)

### GPS Spoofing — attack drone 2
```bash
cd ~/zero-gaurd/src
python3 attack_gps_spoof.py 2
```

### Battery Spoofing — attack drone 1
```bash
cd ~/zero-gaurd/src
python3 attack_battery_spoof.py 1
```

### GPS Spoofing — attack drone 1 (classic demo)
```bash
cd ~/zero-gaurd/src
python3 attack_gps_spoof.py 1
```

---

## Expected Dashboard Behavior

| Time      | Event                                      |
|-----------|--------------------------------------------|
| 0–60s     | ML training, trust at 100%                 |
| Attack    | GPS_JUMP / VOLT_DROP flags appear          |
| ~5–10s    | Trust drops to SUSPICIOUS (yellow)         |
| ~15–20s   | Trust drops to QUARANTINED (red)           |
| Stop atk  | Trust slowly recovers                      |

---

## File Reference

| File                     | Purpose                              |
|--------------------------|--------------------------------------|
| `src/listener.py`        | Multi-drone MAVLink listener         |
| `src/detector.py`        | Rule-based + Isolation Forest        |
| `src/cli_dashboard.py`   | Full-screen terminal dashboard       |
| `src/attack_gps_spoof.py`    | GPS coordinate injection attack  |
| `src/attack_battery_spoof.py`| Battery/voltage drop attack      |
| `start_drones.sh`        | One-shot drone 2/3 startup script    |
| `multi_listner.py`       | Standalone telemetry logger (CSV)    |