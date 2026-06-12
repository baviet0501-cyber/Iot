import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

from werkzeug.security import generate_password_hash


def database_path_from_url(database_url, base_dir):
    """Chuyen DATABASE_URL dang sqlite:///file.db thanh duong dan SQLite."""
    if not database_url:
        return os.path.join(base_dir, "iot_classroom.db")

    parsed = urlparse(database_url)
    if parsed.scheme and parsed.scheme != "sqlite":
        raise ValueError("Project mau chi ho tro SQLite DATABASE_URL.")

    if database_url.startswith("sqlite:///"):
        raw_path = database_url.replace("sqlite:///", "", 1)
    else:
        raw_path = database_url

    if not os.path.isabs(raw_path):
        raw_path = os.path.join(base_dir, raw_path)

    return os.path.abspath(raw_path)


@contextmanager
def get_connection(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path, admin_username, admin_password):
    """Tao bang va user admin demo neu database chua co user."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    with get_connection(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sensor_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                temperature REAL NOT NULL,
                humidity REAL NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS device_status (
                device_id TEXT PRIMARY KEY,
                last_seen TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                secret_hash TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                last_seen TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS security_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                ip_address TEXT,
                device_id TEXT,
                username TEXT,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS used_device_requests (
                device_id TEXT NOT NULL,
                signature TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (device_id, signature)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_sensor_data_created_at ON sensor_data(created_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_security_logs_created_at ON security_logs(created_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_used_device_requests_created_at ON used_device_requests(created_at)"
        )

        user_count = conn.execute("SELECT COUNT(*) AS total FROM users").fetchone()["total"]
        if user_count == 0:
            conn.execute(
                """
                INSERT INTO users (username, password_hash, created_at)
                VALUES (?, ?, ?)
                """,
                (
                    admin_username,
                    generate_password_hash(admin_password),
                    utc_now_iso(),
                ),
            )


def utc_now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def find_user_by_username(db_path, username):
    with get_connection(db_path) as conn:
        return conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,),
        ).fetchone()


def update_user_password(db_path, user_id, new_password):
    with get_connection(db_path) as conn:
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (generate_password_hash(new_password), user_id),
        )


def ensure_device(db_path, device_id, name, secret_hash):
    now = utc_now_iso()
    with get_connection(db_path) as conn:
        existing = conn.execute(
            "SELECT * FROM devices WHERE device_id = ?",
            (device_id,),
        ).fetchone()
        if existing:
            return existing

        cursor = conn.execute(
            """
            INSERT INTO devices (device_id, name, secret_hash, is_active, created_at)
            VALUES (?, ?, ?, 1, ?)
            """,
            (device_id, name, secret_hash, now),
        )
        return conn.execute(
            "SELECT * FROM devices WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()


def find_device_by_id(db_path, device_id):
    with get_connection(db_path) as conn:
        return conn.execute(
            "SELECT * FROM devices WHERE device_id = ?",
            (device_id,),
        ).fetchone()


def remember_device_request_signature(db_path, device_id, timestamp, signature, ttl_seconds):
    """Return False when the same signed request was already accepted."""
    created_at = utc_now_iso()
    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=ttl_seconds)).replace(microsecond=0).isoformat()

    with get_connection(db_path) as conn:
        conn.execute(
            "DELETE FROM used_device_requests WHERE created_at < ?",
            (cutoff,),
        )
        try:
            conn.execute(
                """
                INSERT INTO used_device_requests (device_id, signature, timestamp, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (device_id, signature, timestamp, created_at),
            )
        except sqlite3.IntegrityError:
            return False

    return True


def update_device_last_seen(db_path, device_id, last_seen):
    with get_connection(db_path) as conn:
        conn.execute(
            "UPDATE devices SET last_seen = ? WHERE device_id = ?",
            (last_seen, device_id),
        )


def insert_sensor_data(db_path, device_id, temperature, humidity):
    created_at = utc_now_iso()
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO sensor_data (device_id, temperature, humidity, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (device_id, temperature, humidity, created_at),
        )
        return {
            "id": cursor.lastrowid,
            "device_id": device_id,
            "temperature": temperature,
            "humidity": humidity,
            "created_at": created_at,
        }


