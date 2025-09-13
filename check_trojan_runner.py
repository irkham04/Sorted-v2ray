import base64
import re
import requests
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse, parse_qs

# URL raw GitHub berisi akun Trojan Base64
github_raw_url = "https://raw.githubusercontent.com/user/repo/branch/input.txt"

# Regex untuk mendeteksi Trojan WS
trojan_ws_pattern = re.compile(
    r"trojan://[^@\s]+@[^:\s]+:\d+\?[^ \n]+"
)

def decode_and_extract(line):
    """Decode Base64, ekstrak Trojan WS beserta path (wf)"""
    accounts = []
    try:
        decoded_bytes = base64.b64decode(line.strip())
        decoded_str = decoded_bytes.decode("utf-8")
        matches = trojan_ws_pattern.findall(decoded_str)
        for m in matches:
            parsed = urlparse(m)
            qs = parse_qs(parsed.query)
            # Ambil path ws jika ada, misal ?type=ws&path=/wf
            ws_path = qs.get("path", [""])[0]
            # Simpan lengkap dengan path di output
            accounts.append(f"{m} | path: {ws_path}")
    except Exception:
        pass
    return accounts

def main():
    # Ambil konten dari GitHub
    response = requests.get(github_raw_url)
    if response.status_code != 200:
        print(f"Gagal mengambil file dari GitHub: {response.status_code}")
        return

    lines = response.text.splitlines()
    valid_accounts = []

    # Multi-threaded
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(decode_and_extract, lines)

    for match_list in results:
        if match_list:
            valid_accounts.extend(match_list)

    # Simpan hasil ke output.txt
    with open("output.txt", "w", encoding="utf-8") as f:
        for account in valid_accounts:
            f.write(account + "\n")

    print(f"Proses selesai! {len(valid_accounts)} akun WS ditemukan dan disimpan di output.txt")

if __name__ == "__main__":
    main()
