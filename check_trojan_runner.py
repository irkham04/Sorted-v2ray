#!/usr/bin/env python3
import argparse, re, time, requests, base64, sys
import speedtest  # pip install speedtest-cli

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--sorted", required=True)
    parser.add_argument("--active", required=True)
    parser.add_argument("--only-ws", action="store_true")
    parser.add_argument("--require-sni-host", action="store_true")
    parser.add_argument("--delay", type=int, default=1)
    parser.add_argument("--timeout", type=int, default=10)
    return parser.parse_args()

def fetch_and_decode(url):
    try:
        r = requests.get(url.strip(), timeout=20)
        r.raise_for_status()
        content = r.text.strip()
        try:
            decoded = base64.b64decode(content).decode(errors="ignore")
            return [l.strip() for l in decoded.splitlines() if l.strip()]
        except Exception:
            return [l.strip() for l in content.splitlines() if l.strip()]
    except Exception as e:
        print(f"[ERROR] gagal fetch {url}: {e}", file=sys.stderr)
        return []

def extract_ip(url):
    match = re.search(r"@([\w\.-]+):(\d+)", url)
    return match.group(1) if match else None

def run_speedtest_py(ip, timeout=10, delay=1):
    print(f"[INFO] Speedtest untuk IP {ip} ...")
    try:
        st = speedtest.Speedtest()
        servers = st.get_servers([])
        best = st.get_best_server(servers)
        ping = best['latency']
        isp = st.results.client.get('isp', 'Unknown ISP')
        print(f"# ISP: {isp} | Ping: {ping} ms")
        return {"isp": isp, "ping": ping, "ip": ip}
    except Exception as e:
        print(f"# Speedtest gagal: {e}")
        return {"error": str(e), "isp": "Unknown", "ping": "?", "ip": ip}
    finally:
        time.sleep(delay)

def main():
    args = parse_args()
    all_accounts = []

    # fetch & decode
    with open(args.input) as f:
        urls = [l.strip() for l in f if l.strip()]
    for url in urls:
        accounts = fetch_and_decode(url)
        all_accounts.extend(accounts)

    # filter akun dulu agar counter [INFO] akurat
    filtered_accounts = []
    for acc in all_accounts:
        if args.only_ws and "type=ws" not in acc.lower():
            continue
        if args.require_sni_host and ("sni=" not in acc.lower() or "host=" not in acc.lower()):
            continue
        filtered_accounts.append(acc)

    sorted_lines = []
    active_lines = []

    for idx, acc in enumerate(filtered_accounts):
        print(f"[INFO] Memproses akun {idx+1}/{len(filtered_accounts)}")
        ip = extract_ip(acc)
        if not ip:
            continue

        # run speedtest
        result = run_speedtest_py(ip, timeout=args.timeout, delay=args.delay)

        # simpan di sorted.txt
        sorted_lines.append(acc)
        if "error" in result:
            sorted_lines.append(f"# Speedtest gagal: {result['error']}")
        else:
            sorted_lines.append(f"# ISP: {result.get('isp','Unknown')} | Ping: {result.get('ping','?')} ms")

        # simpan di active.txt hanya jika speedtest sukses
        if "error" not in result:
            info = f"{acc}\n# ISP: {result.get('isp','Unknown')} | Ping: {result.get('ping','?')} ms"
            active_lines.append(info)

    with open(args.sorted, "w") as f:
        f.write("\n".join(sorted_lines) + "\n")
    with open(args.active, "w") as f:
        f.write("\n".join(active_lines) + "\n")

if __name__ == "__main__":
    main()