def save_sensor_data_sample(db_path, device_id, temperature, humidity, stable_interval_seconds=60):
    """
    Nen du lieu lap lai:
    - Neu nhiet do/do am thay doi: them dong moi.
    - Neu ca 2 thong so giu nguyen trong vong stable_interval_seconds:
      chi cap nhat created_at cua dong cuoi de thiet bi van online.
    - Neu giu nguyen du lau: them 1 dong moi lam moc lich su cho bieu do.
    """
    created_at = utc_now_iso()
    now = datetime.fromisoformat(created_at)

    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO device_status (device_id, last_seen)
            VALUES (?, ?)
            ON CONFLICT(device_id) DO UPDATE SET last_seen = excluded.last_seen
            """,
            (device_id, created_at),
        )

        latest = conn.execute(
            """
            SELECT id, device_id, temperature, humidity, created_at
            FROM sensor_data
            WHERE device_id = ?
            ORDER BY datetime(created_at) DESC, id DESC
            LIMIT 1
            """,
            (device_id,),
        ).fetchone()

        if latest:
            same_temperature = round(float(latest["temperature"]), 1) == round(float(temperature), 1)
            same_humidity = round(float(latest["humidity"]), 1) == round(float(humidity), 1)
            latest_time = datetime.fromisoformat(latest["created_at"])
            age_seconds = (now - latest_time).total_seconds()

            if same_temperature and same_humidity and age_seconds < stable_interval_seconds:
                return {
                    "id": latest["id"],
                    "device_id": latest["device_id"],
                    "temperature": float(latest["temperature"]),
                    "humidity": float(latest["humidity"]),
                    "created_at": latest["created_at"],
                    "last_seen": created_at,
                    "action": "skipped",
                }

        cursor = conn.execute(
            """
            INSERT INTO sensor_data (device_id, temperature, humidity, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (device_id, temperature, humidity, created_at),
        )
        return {
            "id": cursor.lastrowid,
            "device_id": device_id,
            "temperature": temperature,
            "humidity": humidity,
            "created_at": created_at,
            "last_seen": created_at,
            "action": "inserted",
        }


def get_latest_sensor_data(db_path):
    with get_connection(db_path) as conn:
        return conn.execute(
            """
            SELECT id, device_id, temperature, humidity, created_at
            FROM sensor_data
            ORDER BY datetime(created_at) DESC, id DESC
            LIMIT 1
            """
        ).fetchone()


def get_device_last_seen(db_path, device_id):
    with get_connection(db_path) as conn:
        row = conn.execute(
            """
            SELECT last_seen
            FROM device_status
            WHERE device_id = ?
            """,
            (device_id,),
        ).fetchone()
        return row["last_seen"] if row else None


def insert_security_log(
    db_path,
    event_type,
    severity,
    message,
    ip_address=None,
    device_id=None,
    username=None,
):
    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO security_logs
                (event_type, severity, ip_address, device_id, username, message, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (event_type, severity, ip_address, device_id, username, message, utc_now_iso()),
        )


def get_security_logs(db_path, limit=100, severity=None, event_type=None):
    query = """
        SELECT id, event_type, severity, ip_address, device_id, username, message, created_at
        FROM security_logs
        WHERE 1 = 1
    """
    params = []
    if severity:
        query += " AND severity = ?"
        params.append(severity)
    if event_type:
        query += " AND event_type = ?"
        params.append(event_type)
    query += " ORDER BY datetime(created_at) DESC, id DESC LIMIT ?"
    params.append(limit)

    with get_connection(db_path) as conn:
        return conn.execute(query, params).fetchall()


def get_sensor_history(db_path, limit=50):
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT id, device_id, temperature, humidity, created_at
            FROM sensor_data
            ORDER BY datetime(created_at) DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return list(reversed(rows))


def row_to_dict(row):
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}
