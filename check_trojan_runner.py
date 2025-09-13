import base64
import re
import requests
import argparse
import subprocess

def decode_base64_lines(file_path):
    """Decode base64 lines from file and return as list of strings."""
    decoded = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                decoded_line = base64.b64decode(line).decode("utf-8", errors="ignore")
                decoded.extend(decoded_line.splitlines())
            except Exception:
                continue
    return decoded

def parse_trojan_accounts(lines):
    """Ambil hanya akun trojan:// dari lines"""
    return [l.strip() for l in lines if l.strip().startswith("trojan://")]

def filter_trojan_ws(accounts):
    """Sortir hanya akun Trojan WS (buang TCP dan yang tidak lengkap)."""
    result = []
    for acc in accounts:
        if not acc.startswith("trojan://"):
            continue
        if "type=ws" not in acc:
            continue
        if "sni=" not in acc or "host=" not in acc:
            continue
        result.append(acc)
    return result

def check_account_active(url):
    """Cek akun trojan aktif dengan request HTTP dummy (head)."""
    try:
        if "@" in url:
            server = url.split("@")[1].split("#")[0]
            if ":" in server:
                server = server.split(":")[0]
            test_url = f"https://{server}"
            r = requests.head(test_url, timeout=5, verify=False)
            return r.status_code < 500
    except Exception:
        return False
    return False

def run_speedtest():
    """Jalankan speedtest Ookla CLI dan ambil hasil (server, ping, download, upload)."""
    try:
        result = subprocess.run(
            ["./speedtest", "--format=json"],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        return None
    return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="File input base64")
    parser.add_argument("--sorted", default="sorted.txt", help="File output sorted WS accounts")
    parser.add_argument("--active", default="active.txt", help="File output active WS accounts")
    args = parser.parse_args()

    # decode file base64
    lines = decode_base64_lines(args.input)
    trojan_accounts = parse_trojan_accounts(lines)

    # filter WS only
    sorted_accounts = filter_trojan_ws(trojan_accounts)

    with open(args.sorted, "w", encoding="utf-8") as f:
        f.write("\n".join(sorted_accounts))

    # cek aktif + speedtest
    active_accounts = []
    for acc in sorted_accounts:
        if check_account_active(acc):
            speedtest_result = run_speedtest()
            if speedtest_result:
                active_accounts.append(f"{acc}\n# Speedtest: {speedtest_result}\n")
            else:
                active_accounts.append(acc)

    with open(args.active, "w", encoding="utf-8") as f:
        f.write("\n".join(active_accounts))

    print(f"Total akun valid (Trojan WS only): {len(sorted_accounts)}")
    print(f"Akun aktif: {len(active_accounts)} dari total {len(sorted_accounts)}")

if __name__ == "__main__":
    main()
