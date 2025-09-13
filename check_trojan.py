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

BUG_HOST = "quiz.vidio.com"

def parse_trojan_url(trojan_url: str):
    parsed = urlparse(trojan_url)
    port = parsed.port or 443
    qs = parse_qs(parsed.query)
    # peer diambil dari sni dulu, jika tidak ada dari host query
    peer = qs.get("sni", qs.get("host", [parsed.hostname]))[0]
    return port, peer

def check_ws_tls(host, port, peer):
    ws_url = f"wss://{host}:{port}/"
    try:
        ws = websocket.create_connection(
            ws_url,
            sslopt={
                "cert_reqs": ssl.CERT_REQUIRED,
                "check_hostname": True,
                "server_hostname": peer
            },
            timeout=5
        )
        ws.send("ping")
        ws.close()
        return True, "OK"
    except Exception as e:
        return False, str(e)

def fetch_accounts_from_url(url):
    """Ambil akun dari raw GitHub, decode Base64 jika perlu"""
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        text = resp.text.strip()

        # coba decode Base64, jika gagal anggap teks biasa
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
    active_accounts = []
    if not os.path.exists(INPUT_FILE):
        print(f"{INPUT_FILE} tidak ditemukan")
        return

    with open(INPUT_FILE, "r") as f:
        source_links = [line.strip() for line in f if line.strip()]

    all_accounts = []
    for link in source_links:
        print(f"Ambil daftar dari {link} ...")
        all_accounts.extend(fetch_accounts_from_url(link))

    print(f"Total {len(all_accounts)} akun ditemukan.")

    for acc in all_accounts:
        parsed = parse_trojan_url(acc)
        if not parsed:
            continue
        port, peer = parsed
        host = BUG_HOST  # ganti host ke quiz.vidio.com
        print(f"Tes {host}:{port} (peer: {peer}) ...", end=" ")
        ok, msg = check_ws_tls(host, port, peer)
        if ok:
            print("OK ✅")
            active_accounts.append(acc)  # simpan baris asli
        else:
            print(f"FAILED ❌ ({msg})")

    with open(OUTPUT_FILE, "w") as f:
        for acc in active_accounts:
            f.write(acc + "\n")

    print(f"\nHasil: {len(active_accounts)} akun aktif disimpan di {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
