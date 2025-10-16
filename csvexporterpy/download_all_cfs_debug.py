#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, time, threading, urllib.request, urllib.error
import websocket
from typing import List, Dict, Any, Tuple

AUTH   = "123"
HOST   = "localhost:2900"
SCOPE  = "DEFAULT"

IDLE_TIMEOUT_SEC = 3.0  # pencere dump’ı bitince ws'in susma süresi

# ---------------- Jobs (dinamik yapı) ----------------
JOBS = [
    {
        "label":  "TM_CFS_DEBUG",
        "target": "CFS_DEBUG",
        "kind":   "TM",         # "TM" veya "TC"
        "window_sec": 43,
        "period_sec": 43,
        "packet_mode": "all",    # "all" -> API'den paket adlarını çek
        "packets": []            # (list modunda doldurulur)
    },
    {
        "label":  "TM_GENERIC_EPS_DEBUG",
        "target": "GENERIC_EPS_DEBUG",
        "kind":   "TM",
        "window_sec": 30,
        "period_sec": 30,
        "packet_mode": "all",
        "packets": []
    },
    {
        "label":  "TM_ARDUCAM_DEBUG",
        "target": "ARDUCAM_DEBUG",
        "kind":   "TM",
        "window_sec": 30,
        "period_sec": 30,
        "packet_mode": "all",
        "packets": []
    },
    {
        "label":  "TM_CFDP_DEBUG",
        "target": "CFDP_DEBUG",
        "kind":   "TM",
        "window_sec": 30,
        "period_sec": 30,
        "packet_mode": "all",
        "packets": []
    },
    {
        "label":  "TM_CFDP_TEST_DEBUG",
        "target": "CFDP_TEST_DEBUG",
        "kind":   "TM",
        "window_sec": 30,
        "period_sec": 30,
        "packet_mode": "all",
        "packets": []
    },
    {
        "label":  "TM_CI_DEBUG_DEBUG",
        "target": "CI_DEBUG_DEBUG",
        "kind":   "TM",
        "window_sec": 30,
        "period_sec": 30,
        "packet_mode": "all",
        "packets": []
    },
    {
        "label":  "TM_CMD_UTIL_DEBUG",
        "target": "CMD_UTIL_DEBUG",
        "kind":   "TM",
        "window_sec": 30,
        "period_sec": 30,
        "packet_mode": "all",
        "packets": []
    },
    {
        "label":  "TM_GENERIC_ADCS_DEBUG",
        "target": "GENERIC_ADCS_DEBUG",
        "kind":   "TM",
        "window_sec": 30,
        "period_sec": 30,
        "packet_mode": "all",
        "packets": []
    },
    {
        "label":  "TM_GENERIC_CSS_DEBUG",
        "target": "GENERIC_CSS_DEBUG",
        "kind":   "TM",
        "window_sec": 30,
        "period_sec": 30,
        "packet_mode": "all",
        "packets": []
    },
    {
        "label":  "TM_GENERIC_FSS_DEBUG",
        "target": "GENERIC_FSS_DEBUG",
        "kind":   "TM",
        "window_sec": 30,
        "period_sec": 30,
        "packet_mode": "all",
        "packets": []
    },
    {
        "label":  "TM_GENERIC_IMU_DEBUG",
        "target": "GENERIC_IMU_DEBUG",
        "kind":   "TM",
        "window_sec": 30,
        "period_sec": 30,
        "packet_mode": "all",
        "packets": []
    },
    {
        "label":  "TM_GENERIC_MAG_DEBUG",
        "target": "GENERIC_MAG_DEBUG",
        "kind":   "TM",
        "window_sec": 30,
        "period_sec": 30,
        "packet_mode": "all",
        "packets": []
    },
    {
        "label":  "TM_GENERIC_RADIO_DEBUG",
        "target": "GENERIC_RADIO_DEBUG",
        "kind":   "TM",
        "window_sec": 30,
        "period_sec": 30,
        "packet_mode": "all",
        "packets": []
    },
    {
        "label":  "TM_GENERIC_REACTION_WHEEL_DEBUG",
        "target": "GENERIC_REACTION_WHEEL_DEBUG",
        "kind":   "TM",
        "window_sec": 30,
        "period_sec": 30,
        "packet_mode": "all",
        "packets": []
    },
    {
        "label":  "TM_GENERIC_STAR_TRACKER_DEBUG",
        "target": "GENERIC_STAR_TRACKER_DEBUG",
        "kind":   "TM",
        "window_sec": 30,
        "period_sec": 30,
        "packet_mode": "all",
        "packets": []
    },
    {
        "label":  "TM_GENERIC_THRUSTER_DEBUG",
        "target": "GENERIC_THRUSTER_DEBUG",
        "kind":   "TM",
        "window_sec": 30,
        "period_sec": 30,
        "packet_mode": "all",
        "packets": []
    },
    {
        "label":  "TM_GENERIC_TORQUER_DEBUG",
        "target": "GENERIC_TORQUER_DEBUG",
        "kind":   "TM",
        "window_sec": 30,
        "period_sec": 30,
        "packet_mode": "all",
        "packets": []
    },
    {
        "label":  "TM_MGR_DEBUG",
        "target": "MGR_DEBUG",
        "kind":   "TM",
        "window_sec": 30,
        "period_sec": 30,
        "packet_mode": "all",
        "packets": []
    },
    {
        "label":  "TM_PDU_DEBUG",
        "target": "PDU_DEBUG",
        "kind":   "TM",
        "window_sec": 30,
        "period_sec": 30,
        "packet_mode": "all",
        "packets": []
    },
    {
        "label":  "TM_SIM_42_TRUTH",
        "target": "SIM_42_TRUTH",
        "kind":   "TM",
        "window_sec": 15,
        "period_sec": 15,
        "packet_mode": "list",   # bu hedefte tek paket kullan
        "packets": ["SIM_42_TRUTH_DATA"]
    },
    {
    	"label": "TC_GENERIC_EPS_DEBUG",
    	"target": "GENERIC_EPS_DEBUG",
    	"kind":   "TC",
    	"window_sec": 15,
    	"period_sec": 15,
    	"packet_mode": "all",
    	"packets": []
    },		
]

