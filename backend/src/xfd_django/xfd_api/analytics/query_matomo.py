import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import pymysql
from fastapi import FastAPI, Query, HTTPException

# ---------- Config (env vars recommended) ----------
MATOMO_DB_HOST = os.getenv("MATOMO_DB_HOST", "matomodb")
MATOMO_DB_PORT = int(os.getenv("MATOMO_DB_PORT", "3306"))
MATOMO_DB_USER = os.getenv("MATOMO_DATABASE_USERNAME", "root")
MATOMO_DB_PASS = os.getenv("MATOMO_DATABASE_PASSWORD", "password")
MATOMO_DB_NAME = os.getenv("MATOMO_DATABASE_DBNAME", "matomo")

CONNECT_TIMEOUT = int(os.getenv("DB_CONNECT_TIMEOUT", "10"))
READ_TIMEOUT = int(os.getenv("DB_READ_TIMEOUT", "20"))
WRITE_TIMEOUT = int(os.getenv("DB_WRITE_TIMEOUT", "20"))

app = FastAPI(title="Matomo minimal API (PyMySQL)")

# ---------- Small helpers ----------
def parse_iso_utc(s: str) -> datetime:
    """Accepts 'YYYY-MM-DDTHH:MM:SSZ' or with timezone; returns aware UTC datetime."""
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt

def _validate_range(start_utc: datetime, end_utc: datetime, max_days: int = 31):
    if end_utc <= start_utc:
        raise HTTPException(status_code=400, detail="end_utc must be after start_utc")
    if (end_utc - start_utc).days > max_days:
        raise HTTPException(status_code=400, detail=f"date range too large (max {max_days} days)")

def get_conn():
    # Create a fresh connection per request (simplest & reliable for a first test).
    # You can switch to a pool later if needed.
    return pymysql.connect(
        host="localhost",
        port=MATOMO_DB_PORT,
        user=MATOMO_DB_USER,
        password=MATOMO_DB_PASS,
        database=MATOMO_DB_NAME,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=CONNECT_TIMEOUT,
        read_timeout=READ_TIMEOUT,
        write_timeout=WRITE_TIMEOUT,
        autocommit=True,
    )

# ---------- One tiny test endpoint: total visits ----------
@app.get("/analytics/visits-total")
def visits_total(
    idsite: int = Query(1, description="Matomo site id"),
    start_utc: Optional[str] = Query(None, description="UTC start, e.g. 2025-08-18T00:00:00Z"),
    end_utc: Optional[str] = Query(None, description="UTC end"),
):
    """
    Returns total distinct visits from matomo_log_visit for the given site and time range.
    Defaults to the last 60 minutes if no range is provided.
    """
    now = datetime.now(timezone.utc)
    end_dt = parse_iso_utc(end_utc) if end_utc else now
    start_dt = parse_iso_utc(start_utc) if start_utc else end_dt - timedelta(minutes=60)
    _validate_range(start_dt, end_dt, max_days=31)

    sql = """
        SELECT COUNT(DISTINCT v.idvisit) AS total_visits
        FROM matomo_log_visit AS v
        WHERE v.idsite = %s
          AND v.visit_last_action_time > %s
          AND v.visit_last_action_time <= %s
    """

    # Matomo stores UTC; pass naive datetimes (MySQL DATETIME) after stripping tzinfo.
    params = (idsite, start_dt.replace(tzinfo=None), end_dt.replace(tzinfo=None))

    try:
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone() or {"total_visits": 0}
        conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error: {e}")

    return {
        "idsite": 1,
        "start_utc": start_dt.isoformat(),
        "end_utc": end_dt.isoformat(),
        "total_visits": int(row["total_visits"] or 0),
    }

# ---------- Healthcheck ----------
@app.get("/healthz")
def healthz():
    try:
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        conn.close()
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
