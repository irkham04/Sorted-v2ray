#!/usr/bin/env python3
import argparse, base64, re, requests, sys, time
import ssl
import socket
from urllib.parse import urlparse, parse_qs
try:
    import websocket
except ImportError:
    print("websocket-client belum terinstall. Jalankan: pip install websocket-client")
    sys.exit(1)

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--sorted", required=True)
    parser.add_argument("--active", required=True)
    parser.add_argument("--require-sni-host", action="store_true")
    parser.add_argument("--delay", type=float, default=1)
    parser.add_argument("--timeout", type=float, default=5)
    return parser.parse_args()

def fetch_and_decode(url):
    try:
        r = requests.get(url.strip(), timeout=10)
        r.raise_for_status()
        content = r.text.strip()
        try:
            decoded = base64.b64decode(content).decode(errors="ignore")
            return [l.strip() for l in decoded.splitlines() if l.strip()]
        except Exception:
            return [l.strip() for l in content.splitlines() if l.strip()]
    except Exception as e:
        print(f"[ERROR] gagal fetch {url}: {e}", file=sys.stderr)
        return []

def parse_trojan_ws(line, require_sni_host=False):
    if not line.lower().startswith("trojan://"):
        return None
    parsed = urlparse(line)
    qs = parse_qs(parsed.query)
    type_ws = qs.get("type", [""])[0].lower() == "ws"
    has_sni = "sni" in qs and qs["sni"][0].strip()
    has_host = "host" in qs and qs["host"][0].strip()
    if require_sni_host and not (has_sni and has_host):
        return None
    if type_ws:
        return {
            "line": line,
            "host": qs.get("host", [""])[0],
            "port": parsed.port,
            "path": qs.get("path", ["/"])[0],
            "sni": qs.get("sni", [""])[0]
        }
    return None

def check_ws(account, timeout=5):
    url = f"wss://{account['host']}:{account['port']}{account['path']}"
    try:
        start = time.time()
        ws = websocket.create_connection(
            url,
            timeout=timeout,
            sslopt={"server_hostname": account["sni"], "cert_reqs": ssl.CERT_NONE}
        )
        ws.close()
        latency = int((time.time() - start)*1000)
        return True, latency
    except Exception as e:
        return False, str(e)

def main():
    args = parse_args()
    all_accounts = []

    with open(args.input) as f:
        urls = [l.strip() for l in f if l.strip()]
    for url in urls:
        all_accounts.extend(fetch_and_decode(url))

    ws_accounts = []
    for line in all_accounts:
        acc = parse_trojan_ws(line, args.require_sni_host)
        if acc:
            ws_accounts.append(acc)

    sorted_lines = []
    active_lines = []

    for idx, acc in enumerate(ws_accounts):
        print(f"[INFO] Memproses akun {idx+1}/{len(ws_accounts)}")
        sorted_lines.append(acc["line"])
        active, info = check_ws(acc, timeout=args.timeout)
        if active:
            sorted_lines.append(f"# Status: Aktif | Ping: {info} ms")
            active_lines.append(f"{acc['line']}\n# Status: Aktif | Ping: {info} ms")
        else:
            sorted_lines.append(f"# Status: Tidak aktif | Info: {info}")

        time.sleep(args.delay)

    with open(args.sorted, "w") as f:
        f.write("\n".join(sorted_lines)+"\n")
    with open(args.active, "w") as f:
        f.write("\n".join(active_lines)+"\n")

if __name__ == "__main__":
    main()
