import hashlib
import hmac
import logging
import os
import secrets
import time
from datetime import datetime, timedelta, timezone
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import check_password_hash

from models import (
    database_path_from_url,
    ensure_device,
    find_device_by_id,
    find_user_by_username,
    get_device_last_seen,
    get_latest_sensor_data,
    get_security_logs,
    get_sensor_history,
    init_db,
    insert_security_log,
    remember_device_request_signature,
    row_to_dict,
    save_sensor_data_sample,
    update_device_last_seen,
    update_user_password,
)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

OFFLINE_SECONDS = 30
STABLE_SAMPLE_INTERVAL_SECONDS = 60
LOGIN_FAILURES = {}

ALERT_MESSAGES = {
    "cold": "Nhiệt độ quá thấp",
    "hot": "Nhiệt độ quá cao",
    "dry": "Độ ẩm quá thấp",
    "too_humid": "Độ ẩm quá cao",
    "warm": "Nhiệt độ đang cao hơn mức khuyến nghị",
    "humid": "Độ ẩm đang cao hơn mức khuyến nghị",
}


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
    app.config["DEVICE_API_KEY"] = os.getenv("DEVICE_API_KEY", "change-this-device-api-key")
    app.config["DEVICE_SECRET"] = os.getenv("DEVICE_SECRET", "classroom-demo-device-secret")
    app.config["DEVICE_CLOCK_SKEW_SECONDS"] = int(os.getenv("DEVICE_CLOCK_SKEW_SECONDS", "60"))
    app.config["DEVICE_REPLAY_CACHE_SECONDS"] = int(
        os.getenv("DEVICE_REPLAY_CACHE_SECONDS", str(app.config["DEVICE_CLOCK_SKEW_SECONDS"] * 2))
    )
    app.config["ALLOW_LEGACY_API_KEY"] = env_bool("ALLOW_LEGACY_API_KEY", True)
    app.config["LOGIN_MAX_ATTEMPTS"] = int(os.getenv("LOGIN_MAX_ATTEMPTS", "5"))
    app.config["LOGIN_LOCK_SECONDS"] = min(int(os.getenv("LOGIN_LOCK_SECONDS", "60")), 60)
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = env_bool("SESSION_COOKIE_SECURE", False)
    app.config["DATABASE_PATH"] = database_path_from_url(
        os.getenv("DATABASE_URL", "sqlite:///iot_classroom.db"),
        BASE_DIR,
    )

    configure_logging()
    init_db(
        app.config["DATABASE_PATH"],
        os.getenv("ADMIN_USERNAME", "admin"),
        os.getenv("ADMIN_PASSWORD", "admin123"),
    )
    ensure_device(
        app.config["DATABASE_PATH"],
        os.getenv("DEFAULT_DEVICE_ID", "CLASSROOM_01"),
        os.getenv("DEFAULT_DEVICE_NAME", "Phòng học 01"),
        sha256_hex(app.config["DEVICE_SECRET"]),
    )

    limiter = Limiter(
        key_func=get_remote_address,
        app=app,
        default_limits=[],
        storage_uri="memory://",
    )

    def login_required(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            if not session.get("user_id"):
                return redirect(url_for("login"))
            return view_func(*args, **kwargs)

        return wrapped

    @app.context_processor
    def inject_csrf_token():
        return {"csrf_token": get_csrf_token}

    @app.after_request
    def add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' https://cdn.jsdelivr.net; "
            "style-src 'self'; "
            "img-src 'self' data: https://images.unsplash.com; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        return response

    @app.route("/")
    def index():
        if session.get("user_id"):
            return redirect(url_for("dashboard"))
        return redirect(url_for("login"))

    @app.route("/login", methods=["GET", "POST"])
    @limiter.limit("10 per minute")
    def login():
        error = None
        lock_message = None
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")

            if not verify_csrf_token(request.form.get("csrf_token")):
                log_security_event(
                    "csrf_failed",
                    "warning",
                    "CSRF token đăng nhập không hợp lệ.",
                    username=username,
                )
                return "CSRF token không hợp lệ.", 400

            locked, seconds_left = is_login_locked(username)
            if locked:
                lock_message = f"Tài khoản/IP đang bị khóa tạm thời. Thử lại sau {seconds_left} giây."
                log_security_event(
                    "login_locked",
                    "warning",
                    lock_message,
                    username=username,
                )
                return render_template("login.html", error=error, lock_message=lock_message)

            user = find_user_by_username(app.config["DATABASE_PATH"], username)
            if user and check_password_hash(user["password_hash"], password):
                session.clear()
                session["user_id"] = user["id"]
                session["username"] = user["username"]
                get_csrf_token()
                reset_login_failures(username)
                log_security_event("login_success", "info", "Đăng nhập thành công.", username=username)
                return redirect(url_for("dashboard"))

            record_login_failure(username)
            error = "Sai tên đăng nhập hoặc mật khẩu."
            app.logger.warning("Đăng nhập thất bại cho user=%s từ ip=%s", username, request.remote_addr)
            log_security_event("login_failed", "warning", error, username=username)

        return render_template("login.html", error=error, lock_message=lock_message)

    @app.route("/logout", methods=["POST"])
    @login_required
    def logout():
        if not verify_csrf_token(request.form.get("csrf_token")):
            return "CSRF token không hợp lệ.", 400
        username = session.get("username")
        session.clear()
        log_security_event("logout", "info", "Đăng xuất dashboard.", username=username)
        return redirect(url_for("login"))

    @app.route("/dashboard")
    @login_required
    def dashboard():
        return render_template(
            "dashboard.html",
            username=session.get("username", "admin"),
        )

    @app.route("/change-password", methods=["GET", "POST"])
    @login_required
    def change_password():
        message = None
        error = None
        if request.method == "POST":
            if not verify_csrf_token(request.form.get("csrf_token")):
                return "CSRF token không hợp lệ.", 400

            current_password = request.form.get("current_password", "")
            new_password = request.form.get("new_password", "")
            confirm_password = request.form.get("confirm_password", "")
            user = find_user_by_username(app.config["DATABASE_PATH"], session.get("username", ""))

            if not user or not check_password_hash(user["password_hash"], current_password):
                error = "Mật khẩu hiện tại không đúng."
                log_security_event("password_change_failed", "warning", error, username=session.get("username"))
            elif len(new_password) < 8:
                error = "Mật khẩu mới phải có ít nhất 8 ký tự."
            elif new_password != confirm_password:
                error = "Mật khẩu xác nhận không khớp."
            else:
                update_user_password(app.config["DATABASE_PATH"], session["user_id"], new_password)
                message = "Đổi mật khẩu thành công."
                log_security_event("password_changed", "info", message, username=session.get("username"))

        return render_template("change_password.html", error=error, message=message, username=session.get("username"))

    @app.route("/security-logs")
    @login_required
    def security_logs():
        severity = request.args.get("severity", "").strip() or None
        event_type = request.args.get("event_type", "").strip() or None
        rows = get_security_logs(
            app.config["DATABASE_PATH"],
            limit=100,
            severity=severity,
            event_type=event_type,
        )
        return render_template(
            "security_logs.html",
            logs=[row_to_dict(row) for row in rows],
            username=session.get("username"),
            severity=severity or "",
            event_type=event_type or "",
            format_vietnam_time=format_vietnam_time,
        )

    @app.route("/api/sensor-data", methods=["POST"])
    @limiter.limit("30 per minute")
    def receive_sensor_data():
        raw_body = request.get_data(cache=True, as_text=True)
        security_ok, security_status, security_error = verify_sensor_request(raw_body)
        if not security_ok:
            return jsonify({"error": security_error}), security_status

        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            message = "Body phải là JSON object"
            app.logger.warning("Dữ liệu sai định dạng: body không phải JSON object")
            log_security_event("invalid_payload", "warning", message, device_id=request.headers.get("X-Device-Id"))
            return jsonify({"error": message}), 400

        is_valid, data_or_error = validate_sensor_payload(payload)
        if not is_valid:
            app.logger.warning("Dữ liệu sai định dạng: %s | payload=%s", data_or_error, payload)
            log_security_event(
                "invalid_payload",
                "warning",
                data_or_error,
                device_id=payload.get("device_id"),
            )
            return jsonify({"error": data_or_error}), 400

        header_device_id = request.headers.get("X-Device-Id")
        if header_device_id and header_device_id != data_or_error["device_id"]:
            message = "device_id trong body không khớp X-Device-Id"
            log_security_event("device_id_mismatch", "warning", message, device_id=header_device_id)
            return jsonify({"error": message}), 401

        saved = save_sensor_data_sample(
            app.config["DATABASE_PATH"],
            stable_interval_seconds=STABLE_SAMPLE_INTERVAL_SECONDS,
            **data_or_error,
        )
        update_device_last_seen(app.config["DATABASE_PATH"], saved["device_id"], saved["last_seen"])

        alert = get_alert_level(saved["temperature"], saved["humidity"])
        app.logger.info(
            "Nhận dữ liệu: device=%s temp=%.1f humidity=%.1f | %s | %s | %s",
            saved["device_id"],
            saved["temperature"],
            saved["humidity"],
            alert["overall"],
            saved["action"],
            security_error,
        )

        if saved["action"] == "inserted" and alert["overall"] != "safe":
            message = (
                f"Cảnh báo {alert['overall']}: temp={saved['temperature']:.1f} "
                f"({alert['temperature']['message']}), humidity={saved['humidity']:.1f} "
                f"({alert['humidity']['message']})"
            )
            app.logger.warning(message)
            log_security_event("threshold_warning", "warning", message, device_id=saved["device_id"])

        status_code = 201 if saved["action"] == "inserted" else 200
        return jsonify(
            {
                "message": "Data saved",
                "security_status": security_error,
                "data": saved,
            }
        ), status_code

    @app.route("/api/latest")
    @login_required
    def api_latest():
        latest = row_to_dict(get_latest_sensor_data(app.config["DATABASE_PATH"]))
        alert = None
        last_seen = None
        if latest:
            alert = get_alert_level(latest["temperature"], latest["humidity"])
            last_seen = get_device_last_seen(app.config["DATABASE_PATH"], latest["device_id"])
        return jsonify(
            {
                "data": latest,
                "device_status": get_device_status(latest, last_seen),
                "last_seen": last_seen,
                "alert": alert,
            }
        )

    @app.route("/api/history")
    @login_required
    def api_history():
        limit = request.args.get("limit", "50")
        try:
            limit = int(limit)
        except ValueError:
            limit = 50
        limit = max(1, min(limit, 200))

        rows = get_sensor_history(app.config["DATABASE_PATH"], limit)
        return jsonify({"data": [row_to_dict(row) for row in rows]})

    def log_security_event(event_type, severity, message, device_id=None, username=None):
        insert_security_log(
            app.config["DATABASE_PATH"],
            event_type=event_type,
            severity=severity,
            message=message,
            ip_address=request.remote_addr if request else None,
            device_id=device_id,
            username=username,
        )

    def verify_sensor_request(raw_body):
        header_device_id = request.headers.get("X-Device-Id", "").strip()
        timestamp = request.headers.get("X-Timestamp", "").strip()
        signature = request.headers.get("X-Signature", "").strip()

        if header_device_id and timestamp and signature:
            device = find_device_by_id(app.config["DATABASE_PATH"], header_device_id)
            if not device:
                message = "Thiết bị không tồn tại."
                log_security_event("unknown_device", "warning", message, device_id=header_device_id)
                return False, 401, message
            if not int(device["is_active"]):
                message = "Thiết bị đã bị vô hiệu hóa."
                log_security_event("inactive_device", "warning", message, device_id=header_device_id)
                return False, 403, message

            if sha256_hex(app.config["DEVICE_SECRET"]) != device["secret_hash"]:
                message = "Secret thiết bị trên server không khớp cấu hình."
                log_security_event("device_secret_mismatch", "critical", message, device_id=header_device_id)
                return False, 401, message

            try:
                timestamp_int = int(timestamp)
            except ValueError:
                message = "Timestamp không hợp lệ."
                log_security_event("invalid_timestamp", "warning", message, device_id=header_device_id)
                return False, 401, message

            skew = abs(int(time.time()) - timestamp_int)
            if skew > app.config["DEVICE_CLOCK_SKEW_SECONDS"]:
                message = "Timestamp quá cũ hoặc quá xa hiện tại."
                log_security_event("replay_detected", "warning", message, device_id=header_device_id)
                return False, 401, message

            signed_payload = f"{header_device_id}{timestamp}{raw_body}"
            expected = hmac.new(
                app.config["DEVICE_SECRET"].encode("utf-8"),
                signed_payload.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(expected, signature):
                message = "Chữ ký HMAC không hợp lệ."
                log_security_event("invalid_signature", "warning", message, device_id=header_device_id)
                return False, 401, message

            is_fresh_signature = remember_device_request_signature(
                app.config["DATABASE_PATH"],
                header_device_id,
                timestamp_int,
                signature,
                app.config["DEVICE_REPLAY_CACHE_SECONDS"],
            )
            if not is_fresh_signature:
                message = "Request HMAC da duoc su dung truoc do."
                log_security_event("replay_detected", "warning", message, device_id=header_device_id)
                return False, 401, message

            return True, 200, "verified"

        api_key = request.headers.get("X-API-Key", "")
        if api_key == app.config["DEVICE_API_KEY"] and app.config["ALLOW_LEGACY_API_KEY"]:
            log_security_event("legacy_api_key_used", "info", "Thiết bị dùng API key tương thích.")
            return True, 200, "legacy_api_key"

        if api_key == app.config["DEVICE_API_KEY"] and not app.config["ALLOW_LEGACY_API_KEY"]:
            message = "Legacy API key da bi tat; hay dung HMAC-SHA256."
            log_security_event("legacy_api_key_disabled", "warning", message)
            return False, 401, message

        message = "Unauthorized"
        app.logger.warning("API key/chữ ký sai từ ip=%s", request.remote_addr)
        log_security_event("invalid_api_key", "warning", "API key hoặc chữ ký sai.")
        return False, 401, message

    return app


def configure_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )


def env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def sha256_hex(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def get_csrf_token():
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def verify_csrf_token(token):
    stored = session.get("csrf_token")
    return bool(stored and token and hmac.compare_digest(stored, token))


def login_failure_key(username):
    return f"{request.remote_addr}:{username.strip().lower()}"


def is_login_locked(username):
    record = LOGIN_FAILURES.get(login_failure_key(username))
    if not record:
        return False, 0
    locked_until = record.get("locked_until", 0)
    seconds_left = int(locked_until - time.time())
    if seconds_left > 0:
        return True, seconds_left
    if locked_until:
        LOGIN_FAILURES.pop(login_failure_key(username), None)
    return False, 0


def record_login_failure(username):
    key = login_failure_key(username)
    record = LOGIN_FAILURES.setdefault(key, {"count": 0, "locked_until": 0})
    record["count"] += 1
    max_attempts = int(os.getenv("LOGIN_MAX_ATTEMPTS", "5"))
    lock_seconds = min(int(os.getenv("LOGIN_LOCK_SECONDS", "60")), 60)
    if record["count"] >= max_attempts:
        record["locked_until"] = time.time() + lock_seconds


def reset_login_failures(username):
    LOGIN_FAILURES.pop(login_failure_key(username), None)


def validate_sensor_payload(payload):
    device_id = str(payload.get("device_id", "")).strip()
    if not device_id:
        return False, "device_id không được rỗng"

    temperature = parse_number(payload.get("temperature"))
    if temperature is None:
        return False, "temperature phải là số"
    if temperature < -40 or temperature > 100:
        return False, "temperature phải nằm trong khoảng -40 đến 100"

    humidity = parse_number(payload.get("humidity"))
    if humidity is None:
        return False, "humidity phải là số"
    if humidity < 0 or humidity > 100:
        return False, "humidity phải nằm trong khoảng 0 đến 100"

    return True, {
        "device_id": device_id,
        "temperature": float(temperature),
        "humidity": float(humidity),
    }


def parse_number(value):
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def classify_temperature(value):
    if value < 10:
        return "cold", "Quá lạnh"
    if value <= 26:
        return "safe", "An toàn"
    if value <= 35:
        return "warm", "Hơi ấm"
    return "hot", "Quá nóng"


def classify_humidity(value):
    if value < 30:
        return "dry", "Quá khô"
    if value <= 70:
        return "safe", "An toàn"
    if value <= 85:
        return "humid", "Hơi ẩm"
    return "too_humid", "Quá ẩm"


def get_alert_level(temperature, humidity):
    temp_level, temp_message = classify_temperature(temperature)
    hum_level, hum_message = classify_humidity(humidity)

    overall = "safe"
    if temp_level in ("hot",) or hum_level in ("too_humid",):
        overall = "danger"
    elif temp_level in ("warm",) or hum_level in ("humid",):
        overall = "warning"
    elif temp_level in ("cold",) or hum_level in ("dry",):
        overall = "warning"

    messages = []
    for level in (temp_level, hum_level):
        message = ALERT_MESSAGES.get(level)
        if message:
            messages.append(message)

    return {
        "temperature": {"level": temp_level, "message": temp_message},
        "humidity": {"level": hum_level, "message": hum_message},
        "overall": overall,
        "message": "; ".join(messages) if messages else "Môi trường an toàn",
    }


def get_device_status(latest, last_seen=None):
    if not latest:
        return "offline"

    created_at = datetime.fromisoformat(last_seen or latest["created_at"])
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)

    age_seconds = (datetime.now(timezone.utc) - created_at).total_seconds()
    return "online" if age_seconds <= OFFLINE_SECONDS else "offline"


def format_vietnam_time(value):
    if not value:
        return "-"
    created_at = datetime.fromisoformat(value)
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    vietnam_time = created_at.astimezone(timezone(timedelta(hours=7)))
    return vietnam_time.strftime("%d/%m/%Y %H:%M:%S")


app = create_app()


if __name__ == "__main__":
    app.run(
        host=os.getenv("FLASK_HOST", "0.0.0.0"),
        port=int(os.getenv("FLASK_PORT", "5000")),
        debug=env_bool("FLASK_DEBUG", False),
    )
