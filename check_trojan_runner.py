import os
import base64
from urllib.parse import urlparse, parse_qs

INPUT_FILE = "input.txt"
OUTPUT_SORTED = "results/sorted.txt"

os.makedirs("results", exist_ok=True)

def fetch_accounts():
    accounts = []
    if not os.path.exists(INPUT_FILE):
        print(f"{INPUT_FILE} tidak ditemukan")
        return accounts
    with open(INPUT_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                decoded = base64.b64decode(line).decode("utf-8")
            except Exception:
                decoded = line
            accounts.append(decoded)
    return accounts

def has_complete_ws_query(url):
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    required_keys = ["type", "host", "path"]
    peer_present = "peer" in qs or "sni" in qs
    type_ws = qs.get("type", [""])[0].lower() == "ws"
    return all(k in qs for k in required_keys) and peer_present and type_ws

def main():
    accounts = fetch_accounts()
    filtered = [a for a in accounts if has_complete_ws_query(a)]
    print(f"Total akun query lengkap & tipe WS: {len(filtered)}")

    with open(OUTPUT_SORTED, "w") as f:
        for acc in filtered:
            f.write(acc + "\n")

    print(f"Hasil disimpan di {OUTPUT_SORTED}")

if __name__ == "__main__":
    main()
