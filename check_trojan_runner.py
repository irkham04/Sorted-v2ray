import base64
import requests
from urllib.parse import urlparse, parse_qs
import re

# URL raw GitHub yang berisi akun Trojan dalam format Base64
GITHUB_URL = "https://raw.githubusercontent.com/Epodonios/v2ray-configs/refs/heads/main/Splitted-By-Protocol/trojan.txt"
OUTPUT_FILE = "output.txt"

# Regex untuk mendeteksi Trojan WS
TROJAN_PATTERN = re.compile(r"trojan://[^@\s]+@[^:\s]+:\d+\?[^ \n]+")

# Query wajib ada
REQUIRED_QUERIES = {"host", "password", "sni", "peer", "ws"}

def has_all_queries(url):
    parsed = urlparse(url)
    qs_keys = {k.lower() for k in parse_qs(parsed.query).keys()}
    return REQUIRED_QUERIES.issubset(qs_keys)

def main():
    valid_count = 0

    with requests.get(GITHUB_URL, stream=True) as r:
        r.raise_for_status()
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            for line in r.iter_lines(decode_unicode=True):
                if not line.strip():
                    continue
                try:
                    decoded = base64.b64decode(line.strip()).decode("utf-8")
                    matches = TROJAN_PATTERN.findall(decoded)
                    for m in matches:
                        if has_all_queries(m):
                            f.write(m + "\n")
                            valid_count += 1
                except Exception:
                    continue

    print(f"Jumlah akun Trojan WS: {valid_count}")

if __name__ == "__main__":
    main()
