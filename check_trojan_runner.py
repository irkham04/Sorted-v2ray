#!/usr/bin/env python3
"""
check_trojan_runner.py

- Input: file berisi daftar URL raw GitHub (satu per baris) yang berisi akun base64 atau teks.
- Output:
  - sorted.txt : daftar trojan:// yang valid (type=ws + sni + host)
  - active.txt : untuk tiap akun aktif: baris akun (plain), baris info speedtest dimulai dengan '#'
"""
import argparse
import base64
import json
import os
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlparse, parse_qs

import requests
import signal

# ---------- helpers ----------
def fetch_raw_text(url, timeout=20):
    try:
        r = requests.get(url.strip(), timeout=timeout)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"[WARN] gagal fetch {url}: {e}", file=sys.stderr)
        return ""

def try_base64_decode_text(text):
    # Jika keseluruhan teks base64 -> decode
    s = "".join(text.splitlines())
    try:
        decoded = base64.b64decode(s, validate=True).decode("utf-8", errors="ignore")
        return decoded
    except Exception:
        # coba decode per baris (bila file berisi banyak base64 baris)
        lines = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                lines.append(base64.b64decode(line).decode("utf-8", errors="ignore"))
            except Exception:
                # kalau bukan base64 -> keep raw line
                lines.append(line)
        return "\n".join(lines)

def extract_trojan_lines(text):
    # ekstrak baris yang memulai trojan://
    lines = []
    for ln in text.splitlines():
        ln = ln.strip()
        if ln.startswith("trojan://"):
            lines.append(ln)
    return lines

def trojan_is_ws_and_complete(uri):
    try:
        p = urlparse(uri)
        qs = parse_qs(p.query)
        # type must be ws
        typev = qs.get("type", [""])[0].lower()
        has_ws = (typev == "ws")
        has_sni = bool(qs.get("sni", [""])[0].strip())
        has_host = bool(qs.get("host", [""])[0].strip())
        return has_ws and has_sni and has_host
    except Exception:
        return False

# ---------- xray helpers ----------
def make_xray_config_for_trojan(uri, listen_port=1080):
    """Buat config xray (socks inbound) yang outbound trojan memakai data dari URI.
       Returns dict (json)"""
    p = urlparse(uri)
    qs = parse_qs(p.query)
    server_host = p.hostname or qs.get("host", [""])[0]
    server_port = int(p.port or 443)
    # password could be in username (userinfo)
    password = p.username or ""
    sni = qs.get("sni", [""])[0]
    path = qs.get("path", ["/"])[0]
    host_header = qs.get("host", [""])[0]

    cfg = {
        "log": {"loglevel": "warning"},
        "inbounds": [
            {
                "port": listen_port,
                "listen": "127.0.0.1",
                "protocol": "socks",
                "settings": {"udp": False, "auth": {"accounts": []}}
            }
        ],
        "outbounds": [
            {
                "protocol": "trojan",
                "settings": {
                    "servers": [
                        {
                            "address": server_host,
                            "port": server_port,
                            "password": password
                        }
                    ]
                },
                "streamSettings": {
                    "network": "ws",
                    "security": "tls",
                    "tlsSettings": {"serverName": sni or server_host},
                    "wsSettings": {"path": path, "headers": {"Host": host_header or server_host}}
                }
            }
        ]
    }
    return cfg

