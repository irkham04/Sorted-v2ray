import os
import base64
import subprocess
from urllib.parse import urlparse, parse_qs

INPUT_FILE = "input.txt"
OUTPUT_FILE = "results/sni.txt"
V2RAY_BIN = "./v2ray/v2ray"  # path v2ray binary di workflow

os.makedirs("results", exist_ok=True)

def fetch_accounts():
    accounts = []
    with open(INPUT_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                decoded = base64.b64decode(line).decode("utf-8")
            except Exception:
                decoded = line
            accounts.extend([l.strip() for l in decoded.splitlines() if l.strip()])
    return accounts

def has_complete_query(url):
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    required_keys = ["type", "host", "path"]
    peer_present = "peer" in qs or "sni" in qs
    return all(k in qs for k in required_keys) and peer_present

def test_with_v2ray(account):
    # Buat config sementara per akun
    config = {
        "inbounds": [],
        "outbounds": [
            {
                "protocol": "trojan",
                "settings": {
                    "servers": [
                        {
                            "address": urlparse(account).hostname,
                            "port": urlparse(account).port or 443,
                            "password": urlparse(account).username,
                            "flow": "",
                        }
                    ]
                },
                "streamSettings": {
                    "network": "ws",
                    "wsSettings": {
                        "path": parse_qs(urlparse(account).query).get("path", ["/"])[0],
                        "headers": {
                            "Host": parse_qs(urlparse(account).query).get("host", [urlparse(account).hostname])[0]
                        }
                    },
                    "security": "tls"
                }
            }
        ]
    }

    import json, tempfile
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as tf:
        json.dump(config, tf)
        tf_path = tf.name

    try:
        # Jalankan v2ray untuk test koneksi singkat
        result = subprocess.run([V2RAY_BIN, "-test", "-config", tf_path],
                                capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
            return True
    except subprocess.TimeoutExpired:
        return False
    finally:
        os.remove(tf_path)

    return False

def main():
    accounts = fetch_accounts()
    filtered = [a for a in accounts if has_complete_query(a)]
    active = []

    for i, acc in enumerate(filtered, 1):
        print(f"[{i}/{len(filtered)}] Testing account...", flush=True)
        if test_with_v2ray(acc):
            print("AKTIF ✅", flush=True)
            active.append(acc)
        else:
            print("GAGAL ❌", flush=True)

    with open(OUTPUT_FILE, "w") as f:
        for acc in active:
            f.write(acc + "\n")

    print(f"\nHasil akhir: {len(active)} akun aktif disimpan di {OUTPUT_FILE}", flush=True)

if __name__ == "__main__":
    main()