# ------- Packet list cache (API çağrılarını azalt) -------
_packet_cache: Dict[Tuple[str,str], Tuple[float, List[str]]] = {}
CACHE_TTL_SEC = 300  # 5 dk

def _rpc_call(method: str, params: List[Any]) -> Any:
    url = f"http://{HOST}/openc3-api/api"
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": 1,
        "keyword_params": {"scope": SCOPE}
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json-rpc")
    req.add_header("Authorization", AUTH)
    with urllib.request.urlopen(req, timeout=10) as resp:
        body = resp.read()
        obj = json.loads(body.decode("utf-8", errors="ignore"))
        if "error" in obj:
            raise RuntimeError(obj["error"])
        return obj.get("result")

def get_all_telemetry_names(target: str) -> List[str]:
    key = ("TM", target)
    now = time.time()
    if key in _packet_cache:
        ts, names = _packet_cache[key]
        if now - ts < CACHE_TTL_SEC:
            return names
    result = _rpc_call("get_all_telemetry_names", [target])
    if not isinstance(result, list):
        result = []
    _packet_cache[key] = (now, result)
    return result

def get_all_command_names(target: str) -> List[str]:
    key = ("CMD", target)
    now = time.time()
    if key in _packet_cache:
        ts, names = _packet_cache[key]
        if now - ts < CACHE_TTL_SEC:
            return names
    result = _rpc_call("get_all_command_names", [target])
    if not isinstance(result, list):
        result = []
    _packet_cache[key] = (now, result)
    return result

def build_packet_keys(kind: str, target: str, packet_names: List[str]) -> List[str]:
    # kind: "TM" (telemetry) -> "TLM"  |  "TC" (command) -> "CMD"
    mode = "TLM" if kind == "TM" else "CMD"
    prefix = f"DECOM__{mode}__{target}__"
    return [prefix + p for p in packet_names]

