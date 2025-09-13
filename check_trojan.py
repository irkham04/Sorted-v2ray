import os
import ssl
import base64
import requests
import websocket
from urllib.parse import urlparse, parse_qs

INPUT_FILE = "input.txt"
OUTPUT_DIR = "results"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "active_accounts.txt")

os.makedirs(OUTPUT_DIR, exist_ok=True)

def parse_trojan_url(trojan_url: str):
    parsed = urlparse(trojan_url)
    qs = parse_qs(parsed.query)

    host_header = qs.get("host", [parsed.hostname])[0]        # Host header
    peer = qs.get("sni", [host_header])[0]                    # SNI fallback ke host header
    path = qs.get("path", [parsed.path or "/"])[0]            # Path WS
    port = parsed.port or 443
    return port, peer, path, host_header

def check_ws_tls(host, port, path, peer, host_header):
    ws_url = f"wss://{host}:{port}{path}"
    try:
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
        ws.close()
        return True, "OK"
    except Exception as e:
        return False, str(e)

def fetch_accounts_from_url(url):
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        text = resp.text.strip()

        # Coba decode Base64, kalau gagal pakai teks biasa
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
        try:
            port, peer, path, host_header = parse_trojan_url(acc)
        except Exception as e:
            print(f"Parsing gagal untuk akun: {acc} ({e})")
            continue

        host = host_header  # gunakan host asli untuk koneksi
        print(f"Tes {host}:{port} path={path} SNI={peer} ...", end=" ")
        ok, msg = check_ws_tls(host, port, path, peer, host_header)
        if ok:
            print("AKTIF ✅")
            active_accounts.append(acc)  # simpan baris lengkap
        else:
            print(f"GAGAL ❌ ({msg})")

    # tulis akun aktif lengkap
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        for acc in active_accounts:
            f.write(acc + "\n")

    print(f"\nHasil: {len(active_accounts)} akun aktif disimpan di {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
