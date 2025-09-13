#!/usr/bin/env python3
import argparse
import subprocess
import json
import time
import re

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="File input")
    parser.add_argument("--sorted", required=True, help="File output sorted")
    parser.add_argument("--active", required=True, help="File output active")
    parser.add_argument("--only-ws", action="store_true", help="Hanya ws")
    parser.add_argument("--require-sni-host", action="store_true", help="Wajib ada SNI & host")
    parser.add_argument("--speedtest-bin", default="./speedtest-bin", help="Lokasi speedtest CLI")
    parser.add_argument("--delay", type=int, default=1, help="Delay antar speedtest (detik)")
    return parser.parse_args()

def run_speedtest(ip, speedtest_bin, tested_ips, delay=1):
    if ip in tested_ips:
        print(f"# IP {ip} sudah dites, skip speedtest", flush=True)
        return {"skip": True, "ip": ip}
    tested_ips.add(ip)
    print(f"[INFO] Jalankan speedtest untuk IP {ip} ...", flush=True)

    try:
        result = subprocess.run(
            [speedtest_bin, "-f", "json"],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode != 0:
            print(f"# Speedtest gagal: {result.stderr.strip()}", flush=True)
            return {"error": f"Speedtest gagal code {result.returncode}"}

        data = json.loads(result.stdout)
        server_data = data.get("server", {})
        isp = data.get("isp", "Unknown ISP")
        server_host = server_data.get("host", "Unknown Host")
        server_name = server_data.get("name", "Unknown Name")
        server_country = server_data.get("country", "Unknown Country")
        ping = data.get("ping", {}).get("latency", "?")
        print(f"# ISP: {isp} | Server: {server_name} ({server_host}, {server_country}) | Ping: {ping} ms", flush=True)
        return {"isp": isp, "server": server_name, "host": server_host, "country": server_country, "ping": ping, "ip": ip}
    except Exception as e:
        print(f"# Speedtest exception: {e}", flush=True)
        return {"error": str(e)}
    finally:
        time.sleep(delay)

def extract_ip(url):
    match = re.search(r"@([\w\.-]+):(\d+)", url)
    return match.group(1) if match else None

def main():
    args = parse_args()
    with open(args.input, "r") as f:
        lines = [l.strip() for l in f if l.strip()]

    accounts = [l for l in lines if not l.startswith("#")]
    tested_ips = set()

    sorted_lines = []
    active_lines = []

    for idx, acc in enumerate(accounts):
        print(f"[INFO] Memproses akun {idx+1}/{len(accounts)}", flush=True)

        if args.only_ws and "type=ws" not in acc.lower():
            continue
        if args.require_sni_host and ("sni=" not in acc.lower() or "host=" not in acc.lower()):
            continue

        ip = extract_ip(acc)
        if not ip:
            continue

        result = run_speedtest(ip, args.speedtest_bin, tested_ips, delay=args.delay)

        sorted_lines.append(acc)
        if "error" not in result and not result.get("skip", False):
            active_lines.append(acc)
            sorted_lines.append(f"# ISP: {result.get('isp','Unknown')} | Server: {result.get('server','Unknown')} ({result.get('host','Unknown')}, {result.get('country','Unknown')}) | Ping: {result.get('ping','?')} ms")

    with open(args.sorted, "w") as f:
        f.write("\n".join(sorted_lines) + "\n")

    with open(args.active, "w") as f:
        f.write("\n".join(active_lines) + "\n")

if __name__ == "__main__":
    main()