# --------------- Dump (mevcut yapıyı bozma) ---------------
def dump_decom_ndjson(decom_packet_keys: List[str], window_sec: int, outfile: str, label: str):
    end_ns   = int(time.time() * 1e9)
    start_ns = int((time.time() - window_sec) * 1e9)

    ws_url = f"ws://{HOST}/openc3-api/cable?scope={SCOPE}&authorization={AUTH}"
    ws = websocket.WebSocket()
    ws.connect(ws_url)

    identifier = json.dumps({"channel":"StreamingChannel"})
    ws.send(json.dumps({"command":"subscribe","identifier":identifier}))

    data = {
      "action":"add","scope":SCOPE,"token":AUTH,
      "packets": decom_packet_keys,
      "start_time": start_ns,
      "end_time": end_ns
    }
    ws.send(json.dumps({"command":"message","identifier":identifier,"data":json.dumps(data)}))

    print(f"[{time.strftime('%X')}] {label} → pencere {window_sec}s, dosya: {outfile}")

    last_data_time = time.time()
    count = 0
    with open(outfile,"w") as f:
        try:
            while True:
                now = time.time()
                if now - last_data_time > IDLE_TIMEOUT_SEC:
                    break
                try:
                    ws.settimeout(1.0)
                    msg = ws.recv()
                except websocket._exceptions.WebSocketTimeoutException:
                    continue

                try:
                    obj = json.loads(msg)
                except Exception:
                    f.write(msg+"\n"); f.flush()
                    count += 1
                    last_data_time = now
                    continue

                if isinstance(obj, dict):
                    if obj.get("type") in ("welcome","ping","confirm_subscription"):
                        continue
                    payload = obj.get("message")
                    if not payload:
                        continue

                    def write_rec(rec):
                        nonlocal count
                        if not isinstance(rec, dict):
                            return
                        f.write(json.dumps(rec)+"\n")
                        count += 1

                    if isinstance(payload, list):
                        for rec in payload:
                            write_rec(rec)
                    else:
                        write_rec(payload)

                    f.flush()
                    last_data_time = now
        finally:
            ws.close()

    print(f"[{time.strftime('%X')}] {label} → bütün paketler yazdırıldı → {outfile} ({count} satır)")

# --------------- Periodik tetik (mevcut) ---------------
def _align_start(period_sec: int) -> int:
    now = time.time()
    return int(now - (now % period_sec) + period_sec)

def _loop(period_sec: int, fn):
    next_tick = _align_start(period_sec)
    while True:
        sleep_dur = max(0.0, next_tick - time.time())
        time.sleep(sleep_dur)
        try:
            fn()
        except Exception as e:
            print(f"[job error] {e}")
        next_tick += period_sec

# --------------- Job runner ---------------
def run_job(job: Dict[str, Any]):
    target = job["target"]
    kind   = job["kind"]
    label  = job["label"]
    window = job["window_sec"]

    # 1) Paket listesi (dinamik)
    if job["packet_mode"] == "all":
        names = get_all_telemetry_names(target) if kind == "TM" else get_all_command_names(target)
    else:
        names = job["packets"]

    if not names:
        print(f"[{time.strftime('%X')}] {label} → paket listesi boş, atlandı.")
        return

    keys = build_packet_keys(kind, target, names)

    # 2) Dosya: TC_/TM_ prefix
    prefix = "TM"
    if kind == "TC":
        prefix = "TC"
    outfile = f"dbprocesses/logs/{prefix}_{target}.ndjson"

    # 3) Dump
    dump_decom_ndjson(keys, window, outfile, label)


if __name__ == "__main__":
    # Her job için kendi periodunda sürekli koştur
    for j in JOBS:
        t = threading.Thread(target=_loop, args=(j["period_sec"], lambda jj=j: run_job(jj)), daemon=True)
        t.start()

    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        print("Kapanıyor…")

