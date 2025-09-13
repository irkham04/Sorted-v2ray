import base64
import requests

# URL raw GitHub yang berisi akun Trojan dalam format Base64
GITHUB_URL = "https://raw.githubusercontent.com/Epodonios/v2ray-configs/refs/heads/main/Splitted-By-Protocol/trojan.txt"
OUTPUT_FILE = "output.txt"

def main():
    try:
        response = requests.get(GITHUB_URL, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"Gagal mengambil file: {e}")
        return

    lines = response.text.splitlines()
    decoded_accounts = []

    for idx, line in enumerate(lines, start=1):
        try:
            decoded = base64.b64decode(line.strip()).decode("utf-8")
            decoded_accounts.append(decoded)
        except Exception as e:
            print(f"Gagal decode baris {idx}: {e}")

    # Tulis semua hasil decode ke output.txt
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for account in decoded_accounts:
            f.write(account + "\n")

    print(f"Selesai! {len(decoded_accounts)} akun Trojan berhasil didecode dan disimpan di {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
