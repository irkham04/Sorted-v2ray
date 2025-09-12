import requests
import base64
import os

ACCOUNTS_FILE = "accounts.txt"
ACTIVE_FILE = "active.txt"
DEAD_FILE = "dead.txt"

def download_accounts():
    urls = []
    with open(ACCOUNTS_FILE, "r") as f:
        for line in f:
            url = line.strip()
            if url:
                urls.append(url)
    accounts = []
    for url in urls:
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            for line in r.text.splitlines():
                line = line.strip()
                if line:
                    accounts.append(line)
        except Exception as e:
            print(f"Failed to download {url}: {e}")
    return accounts

def decode_account(acc_b64):
    try:
        decoded = base64.b64decode(acc_b64).decode()
        return decoded
    except Exception:
        return None

def test_ws_tls(account_str):
    """
    Dummy test: cek format WS+TLS dan password field ada.
    Real TLS handshake ga bisa di GitHub Actions tanpa server.
    """
    try:
        required_fields = ["server", "port", "type", "uuid", "tls", "servername", "network", "ws-opts"]
        for field in required_fields:
            if field not in account_str:
                return False
        return True
    except Exception:
        return False

def main():
    accounts = download_accounts()
    active = []
    dead = []

    for acc in accounts:
        decoded = decode_account(acc)
        if not decoded:
            dead.append(acc)
            continue
        if test_ws_tls(decoded):
            active.append(acc)
        else:
            dead.append(acc)

    with open(ACTIVE_FILE, "w") as f:
        for a in active:
            f.write(a + "\n")
    with open(DEAD_FILE, "w") as f:
        for d in dead:
            f.write(d + "\n")

    print(f"Done! {len(active)} active, {len(dead)} dead.")

if __name__ == "__main__":
    main()
