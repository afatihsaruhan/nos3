#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NDJSON -> InfluxDB v2 consumer (ESKİ SADE HAL)
- dbprocesses/logs içindeki *.ndjson dosyalarını izler
- HWM / dedupe YOK
- Flat & items’lı kayıtlar dinamik işlenir
- measurement = target, tags: packet, kind=TM/TC
"""

import os, platform, sys, json, math, logging, time, threading
from typing import Any, Dict, List, Optional, Tuple

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from influxdb_client import InfluxDBClient, WriteOptions

# ===================== ENV & LOG =====================
INFLUX_URL    = "10.1.208.88:8086"
INFLUX_ORG    = "my-org"
INFLUX_BUCKET = "my-bucket"
INFLUX_TOKEN  = "dev-admin-token-123"
if not all([INFLUX_URL, INFLUX_ORG, INFLUX_BUCKET, INFLUX_TOKEN]):
    print("Hata: INFLUX_URL/INFLUX_ORG/INFLUX_BUCKET/INFLUX_TOKEN eksik.", file=sys.stderr)
    sys.exit(1)

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
NDJSON_DIR  = os.path.join(BASE_DIR, "logs")
LOG_LEVEL       = os.getenv("LOG_LEVEL", "INFO").upper()
DEBOUNCE_SEC    = float(os.getenv("DEBOUNCE_SEC", "2.0"))

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("consumer")

# ===================== Influx =====================
client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG, enable_gzip=True)
write_api = client.write_api(write_options=WriteOptions(batch_size=10_000, flush_interval=1_000))

# ===================== LP helpers =====================
def esc_measurement(s: str) -> str:
    return s.replace(",", r"\,").replace(" ", r"\ ")

def esc_tag(s: str) -> str:
    return s.replace(",", r"\,").replace(" ", r"\ ").replace("=", r"\=")

def norm_field_key(s: str) -> str:
    out = []
    for ch in s:
        out.append(ch if (ch.isalnum() or ch in ("_", ".", "-", ":")) else "_")
    return "".join(out)

def format_field_value(v: Any) -> Optional[str]:
    if v is None: return None
    if isinstance(v, bool):  return "true" if v else "false"
    if isinstance(v, int):   return f"{v}i"
    if isinstance(v, float):
        if math.isnan(v) or math.isinf(v): return None
        return str(v)
    s = str(v).replace("\\", "\\\\").replace("\"", "\\\"")
    return f"\"{s}\""

# ===================== Meta extraction =====================
def split_packet_key(pktkey: str) -> Tuple[Optional[str], Optional[str], str]:
    # "DECOM__TLM__CFS_DEBUG__SC_HKTLM" -> ("CFS_DEBUG","SC_HKTLM","TM")
    # "DECOM__CMD__CFS_DEBUG__SC_CMD"   -> ("CFS_DEBUG","SC_CMD","TC")
    parts = str(pktkey).split("__")
    if len(parts) >= 4:
        kind = "TC" if parts[1] == "CMD" else "TM"
        return parts[2], parts[3], kind
    return None, None, "TM"

def extract_meta(rec: Dict[str, Any]):
    """
    Her kayıttan (t_ns, target, packet, kind, fields) çıkar.
    t_ns: PACKET_TIMESECONDS(ns) > __time > time
    """
    # items'lı form
    if "items" in rec and ("time" in rec and "target" in rec and "packet" in rec):
        t_ns = rec.get("time")
        items = rec.get("items") or []
        if t_ns is None or not items: return None, None, None, "TM", {}
        fields: Dict[str, Any] = {}
        for it in items:
            name = it.get("name")
            if not name: continue
            val = it.get("converted")
            if val is None: val = it.get("formatted")
            if val is None: val = it.get("raw")
            if val is None: val = it.get("value")
            fields[str(name)] = val
        return int(t_ns), str(rec["target"]), str(rec["packet"]), "TM", fields

    # flat form
    t_ns: Optional[int] = None
    if "PACKET_TIMESECONDS" in rec:
        try: t_ns = int(float(rec["PACKET_TIMESECONDS"]) * 1e9)
        except Exception: t_ns = None
    if t_ns is None: t_ns = rec.get("__time") or rec.get("time")
    if t_ns is None: return None, None, None, "TM", {}

    tgt = pkt = None
    kind = "TM"
    pktkey = rec.get("__packet")
    if pktkey:
        tgt, pkt, kind = split_packet_key(pktkey)
    if tgt is None: tgt = rec.get("target")
    if pkt is None: pkt = rec.get("packet")
    if tgt is None or pkt is None: return None, None, None, "TM", {}

    skip_keys = {"__time","__packet","__type","target","packet","time"}
    fields: Dict[str, Any] = {}
    for k, v in rec.items():
        if isinstance(k, str) and (k in skip_keys or k.startswith("__")):
            continue
        fields[str(k)] = v

    return int(t_ns), str(tgt), str(pkt), kind, fields

def to_line_protocol(tgt: str, pkt: str, kind: str, fields: Dict[str, Any], t_ns: int) -> Optional[str]:
    pairs = []
    for k, v in fields.items():
        fv = format_field_value(v)
        if fv is None: continue
        pairs.append(f"{norm_field_key(k)}={fv}")
    if not pairs: return None
    meas = esc_measurement(tgt)  # measurement = target
    host = os.environ.get("HOSTNAME") or platform.node()  # yeni ek: host adı ortam değişkeninden
    tag_part = f"packet={esc_tag(pkt)},kind={kind},host={esc_tag(host)}"
    return f"{meas},{tag_part} {','.join(pairs)} {t_ns}"
# ===================== NDJSON -> LP =====================
def ndjson_file_to_lp(path: str) -> List[str]:
    lp: List[str] = []
    total = parsed = 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s: continue
            total += 1
            try:
                obj = json.loads(s); parsed += 1
            except Exception:
                continue
            recs = obj if isinstance(obj, list) else [obj]
            for rec in recs:
                if not isinstance(rec, dict): continue
                t_ns, tgt, pkt, kind, fields = extract_meta(rec)
                if (t_ns is None) or (tgt is None) or (pkt is None) or not fields:
                    continue
                row = to_line_protocol(tgt, pkt, kind, fields, t_ns)
                if row: lp.append(row)
    return lp

# ===================== Watcher (timer-debounce) =====================
_pending_timers: Dict[str, threading.Timer] = {}
_last_signature: Dict[str, Tuple[int, int]] = {}

class NDJSONHandler(FileSystemEventHandler):
    def on_modified(self, event): self._schedule(event)
    def on_created(self, event):  self._schedule(event)

    def _schedule(self, event):
        if event.is_directory: return
        path = event.src_path
        if not path.endswith(".ndjson"): return
        t = _pending_timers.get(path)
        if t and t.is_alive(): t.cancel()
        timer = threading.Timer(DEBOUNCE_SEC, self._process_once, args=(path,))
        _pending_timers[path] = timer
        timer.start()

    def _process_once(self, path: str):
        time.sleep(0.2)  # üretici yazmayı bitirsin
        try:
            st = os.stat(path)
        except FileNotFoundError:
            return
        sig = (st.st_mtime_ns, st.st_size)
        if _last_signature.get(path) == sig:
            return
        base = os.path.basename(path)
        try:
            rows = ndjson_file_to_lp(path)
            if not rows:
                log.info(f"{base} -> kayıt yok | size={st.st_size}B")
                _last_signature[path] = sig
                return
            write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=rows)
            log.info(f"{base} -> kayıt yazdırıldı ({len(rows)} point) | size={st.st_size}B mtime_ns={st.st_mtime_ns}")
            _last_signature[path] = sig
        except Exception as e:
            log.error(f"{base} yazım hatası: {e}")

# ===================== Main =====================
def main():
    os.makedirs(NDJSON_DIR, exist_ok=True)
    log.info(f"Watching: {NDJSON_DIR} (*.ndjson) — debounce={DEBOUNCE_SEC}s")
    obs = Observer()
    handler = NDJSONHandler()
    obs.schedule(handler, NDJSON_DIR, recursive=False)
    obs.start()
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        log.info("Kapanıyor…")
    finally:
        obs.stop(); obs.join()
        try: write_api.flush()
        except Exception: pass
        client.close()

if __name__ == "__main__":
    main()

