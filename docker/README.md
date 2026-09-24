# Local testing without hardware

Runs the full RoboControl dashboard — login, motor controls, telemetry,
camera stream, settings — on your laptop with **no Raspberry Pi, no RRB3
board, no camera**, so you can try changes before deploying to real
hardware.

This works by setting `SIMULATE=true`, which makes `app/hardware/*`
skip real GPIO/camera access entirely and simulate plausible values
instead:

- **Motors** accept every command and never error.
- **Sonar** reports a distance that sweeps 15–150cm on a ~10s cycle, so
  obstacle-avoidance logic and telemetry (`obstacles_detected`,
  `last_obstacle_cm`, `estimated_distance_m`) actually do something.
- **Camera** streams a generated test pattern (a bouncing circle + frame
  counter) instead of a real MJPEG feed.
- **Servos** (pan/tilt) track angle state normally, just without moving
  real hardware.
- **Battery / ML detection** stay unavailable, same as on real hardware
  without that specific sensor/model present — that's accurate, not a
  simulation gap.

`SIMULATE` only ever needs to be set explicitly — it defaults to `false`,
so a real Pi or Jetson never accidentally ignores its actual hardware.

## Run it

From the repo root:

```bash
docker compose -f docker/docker-compose.yml up --build
```

or without compose:

```bash
docker build -f docker/Dockerfile -t robocar-sim .
docker run --rm -p 8000:8000 robocar-sim
```

Then open **http://localhost:8000** — log in with `admin` / `admin` (you'll
be asked to change it on first login, same as on real hardware).

## What this does *not* catch

This is a software simulation of the hardware boundary, not the hardware
itself — it's for the dashboard, API, auth, and telemetry logic. It won't
catch real motor wiring, GPIO pin, or camera issues; verify those in
`app/hardware/` and README → **Supported Hardware** before deploying to a
board.
