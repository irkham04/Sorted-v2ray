import os
import base64
import requests
from urllib.parse import urlparse, parse_qs

INPUT_FILE = "input.txt"
OUTPUT_DIR = "results"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "sorted_accounts.txt")

os.makedirs(OUTPUT_DIR, exist_ok=True)

def fetch_accounts_from_url(url):
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        text = resp.text.strip()

        # Coba decode Base64, kalau gagal pakai teks langsung
        try:
            decoded = base64.b64decode(text).decode('utf-8')
        except Exception:
            decoded = text

        lines = [line.strip() for line in decoded.splitlines() if line.strip()]
        return [line for line in lines if line.startswith("trojan://")]
    except Exception as e:
        print(f"Gagal fetch {url}: {e}")
        return []

def has_complete_query(url):
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    # Pastikan memiliki semua parameter penting
    required_keys = ["type", "host", "path"]
    # peer atau sni wajib ada
    peer_present = "peer" in qs or "sni" in qs
    return all(k in qs for k in required_keys) and peer_present

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"{INPUT_FILE} tidak ditemukan")
        return

    sorted_accounts = []

    with open(INPUT_FILE, "r") as f:
        source_links = [line.strip() for line in f if line.strip()]

    all_accounts = []
    for link in source_links:
        print(f"Ambil akun dari {link} ...")
        all_accounts.extend(fetch_accounts_from_url(link))

    print(f"Total {len(all_accounts)} akun ditemukan.")

    for acc in all_accounts:
        if has_complete_query(acc):
            sorted_accounts.append(acc)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        for acc in sorted_accounts:
            f.write(acc + "\n")

    print(f"\nHasil: {len(sorted_accounts)} akun dengan query lengkap disimpan di {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
