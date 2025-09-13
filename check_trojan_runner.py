#!/usr/bin/env python3
import base64, re, requests, argparse, sys
from urllib.parse import urlparse, parse_qs

def fetch_and_decode(url):
    try:
        text = requests.get(url, timeout=20).text.strip()
        try:
            return base64.b64decode(text).decode(errors="ignore")
        except Exception:
            return text
    except Exception as e:
        print(f"[ERROR] gagal fetch {url}: {e}", file=sys.stderr)
        return ""

def parse_trojan(lines, require_sni_host=False, only_ws=False):
    good = []
    for line in lines.splitlines():
        line = line.strip()
        if not line.startswith("trojan://"):
            continue
        try:
            parts = urlparse(line)
            qs = parse_qs(parts.query)
            has_sni = 'sni' in qs and qs['sni'][0].strip()
            has_host = 'host' in qs and qs['host'][0].strip()
            type_is_ws = (qs.get("type", [""])[0] == "ws")
            if require_sni_host and not (has_sni and has_host):
                continue
            if only_ws and not type_is_ws:
                continue
            good.append(line)
        except Exception:
            continue
    return good

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--active", required=True)
    p.add_argument("--require-sni-host", action="store_true")
    p.add_argument("--only-ws", action="store_true")
    args = p.parse_args()

    total, all_good = 0, []
    with open(args.input) as f:
        for url in f:
            url = url.strip()
            if not url: continue
            raw = fetch_and_decode(url)
            total += raw.count("trojan://")
            all_good.extend(parse_trojan(raw,
                                         require_sni_host=args.require_sni_host,
                                         only_ws=args.only_ws))

    with open(args.output, "w") as out:
        out.write(f"# Akun aktif: {len(all_good)} dari total: {total}\n")
        for line in all_good:
            out.write(line + "\n")

    with open(args.active, "w") as act:
        act.write("# Hasil speedtest server Ookla\n")

    print(f"Total akun valid: {len(all_good)} dari {total}")

if __name__ == "__main__":
    main()
