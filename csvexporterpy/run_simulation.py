#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Basit orkestratör:
- Önce dbprocesses/influx_consumer_simple.py için hızlı sağlık kontrolü yapar.
- Hata yoksa iki ayrı terminal açar:
    1) influx_consumer_simple.py (dbprocesses dizininde)
    2) download_all_cfs_debug.py (bu dosyanın bulunduğu dizin)
- Hata varsa hangi dosyada ve mesajı yazdırır.
- "Çıkmak için CTRL+C" yazar; CTRL+C ile her iki terminali kapatır.

Not: Bir terminal öykünücüsü bulunmalı (gnome-terminal, konsole, xfce4-terminal, xterm). 
"""
import os, sys, subprocess, time, shlex, signal

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONSUMER_PATH = os.path.join(BASE_DIR, "dbprocesses", "influx_consumer_simple.py")
DOWNLOADER_PATH = os.path.join(BASE_DIR, "download_all_cfs_debug.py")

GRACE_SEC = 5  # hızlı hata kontrolü için bekleme süresi

def which(cmd):
    from shutil import which as _which
    return _which(cmd)

def detect_terminal():
    candidates = [
        ("gnome-terminal", lambda title, cmd, cwd: [
            "gnome-terminal", "--title", title, "--", "bash", "-lc",
            f'cd {shlex.quote(cwd)}; {cmd}'
        ]),
        ("konsole", lambda title, cmd, cwd: [
            "konsole", "--new-tab", "-p", f'tabtitle={title}', "-e", "bash", "-lc",
            f'cd {shlex.quote(cwd)}; {cmd}'
        ]),
        ("xfce4-terminal", lambda title, cmd, cwd: [
            "xfce4-terminal", "-T", title, "-e", f"bash -lc {shlex.quote(f'cd {cwd}; {cmd}')}"
        ]),
        ("xterm", lambda title, cmd, cwd: [
            "xterm", "-T", title, "-e", "bash", "-lc", f'cd {shlex.quote(cwd)}; {cmd}'
        ]),
    ]
    for name, builder in candidates:
        if which(name):
            return name, builder
    return None, None

def quick_health_check(script_path, workdir):
    """
    Scripti arka planda DOĞRUDAN çalıştırıp (terminal olmadan) kısa süre gözler.
    - 5 sn içinde non-zero ile çıkarsa: hata yakalanmış sayılır.
    - 5 sn sonunda hala çalışıyorsa: temel sağlık OK (sonlandırıp devam ederiz).
    """
    if not os.path.exists(script_path):
        return False, f"Dosya bulunamadı: {script_path}"
    cmd = [sys.executable, script_path]
    proc = subprocess.Popen(
        cmd, cwd=workdir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, preexec_fn=os.setsid
    )
    start = time.time()
    while time.time() - start < GRACE_SEC:
        ret = proc.poll()
        if ret is not None:
            # Erken çıktı
            out, err = proc.communicate(timeout=1)
            msg = err.strip() or out.strip() or f"erken çıkış kodu: {ret}"
            return False, msg
        time.sleep(0.2)
    # Sağlık OK say, durdur
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except Exception:
        pass
    return True, ""

def launch_in_terminal(terminal_builder, title, script_path, workdir):
    # Kullanıcıya şeffaflık için terminalde kapanış notu ekleyelim
    run_cmd = f'{shlex.quote(sys.executable)} {shlex.quote(script_path)}; ' \
              f'code=$?; echo; echo "[{title}] bitti. exit=$code"; ' \
              f'read -p "Pencereyi kapatmak için ENTER" _'
    argv = terminal_builder(title, run_cmd, workdir)
    # Ayrı process group'la başlat, sonra CTRL+C ile kapatabileceğiz
    return subprocess.Popen(argv, preexec_fn=os.setsid)

def main():
    term_name, term_builder = detect_terminal()
    if not term_builder:
        print("Hata: Uygun terminal bulunamadı. Yüklü bir terminal emülatörü (gnome-terminal/konsole/xfce4-terminal/xterm) gerekli.", file=sys.stderr)
        sys.exit(1)

    # 1) Ön sağlık kontrolü: influx_consumer_simple.py
    ok, err = quick_health_check(CONSUMER_PATH, os.path.join(BASE_DIR, "dbprocesses"))
    if not ok:
        print(f"HATA: influx_consumer_simple.py başlatılamadı.\nMesaj: {err}")
        sys.exit(1)

    # 2) İki terminali başlat
    t1 = launch_in_terminal(term_builder, "influx-consumer", CONSUMER_PATH, os.path.join(BASE_DIR, "dbprocesses"))
    # kısa nefes ver, consumer logları başlasın
    time.sleep(1.0)
    t2 = launch_in_terminal(term_builder, "downloader", DOWNLOADER_PATH, BASE_DIR)

    print("Başarı: simülasyon başlatıldı.")
    print('Çıkmak için CTRL+C')

    try:
        # Ana süreç bekler
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        print("\nKapanıyor… (terminalleri kapatacağım)")
        # Terminal gruplarına SIGINT gönder
        for p in (t2, t1):
            try:
                os.killpg(p.pid, signal.SIGINT)
            except Exception:
                pass
            # Nazikçe bekle
            try:
                p.wait(timeout=2)
            except Exception:
                pass
            # Hala yaşıyorsa SIGTERM
            try:
                os.killpg(p.pid, signal.SIGTERM)
            except Exception:
                pass
        print("Bitti.")
        sys.exit(0)

if __name__ == "__main__":
    main()
