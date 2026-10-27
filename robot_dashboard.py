#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""لوحة تحكم روبوت عبر Wi-Fi.

تشغيلها على Raspberry Pi:
    python3 robot_dashboard.py
ثم افتح من الحاسوب (على نفس الشبكة):
    http://IP-OF-RASPBERRY:5000

القيادة: أسهم الكيبورد أو W/A/S/D. المسافة = حركة جانبية لليمين/اليسار.
الذراع: PCA9685 على القنوات 0، 1، 2 فقط.
"""

from time import sleep, monotonic
from threading import Lock, Thread

import cv2
import numpy as np
from flask import Flask, Response, jsonify, render_template_string, request
from gpiozero import Motor
from picamera2 import Picamera2
from adafruit_servokit import ServoKit


# ==================== إعدادات يمكن تعديلها ====================
DRIVE_SPEED = 0.30          # ارفعها/اخفضها ضمن 0.20 إلى 0.50 بعد التجربة
MOTOR_TIMEOUT = 0.50        # يتوقف الروبوت إن لم تصله أوامر خلال نصف ثانية
PCA_ADDRESS = 0x40
ARM_CHANNELS = (0, 1, 2)

# المجال الآمن لكل مفصل. عدّله لاحقاً حسب حدود ذراعك الفعلية.
# مثال: إن كان السيرفو رقم 1 لا يجب أن يتجاوز 130، اكتب 130 مكان 160.
ARM_LIMITS = {
    0: (20, 160),
    1: (20, 160),
    2: (20, 160),
}

# إن دارت عجلة بعكس المطلوب، بدّل False إلى True أمام اسمها فقط.
MOTOR_INVERT = {"FL": False, "BL": False, "FR": False, "BR": False}


# ==================== المحركات ====================
FL = Motor(forward=5, backward=6, enable=12, pwm=True)
BL = Motor(forward=16, backward=20, enable=13, pwm=True)
FR = Motor(forward=21, backward=26, enable=18, pwm=True)
BR = Motor(forward=25, backward=8, enable=19, pwm=True)
MOTORS = {"FL": FL, "BL": BL, "FR": FR, "BR": BR}

last_motor_command = monotonic()
motor_lock = Lock()


def set_motor(name, value):
    """القيمة من -1 إلى +1: موجب أمام، سالب خلف."""
    value = max(-1.0, min(1.0, float(value)))
    if MOTOR_INVERT[name]:
        value = -value
    motor = MOTORS[name]
    if value > 0:
        motor.forward(value)
    elif value < 0:
        motor.backward(-value)
    else:
        motor.stop()


def stop_motors():
    for motor in MOTORS.values():
        motor.stop()


def drive(command):
    """الحركات مطابقة لتوصيلات فحص المحركات التي نجحت عندك."""
    global last_motor_command
    s = DRIVE_SPEED
    commands = {
        "forward": (s, s, s, s),
        "backward": (-s, -s, -s, -s),
        # حركة جانبية لعجلات mecanum، وليست دوراناً حول مكان الروبوت.
        "right": (s, -s, -s, s),
        "left": (-s, s, s, -s),
        "stop": (0, 0, 0, 0),
    }
    if command not in commands:
        return False
    fl, fr, bl, br = commands[command]
    with motor_lock:
        set_motor("FL", fl)
        set_motor("FR", fr)
        set_motor("BL", bl)
        set_motor("BR", br)
        last_motor_command = monotonic()
    return True


def motor_watchdog():
    """طبقة أمان: توقف فوري عند انقطاع الواي فاي أو تحرير الزر."""
    while True:
        if monotonic() - last_motor_command > MOTOR_TIMEOUT:
            with motor_lock:
                stop_motors()
        sleep(0.05)


# ==================== الذراع PCA9685 ====================
kit = ServoKit(channels=16, address=PCA_ADDRESS)
for channel in ARM_CHANNELS:
    # يناسب أغلب Servo 5V. لا يرسل أي زاوية عند بدء البرنامج.
    kit.servo[channel].set_pulse_width_range(500, 2500)


def move_servo(channel, angle):
    if channel not in ARM_CHANNELS:
        return None
    low, high = ARM_LIMITS[channel]
    angle = max(low, min(high, int(angle)))
    kit.servo[channel].angle = angle
    return angle


# ==================== الكاميرا وقراءة اللون ====================
camera_lock = Lock()
latest_jpeg = None
latest_colour = "بانتظار الكاميرا"
latest_score = 0.0
camera_error = ""

COLOUR_AR = {
    "blue": "أزرق",
    "yellow": "أصفر",
    "white": "أبيض",
    "red": "أحمر",
    "green": "أخضر",
    "black": "أسود",
    "unknown": "غير معروف",
}


def detect_colour(rgb):
    """يفحص المنطقة الوسطية كي لا تتأثر بخلفية المكان."""
    height, width = rgb.shape[:2]
    x1, x2 = int(width * 0.25), int(width * 0.75)
    y1, y2 = int(height * 0.25), int(height * 0.75)
    roi = rgb[y1:y2, x1:x2]
    hsv = cv2.cvtColor(roi, cv2.COLOR_RGB2HSV)

    masks = {
        "blue": cv2.inRange(hsv, (90, 80, 45), (135, 255, 255)),
        "yellow": cv2.inRange(hsv, (18, 80, 70), (40, 255, 255)),
        "green": cv2.inRange(hsv, (40, 65, 45), (90, 255, 255)),
        "white": cv2.inRange(hsv, (0, 0, 170), (180, 55, 255)),
        "black": cv2.inRange(hsv, (0, 0, 0), (180, 255, 55)),
    }
    red1 = cv2.inRange(hsv, (0, 90, 45), (10, 255, 255))
    red2 = cv2.inRange(hsv, (170, 90, 45), (180, 255, 255))
    masks["red"] = cv2.bitwise_or(red1, red2)

    total = roi.shape[0] * roi.shape[1]
    scores = {name: 100.0 * cv2.countNonZero(mask) / total
              for name, mask in masks.items()}
    name = max(scores, key=scores.get)
    score = scores[name]
    # أقل من 5% من وسط الصورة: لا نعرض لوناً خاطئاً.
    if score < 5.0:
        return "unknown", score
    return name, score


def camera_worker():
    global latest_jpeg, latest_colour, latest_score, camera_error
    camera = None
    try:
        camera = Picamera2()
        config = camera.create_video_configuration(
            main={"size": (640, 480), "format": "RGB888"}
        )
        camera.configure(config)
        camera.start()
        sleep(1.5)

        while True:
            rgb = camera.capture_array()
            colour, score = detect_colour(rgb)
            bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
            label = f"{COLOUR_AR[colour]}  {score:.1f}%"
            cv2.rectangle(bgr, (160, 120), (480, 360), (0, 255, 0), 2)
            cv2.putText(bgr, label, (20, 40), cv2.FONT_HERSHEY_SIMPLEX,
                        0.9, (0, 255, 0), 2)
            ok, buffer = cv2.imencode(".jpg", bgr,
                                      [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            if ok:
                with camera_lock:
                    latest_jpeg = buffer.tobytes()
                    latest_colour = colour
                    latest_score = score
            sleep(0.03)
    except Exception as exc:
        camera_error = str(exc)
        print("خطأ الكاميرا:", camera_error)
    finally:
        if camera is not None:
            camera.stop()


# ==================== واجهة الويب ====================
app = Flask(__name__)

PAGE = """
<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>لوحة تحكم الروبوت</title>
<style>
  body{font-family:Arial,sans-serif;background:#111827;color:#e5e7eb;margin:0;padding:18px}
  h1{margin-top:0;color:#60a5fa}.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px;max-width:1100px;margin:auto}
  .card{background:#1f2937;border-radius:14px;padding:18px;box-shadow:0 3px 10px #0007}
  button{font-size:18px;background:#2563eb;color:#fff;border:0;border-radius:10px;padding:14px;min-width:85px;margin:4px;touch-action:none}
  button.stop{background:#dc2626} button:active{background:#1d4ed8}.drive{text-align:center;direction:ltr}.spacer{display:inline-block;width:94px}
  .camera{width:100%;max-width:640px;border-radius:10px;background:#000}.colour{font-size:25px;color:#facc15;font-weight:bold}
  .servo{border-top:1px solid #4b5563;padding:12px 0}.servo:first-of-type{border-top:0}
  input[type=range]{width:65%} input[type=number]{width:70px;padding:7px;font-size:16px;border-radius:7px;border:0}
  small{color:#9ca3af}@media(max-width:760px){.grid{grid-template-columns:1fr}}
</style>
</head>
<body>
<h1>🤖 لوحة تحكم الروبوت</h1>
<div class="grid">
  <section class="card">
    <h2>القيادة</h2>
    <p>استخدم الأسهم أو <b>W A S D</b>. الحركة يمين/يسار جانبية.</p>
    <div class="drive">
      <button data-cmd="forward">▲<br>أمام</button><br>
      <button data-cmd="left">◀<br>يسار</button>
      <button class="stop" id="stop">■<br>توقف</button>
      <button data-cmd="right">▶<br>يمين</button><br>
      <button data-cmd="backward">▼<br>خلف</button>
    </div>
    <p><small>أمان: يتوقف تلقائياً خلال نصف ثانية إن انقطع الأمر.</small></p>
  </section>
  <section class="card">
    <h2>الكاميرا وقراءة لون المكعب</h2>
    <img class="camera" src="/stream" alt="بث الكاميرا">
    <p>اللون الحالي: <span class="colour" id="colour">بانتظار الكاميرا</span></p>
    <small id="score"></small>
  </section>
  <section class="card">
    <h2>الذراع – PCA9685</h2>
    <p><small>حرّك المنزلق أو اكتب زاوية. لا نرسل أمر للسيرفو إلا بعد تغييرك للقيمة.</small></p>
    {% for channel in channels %}
    <div class="servo">
      <b>سيرفو القناة {{ channel }}</b> <small>({{ limits[channel][0] }}°–{{ limits[channel][1] }}°)</small><br>
      <input class="slider" data-channel="{{ channel }}" type="range" min="{{ limits[channel][0] }}" max="{{ limits[channel][1] }}" value="90">
      <input class="angle" data-channel="{{ channel }}" type="number" min="{{ limits[channel][0] }}" max="{{ limits[channel][1] }}" value="90"> °
    </div>
    {% endfor %}
  </section>
</div>
<script>
let held = null, repeatTimer = null;
function send(cmd){ fetch('/api/move',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({command:cmd})}); }
function begin(cmd){ if(held===cmd)return; end(); held=cmd; send(cmd); repeatTimer=setInterval(()=>send(cmd),120); }
function end(){ if(repeatTimer)clearInterval(repeatTimer); repeatTimer=null; held=null; send('stop'); }
document.querySelectorAll('[data-cmd]').forEach(b=>{
  b.addEventListener('pointerdown',e=>{e.preventDefault();begin(b.dataset.cmd)});
  b.addEventListener('pointerup',end);b.addEventListener('pointerleave',end);b.addEventListener('pointercancel',end);
});
document.getElementById('stop').addEventListener('click',end);
const keys={ArrowUp:'forward',w:'forward',W:'forward',ArrowDown:'backward',s:'backward',S:'backward',ArrowRight:'right',d:'right',D:'right',ArrowLeft:'left',a:'left',A:'left'};
document.addEventListener('keydown',e=>{if(document.activeElement.tagName==='INPUT')return;if(keys[e.key]){e.preventDefault();begin(keys[e.key])}if(e.code==='Space'){e.preventDefault();end()}});
document.addEventListener('keyup',e=>{if(keys[e.key]){e.preventDefault();end()}});window.addEventListener('blur',end);window.addEventListener('beforeunload',end);
function setServo(channel, value){ value=parseInt(value); if(Number.isNaN(value))return; fetch('/api/servo',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({channel:channel,angle:value})}).then(r=>r.json()).then(d=>{if(d.ok){document.querySelector('.slider[data-channel="'+channel+'"]').value=d.angle;document.querySelector('.angle[data-channel="'+channel+'"]').value=d.angle;}}); }
document.querySelectorAll('.slider').forEach(s=>s.addEventListener('input',()=>setServo(s.dataset.channel,s.value)));
document.querySelectorAll('.angle').forEach(n=>n.addEventListener('change',()=>setServo(n.dataset.channel,n.value)));
setInterval(()=>fetch('/api/colour').then(r=>r.json()).then(d=>{document.getElementById('colour').textContent=d.name;document.getElementById('score').textContent=d.error||('نسبة اللون في وسط الصورة: '+d.score.toFixed(1)+'%');}),400);
</script>
</body></html>
"""


@app.get("/")
def index():
    return render_template_string(PAGE, channels=ARM_CHANNELS, limits=ARM_LIMITS)


@app.post("/api/move")
def api_move():
    data = request.get_json(silent=True) or {}
    command = data.get("command", "stop")
    return jsonify(ok=drive(command), command=command)


@app.post("/api/servo")
def api_servo():
    data = request.get_json(silent=True) or {}
    try:
        angle = move_servo(int(data.get("channel")), int(data.get("angle")))
    except (TypeError, ValueError):
        angle = None
    return jsonify(ok=angle is not None, angle=angle)


@app.get("/api/colour")
def api_colour():
    with camera_lock:
        return jsonify(name=COLOUR_AR.get(latest_colour, latest_colour),
                       score=latest_score, error=camera_error)


@app.get("/stream")
def stream():
    def frames():
        while True:
            with camera_lock:
                frame = latest_jpeg
            if frame is not None:
                yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
            sleep(0.04)
    return Response(frames(), mimetype="multipart/x-mixed-replace; boundary=frame")


def cleanup():
    stop_motors()
    for motor in MOTORS.values():
        motor.close()


if __name__ == "__main__":
    print("\n===== لوحة تحكم الروبوت =====")
    print("افتح من الحاسوب: http://عنوان-IP-الراسبري:5000")
    print("لإظهار عنوان الـ IP على الراسبري نفّذ: hostname -I")
    Thread(target=motor_watchdog, daemon=True).start()
    Thread(target=camera_worker, daemon=True).start()
    try:
        app.run(host="0.0.0.0", port=5000, threaded=True, debug=False)
    except KeyboardInterrupt:
        pass
    finally:
        cleanup()
