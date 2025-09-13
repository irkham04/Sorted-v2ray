#!/usr/bin/env python3
import argparse, re, time, requests, base64
import speedtest  # pip install speedtest-cli

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--sorted", required=True)
    parser.add_argument("--active", required=True)
    parser.add_argument("--only-ws", action="store_true")
    parser.add_argument("--require-sni-host", action="store_true")
    parser.add_argument("--delay", type=int, default=1)
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
        print(f"[ERROR] gagal fetch {url}: {e}")
        return []

def run_speedtest_py(ip, tested_ips, delay=1):
    if ip in tested_ips:
        print(f"# IP {ip} sudah dites, skip speedtest")
        return {"skip": True, "ip": ip}
    tested_ips.add(ip)
    print(f"[INFO] Speedtest untuk IP {ip} ...")
    try:
        st = speedtest.Speedtest()
        st.get_best_server()
        ping = st.results.ping
        isp = getattr(st.results, "client", {}).get("isp", "Unknown ISP")
        print(f"# ISP: {isp} | Ping: {ping} ms")
        return {"isp": isp, "ping": ping, "ip": ip}
    except Exception as e:
        print(f"# Speedtest gagal: {e}")
        return {"error": str(e)}
    finally:
        time.sleep(delay)

def extract_ip(url):
    match = re.search(r"@([\w\.-]+):(\d+)", url)
    return match.group(1) if match else None

def main():
    args = parse_args()
    all_accounts = []

    # fetch & decode
    with open(args.input) as f:
        urls = [l.strip() for l in f if l.strip()]
    for url in urls:
        accounts = fetch_and_decode(url)
        all_accounts.extend(accounts)

    tested_ips = set()
    sorted_lines = []
    active_lines = []

    for idx, acc in enumerate(all_accounts):
        print(f"[INFO] Memproses akun {idx+1}/{len(all_accounts)}")

        if args.only_ws and "type=ws" not in acc.lower():
            continue
        if args.require_sni_host and ("sni=" not in acc.lower() or "host=" not in acc.lower()):
            continue

        ip = extract_ip(acc)
        if not ip:
            continue

        result = run_speedtest_py(ip, tested_ips, delay=args.delay)
        sorted_lines.append(acc)
        if "error" not in result and not result.get("skip", False):
            active_lines.append(acc)
            sorted_lines.append(f"# ISP: {result.get('isp','Unknown')} | Ping: {result.get('ping','?')} ms")

    with open(args.sorted, "w") as f:
        f.write("\n".join(sorted_lines) + "\n")
    with open(args.active, "w") as f:
        f.write("\n".join(active_lines) + "\n")

if __name__ == "__main__":
    main()
