import re
import requests
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

# ========================
# Helper functions
# ========================

def parse_trojan(url):
    """
    Parse trojan://password@host:port
    """
    pattern = r"trojan://(.+)@(.+):(\d+)"
    match = re.match(pattern, url)
    if match:
        return {"password": match.group(1), "host": match.group(2), "port": int(match.group(3)), "url": url}
    return None

def test_account(account):
    """
    Tes koneksi Trojan menggunakan openssl.
    Hanya kembalikan URL jika akun aktif.
    """
    host = account["host"]
    port = account["port"]
    cmd = f"echo | openssl s_client -connect {host}:{port} -crlf"
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        if "CONNECTED" in result.stdout or "SSL handshake" in result.stdout:
            return account["url"]  # Akun aktif
    except:
        pass
    return None  # Akun mati

# ========================
# Load accounts from file
# ========================

def load_accounts(file_path):
    """
    Baca accounts.txt
    - Sub-URL langsung
    - Link yang berisi banyak akun
    """
    accounts = []
    with open(file_path, "r") as f:
        lines = f.read().splitlines()

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Jika line adalah link
        if line.startswith("http://") or line.startswith("https://"):
            try:
                resp = requests.get(line, timeout=10)
                if resp.status_code == 200:
                    content = resp.text.splitlines()
                    for subline in content:
                        acc = parse_trojan(subline.strip())
                        if acc:
                            accounts.append(acc)
            except Exception as e:
                print(f"Gagal akses link: {line} ({e})")
        else:
            acc = parse_trojan(line)
            if acc:
                accounts.append(acc)
    return accounts

# ========================
# Main
# ========================

def main():
    input_file = "accounts.txt"
    output_file = "results.txt"

    accounts = load_accounts(input_file)
    active_accounts = []

    # Tes paralel
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_account = {executor.submit(test_account, acc): acc for acc in accounts}
        for future in as_completed(future_to_account):
            res = future.result()
            if res:
                print(res)
                active_accounts.append(res)

    # Simpan hanya akun aktif ke results.txt
    with open(output_file, "w") as f:
        for line in active_accounts:
            f.write(line + "\n")

    print(f"\nSelesai! Hanya akun aktif tersimpan di {output_file}")

if __name__ == "__main__":
    main()
