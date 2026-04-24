import numpy as np
import pandas as pd
import math

class FeatureExtractor:
    def __init__(self, window_seconds=2.0):
        self.window_seconds = window_seconds

    def extract_features(self, history):
        """
        Extracts features from a list of drone states (history).
        History is a list of dicts with 'time', 'yaw', 'lat', 'lon', 'alt', 'vx', 'vy', 'vz', 'voltage', 'acc_x', 'acc_y', 'acc_z'.
        """
        if not history or len(history) < 2:
            return None

        # Filter history to the last window_seconds
        now = history[-1]['time']
        window_data = [h for h in history if now - h['time'] <= self.window_seconds]
        
        if len(window_data) < 2:
            return None

        df = pd.DataFrame(window_data)
        
        # 1. yaw_rate (rad/s)
        # We can use yawspeed from telemetry or calculate it from yaw
        # Let's use the average yawspeed if available, otherwise delta yaw
        if 'yawspeed' in df.columns and not df['yawspeed'].isnull().all():
            yaw_rate = df['yawspeed'].mean()
        else:
            delta_yaw = df['yaw'].iloc[-1] - df['yaw'].iloc[0]
            delta_time = df['time'].iloc[-1] - df['time'].iloc[0]
            yaw_rate = delta_yaw / delta_time if delta_time > 0 else 0

        # 2. gps_jump (meters)
        # Calculate distance between start and end of window
        # Using a simple approximation for small distances
        lat1, lon1 = df['lat'].iloc[0], df['lon'].iloc[0]
        lat2, lon2 = df['lat'].iloc[-1], df['lon'].iloc[-1]
        gps_jump = math.sqrt((lat2 - lat1)**2 + (lon2 - lon1)**2) * 111320 # approx meters

        # 3. alt_rate (m/s)
        delta_alt = df['alt'].iloc[-1] - df['alt'].iloc[0]
        delta_time = df['time'].iloc[-1] - df['time'].iloc[0]
        alt_rate = delta_alt / delta_time if delta_time > 0 else 0

        # 4. vel_magnitude (m/s)
        latest = window_data[-1]
        vel_magnitude = math.sqrt(latest.get('vx', 0)**2 + latest.get('vy', 0)**2 + latest.get('vz', 0)**2)

        # 5. acc_vel_mismatch
        # Compare change in velocity with integrated acceleration
        # delta_v = a * delta_t
        # mismatch = |(v_end - v_start) - sum(a * dt)|
        if 'acc_x' in df.columns:
            # Simple version: compare average acceleration with average velocity change
            acc_mag = np.sqrt(df['acc_x']**2 + df['acc_y']**2 + df['acc_z']**2).mean() / 1000.0 # m/s^2 (MAVLink acc is usually mG or cm/s^2, assuming cm/s^2 here for simplicity)
            # Actually HIGHRES_IMU is m/s^2 usually. Let's assume m/s^2.
            # But let's just use the difference between raw velocity and expected velocity from IMU
            # For now, a simpler metric: variance of velocity
            acc_vel_mismatch = df[['vx', 'vy', 'vz']].std().mean() # Placeholder for more complex logic
        else:
            acc_vel_mismatch = 0

        # 6. volt_drop (V)
        volt_drop = df['voltage'].iloc[0] - df['voltage'].iloc[-1]

        return {
            'yaw_rate': abs(yaw_rate),
            'gps_jump': gps_jump,
            'alt_rate': abs(alt_rate),
            'vel_magnitude': vel_magnitude,
            'acc_vel_mismatch': acc_vel_mismatch,
            'volt_drop': volt_drop
        }

if __name__ == "__main__":
    # Test extractor
    extractor = FeatureExtractor()
    test_history = [
        {'time': 0, 'yaw': 0, 'lat': 12.0, 'lon': 77.0, 'alt': 10, 'vx': 1, 'vy': 0, 'vz': 0, 'voltage': 12.6, 'acc_x': 0, 'acc_y': 0, 'acc_z': 9.8},
        {'time': 1, 'yaw': 0.1, 'lat': 12.0001, 'lon': 77.0, 'alt': 11, 'vx': 1.1, 'vy': 0, 'vz': 0, 'voltage': 12.5, 'acc_x': 0.1, 'acc_y': 0, 'acc_z': 9.8},
        {'time': 2, 'yaw': 0.2, 'lat': 12.0002, 'lon': 77.0, 'alt': 12, 'vx': 1.2, 'vy': 0, 'vz': 0, 'voltage': 12.4, 'acc_x': 0.2, 'acc_y': 0, 'acc_z': 9.8},
    ]
    features = extractor.extract_features(test_history)
    print("Extracted Features:", features)
