import os
import base64
import requests
import websocket
from urllib.parse import urlparse, parse_qs

INPUT_FILE = "input.txt"
OUTPUT_ACTIVE = "results/sni.txt"
OUTPUT_LOG = "results/log.txt"

MAX_RETRY = 2
TIMEOUT = 20

os.makedirs("results", exist_ok=True)

# --------------------------
# Ambil akun dari raw GitHub URL
# --------------------------
def fetch_accounts():
    accounts = []
    if not os.path.exists(INPUT_FILE):
        print(f"{INPUT_FILE} tidak ditemukan")
        return accounts

    with open(INPUT_FILE, "r") as f:
        urls = [line.strip() for line in f if line.strip()]

    for url in urls:
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            content = r.text
            for line in content.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    decoded = base64.b64decode(line).decode("utf-8")
                except Exception:
                    decoded = line
                accounts.append(decoded)
        except Exception as e:
            print(f"Gagal ambil {url}: {e}")

    return accounts

# ----------------------------------------
# Cek query lengkap: type, host, path, sni/peer
# ----------------------------------------
def has_complete_query(url):
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    # DEBUG: tampilkan query yang terbaca
    # print("DEBUG QUERY:", qs)
    required_keys = ["type", "host", "path"]
    peer_present = "peer" in qs or "sni" in qs
    return all(k in qs for k in required_keys) and peer_present

# --------------------------
# Parsing Trojan URL
# --------------------------
def parse_trojan_url(url):
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    host_header = qs.get("host", [parsed.hostname])[0]
    peer = qs.get("sni", qs.get("peer", [host_header]))[0]
    path = qs.get("path", [parsed.path or "/"])[0]
    port = parsed.port or 443
    return port, peer, path, host_header

# --------------------------
# Tes WS/TLS dengan retry
# --------------------------
def check_ws(host, port, peer, host_header):
    last_error = ""
    for attempt in range(1, MAX_RETRY + 1):
        try:
            ws_url = f"wss://{host}:{port}/"
            ws = websocket.create_connection(
                ws_url,
                sslopt={"cert_reqs": 0, "check_hostname": False, "server_hostname": peer},
                header=[f"Host: {host_header}"],
                timeout=TIMEOUT,
            )
            ws.close()
            return True
        except Exception as e:
            last_error = str(e)
            print(f"Attempt {attempt}/{MAX_RETRY} gagal: {last_error}")
    return last_error

# --------------------------
# Main
# --------------------------
def main():
    accounts = fetch_accounts()
    filtered = [a for a in accounts if has_complete_query(a)]
    print(f"Total akun query lengkap: {len(filtered)}")

    active = []
    log_lines = []

    for i, acc in enumerate(filtered, 1):
        port, peer, path, host_header = parse_trojan_url(acc)
        print(f"[{i}/{len(filtered)}] Tes WS {host_header}:{port} SNI={peer} ...")
        result = check_ws(host_header, port, peer, host_header)
        if result is True:
            print("AKTIF ✅")
            active.append(acc)
            log_lines.append(f"AKTIF: {acc}")
        else:
            print("GAGAL ❌")
            log_lines.append(f"GAGAL ({result}): {acc}")

    # Simpan akun aktif
    with open(OUTPUT_ACTIVE, "w") as f:
        for acc in active:
            f.write(acc + "\n")

    # Simpan log detail
    with open(OUTPUT_LOG, "w") as f:
        for line in log_lines:
            f.write(line + "\n")

    print(f"\nTotal akun aktif: {len(active)}")
    print(f"Hasil aktif disimpan di {OUTPUT_ACTIVE}")
    print(f"Log detail disimpan di {OUTPUT_LOG}")

if __name__ == "__main__":
    main()
