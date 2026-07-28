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
        with open(path, encoding="utf-8") as f:
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


# 名簿: A番号 B氏名 … J直近の出席日 / KカードID（アプリが追加）
MEIBO_NAME_COL = 2       # B
MEIBO_CARD_ID_COL = 11   # K
CARD_ID_HEADER = "カードID"


def get_sheets_client():
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPE)
    return gspread.authorize(creds)


def ensure_card_id_column(ws):
    """名簿にカードID列（K列）が無ければヘッダーを追加する。"""
    header = ws.row_values(1)
    if len(header) >= MEIBO_CARD_ID_COL and header[MEIBO_CARD_ID_COL - 1] == CARD_ID_HEADER:
        return
    ws.update_cell(1, MEIBO_CARD_ID_COL, CARD_ID_HEADER)


def find_member(client, card_id):
    ws = client.open_by_key(SPREADSHEET_KEY).worksheet("名簿")
    ensure_card_id_column(ws)
    for r in ws.get_all_records():
        if str(r.get(CARD_ID_HEADER, "")).strip() == card_id:
            return r
    return None


def load_all_members(client):
    ws = client.open_by_key(SPREADSHEET_KEY).worksheet("名簿")
    ensure_card_id_column(ws)
    records = ws.get_all_records()
    return {str(r.get(CARD_ID_HEADER, "")).strip(): r
            for r in records if r.get(CARD_ID_HEADER, "")}


def record(client, member):
    """出席時刻のみを新規行として記録する

    名簿の「直近の出席日」は出席シートを参照する数式なので、
    日付・時刻は USER_ENTERED で本物の日付/時刻セルとして書く。
    """
    ws = client.open_by_key(SPREADSHEET_KEY).worksheet("出席")
    now = datetime.now()
    name = member.get("氏名", "")
    date_str = now.strftime("%Y/%m/%d")
    time_str = now.strftime("%H:%M")
    # A:日付 B:名前 C:開始時間 D:終了時間（未使用）
    ws.append_row(
        [date_str, name, time_str, ""],
        value_input_option="USER_ENTERED",
    )


def register_card_to_sheet(client, card_id, name):
    """カードUID を名簿に登録（K列: カードID）"""
    ws = client.open_by_key(SPREADSHEET_KEY).worksheet("名簿")
    ensure_card_id_column(ws)
    records = ws.get_all_records()

    for i, r in enumerate(records):
        if r.get("氏名", "") == name:
            ws.update_cell(i + 2, MEIBO_CARD_ID_COL, card_id)
            return True

    row = len(records) + 2
    ws.update_cell(row, MEIBO_NAME_COL, name)
    ws.update_cell(row, MEIBO_CARD_ID_COL, card_id)
    return True


def get_history(client, limit=50):
    """出席シートの履歴を取得（A日付 B名前 C開始時間）"""
    ws = client.open_by_key(SPREADSHEET_KEY).worksheet("出席")
    rows = ws.get_all_values()
    records = []
    for row in rows[1:]:
        if len(row) < 2 or not (row[0] or row[1]):
            continue
        records.append({
            "日時": row[0],
            "名前": row[1] if len(row) > 1 else "",
            "開始時間": row[2] if len(row) > 2 else "",
        })
    records.reverse()
    return records[:limit]


# ── API ────────────────────────────────────────────────

@app.route("/api/cancel", methods=["POST"])
def api_cancel():
    cancel_event.set()
    return jsonify({"ok": True})


@app.route("/api/read", methods=["POST"])
def api_read():
    data = request.get_json()
    record_type = data.get("type")  # "start" | "check"

    if record_type not in ("start", "check"):
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

    # 出席モード（出席時刻のみ記録）
    try:
        client = get_sheets_client()
        member = find_member(client, uid)
    except Exception as e:
        return jsonify({"ok": False, "error": f"スプレッドシートエラー: {e}"}), 500

    if not member:
        return jsonify({"ok": False, "uid": uid, "unregistered": True,
                        "error": "未登録のカードです"}), 404

    try:
        record(client, member)
    except Exception as e:
        return jsonify({"ok": False, "error": f"打刻エラー: {e}"}), 500

    now = datetime.now().strftime("%H:%M")
    return jsonify({"ok": True, "uid": uid, "name": member.get("氏名", ""),
                    "type": "出席", "time": now})


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
