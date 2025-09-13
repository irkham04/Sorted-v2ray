#!/usr/bin/env python3
import base64, requests, argparse, sys
from urllib.parse import urlparse, parse_qs

def fetch_and_decode(url):
    try:
        text = requests.get(url, timeout=20).text.strip()
        try:
            # coba decode base64
            import base64 as b64
            return b64.b64decode(text).decode(errors="ignore")
        except Exception:
            return text
    except Exception as e:
        print(f"[ERROR] gagal fetch {url}: {e}", file=sys.stderr)
        return ""

def parse_trojan(lines, require_sni_host=False):
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
            if require_sni_host and not (has_sni and has_host):
                continue
            good.append(line)
        except Exception:
            continue
    return good

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--require-sni-host", action="store_true")
    args = p.parse_args()

    all_good = []
    total_all = 0
    with open(args.input) as f:
        for url in f:
            url = url.strip()
            if not url: continue
            raw = fetch_and_decode(url)
            lines = raw.splitlines()
            total_all += sum(1 for l in lines if l.strip().startswith("trojan://"))
            all_good.extend(parse_trojan(raw, require_sni_host=args.require_sni_host))

    with open(args.output, "w") as out:
        out.write(f"# Akun aktif: {len(all_good)} dari total: {total_all}\n")
        for line in all_good:
            out.write(line + "\n")

    print(f"Akun aktif: {len(all_good)} dari total: {total_all}")

if __name__ == "__main__":
    main()    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--require-sni-host", action="store_true")
    args = p.parse_args()

    all_good = []
    with open(args.input) as f:
        for url in f:
            url = url.strip()
            if not url: continue
            raw = fetch_and_decode(url)
            all_good.extend(parse_trojan(raw, require_sni_host=args.require_sni_host))

    with open(args.output, "w") as out:
        for line in all_good:
            out.write(line + "\n")

    print(f"Total akun valid: {len(all_good)}")

if __name__ == "__main__":
    main()
