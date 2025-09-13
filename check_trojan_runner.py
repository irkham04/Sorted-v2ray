name: Sort Trojan WS

on:
  workflow_dispatch:

jobs:
  sort-trojan:
    runs-on: ubuntu-latest

    steps:
    - name: Checkout repository
      uses: actions/checkout@v5

    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: "3.11"

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install requests

    - name: Run Trojan WS Sorter
      run: |
        python check_trojan_runner.py

    - name: Upload output.txt as artifact
      uses: actions/upload-artifact@v4
      with:
        name: trojan-output
        path: output.txt
