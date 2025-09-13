import re
from urllib.parse import urlparse, parse_qs

# File input dan output
INPUT_FILE = "input.txt"
OUTPUT_FILE = "output.txt"

# Regex untuk mendeteksi Trojan WS
TROJAN_PATTERN = re.compile(r"trojan://[^@\s]+@[^:\s]+:\d+\?[^ \n]+")

# Query wajib ada
REQUIRED_QUERIES = {"host", "password", "sni", "peer", "ws"}

def has_all_queries(url):
    """Cek apakah Trojan memiliki semua query wajib"""
    parsed = urlparse(url)
    qs_keys = {k.lower() for k in parse_qs(parsed.query).keys()}
    return REQUIRED_QUERIES.issubset(qs_keys)

def main():
    valid_accounts = []

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()
        matches = TROJAN_PATTERN.findall(line)
        for m in matches:
            if has_all_queries(m):
                valid_accounts.append(m)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for account in valid_accounts:
            f.write(account + "\n")

    print(f"Selesai! {len(valid_accounts)} akun Trojan dengan query lengkap disimpan di {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
