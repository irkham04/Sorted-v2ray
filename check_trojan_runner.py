#!/usr/bin/env python3
import argparse
import base64
import json
import requests
import subprocess
import time

def decode_base64_url(url):
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        decoded = base64.b64decode(r.text).decode("utf-8", errors="ignore")
        return decoded.splitlines()
    except Exception as e:
        print(f"[ERROR] Gagal fetch/decode {url}: {e}")
        return []

def is_valid_trojan(line):
    if not line.startswith("trojan://"):
        return False
    if "type=ws" not in line.lower():
        return False
    if "sni=" not in line or "host=" not in line:
        return False
    return True

def run_speedtest(speedtest_bin="./speedtest"):
    try:
        result = subprocess.check_output([speedtest_bin, "-f", "json"], timeout=60)
        data = json.loads(result.decode("utf-8"))
        isp = data.get("isp", "Unknown ISP")
        server = data.get("server", {})
        server_name = server.get("name", "Unknown")
        server_loc = f"{server.get('location','?')}, {server.get('country','?')}"
        ping = data.get("ping", {}).get("latency", "?")
        return f"# ISP: {isp} | Server: {server_name} ({server_loc}) | Ping: {ping} ms"
    except Exception as e:
        return f"# Speedtest gagal: {e}"

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, help="File input berisi URL raw GitHub")
    p.add_argument("--sorted", default="sorted.txt", help="File output akun tersortir")
    p.add_argument("--speedtest-bin", default="./speedtest", help="Path binary speedtest Ookla")
    p.add_argument("--batch-size", type=int, default=5, help="Jumlah akun per batch speedtest")
    p.add_argument("--delay", type=int, default=5, help="Delay antar akun speedtest (detik)")
    args = p.parse_args()

    urls = []
    with open(args.input, "r") as f:
        urls = [line.strip() for line in f if line.strip()]

    all_accounts = []
    for url in urls:
        all_accounts.extend(decode_base64_url(url))

    valid_accounts = [acc for acc in all_accounts if is_valid_trojan(acc)]

    # tulis sorted.txt
    with open(args.sorted, "w") as f:
        f.write(f"# Total akun valid: {len(valid_accounts)}\n")
        for acc in valid_accounts:
            f.write(acc + "\n")
    print(f"[INFO] sorted.txt dibuat: {len(valid_accounts)} akun valid")

    # tulis active.txt
    with open("active.txt", "w") as f:
        f.write("# Akun aktif dengan info speedtest (baris info diawali #)\n\n")
        for i, acc in enumerate(valid_accounts, start=1):
            f.write(acc + "\n")
            if i % args.batch_size == 0:
                print(f"[INFO] Batch {i//args.batch_size} selesai, delay {args.delay}s")
                time.sleep(args.delay)
            info = run_speedtest(args.speedtest_bin)
            f.write(info + "\n\n")
    print(f"[INFO] active.txt dibuat dengan speedtest untuk tiap akun")

if __name__ == "__main__":
    main()
