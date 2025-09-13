import os
import ssl
import base64
import requests
import websocket
from urllib.parse import urlparse, parse_qs

INPUT_FILE = "input.txt"
OUTPUT_DIR = "results"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "sni.txt")  # hasil akhir

os.makedirs(OUTPUT_DIR, exist_ok=True)

def fetch_accounts_from_url(url):
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        text = resp.text.strip()
        try:
            decoded = base64.b64decode(text).decode("utf-8")
        except Exception:
            decoded = text
        lines = [line.strip() for line in decoded.splitlines() if line.strip()]
        return [line for line in lines if line.startswith("trojan://")]
    except Exception as e:
        print(f"Gagal fetch {url}: {e}", flush=True)
        return []

def has_complete_query(url):
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    required_keys = ["type", "host", "path"]
    peer_present = "peer" in qs or "sni" in qs
    return all(k in qs for k in required_keys) and peer_present

def parse_trojan_url(url):
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    host_header = qs.get("host", [parsed.hostname])[0]
    peer = qs.get("sni", qs.get("peer", [host_header]))[0]
    path = qs.get("path", [parsed.path or "/"])[0]
    port = parsed.port or 443
    return port, peer, path, host_header

def check_tls(host, port, peer, host_header):
    try:
        ws_url = f"wss://{host}:{port}/"
        ws = websocket.create_connection(
            ws_url,
            sslopt={
                "cert_reqs": ssl.CERT_REQUIRED,
                "check_hostname": True,
                "server_hostname": peer,
            },
            header=[f"Host: {host_header}"],
            timeout=10,
        )
        ws.close()
        return True
    except Exception:
        return False

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"{INPUT_FILE} tidak ditemukan", flush=True)
        return

    active_accounts = []
    all_accounts = []

    with open(INPUT_FILE, "r") as f:
        source_links = [line.strip() for line in f if line.strip()]

    for link in source_links:
        print(f"Ambil akun dari {link} ...", flush=True)
        all_accounts.extend(fetch_accounts_from_url(link))

    print(f"Total {len(all_accounts)} akun ditemukan.", flush=True)

    filtered = [acc for acc in all_accounts if has_complete_query(acc)]
    print(f"{len(filtered)} akun dengan query lengkap ditemukan.", flush=True)

    for i, acc in enumerate(filtered, start=1):
        port, peer, path, host_header = parse_trojan_url(acc)
        host = host_header
        print(f"[{i}/{len(filtered)}] TLS check {host}:{port} SNI={peer} ...", end=" ", flush=True)
        if check_tls(host, port, peer, host_header):
            print("AKTIF ✅", flush=True)
            active_accounts.append(acc)
        else:
            print("GAGAL ❌", flush=True)

    with open(OUTPUT_FILE, "w") as f:
        for acc in active_accounts:
            f.write(acc + "\n")

    print(f"\nHasil akhir: {len(active_accounts)} akun aktif disimpan di {OUTPUT_FILE}", flush=True)

if __name__ == "__main__":
    main()
