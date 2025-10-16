#!/usr/bin/env python3
import json, time, websocket

AUTH   = "123"
HOST   = "localhost:2900"
SCOPE  = "DEFAULT"

# ---------- CFS_DEBUG AYARLARI ----------
CFS_TARGET = "CFS_DEBUG"
CFS_PACKET_NAMES = [
 "CFE_ES_HKPACKET","CFE_ES_ONEAPPTLM","CFE_ES_POOLSTATSTLM","CFE_ES_SHELLPACKET",
 "CFE_EVS_PACKET","CFE_EVS_TLMPKT","CFE_HK_COMBINED_PKT1","CFE_SB_HKMSG",
 "CFE_SB_PREVSUBMSG","CFE_SB_STATMSG","CFE_SB_SUBRPRTMSG","CFE_TBL_HKPACKET",
 "CFE_TBL_TBLREGPACKET","CFE_TIME_DIAGPACKET","CFE_TIME_HKPACKET","CF_HKPACKET",
 "CF_TRANSPACKET","CI_HKPACKET","CS_HKPACKET","DS_FILEINFOPKT","DS_HKPACKET",
 "FM_DIRLISTPKT","FM_FILEINFOPKT","FM_FREESPACEPKT","FM_HOUSEKEEPINGPKT",
 "FM_OPENFILESPKT","HK_HKPACKET","HS_HKPACKET","LC_HKPACKET","MD_DWELLPKT",
 "MD_HKTLM","MM_HKPACKET","SCH_DIAGPACKET","SCH_HKPACKET","SC_HKTLM","TO_HKPACKET"
]
CFS_OUTFILE = "cfs_debug_all_last1min_decom.ndjson"
CFS_WINDOW_SEC = 60

# ---------- SIM_42_TRUTH AYARLARI ----------
SIM_TARGET = "SIM_42_TRUTH"
# Yalnızca tek paket istiyoruz:
SIM_DECOM_PACKETS = ["DECOM__TLM__SIM_42_TRUTH__SIM_42_TRUTH_DATA"]
SIM_OUTFILE = "sim_42_truth_last30s_decom.ndjson"
SIM_WINDOW_SEC = 30

IDLE_TIMEOUT_SEC = 3.0  # bu kadar saniye yeni veri yoksa batch bitti kabul et


def dump_decom_ndjson(decom_packet_keys, window_sec, outfile):
    end_ns   = int(time.time() * 1e9)
    start_ns = int((time.time() - window_sec) * 1e9)

    ws_url = f"ws://{HOST}/openc3-api/cable?scope={SCOPE}&authorization={AUTH}"
    ws = websocket.WebSocket()
    ws.connect(ws_url)

    identifier = json.dumps({"channel":"StreamingChannel"})
    ws.send(json.dumps({"command":"subscribe","identifier":identifier}))

    data = {
      "action":"add","scope":SCOPE,"token":AUTH,
      "packets": decom_packet_keys,          # <- string listesi
      "start_time": start_ns,
      "end_time": end_ns
    }
    ws.send(json.dumps({"command":"message","identifier":identifier,"data":json.dumps(data)}))

    print(f"{outfile} dosyasına yazılıyor (pencere: son {window_sec} sn)…")
    last_data_time = time.time()

    with open(outfile,"w") as f:
        try:
            while True:
                msg = ws.recv()
                now = time.time()
                try:
                    obj = json.loads(msg)
                except Exception:
                    f.write(msg+"\n"); f.flush()
                    last_data_time = now
                    continue

                if isinstance(obj, dict):
                    if obj.get("type") in ("welcome","ping","confirm_subscription"):
                        # ping/welcome mesajlarını atla
                        pass
                    else:
                        payload = obj.get("message")
                        if payload:
                            if isinstance(payload, list):
                                for rec in payload:
                                    f.write(json.dumps(rec)+"\n")
                            else:
                                f.write(json.dumps(payload)+"\n")
                            f.flush()
                            last_data_time = now
                else:
                    f.write(msg+"\n"); f.flush()
                    last_data_time = now

                if now - last_data_time > IDLE_TIMEOUT_SEC:
                    print(f"Kayıt bitti, çıkış yapılıyor → {outfile}")
                    break
        finally:
            ws.close()


if __name__ == "__main__":
    # 1) CFS_DEBUG: tüm paketler, son 1 dakika
    cfs_decom_packets = [f"DECOM__TLM__{CFS_TARGET}__{p}" for p in CFS_PACKET_NAMES]
    dump_decom_ndjson(cfs_decom_packets, CFS_WINDOW_SEC, CFS_OUTFILE)

    # 2) SIM_42_TRUTH: sadece SIM_42_TRUTH_DATA, son 30 saniye
    dump_decom_ndjson(SIM_DECOM_PACKETS, SIM_WINDOW_SEC, SIM_OUTFILE)
