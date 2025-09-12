import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import shlex

def parse_accounts_line(line):
    line = line.strip()
    if not line or line.startswith("#"):
        return []
    # Jika link raw
    if line.startswith("http://") or line.startswith("https://"):
        try:
            resp = requests.get(line, timeout=10)
            if resp.status_code == 200:
                content = resp.text.splitlines()
                accounts = [c.strip() for c in content if c.strip()]
                return accounts
        except Exception as e:
            print(f"Gagal akses link: {line} ({e})")
            return []
    else:
        return [line]

def test_account(account_url):
    """
    Jalankan trojan-go headless untuk cek login.
    Memanggil subprocess tanpa shell=True.
    """
    cmd_list = shlex.split(f"trojan-go client -s {account_url} -p 0 --headless")
    try:
        result = subprocess.run(cmd_list, capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
            return account_url
    except Exception as e:
        print(f"Error {account_url} -> {e}")
    return None

def main():
    input_file = "accounts.txt"
    output_file = "results.txt"
    accounts = []

    # Load akun dari file
    with open(input_file, "r") as f:
        lines = f.read().splitlines()
        for line in lines:
            accounts.extend(parse_accounts_line(line))

    active_accounts = []

    # Tes paralel (max 5 akun sekaligus)
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_acc = {executor.submit(test_account, acc): acc for acc in accounts}
        for future in as_completed(future_to_acc):
            res = future.result()
            if res:
                print(res)
                active_accounts.append(res)

    # Simpan hanya akun aktif
    with open(output_file, "w") as f:
        for acc in active_accounts:
            f.write(acc + "\n")

    print("Selesai! Hanya akun aktif tersimpan di results.txt")

if __name__ == "__main__":
    main()
