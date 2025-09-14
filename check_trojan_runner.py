#!/usr/bin/env python3
import argparse, base64, requests, sys, time
from urllib.parse import urlparse, parse_qs

try:
    import websocket
except ImportError:
    print("Install websocket-client package!", file=sys.stderr)
    sys.exit(1)

def fetch_and_decode(url, timeout=20):
    try:
        text = requests.get(url, timeout=timeout).text.strip()
        try:
            return base64.b64decode(text).decode(errors="ignore")
        except Exception:
            return text
    except Exception as e:
        print(f"[ERROR] gagal fetch {url}: {e}", file=sys.stderr)
        return ""

def parse_trojan_ws(line, require_sni_host=False):
    if not line.lower().startswith("trojan://"):
        return None
    parsed = urlparse(line)
    qs = parse_qs(parsed.query)
    if qs.get("type", [""])[0].lower() != "ws":
        return None
    has_sni = "sni" in qs and qs["sni"][0].strip()
    has_host = "host" in qs and qs["host"][0].strip()
    if require_sni_host and not (has_sni and has_host):
        return None
    return {
        "original": line,
        "scheme": parsed.scheme,
        "user": parsed.username,
        "host": parsed.hostname,
        "port": parsed.port,
        "path": qs.get("path", ["/"])[0],
        "sni": qs.get("sni", [""])[0],
        "host_query": qs.get("host", [""])[0],
        "query": parsed.query,
        "fragment": parsed.fragment
    }

def ws_check(account, delay=1, timeout=5):
    ws_url = f"ws://{account['host']}:{account['port']}{account['path']}"
    try:
        ws = websocket.create_connection(ws_url, timeout=timeout, sslopt={"server_hostname": account["sni"]})
        ws.close()
        time.sleep(delay)
        return True, 0
    except Exception as e:
        time.sleep(delay)
        return False, str(e)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--sorted", default="sorted.txt")
    parser.add_argument("--active", default="active.txt")
    parser.add_argument("--require-sni-host", action="store_true")
    parser.add_argument("--delay", type=float, default=1)
    parser.add_argument("--timeout", type=int, default=5)
    args = parser.parse_args()

    all_accounts = []

    with open(args.input) as f:
        for url in f:
            url = url.strip()
            if not url:
                continue
            raw = fetch_and_decode(url)
            for line in raw.splitlines():
                acc = parse_trojan_ws(line, require_sni_host=args.require_sni_host)
                if acc:
                    all_accounts.append(acc)

    sorted_lines = []
    active_lines = []
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

    for idx, acc in enumerate(all_accounts, start=1):
        print(f"[INFO] Memproses akun {idx}/{len(all_accounts)}")
        ok, info = ws_check(acc, delay=args.delay, timeout=args.timeout)
        # Output: ganti host sebelum port menjadi quiz.vidio.com
        url = f"{acc['scheme']}://{acc['user']}@quiz.vidio.com:{acc['port']}?{acc['query']}#{acc['fragment']}"
        if ok:
            line = f"{url}\n# Status: Aktif | Ping: {info} ms | Checked: {timestamp}\n"
            sorted_lines.append(line)
            active_lines.append(line)
        else:
            line = f"{url}\n# Status: Tidak aktif | Info: {info} | Checked: {timestamp}\n"
            sorted_lines.append(line)

    with open(args.sorted, "w") as f:
        f.writelines(sorted_lines)
    with open(args.active, "w") as f:
        f.writelines(active_lines)

    print(f"[INFO] Total akun WS: {len(all_accounts)}, Aktif: {len(active_lines)}")

if __name__ == "__main__":
    main()
