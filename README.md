# RoboControl

Web-based controller for a Raspberry Pi robot car built on the RaspiRobot Board V3 (RRB3).

![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?style=flat&logo=fastapi&logoColor=white)
![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-3B%2B%2F4-C51A4A?style=flat&logo=raspberrypi&logoColor=white)
![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS-lightgrey?style=flat)
![License](https://img.shields.io/badge/license-MIT-green?style=flat)
![Hardware](https://img.shields.io/badge/hardware-RRB3-orange?style=flat)

---

## Gallery

| Front view | Top view | Angle view |
| :---: | :---: | :---: |
| ![Front](images/IMG_5125.JPG) | ![Top](images/IMG_5126.JPG) | ![Angle](images/IMG_5127.JPG) |

---

## Web UI

The control panel is a mobile-friendly dark-themed web app accessible at `http://<pi-ip>:8000`.

### Login

The login page shows a **robot status dot** (green = online, red = unreachable) before you even sign in. You can log in with your admin credentials or — if GitHub OAuth is configured — with the **Login with GitHub** button.

### Drive

![Drive tab](images/IMG_dash.png)

The main control screen. From top to bottom:

- **Camera preview** — live MJPEG stream inline while you drive (CSI or USB camera, auto-detected).
- **D-pad** — five-button directional controller. Top = forward, bottom = reverse, left/right turn, red centre = stop.
- **Speed slider** — sets motor power 0–100% (default 75%). Sent with every motor command.
- **Auto-Drive toggle** — reserved for upcoming autonomous navigation; currently labelled *"Not available yet"*.

---

### Camera

![Camera tab](images/IMG_camera.png)

Full-size live stream and a **Camera Pan & Tilt** 3×3 grid:

- Directional buttons nudge the pan/tilt servos.
- Centre button re-centres both servos.
- Stream source priority: **built-in CSI/USB camera → `CAMERA_STREAM_URL` → placeholder**.

---

### Missions

![Missions tab](images/IMG_missions.png)

Autonomous mission modes — all currently *"Coming soon"*:

| Mission | Description |
| ------- | ----------- |
| **Path Following** | Define a sequence of waypoints; the car executes the route autonomously. |
| **Visual Search** | Upload a target image; the car roams until the camera recognises it, then beeps and alerts you. |
| **Auto-Drive** | Fully autonomous free-roam using the sonar sensor to avoid obstacles. |

---

### Telemetry

![Telemetry tab](images/IMG_telemetry.png)

Live session statistics (resets on server restart):

| Metric | Description |
| ------ | ----------- |
| **Battery** | Voltage from the RRB3 ADC. |
| **Uptime** | Time elapsed since the server process started. |
| **Last CMD Latency** | Round-trip time of the most recent motor command. |
| **Commands Sent** | Total motor commands issued in this session. |
| **Obstacles Hit** | Times the sonar triggered an automatic stop. |
| **Est. Distance** | Approximate distance travelled, calculated from command duration. |

---

### Settings *(admin only)*

- **User management** — approve or revoke GitHub OAuth users.
- **GitHub OAuth** — set Client ID and Secret to enable social login.
- **Change password** — update the admin account password.

---

## Hardware

| Component | Details |
| ----------- | --------- |
| Raspberry Pi | 3B+ or later |
| Motor HAT | RaspiRobot Board V3 (RRB3) — dual DC motor driver |
| Distance sensor | HC-SR04 ultrasonic, mounted on the RRB3 sonar header |
| Camera | CSI Pi Camera Module **or** any USB webcam (auto-detected) |
| Servos (optional) | Pan/tilt camera mount, controlled via GPIO PWM |

---

## Bill of Materials

| # | Component | Notes |
| --- | ----------- | ------- |
| 1 | **Raspberry Pi 3B+ or 4** | Any model with 40-pin GPIO header |
| 2 | **RaspiRobot Board V3 (RRB3)** | Motor driver HAT, plugs directly onto GPIO header |
| 3 | **HC-SR04 Ultrasonic Sensor** | Plugs into the RRB3 sonar header |
| 4 | **2× DC Gear Motors with rubber wheels** | Any TT-motor compatible pair, ~3–6V |
| 5 | **2-wheel differential drive chassis** | Acrylic or 3D-printed frame |
| 6 | **LiPo battery pack** | 7.4V 2S LiPo; the RRB3 accepts 6–12V |
| 7 | **LiPo balance charger** | e.g. IMAX B6 or similar 2S charger |
| 8 | **Micro-USB cable** | Power to the Pi |
| 9 | **Dupont jumper wires** | For HC-SR04 and optional servo connections |
| 10 | **MicroSD card (16 GB+)** | For Raspberry Pi OS |
| 11 | **Pan/tilt servo bracket** *(optional)* | Any SG90-compatible 2-axis kit |
| 12 | **2× SG90 micro servos** *(optional)* | For camera pan/tilt mount |
| 13 | **USB webcam** *(optional)* | Logitech C270 / C920 or any UVC-compatible webcam |
| 14 | **Pi Camera Module** *(optional)* | CSI ribbon cable camera (1080P IR or standard) — alternative to USB |
| 15 | **Buzzer (passive/active)** *(optional)* | 5V, connects to GPIO 18 by default |

### Wiring overview

```text
Raspberry Pi GPIO header
        │
  RaspiRobot Board V3 (RRB3)
  ├── Left motor terminals  → Motor A
  ├── Right motor terminals → Motor B
  ├── Sonar header (5V / Trig / Echo / GND) → HC-SR04
  └── Power input (7.4V LiPo)

GPIO 12 (PWM) → Pan servo signal
GPIO 13 (PWM) → Tilt servo signal
GPIO 18       → Buzzer
CSI port      → Pi Camera Module ribbon cable  (option A)
USB port      → USB webcam                     (option B)
```

> **Power tip:** The RRB3 powers the motors from the LiPo. Power the Pi separately via its micro-USB port to avoid motor noise causing reboots.

---

## Camera Setup

The app auto-detects the camera on startup — no `.env` change needed:

| Camera type | How to connect | Extra setup |
| ----------- | -------------- | ----------- |
| **Pi Camera Module (CSI)** | Ribbon cable into the CSI port | `sudo apt install -y python3-picamera2` |
| **USB webcam** | Plug into any USB port | None — works out of the box |
| **External MJPEG stream** | Any IP camera / `mjpg-streamer` | Set `CAMERA_STREAM_URL=http://...` in `.env` |

Detection order: **CSI (`picamera2`) → USB (`opencv`) → `CAMERA_STREAM_URL` → placeholder**.

### Enabling the Pi Camera Module (CSI)

```bash
# Install the system package (not available via pip)
sudo apt install -y python3-picamera2

# Enable the camera interface
sudo raspi-config nonint do_camera 0

sudo reboot
```

### USB webcam — no extra steps

Just plug in the webcam and restart the service:

```bash
sudo systemctl restart robocontrol
```

---

## Setup (first time on the Pi)

SSH into the Pi and clone the repo:

```bash
git clone https://github.com/ZioGuillo/robocontrol.git ~/robocontrol
cd ~/robocontrol
```

Edit your config:

```bash
cp .env.example .env
nano .env
```

At minimum, set `SESSION_SECRET_KEY` — a random 32+ character string:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Run the install script — creates the venv, installs dependencies, and registers the systemd service:

```bash
bash scripts/install.sh
```

The web UI is available at `http://<pi-ip>:8000`.

### First login & changing the admin password

Default credentials: **`admin` / `admin`** — change immediately:

```bash
# From your local machine:
make set-password ADMIN_PASS=MyNewSecurePassword!
```

Or set it as part of the initial deploy:

```bash
make deploy ADMIN_PASS=MyNewSecurePassword!
```

---

## Authentication

RoboControl uses session-based login. There is one built-in admin account; additional users can sign in via **GitHub OAuth**.

| Role | Access |
| ---- | ------ |
| `admin` | All tabs including Settings |
| `approved` | Drive, Camera, Missions, Telemetry |
| `pending` | Sees "Awaiting approval" message |
| `revoked` | Sees "Access denied" message |

### GitHub OAuth setup

1. Go to **GitHub → Settings → Developer Settings → OAuth Apps → New OAuth App**
2. Set **Authorization callback URL** to `http://<pi-ip>:8000/auth/callback`
   - If the robot is exposed via a Cloudflare tunnel or reverse proxy, use the public URL instead: `https://rover.example.com/auth/callback`
3. Copy the **Client ID** and generate a **Client Secret**
4. Log in to RoboControl as admin → **Settings tab** → paste the credentials and enable GitHub OAuth
5. If using a public domain, set `BASE_URL=https://rover.example.com` in `.env` so OAuth redirect URIs match what GitHub expects

New GitHub users land in `pending` state until the admin approves them in the Settings tab.

### User avatar / icon

Each logged-in user can click their avatar in the top bar to choose a personal icon:

| Icon | Name |
| ---- | ---- |
| 🧑‍🚀 | Astronaut (default) |
| 👽 | Alien |
| 🛸 | UFO |
| 🐶 | Dog |

---

## Makefile — day-to-day commands

```bash
make help         # list all commands
make deploy       # push latest commits to the robot and restart
make restart      # restart the app without re-deploying
make logs         # stream live logs from the robot
make status       # check if the app is running
make test         # run the test suite locally
make open         # open the robot web UI in your browser
make set-password ADMIN_PASS=<new>   # change the admin password
make connect      # open an SSH shell on the robot
```

Override the robot IP for a single command:

```bash
make deploy PI_HOST=ec2-user@10.0.0.5
```

Or set it permanently in `.env`:

```bash
echo "PI_HOST=ec2-user@10.0.0.5" >> .env
```

---

## Service management (on the Pi)

```bash
sudo systemctl status robocontrol    # check if running
sudo systemctl restart robocontrol   # restart
sudo systemctl stop robocontrol      # stop
journalctl -u robocontrol -f         # live logs
journalctl -u robocontrol -n 50      # last 50 lines
```

---

## Configuration

All settings are read from `.env` (or environment variables):

| Variable | Default | Description |
| ---------- | --------- | ------------- |
| `SESSION_SECRET_KEY` | *(required)* | Signs session cookies — 32+ random chars |
| `PORT` | `8000` | HTTP port |
| `BASE_URL` | *(empty)* | Public base URL when behind a reverse proxy or Cloudflare tunnel (e.g. `https://rover.example.com`) — required for GitHub OAuth redirect URIs to resolve correctly |
| `CAMERA_STREAM_URL` | *(empty)* | Fallback MJPEG URL if no local camera is detected |
| `MOTOR_SPEED_DEFAULT` | `0.75` | Default motor speed (0.0–1.0) |
| `OBSTACLE_THRESHOLD_CM` | `20` | Sonar stop-and-turn threshold in centimetres |
| `PAN_SERVO_PIN` | `12` | GPIO pin for pan servo |
| `TILT_SERVO_PIN` | `13` | GPIO pin for tilt servo |
| `BUZZER_PIN` | `18` | GPIO pin for buzzer |
| `MOTOR_RATE_LIMIT` | `20` | Max motor commands/second per IP (0 = unlimited) |

---

## API

| Method | Path | Auth | Description |
| -------- | ------ | ---- | ------------- |
| `GET` | `/api/ping` | Public | Liveness check — always returns `{"ok": true}` |
| `GET` | `/api/status` | Required | Hardware availability (motors, servos) |
| `GET` | `/api/camera/stream` | Required | Live MJPEG stream (`multipart/x-mixed-replace`) |
| `POST` | `/api/camera/{action}` | Required | Pan/tilt: `up`, `down`, `left`, `right`, `center` |
| `POST` | `/api/motors/{action}` | Required | `forward`, `reverse`, `left`, `right`, `stop` |
| `POST` | `/api/motors/auto` | Required | Not implemented (501) |
| `POST` | `/api/missions/path` | Required | Not implemented (501) |
| `POST` | `/api/missions/search` | Required | Not implemented (501) |

Motor requests accept an optional JSON body: `{"speed": 0.75}` (0.0–1.0).

### Obstacle avoidance

When `forward` is called and the HC-SR04 reads below `OBSTACLE_THRESHOLD_CM`, the car automatically stops, turns right briefly, then stops again. The response includes `"blocked": true` and the measured distance, which triggers an alert in the UI.

---

## Development

Run tests (no hardware required — GPIO/rrb3 imports degrade gracefully):

```bash
pytest -v
```

The project uses **graceful hardware degradation**: if `rrb3`, `RPi.GPIO`, `picamera2`, or `opencv` are unavailable, the relevant driver sets `available = False` and all dependent routes return `503` rather than crashing.

---

## Extending the App

> The app uses **route auto-discovery** — you never need to touch `main.py` to add a new feature.

1. Copy `app/routes/_template.py` to a new file (no leading underscore), e.g. `app/routes/lights.py`.
2. Set the `prefix` and add your endpoints.
3. Restart — the new routes are live automatically.

```text
app/routes/
├── _template.py       ← copy this to start a new feature
├── camera.py          ← camera stream + pan/tilt
├── missions.py        ← stubs with IMPLEMENT comments
├── motors.py          ← drive commands + auto-drive stub
├── settings.py        ← user management, GitHub OAuth, password
├── status.py          ← hardware availability + ping
└── telemetry.py       ← session stats
```

### Hardware helpers

| Import | Provides |
| ------ | -------- |
| `from app.hardware import rrb3_driver` | `set_motors()`, `get_distance()`, `available` |
| `from app.hardware import servo_driver` | `move()`, `center()`, `available` |
| `from app.hardware import camera_driver` | `get_frame()`, `start()`, `stop()`, `available`, `_backend` |
| `from app.config import settings` | all `.env` values |
| `from app import telemetry` | `record_command()` |

---

## Future Implementations

- **Auto-drive** — fully autonomous navigation using the sonar sensor
- **Path following** — define a waypoint route; the car executes it autonomously
- **Visual search** — roam until the camera finds a target image match, then alert
- **Buzzer feedback** — audio confirmation for commands and obstacle alerts
- **Light control** — toggle RRB3 onboard LEDs from the UI
- **Battery monitoring** — display voltage from the RRB3 ADC

---

## Adapting to Different Hardware

Only the files in `app/hardware/` are tied to specific components. Everything else is hardware-agnostic.

### Alternative microcomputers

| Board | Notes |
| ----- | ----- |
| **NVIDIA Jetson Nano** | Swap `RPi.GPIO` for `Jetson.GPIO` (same API). |
| **Orange Pi / Banana Pi** | Use `OPi.GPIO` or `wiringOP`. |
| **BeagleBone Black** | Use `Adafruit_BBIO`. |
| **Arduino (co-processor)** | Send serial commands from `rrb3_driver.py` over USB. |

### Alternative motor drivers

| Driver | Notes |
| ------ | ----- |
| **L298N** | Direct `RPi.GPIO` PWM — no extra library. |
| **Adafruit Motor HAT** | `adafruit-circuitpython-motorkit`. |
| **Cytron MDD3A / MDD10A** | PWM + direction pins, same pattern as L298N. |
| **Pololu DRV8833** | Two PWM pins per motor. |

### Additional components

| Component | Library |
| --------- | ------- |
| **Encoder wheels** | `RPi.GPIO` interrupt — accurate odometry. |
| **IMU (MPU-6050)** | `mpu6050-raspberrypi` — orientation + acceleration. |
| **LIDAR (RPLidar A1)** | `rplidar-roboticia` — 2D mapping for auto-drive. |
| **NeoPixel LEDs** | `rpi_ws281x` — controllable RGB lighting. |
| **GPS module** | `gpsd` + `gps3` — real-world position. |
