#!/usr/bin/env python3
"""
出席管理システム Web アプリ
"""
import os
import sys
import time
import threading
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
                    k, _, v = line.partition("=")
                    if k.strip() not in os.environ:
                        os.environ[k.strip()] = v.strip()

_load_dotenv()

# ── 設定 ─────────────────────────────────────────────────
SPREADSHEET_KEY = os.environ.get("SPREADSHEET_KEY", "your-spreadsheet-key")
CREDENTIALS_FILE = os.environ.get("CREDENTIALS_FILE", "credentials/your-credentials-file.json")
READER_NAME = "PaSoRi"
CARD_TIMEOUT = 30
# ────────────────────────────────────────────────────────

SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

app = Flask(__name__)
cancel_event = threading.Event()


def find_pasori():
    for r in readers():
        if READER_NAME in r.name:
            return r
    return None


def read_card_uid(reader, timeout=CARD_TIMEOUT):
    """カードを待って UID を返す。キャンセル可能。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if cancel_event.is_set():
            cancel_event.clear()
            return None
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


def load_all_members(client):
    ws = client.open_by_key(SPREADSHEET_KEY).worksheet("名簿")
    records = ws.get_all_records()
    return {str(r.get("カードID", "")).strip(): r
            for r in records if r.get("カードID", "")}


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


def register_card_to_sheet(client, card_id, name):
    """カードUID を名簿に登録"""
    ws = client.open_by_key(SPREADSHEET_KEY).worksheet("名簿")
    records = ws.get_all_records()

    # 既存の氏名を検索
    for i, r in enumerate(records):
        if r.get("氏名", "") == name:
            ws.update_cell(i + 2, 10, card_id)  # J列: カードID
            return True

    # 新規追加
    ws.update_cell(len(records) + 2, 2, name)
    ws.update_cell(len(records) + 2, 10, card_id)
    return True


def get_history(client, limit=50):
    """出席シートの履歴を取得"""
    ws = client.open_by_key(SPREADSHEET_KEY).worksheet("出席")
    records = ws.get_all_records()
    records.reverse()  # 新しい順
    return records[:limit]


# ── API ────────────────────────────────────────────────

@app.route("/api/cancel", methods=["POST"])
def api_cancel():
    cancel_event.set()
    return jsonify({"ok": True})


@app.route("/api/read", methods=["POST"])
def api_read():
    data = request.get_json()
    record_type = data.get("type")  # "start" | "end" | "check"

    if record_type not in ("start", "end", "check"):
        return jsonify({"ok": False, "error": "type が不正です"}), 400

    reader = find_pasori()
    if not reader:
        return jsonify({"ok": False, "error": "PaSoRi が見つかりません"}), 500

    cancel_event.clear()
    uid = read_card_uid(reader, timeout=CARD_TIMEOUT)

    if uid is None:
        return jsonify({"ok": False, "cancelled": cancel_event.is_set(),
                        "error": "キャンセルされました" if cancel_event.is_set()
                        else f"タイムアウト（{CARD_TIMEOUT}秒）"}), 408

    # UID 確認モード
    if record_type == "check":
        try:
            client = get_sheets_client()
            member = find_member(client, uid)
        except Exception as e:
            return jsonify({"ok": False, "error": f"スプレッドシートエラー: {e}"}), 500

        if member:
            return jsonify({"ok": True, "uid": uid, "name": member.get("氏名", ""),
                            "registered": True})
        else:
            return jsonify({"ok": True, "uid": uid, "registered": False})

    # 出席/退勤モード
    try:
        client = get_sheets_client()
        member = find_member(client, uid)
    except Exception as e:
        return jsonify({"ok": False, "error": f"スプレッドシートエラー: {e}"}), 500

    if not member:
        return jsonify({"ok": False, "uid": uid, "unregistered": True,
                        "error": "未登録のカードです"}), 404

    try:
        record(client, member, record_type)
    except Exception as e:
        return jsonify({"ok": False, "error": f"打刻エラー: {e}"}), 500

    label = {"start": "出席", "end": "退勤"}[record_type]
    now = datetime.now().strftime("%H:%M")
    return jsonify({"ok": True, "uid": uid, "name": member.get("氏名", ""),
                    "type": label, "time": now})


@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.get_json()
    uid = data.get("uid")
    name = data.get("name", "").strip()

    if not uid or not name:
        return jsonify({"ok": False, "error": "UID と氏名が必要です"}), 400

    try:
        client = get_sheets_client()
        register_card_to_sheet(client, uid, name)
        return jsonify({"ok": True, "name": name, "uid": uid})
    except Exception as e:
        return jsonify({"ok": False, "error": f"登録エラー: {e}"}), 500


@app.route("/api/history")
def api_history():
    try:
        client = get_sheets_client()
        records = get_history(client)
        return jsonify({"ok": True, "records": records})
    except Exception as e:
        return jsonify({"ok": False, "error": f"取得エラー: {e}"}), 500


# ── ページ ─────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/history")
def history_page():
    return render_template("history.html")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
