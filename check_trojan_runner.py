import base64
import re
import requests
from urllib.parse import urlparse, parse_qs

INPUT_FILE = "input.txt"
OUTPUT_FILE = "output.txt"

TROJAN_PATTERN = re.compile(r"trojan://[^@\s]+@[^:\s]+:\d+\?[^ \n]+")
REQUIRED_QUERIES = {"host", "password", "sni", "peer", "ws"}

def has_all_queries(url):
    parsed = urlparse(url)
    qs_keys = {k.lower() for k in parse_qs(parsed.query).keys()}
    return REQUIRED_QUERIES.issubset(qs_keys)

def process_github_raw_url(url):
    """Download raw GitHub file, decode Base64, return list akun valid"""
    try:
        r = requests.get(url.strip(), timeout=10)
        if r.status_code != 200:
            return []
        decoded_content = base64.b64decode(r.text).decode("utf-8")
        matches = TROJAN_PATTERN.findall(decoded_content)
        return [m for m in matches if has_all_queries(m)]
    except Exception:
        return []

def main():
    valid_accounts = []

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        urls = f.readlines()

    for url in urls:
        accounts = process_github_raw_url(url)
        valid_accounts.extend(accounts)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for account in valid_accounts:
            f.write(account + "\n")

    print(f"Selesai! {len(valid_accounts)} akun Trojan dengan query lengkap disimpan di {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
