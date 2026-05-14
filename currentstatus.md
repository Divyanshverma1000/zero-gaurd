## Demo Setup — Complete Runbook

### Pre-requisite: Drone must be flying

Go to `http://34.61.213.128:8000` and click:
1. **Initial Boot** → wait 30 seconds
2. **Arm & Takeoff** → wait until ARMED
3. **Autopilot Flight**

---

### Terminal 1 — Start the Detector (run this first)

```bash
ssh -i C:\Users\divya\.ssh\zeroguard microaimsportal_noreply@34.61.213.128
cd ~/zero-gaurd
python3 src/detector.py
```

You will see:
```
ZeroGuard IDS — Real-time UAV Anomaly Detection
Drone 1 | Watching for GPS spoofing attacks...
[Drone 1] lat=37.2419 lon=-115.7969 alt=139.8m | Trust [████████████████████] 100.0% TRUSTED
```

Wait until this is scrolling steadily before launching any attack.

---

### Terminal 2 — Launch the GPS Spoofing Attack

```bash
ssh -i C:\Users\divya\.ssh\zeroguard microaimsportal_noreply@34.61.213.128
cd ~/zero-gaurd
sudo python3 src/attack_gps_spoof.py
```

Immediately watch Terminal 1. You will see:

```
⚠️  ALERT Drone 1: GPS_JUMP 10373.67km in 0.30s
============================================================
  🚨 DRONE 1 QUARANTINED — GPS SPOOFING DETECTED
============================================================
```

Stop the attack with Ctrl+C. Trust score will slowly recover back to TRUSTED.

---

### Terminal 3 — (Optional) Battery Spoofing Attack

```bash
ssh -i C:\Users\divya\.ssh\zeroguard microaimsportal_noreply@34.61.213.128
cd ~/zero-gaurd
python3 src/attack_battery_spoof.py
```

Watch Terminal 1 show VOLT_DROP alert → SUSPICIOUS.

---

### File Summary — What each file does

```
~/zero-gaurd/
│
├── src/
│   ├── listener.py              ← reads MAVLink UDP stream from drone
│   ├── detector.py              ← runs listener + trust scoring + prints alerts
│   ├── attack_gps_spoof.py      ← GPS spoofing attack (UDP injection)
│   ├── attack_mavlink_inject.py ← GPS injection via TCP:5760 (cleaner attack)
│   ├── attack_battery_spoof.py  ← battery spoofing attack
│   └── attack_attitude_spoof.py ← attitude spoofing attack
│
~/drone1/
│   └── docker-compose-lite.yaml ← starts all 4 drone containers
│
http://34.61.213.128:8000        ← web UI to boot and fly the drone
```

---

### Demo Order for Professor (10 minutes)

```
Step 1  Open Terminal 1 → run detector.py       → show TRUSTED green
Step 2  Open Terminal 2 → run attack_gps_spoof  → show QUARANTINED red
Step 3  Stop attack     → show trust recovering → back to TRUSTED
Step 4  Run battery attack                      → show SUSPICIOUS yellow
Step 5  Explain the architecture while it runs
```

### If anything breaks — quick recovery

```bash
# Drone stopped? Restart everything:
cd ~/drone1
docker compose -f docker-compose-lite.yaml down
docker compose -f docker-compose-lite.yaml up -d
# Then redo web UI boot sequence at http://34.61.213.128:8000

# Detector not receiving data?
python3 -c "
from pymavlink import mavutil
m = mavutil.mavlink_connection('udpin:0.0.0.0:14550')
msg = m.recv_match(blocking=True, timeout=8)
print('OK:', msg.get_type()) if msg else print('NO DATA — reboot drone')
"

# Attack script says module not found?
pip3 install pymavlink scapy --break-system-packages
```

That's everything you need. Three terminals, one web browser tab, and those five commands. Good luck with the presentation.