def start_xray_with_config(cfg):
    """Write temp config, start xray -c <file>. Returns (proc, cfg_path)"""
    cfg_fd, cfg_path = tempfile.mkstemp(prefix="xray_cfg_", suffix=".json")
    os.write(cfg_fd, json.dumps(cfg).encode("utf-8"))
    os.close(cfg_fd)
    # start xray
    try:
        proc = subprocess.Popen(["xray", "-c", cfg_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # wait briefly for it to initialize
        time.sleep(2.5)
        return proc, cfg_path
    except Exception as e:
        try:
            os.remove(cfg_path)
        except Exception:
            pass
        print(f"[WARN] gagal start xray: {e}", file=sys.stderr)
        return None, None

def stop_xray(proc, cfg_path):
    try:
        if proc:
            proc.terminate()
            # wait shortly
            try:
                proc.wait(timeout=4)
            except Exception:
                proc.kill()
    except Exception:
        pass
    try:
        if cfg_path and os.path.exists(cfg_path):
            os.remove(cfg_path)
    except Exception:
        pass

# ---------- speedtest helpers ----------
def run_speedtest_via_proxy(proxy_socks="socks5://127.0.0.1:1080", speedtest_bin="./speedtest", timeout=60):
    """Run Ookla speedtest with ALL_PROXY env pointing to socks proxy, return parsed JSON dict or None."""
    env = os.environ.copy()
    env["ALL_PROXY"] = proxy_socks
    # Accept license/gdpr if binary requires
    cmd = [speedtest_bin, "--accept-license", "--accept-gdpr", "-f", "json"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=timeout)
        if proc.returncode == 0 and proc.stdout:
            return json.loads(proc.stdout)
        else:
            # try to print stderr for debug
            # print(proc.stderr, file=sys.stderr)
            return None
    except Exception as e:
        # print(e, file=sys.stderr)
        return None

def format_short_speedtest_info(json_obj):
    """Return string like: ISP: X | Server: NAME (Location, Country) | Ping: 5.37 ms"""
    try:
        isp = json_obj.get("isp", "") if isinstance(json_obj, dict) else ""
        server = json_obj.get("server", {}) if isinstance(json_obj, dict) else {}
        name = server.get("name", "")
        location = server.get("location", "")
        country = server.get("country", "")
        ping = json_obj.get("ping", {}).get("latency", None)
        ping_str = f"{ping:.2f} ms" if ping is not None else "N/A"
        return f"ISP: {isp} | Server: {name} ({location}, {country}) | Ping: {ping_str}"
    except Exception:
        return "ISP: ? | Server: ? | Ping: ?"

# ---------- main ----------
def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, help="File input (daftar URL raw github, 1 per baris)")
    p.add_argument("--sorted", default="sorted.txt", help="Output sorted trojan ws")
    p.add_argument("--active", default="active.txt", help="Output active (account + # info)")
    p.add_argument("--speedtest-bin", default="./speedtest", help="Path to speedtest binary")
    p.add_argument("--proxy-port", type=int, default=1080, help="Local socks port xray will listen")
    p.add_argument("--only-ws", action="store_true", help="Filter only type=ws")
    p.add_argument("--require-sni-host", action="store_true", help="Require sni and host in query")
    p.add_argument("--timeout-fetch", type=int, default=20)
    args = p.parse_args()

    # collect raw trojan lines from all URLs
    all_trojans = []
    total_count = 0
    with open(args.input, "r", encoding="utf-8") as f:
        for url in f:
            url = url.strip()
            if not url:
                continue
            raw = fetch_raw_text(url, timeout=args.timeout_fetch)
            if not raw:
                continue
            decoded = try_base64_decode_text(raw)
            lines = extract_trojan_lines(decoded)
            all_trojans.extend(lines)
            total_count += sum(1 for _ in extract_trojan_lines(decoded))

    # filter WS only and completeness
    filtered = []
    for t in all_trojans:
        if args.only_ws and not trojan_is_ws_and_complete(t):
            continue
        if args.require_sni_host:
            if not trojan_is_ws_and_complete(t):
                continue
        # if neither flag set but want default WS-only behavior, apply:
        if not args.only_ws and not args.require_sni_host:
            # default we keep only ws & sni+host
            if not trojan_is_ws_and_complete(t):
                continue
        filtered.append(t)

    # deduplicate preserve order
    seen = set()
    filtered_unique = []
    for x in filtered:
        if x not in seen:
            seen.add(x)
            filtered_unique.append(x)

    # write sorted
    with open(args.sorted, "w", encoding="utf-8") as out:
        out.write(f"# Akun valid (Trojan WS only): {len(filtered_unique)} dari total trojan: {total_count}\n")
        for line in filtered_unique:
            out.write(line + "\n")

    print(f"[INFO] sorted written: {args.sorted} ({len(filtered_unique)})")

    # iterate and test each account
    results = []
    for uri in filtered_unique:
        print(f"[INFO] testing account: {uri[:80]}...")
        cfg = make_xray_config_for_trojan(uri, listen_port=args.proxy_port)
        proc, cfg_path = start_xray_with_config(cfg)
        time.sleep(1.5)  # wait a bit
        st_json = None
        try:
            st_json = run_speedtest_via_proxy(proxy_socks=f"socks5://127.0.0.1:{args.proxy_port}", speedtest_bin=args.speedtest_bin, timeout=40)
        except Exception as e:
            st_json = None
        # stop xray
        stop_xray(proc, cfg_path)
        if st_json:
            info = format_short_speedtest_info(st_json)
            results.append((uri, info))
            print(f"[OK] {info}")
        else:
            results.append((uri, None))
            print("[FAIL] speedtest failed or no server")

    # write active.txt with requested format:
    # for each account -> write account line (plain), then the speedtest info line prefixed with '# '
    with open(args.active, "w", encoding="utf-8") as fout:
        fout.write("# Hasil per akun (baris info speedtest diberi # agar tidak memengaruhi sub-URL)\n")
        for uri, info in results:
            fout.write(uri + "\n")
            if info:
                fout.write("# " + info + "\n\n")
            else:
                fout.write("# Speedtest: failed or no server\n\n")

    print(f"[DONE] active written: {args.active}")

if __name__ == "__main__":
    main()
