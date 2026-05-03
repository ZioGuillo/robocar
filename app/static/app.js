// ── Tab switching ──────────────────────────────────────────────
function showTab(name, btn) {
  document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  if (btn) btn.classList.add('active');
}

// ── Notifications ──────────────────────────────────────────────
function notify(message, type) {
  type = type || 'info';
  const area = document.getElementById('notification-area');
  const el = document.createElement('div');
  el.className = 'notification ' + type;

  const text = document.createElement('span');
  text.textContent = message;

  const close = document.createElement('button');
  close.className = 'notif-close';
  close.textContent = '✕';
  close.onclick = function() { el.remove(); };

  el.appendChild(text);
  el.appendChild(close);
  area.appendChild(el);
  setTimeout(function() { if (el.parentElement) el.remove(); }, 5000);
}

// ── Stream reconnect ───────────────────────────────────────────
var _streamRetry = {};

function onStreamError(id) {
  var overlay = document.getElementById(id + '-overlay');
  if (overlay) overlay.style.display = 'flex';
  if (_streamRetry[id]) return;
  _streamRetry[id] = setTimeout(function() {
    _streamRetry[id] = null;
    var el = document.getElementById(id);
    if (el) {
      var base = el.getAttribute('data-src') || el.src.split('?')[0];
      el.setAttribute('data-src', base);
      el.src = base + '?t=' + Date.now();
    }
  }, 3000);
}

function onStreamLoad(id) {
  var overlay = document.getElementById(id + '-overlay');
  if (overlay) overlay.style.display = 'none';
  clearTimeout(_streamRetry[id]);
  _streamRetry[id] = null;
}

function reconnectStreams() {
  ['cam-stream', 'pip-cam'].forEach(function(id) {
    clearTimeout(_streamRetry[id]);
    _streamRetry[id] = null;
    var el = document.getElementById(id);
    if (el && el.tagName === 'IMG') {
      var base = el.getAttribute('data-src') || el.src.split('?')[0];
      el.setAttribute('data-src', base);
      el.src = base + '?t=' + Date.now();
    }
  });
}

function reconnectAll() {
  _statusDisconnected = false;
  var btn = document.getElementById('reconnect-btn');
  if (btn) btn.style.display = 'none';
  reconnectStreams();
}

// ── Status polling ─────────────────────────────────────────────
var _statusDisconnected = false;

function pollStatus() {
  fetch('/api/status')
    .then(function(r) { return r.json(); })
    .then(function(data) {
      var wasDisconnected = _statusDisconnected;
      _statusDisconnected = false;
      var dot = document.getElementById('status-dot');
      var msg = document.getElementById('status-msg');
      var servoDot = document.getElementById('servo-dot');
      dot.className = 'status-dot ' + (data.ok ? 'ok' : 'error');
      dot.title = data.message;
      msg.textContent = data.ok ? '' : data.message;
      if (servoDot) {
        servoDot.className = data.servo_ok ? 'status-dot ok' : 'status-dot';
        servoDot.title = data.servo_ok ? 'Servo: connected' : 'Servo: not connected';
      }
      if (wasDisconnected) {
        reconnectAll();
      }
    })
    .catch(function() {
      var dot = document.getElementById('status-dot');
      var servoDot = document.getElementById('servo-dot');
      var reconnectBtn = document.getElementById('reconnect-btn');
      dot.className = 'status-dot error';
      dot.title = 'Cannot reach server';
      if (servoDot) {
        servoDot.className = 'status-dot';
        servoDot.title = 'Servo: unknown';
      }
      if (reconnectBtn) reconnectBtn.style.display = 'inline-flex';
      if (!_statusDisconnected) {
        _statusDisconnected = true;
        notify('Connection lost — reconnecting automatically', 'alert');
      }
    });
}

setInterval(pollStatus, 3000);
pollStatus();

// ── Motor control ──────────────────────────────────────────────
var currentSpeed = typeof MOTOR_SPEED_DEFAULT !== 'undefined' ? MOTOR_SPEED_DEFAULT : 0.75;
var actionInterval = null;
var holdStart = null;
var HOLD_LOCK_MS = 3000;   // hold > 3 s → keep moving until stop is pressed
var actionLocked = false;

function updateSpeed(val) {
  currentSpeed = val / 100;
  document.getElementById('speed-value').textContent = val + '%';
}

function beepWarning() {
  try {
    var ctx = new (window.AudioContext || window.webkitAudioContext)();
    [0, 0.25].forEach(function(offset) {
      var osc = ctx.createOscillator();
      var gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.type = 'square';
      osc.frequency.value = 880;
      gain.gain.setValueAtTime(0.25, ctx.currentTime + offset);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + offset + 0.2);
      osc.start(ctx.currentTime + offset);
      osc.stop(ctx.currentTime + offset + 0.2);
    });
  } catch (e) {}
}

