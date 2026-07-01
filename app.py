#!/usr/bin/env python3
"""
出席管理システム Web アプリ
ボタンを押してから PaSoRi に NTAG215 カードをタッチすると
Google スプレッドシートに打刻します。
"""
import os
import sys
import time
from datetime import datetime
from binascii import hexlify

from flask import Flask, jsonify, render_template, request
from smartcard.System import readers

import gspread
from google.oauth2.service_account import Credentials

# ── .env 読み込み ──────────────────────────────────────
def _load_dotenv(path=None):
    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    if key.strip() not in os.environ:
                        os.environ[key.strip()] = value.strip()

_load_dotenv()

# ── 設定 ─────────────────────────────────────────────────
SPREADSHEET_KEY = os.environ.get("SPREADSHEET_KEY", "your-spreadsheet-key")
CREDENTIALS_FILE = os.environ.get("CREDENTIALS_FILE", "credentials/your-credentials-file.json")
READER_NAME = "PaSoRi"
CARD_TIMEOUT = 30  # カード待ちタイムアウト（秒）
# ────────────────────────────────────────────────────────

SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

app = Flask(__name__)


def find_pasori():
    for r in readers():
        if READER_NAME in r.name:
            return r
    return None


def read_card_uid(reader, timeout=CARD_TIMEOUT):
    """カードを待って UID を返す"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            conn = reader.createConnection()
            conn.connect()
            resp, sw1, sw2 = conn.transmit([0xFF, 0xCA, 0x00, 0x00, 0x00])
            conn.disconnect()
            if sw1 == 0x90 and sw2 == 0x00:
                return hexlify(bytes(resp)).decode().upper()
        except Exception:
            pass
        time.sleep(0.3)
    return None


def get_sheets_client():
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPE)
    return gspread.authorize(creds)


def find_member(client, card_id):
    ws = client.open_by_key(SPREADSHEET_KEY).worksheet("名簿")
    for r in ws.get_all_records():
        if str(r.get("カードID", "")).strip() == card_id:
            return r
    return None


def record(client, member, record_type):
    """record_type: 'start' or 'end'"""
    ws = client.open_by_key(SPREADSHEET_KEY).worksheet("出席")
    now = datetime.now()
    name = member.get("氏名", "")
    date_str = now.strftime("%Y/%m/%d")
    time_str = now.strftime("%H:%M")

    ws.append_row([date_str, name,
                   time_str if record_type == "start" else "",
                   time_str if record_type == "end" else ""])


# ── ルート ─────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/read", methods=["POST"])
def api_read():
    data = request.get_json()
    record_type = data.get("type")  # "start" or "end"

    if record_type not in ("start", "end"):
        return jsonify({"ok": False, "error": "type は start または end を指定してください"}), 400

    reader = find_pasori()
    if not reader:
        return jsonify({"ok": False, "error": "PaSoRi が見つかりません"}), 500

    # カードを待つ
    uid = read_card_uid(reader, timeout=CARD_TIMEOUT)
    if not uid:
        return jsonify({"ok": False, "error": f"タイムアウト（{CARD_TIMEOUT}秒以内にカードがタッチされませんでした）"}), 408

    # 名簿検索
    try:
        client = get_sheets_client()
        member = find_member(client, uid)
    except Exception as e:
        return jsonify({"ok": False, "error": f"スプレッドシート接続エラー: {e}"}), 500

    if not member:
        return jsonify({
            "ok": False,
            "uid": uid,
            "error": f"未登録のカードです（UID: {uid}）。名簿に登録してください。"
        }), 404

    # 打刻
    try:
        record(client, member, record_type)
    except Exception as e:
        return jsonify({"ok": False, "error": f"打刻エラー: {e}"}), 500

    label = "出席" if record_type == "start" else "退勤"
    now = datetime.now().strftime("%H:%M")
    return jsonify({
        "ok": True,
        "uid": uid,
        "name": member.get("氏名", ""),
        "type": label,
        "time": now,
    })


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
