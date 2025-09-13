import os
import ssl
import base64
import requests
import websocket
import time
from urllib.parse import urlparse, parse_qs

INPUT_FILE = "input.txt"
OUTPUT_DIR = "results"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "active_accounts.txt")

os.makedirs(OUTPUT_DIR, exist_ok=True)

def parse_trojan_url(trojan_url: str):
    parsed = urlparse(trojan_url)
    qs = parse_qs(parsed.query)

    # Hanya proses akun yang memiliki ws, peer, path
    if qs.get("type", [""])[0] != "ws":
        return None
    if not qs.get("sni") and not qs.get("peer"):
        return None
    if not qs.get("path") and not parsed.path:
        return None

    host_header = qs.get("host", [parsed.hostname])[0]
    peer = qs.get("sni", qs.get("peer", [host_header]))[0]
    path = qs.get("path", [parsed.path or "/"])[0]
    port = parsed.port or 443
    return port, peer, path, host_header

def check_ws_tls(host, port, path, peer, host_header):
    ws_url = f"wss://{host}:{port}{path}"
    try:
        t1 = time.time()
        ws = websocket.create_connection(
            ws_url,
            sslopt={
                "cert_reqs": ssl.CERT_REQUIRED,
                "check_hostname": True,
                "server_hostname": peer
            },
            header=[f"Host: {host_header}"],
            timeout=10
        )
        ws.send("ping")
        ws.recv()  # menerima pong / echo
        ws.close()
        t2 = time.time()
        delay_ms = int((t2 - t1) * 1000)
        return True, delay_ms
    except Exception as e:
        return False, str(e)

def fetch_accounts_from_url(url):
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        text = resp.text.strip()
        try:
            decoded = base64.b64decode(text).decode('utf-8')
        except Exception:
            decoded = text
        lines = [line.strip() for line in decoded.splitlines() if line.strip()]
        return [line for line in lines if line.startswith("trojan://")]
    except Exception as e:
        print(f"Gagal fetch {url}: {e}")
        return []

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"{INPUT_FILE} tidak ditemukan")
        return

    active_accounts = []

    with open(INPUT_FILE, "r") as f:
        source_links = [line.strip() for line in f if line.strip()]

    all_accounts = []
    for link in source_links:
        print(f"Ambil akun dari {link} ...")
        all_accounts.extend(fetch_accounts_from_url(link))

    print(f"Total {len(all_accounts)} akun ditemukan.")

    for acc in all_accounts:
        parsed = parse_trojan_url(acc)
        if not parsed:
            continue
        port, peer, path, host_header = parsed
        host = host_header
        print(f"Tes {host}:{port} path={path} SNI={peer} ...", end=" ")
        ok, result = check_ws_tls(host, port, path, peer, host_header)
        if ok:
            print(f"AKTIF ✅ delay={result}ms")
            active_accounts.append(f"{acc} #delay={result}ms")
        else:
            print(f"GAGAL ❌ ({result})")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        for acc in active_accounts:
            f.write(acc + "\n")

    print(f"\nHasil: {len(active_accounts)} akun aktif disimpan di {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
