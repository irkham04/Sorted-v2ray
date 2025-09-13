import base64
import requests
import argparse
import subprocess
import json

def decode_base64_url(url):
    """Ambil raw base64 dari URL & decode jadi string akun Trojan"""
    try:
        raw = requests.get(url.strip()).text.strip().splitlines()
        decoded = []
        for line in raw:
            try:
                decoded_line = base64.b64decode(line).decode("utf-8").strip()
                decoded.append(decoded_line)
            except Exception:
                continue
        return decoded
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return []

def filter_trojan_ws(accounts):
    """Sortir hanya akun trojan WS dengan SNI & host"""
    result = []
    for acc in accounts:
        if acc.startswith("trojan://") and "type=ws" in acc and "sni=" in acc and "host=" in acc:
            result.append(acc)
    return result

def test_account_with_xray(account):
    """TODO: Tes koneksi pakai Xray. Sekarang dummy return True"""
    return True

def run_speedtest():
    """Jalankan Ookla Speedtest CLI format JSON"""
    try:
        result = subprocess.check_output(
            ["speedtest", "--accept-license", "--accept-gdpr", "-f", "json"],
            text=True
        )
        return result
    except Exception as e:
        print(f"Speedtest error: {e}")
        return None

def parse_speedtest(json_data):
    """Ambil info server dari hasil speedtest JSON"""
    try:
        data = json.loads(json_data)
        server = data.get("server", {})
        return f'Server: ID={server.get("id")} | Name="{server.get("name")}" | Location="{server.get("location")}" | Sponsor="{server.get("sponsor")}"'
    except Exception:
        return "Server: Unknown"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--only-ws", action="store_true")
    parser.add_argument("--require-sni-host", action="store_true")
    parser.add_argument("--check-active", action="store_true")
    args = parser.parse_args()

    urls = open(args.input).read().splitlines()
    all_accounts, sorted_accounts, active_accounts = [], [], []

    for url in urls:
        decoded = decode_base64_url(url)
        all_accounts.extend(decoded)

    # filter trojan
    for acc in all_accounts:
        if acc.startswith("trojan://"):
            if args.only_ws and "type=ws" not in acc:
                continue
            if args.require_sni_host and not ("sni=" in acc and "host=" in acc):
                continue
            sorted_accounts.append(acc)

    # simpan hasil sortir
    with open(args.output, "w") as f:
        f.write(f"# Akun aktif: 0 dari total: {len(all_accounts)}\n")
        f.write("\n".join(sorted_accounts))

    # cek aktif + speedtest
    if args.check_active:
        with open("active.txt", "w") as f:
            for acc in sorted_accounts:
                if test_account_with_xray(acc):
                    spd = run_speedtest()
                    server_info = parse_speedtest(spd) if spd else "Server: Unknown"
                    f.write(acc + "\n" + server_info + "\n\n")
                    active_accounts.append(acc)

        # update header sorted.txt
        with open(args.output, "r+") as f:
            lines = f.readlines()
            lines[0] = f"# Akun aktif: {len(active_accounts)} dari total: {len(all_accounts)}\n"
            f.seek(0)
            f.writelines(lines)

if __name__ == "__main__":
    main()
