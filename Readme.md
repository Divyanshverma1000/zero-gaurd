# ZeroGuard — A Zero Trust Intrusion Detection System for UAV Swarms

## Overview

ZeroGuard is a real-time intrusion detection system designed for UAV swarms. It monitors drone telemetry, detects anomalous behavior, and isolates compromised drones using a combination of machine learning and cross-drone validation.

The system follows a Zero Trust approach, meaning no drone is trusted by default. Each drone is continuously evaluated based on its own behavior and its consistency with the rest of the swarm.

---

## System Architecture

### Swarm Layer (Cloud)

The system uses three UAVs simulated using DVDrone SITL, running as Docker containers on a cloud virtual machine. Each drone operates independently and continuously sends MAVLink telemetry data.

---

### Listener Layer (Local)

A Python-based listener connects to all drones simultaneously and collects telemetry data at regular intervals. The data is stored in sliding window buffers for each drone.

---

### Feature Extraction

At fixed intervals, the system computes a set of features from telemetry data, including:

* Yaw rate
* GPS discontinuity (position jumps)
* Altitude rate
* Velocity magnitude
* Acceleration and velocity consistency
* Battery voltage changes

These features represent the behavioral state of each drone.

---

### Machine Learning Model

An Isolation Forest model is trained on normal flight data. During operation, it assigns an anomaly score to each drone based on its behavior.

Scores close to zero indicate normal behavior, while lower scores indicate anomalies.

---

### Cross-Drone Validation

The system compares drones against each other to check consistency in their reported states. If one drone significantly disagrees with others in terms of position or motion, it is considered suspicious.

This enables detection of compromised drones even if their individual behavior appears normal.

---

### Trust Score Engine

A final trust score is computed for each drone by combining:

* The anomaly score from the machine learning model
* The consistency score from cross-drone validation

Based on this score, each drone is classified as:

* Trusted
* Suspicious
* Quarantined

---

### Dashboard

A live dashboard displays:

* Trust scores of all drones
* Current status of each drone
* Time-series graph of trust scores
* Detection events

---

## Project Structure

```
zeroguard/
├── cloud/
│   └── docker-compose-swarm.yml
├── data/
│   ├── normal/
│   └── attacks/
├── model/
│   └── isolation_forest.pkl
├── src/
│   ├── listener.py
│   ├── feature_extractor.py
│   ├── scorer.py
│   ├── cross_validator.py
│   ├── trust_engine.py
│   └── dashboard.py
├── training/
│   └── train_model.py
├── evaluation/
│   └── run_experiments.py
└── README.md
```

---

## How It Works

1. Drones send telemetry data continuously.
2. The listener collects and buffers this data.
3. Features are extracted from recent telemetry.
4. The machine learning model assigns anomaly scores.
5. The cross-validator checks consistency across drones.
6. A final trust score is computed.
7. Drones are labeled and displayed on the dashboard.
8. If a drone is compromised, it is detected and isolated.

---

## Running the Project

Start the swarm on the cloud:

```
cd cloud
docker-compose -f docker-compose-swarm.yml up
```

Run the local system:

```
python src/listener.py
python src/dashboard.py
```

---

## Training

To train the model on normal flight data:

```
python training/train_model.py
```

---

## Evaluation

To run experiments and generate metrics:

```
python evaluation/run_experiments.py
```

---

## Key Features

* Real-time intrusion detection
* Behavioral analysis of UAV telemetry
* Cross-drone validation for Zero Trust enforcement
* Lightweight machine learning model
* Live monitoring dashboard

---

## Future Improvements

* Support for larger swarm sizes
* Deployment on real UAV hardware
* Edge deployment capabilities
* Integration of advanced models

---

## Summary

ZeroGuard provides a practical approach to securing UAV swarms by combining real-time anomaly detection with cross-drone validation. It ensures that compromised drones can be detected and isolated without relying on prior trust assumptions.
