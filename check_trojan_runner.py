#!/usr/bin/env python3
import base64, requests, argparse, sys, subprocess, json, time, os, signal
from urllib.parse import urlparse, parse_qs
import tempfile


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
            if only_ws:
                if not ("type" in qs and qs["type"][0].lower() == "ws"):
                    continue
            if require_sni_host:
                has_sni = "sni" in qs and qs["sni"][0].strip()
                has_host = "host" in qs and qs["host"][0].strip()
                if not (has_sni and has_host):
                    continue
            good.append(line)
        except Exception:
            continue
    return good


def make_xray_config(uri, port=1080):
    return {
        "log": {"loglevel": "warning"},
        "inbounds": [{
            "listen": "127.0.0.1",
            "port": port,
            "protocol": "socks",
            "settings": {"udp": False}
        }],
        "outbounds": [{
            "protocol": "trojan",
            "settings": {"servers": [{
                "address": urlparse(uri).hostname,
                "port": int(urlparse(uri).port or 443),
                "password": urlparse(uri).username or "",
                "flow": ""
            }]},
            "streamSettings": {
                "network": "ws",
                "security": "tls",
                "tlsSettings": {"serverName": parse_qs(urlparse(uri).query).get("sni", [""])[0]},
                "wsSettings": {"path": parse_qs(urlparse(uri).query).get("path", ["/"])[0],
                               "headers": {"Host": parse_qs(urlparse(uri).query).get("host", [""])[0]}}
            }
        }]
    }


def run_xray(config):
    cfg_file = tempfile.NamedTemporaryFile("w", delete=False)
    import json as js
    cfg_file.write(js.dumps(config))
    cfg_file.close()
    proc = subprocess.Popen(["xray", "-c", cfg_file.name])
    time.sleep(3)
    return proc, cfg_file.name


def stop_xray(proc, cfg_file):
    try:
        os.kill(proc.pid, signal.SIGTERM)
    except Exception:
        pass
    try:
        os.remove(cfg_file)
    except Exception:
        pass


def test_speedtest(proxy="socks5://127.0.0.1:1080"):
    env = os.environ.copy()
    env["ALL_PROXY"] = proxy
    try:
        out = subprocess.check_output(
            ["speedtest", "--servers", "--format=json"],
            env=env,
            timeout=15
        )
        data = json.loads(out)
        if "servers" in data and data["servers"]:
            return data["servers"][0]
    except Exception:
        return None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--require-sni-host", action="store_true")
    p.add_argument("--only-ws", action="store_true")
    p.add_argument("--check-active", action="store_true", help="Tes server dengan speedtest")
    args = p.parse_args()

    all_good, total_all = [], 0
    with open(args.input) as f:
        for url in f:
            url = url.strip()
            if not url: continue
            raw = fetch_and_decode(url)
            lines = raw.splitlines()
            total_all += sum(1 for l in lines if l.strip().startswith("trojan://"))
            all_good.extend(parse_trojan(raw, require_sni_host=args.require_sni_host, only_ws=args.only_ws))

    with open(args.output, "w") as out:
        out.write(f"# Akun aktif: {len(all_good)} dari total: {total_all}\n")
        for line in all_good:
            out.write(line + "\n")

    print(f"Akun aktif: {len(all_good)} dari total: {total_all}")

    if args.check_active:
        active = []
        for uri in all_good:
            cfg = make_xray_config(uri)
            proc, cfg_file = run_xray(cfg)
            server = test_speedtest()
            stop_xray(proc, cfg_file)
            if server:
                active.append((uri, server))
                print(f"[OK] {uri[:40]}... → {server['name']}")
            else:
                print(f"[FAIL] {uri[:40]}...")

        with open("active.txt", "w") as out:
            out.write(f"# Total aktif (speedtest OK): {len(active)} dari {len(all_good)}\n")
            for uri, server in active:
                out.write(f"{uri}  # {server['name']}\n")


if __name__ == "__main__":
    main()