function sendMotor(action) {
  fetch('/api/motors/' + action, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ speed: currentSpeed })
  })
    .then(function(r) { return r.json(); })
    .then(function(data) {
      if (data.blocked) {
        stopAction();
        beepWarning();
        notify(data.message || 'Obstacle detected!', 'alert');
      } else if (data.detail && !data.detail.ok) {
        notify(data.detail.message || 'Motor error', 'warning');
      }
    })
    .catch(function() { notify('Connection lost', 'alert'); });
}

function _setLockIndicator(locked) {
  var btn = document.getElementById('stop-btn');
  if (btn) btn.style.outline = locked ? '3px solid #f9a825' : '';
}

function startAction(action) {
  if (actionLocked) {
    // Switch to new direction without stopping
    clearInterval(actionInterval);
    actionInterval = null;
  }
  holdStart = Date.now();
  actionLocked = false;
  _setLockIndicator(false);
  clearInterval(actionInterval);
  actionInterval = null;
  sendMotor(action);
  actionInterval = setInterval(function() { sendMotor(action); }, 200);
}

function releaseAction() {
  if (!holdStart) return;
  var held = Date.now() - holdStart;
  holdStart = null;
  if (held >= HOLD_LOCK_MS) {
    // Held long enough → lock, keep moving, show indicator
    actionLocked = true;
    _setLockIndicator(true);
    notify('Locked — press Stop to halt', 'info');
    return;
  }
  stopAction();
}

function stopAction() {
  clearInterval(actionInterval);
  actionInterval = null;
  holdStart = null;
  actionLocked = false;
  _setLockIndicator(false);
  sendMotor('stop');
}

function autoDriveClick() {
  notify('Auto-drive is not available yet', 'info');
}

// ── Camera pan/tilt ────────────────────────────────────────────
function sendCamera(action) {
  fetch('/api/camera/' + action, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: '{}'
  })
    .then(function(r) { return r.json(); })
    .then(function(data) {
      if (data.detail && !data.detail.ok) {
        notify(data.detail.message || 'Camera error', 'warning');
      }
    })
    .catch(function() { notify('Connection lost', 'alert'); });
}

// ── Telemetry ──────────────────────────────────────────────────
function fmtUptime(s) {
  var h = Math.floor(s / 3600);
  var m = Math.floor((s % 3600) / 60);
  var sec = s % 60;
  return (h ? h + 'h ' : '') + (h || m ? m + 'm ' : '') + sec + 's';
}

// ok is a boolean from the API — safe to use innerHTML (no user input interpolated)
function batteryLabel(ok) {
  return ok
    ? '<span class="tel-latency-dot" style="background:#2dc653"></span>Connected'
    : '<span class="tel-latency-dot" style="background:#e53935"></span>Not detected';
}

function pollTelemetry() {
  fetch('/api/telemetry')
    .then(function(r) { return r.json(); })
    .then(function(d) {
      // Uptime
      document.getElementById('tel-uptime').textContent = fmtUptime(d.uptime_seconds);

      // Battery status (no ADC — show connection state)
      var motorBatEl = document.getElementById('tel-battery-motor');
      var piBatEl = document.getElementById('tel-battery-pi');
      if (motorBatEl) motorBatEl.innerHTML = batteryLabel(d.battery_motor_ok);
      if (piBatEl) piBatEl.innerHTML = batteryLabel(d.battery_pi_ok);

      // Latency
      var latEl = document.getElementById('tel-latency');
      var latBar = document.getElementById('tel-latency-bar');
      if (d.last_command_ms !== null && d.last_command_ms !== undefined) {
        latEl.textContent = d.last_command_ms + ' ms';
        var color = d.last_command_ms < 30 ? '#2dc653'
                  : d.last_command_ms < 80 ? '#f9a825'
                  : '#e53935';
        latBar.innerHTML = '<span class="tel-latency-dot" style="background:' + color + '"></span>'
          + (d.last_command_ms < 30 ? 'Fast' : d.last_command_ms < 80 ? 'OK' : 'Slow');
      } else {
        latEl.textContent = '—';
        latBar.textContent = '';
      }

      // Counters
      document.getElementById('tel-commands').textContent = d.commands_sent;
      document.getElementById('tel-obstacles').textContent = d.obstacles_detected;

      var obsEl = document.getElementById('tel-last-obstacle');
      obsEl.textContent = d.last_obstacle_cm !== null && d.last_obstacle_cm !== undefined
        ? 'last: ' + d.last_obstacle_cm + ' cm' : '';

      // Distance
      var distM = d.estimated_distance_m;
      document.getElementById('tel-distance').textContent =
        distM >= 1 ? distM.toFixed(1) + ' m' : Math.round(distM * 100) + ' cm';
    })
    .catch(function() {});
}

setInterval(pollTelemetry, 5000);
pollTelemetry();

// ── Mission stubs ──────────────────────────────────────────────
function sendMission(action) {
  fetch('/api/missions/' + action, { method: 'POST' })
    .then(function(r) { return r.json(); })
    .then(function(data) {
      if (data.detail) notify(data.detail.message, 'info');
    })
    .catch(function() { notify('Connection lost', 'alert'); });
}
