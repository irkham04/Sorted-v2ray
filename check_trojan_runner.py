#!/usr/bin/env python3
import base64
import requests
import argparse
import sys
from urllib.parse import urlparse, parse_qs


def fetch_and_decode(url):
    """Ambil konten dari URL, decode base64 kalau bisa"""
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
    """Filter trojan://, cek sni/host, dan filter hanya ws bila diminta"""
    good = []
    for line in lines.splitlines():
        line = line.strip()
        if not line.startswith("trojan://"):
            continue
        try:
            parts = urlparse(line)
            qs = parse_qs(parts.query)

            # cek type=ws
            if only_ws:
                if not ("type" in qs and qs["type"][0].lower() == "ws"):
                    continue

            # cek sni dan host
            if require_sni_host:
                has_sni = "sni" in qs and qs["sni"][0].strip()
                has_host = "host" in qs and qs["host"][0].strip()
                if not (has_sni and has_host):
                    continue

            good.append(line)
        except Exception:
            continue
    return good


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, help="File berisi daftar URL raw github")
    p.add_argument("--output", required=True, help="File hasil sortir")
    p.add_argument("--require-sni-host", action="store_true", help="Hanya ambil akun yang punya sni dan host")
    p.add_argument("--only-ws", action="store_true", help="Hanya ambil akun dengan network ws")
    args = p.parse_args()

    all_good = []
    total_all = 0

    with open(args.input) as f:
        for url in f:
            url = url.strip()
            if not url:
                continue
            raw = fetch_and_decode(url)
            lines = raw.splitlines()
            total_all += sum(1 for l in lines if l.strip().startswith("trojan://"))
            all_good.extend(parse_trojan(raw, require_sni_host=args.require_sni_host, only_ws=args.only_ws))

    with open(args.output, "w") as out:
        out.write(f"# Akun aktif: {len(all_good)} dari total: {total_all}\n")
        for line in all_good:
            out.write(line + "\n")

    print(f"Akun aktif: {len(all_good)} dari total: {total_all}")


if __name__ == "__main__":
    main()
