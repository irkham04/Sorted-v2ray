#!/usr/bin/env python3
import argparse, base64, requests, time, socket, sys
from urllib.parse import urlparse
import speedtest

def decode_base64_url(url):
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        decoded = base64.b64decode(r.text).decode("utf-8", errors="ignore")
        return decoded.splitlines()
    except Exception as e:
        print(f"[ERROR] Gagal fetch/decode {url}: {e}")
        return []

def is_valid_trojan(line):
    if not line.startswith("trojan://"):
        return False
    if "type=ws" not in line.lower():
        return False
    if "sni=" not in line or "host=" not in line:
        return False
    return True

def run_speedtest():
    try:
        st = speedtest.Speedtest()
        st.get_best_server()
        st.download()
        st.upload()
        server = st.results.server
        ping = st.results.ping
        isp = st.results.client["isp"]
        server_name = server["name"]
        server_loc = f"{server['location']}, {server['country']}"
        return f"# ISP: {isp} | Server: {server_name} ({server_loc}) | Ping: {ping} ms"
    except Exception as e:
        return f"# Speedtest gagal: {e}"

def test_browsing(host, port=443, timeout=5):
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        return "# Browsing: OK"
    except Exception:
        return "# Browsing: FAIL"

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--sorted", default="sorted.txt")
    p.add_argument("--delay", type=int, default=3)
    args = p.parse_args()

    urls = []
    with open(args.input) as f:
        urls = [line.strip() for line in f if line.strip()]

    all_accounts = []
    for url in urls:
        all_accounts.extend(decode_base64_url(url))

    valid_accounts = [acc for acc in all_accounts if is_valid_trojan(acc)]

    # tulis sorted.txt
    with open(args.sorted, "w") as f:
        f.write(f"# Total akun valid: {len(valid_accounts)}\n")
        for acc in valid_accounts:
            f.write(acc + "\n")
    print(f"[INFO] sorted.txt dibuat: {len(valid_accounts)} akun valid")

    # tulis active.txt
    tested_ips = {}
    with open("active.txt", "w") as f:
        f.write("# Akun aktif dengan info speedtest dan browsing (baris info diawali #)\n\n")
        for i, acc in enumerate(valid_accounts, start=1):
            f.write(acc + "\n")
            try:
                ip = acc.split("@")[1].split(":")[0]
            except:
                ip = None

            if ip in tested_ips:
                f.write(tested_ips[ip] + "\n\n")
                continue

            info = run_speedtest()

            # test browsing host dari query sni atau host
            parsed = urlparse(acc)
            qs = dict([p.split("=") for p in parsed.query.split("&") if "=" in p])
            host = qs.get("sni") or qs.get("host") or ip
            browse_info = test_browsing(host)

            full_info = info + "\n" + browse_info
            f.write(full_info + "\n\n")

            if ip:
                tested_ips[ip] = full_info

            print(f"[INFO] Selesai akun {i}, delay {args.delay}s")
            time.sleep(args.delay)

    print("[INFO] active.txt selesai dibuat")

if __name__ == "__main__":
    main()
