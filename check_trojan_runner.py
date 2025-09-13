import re
from urllib.parse import urlparse, parse_qs

# File input dan output
input_file = "input.txt"
output_file = "output.txt"

# Regex untuk mendeteksi Trojan WS
trojan_pattern = re.compile(r"trojan://[^@\s]+@[^:\s]+:\d+\?[^ \n]+")

# Daftar query yang wajib ada
required_queries = {"host", "password", "sni", "peer", "ws"}  # ws bisa juga ws-host

def has_all_queries(url):
    """Cek apakah Trojan memiliki semua query wajib"""
    parsed = urlparse(url)
    qs = {k.lower() for k in parse_qs(parsed.query).keys()}
    return required_queries.issubset(qs)

def main():
    valid_accounts = []

    with open(input_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()
        matches = trojan_pattern.findall(line)
        for m in matches:
            if has_all_queries(m):
                valid_accounts.append(m)

    with open(output_file, "w", encoding="utf-8") as f:
        for account in valid_accounts:
            f.write(account + "\n")

    print(f"Selesai! {len(valid_accounts)} akun Trojan dengan query lengkap disimpan di {output_file}")

if __name__ == "__main__":
    main()
