#!/usr/bin/env python3
"""
出席管理システム
PaSoRi RC-S300 + NTAG215 カードで出席・退勤を打刻し、
Google スプレッドシートに記録します。

通信方式: PC/SC (pyscard)
"""
import os
import sys
import time
from datetime import datetime
from binascii import hexlify

import gspread
from google.oauth2.service_account import Credentials
from smartcard.CardMonitoring import CardMonitor, CardObserver
from smartcard.System import readers
from smartcard.util import toHexString

# ── .env 読み込み ──────────────────────────────────────
def _load_dotenv(path=None):
    """簡易 .env ローダー（python-dotenv 不要）"""
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
# 環境変数から読み取り。未設定時はデフォルト値を使用。
SPREADSHEET_KEY = os.environ.get(
    "SPREADSHEET_KEY",
    "your-spreadsheet-key"
)
CREDENTIALS_FILE = os.environ.get(
    "CREDENTIALS_FILE",
    "credentials/your-credentials-file.json"
)
READER_NAME = "PaSoRi"  # 部分一致で探す
POLL_INTERVAL = 0.5     # ポーリング間隔（秒）
# ────────────────────────────────────────────────────────

SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]


def find_pasori():
    """PaSoRi リーダーを探して返す"""
    for r in readers():
        if READER_NAME in r.name:
            return r
    return None


def get_card_uid(card):
    """カードの UID（7バイト）を取得する

    PC/SC の Get Data コマンド (FF CA 00 00 00) で UID を取得。
    Type A（NTAG215）の場合は 7 バイト、Type B は 4 バイトなど。
    """
    GET_UID = [0xFF, 0xCA, 0x00, 0x00, 0x00]
    response, sw1, sw2 = card.transmit(GET_UID)

    if sw1 == 0x90 and sw2 == 0x00:
        uid_bytes = bytes(response)
        return hexlify(uid_bytes).decode().upper()

    # カードが応答中の可能性があり、リトライ
    time.sleep(0.05)
    response, sw1, sw2 = card.transmit(GET_UID)
    if sw1 == 0x90 and sw2 == 0x00:
        uid_bytes = bytes(response)
        return hexlify(uid_bytes).decode().upper()

    return None


# ── Google Sheets ──────────────────────────────────────

def get_sheets_client():
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPE)
    return gspread.authorize(creds)


def load_members(client):
    """名簿シートからメンバー情報を読み込む"""
    ws = client.open_by_key(SPREADSHEET_KEY).worksheet("名簿")
    records = ws.get_all_records()
    members = {}
    for r in records:
        card_id = str(r.get("カードID", "") or "").strip()
        if card_id:
            members[card_id] = r
    return members


def record_attendance(client, member):
    """出席シートに打刻

    同日・同人物の未完了レコード（終了時刻が空）があれば終了時刻を更新。
    なければ新規行として開始時刻を記録。
    """
    ws = client.open_by_key(SPREADSHEET_KEY).worksheet("出席")
    now = datetime.now()
    name = member.get("氏名", "")
    date_str = now.strftime("%Y/%m/%d")
    time_str = now.strftime("%H:%M")

    # 既存レコードをチェック
    records = ws.get_all_records()
    for i, r in enumerate(records):
        if (str(r.get("日付", "")).strip() == date_str and
            str(r.get("氏名", "")).strip() == name and
            str(r.get("終了時刻", "")).strip() == ""):
            # 退勤打刻
            ws.update_cell(i + 2, 4, time_str)  # D列: 終了時刻
            print(f"  🏠 {name} さん  → 退勤 {time_str}")
            return

    # 出席打刻（新規行）
    ws.append_row([date_str, name, time_str, ""])
    print(f"  ✅ {name} さん  → 出席 {time_str}")


def register_card(client, card_id):
    """未登録カードを名簿に紐付け"""
    ws = client.open_by_key(SPREADSHEET_KEY).worksheet("名簿")
    records = ws.get_all_records()
    print(f"\nカードID: {card_id}")
    name = input("氏名を入力してください: ").strip()
    if not name:
        print("  ⚠ 登録をキャンセルしました")
        return

    for i, r in enumerate(records):
        if r.get("氏名", "") == name:
            ws.update_cell(i + 2, 10, card_id)  # J列: カードID
            print(f"  ✅ {name} さんにカードを紐付けました")
            return

    print(f"  ℹ {name} さんは名簿に未登録です")
    yn = input("名簿に新規追加しますか？ (y/n): ").strip().lower()
    if yn == "y":
        ws.update_cell(len(records) + 2, 2, name)
        ws.update_cell(len(records) + 2, 10, card_id)
        print(f"  ✅ {name} さんを新規登録しました")


# ── メインループ ───────────────────────────────────────

def main():
    mode = "attendance"
    if len(sys.argv) > 1 and sys.argv[1] in ("--register", "-r"):
        mode = "register"
    elif len(sys.argv) > 1 and sys.argv[1] in ("--list", "-l"):
        mode = "list"

    print("=" * 50)
    print("  NTAG215 出席管理システム")
    print("=" * 50)

    # PaSoRi を探す
    reader = find_pasori()
    if not reader:
        print("\n❌ PaSoRi が見つかりません")
        print("  USB接続を確認してください")
        sys.exit(1)
    print(f"\n📡 {reader.name}")

    client = get_sheets_client()

    if mode == "list":
        members = load_members(client)
        print(f"\n登録済みカード: {len(members)} 件")
        for cid, m in sorted(members.items(), key=lambda x: x[1].get("会員番号", 0)):
            print(f"  {m.get('氏名',''):>8s} → {cid}")
        return

    members = load_members(client)
    print(f"登録者数: {len(members)} 人")
    print("\n💡 PaSoRi にカードをかざしてください（Ctrl+C で終了）\n")

    connection = None
    try:
        while True:
            try:
                connection = reader.createConnection()
                connection.connect()

                uid = get_card_uid(connection)
                if uid:
                    now = datetime.now().strftime("%H:%M:%S")
                    print(f"\n📱 [{now}] カード検出: {uid}")

                    if mode == "register":
                        if uid in members:
                            print(f"  このカードは既に {members[uid].get('氏名','')} さんに登録されています")
                        else:
                            register_card(client, uid)
                            members = load_members(client)
                    else:
                        if uid in members:
                            record_attendance(client, members[uid])
                        else:
                            print(f"  ⚠ 未登録のカードです")
                            yn = input("  登録しますか？ (y/n): ").strip().lower()
                            if yn == "y":
                                register_card(client, uid)
                                members = load_members(client)

                    # カードが離れるのを待つ
                    time.sleep(1)
                    connection.disconnect()
                    connection = None
                    print("  待機中...")

            except Exception:
                # カードがまだ置かれていない / 通信エラー → 次のループへ
                if connection:
                    try:
                        connection.disconnect()
                    except Exception:
                        pass
                    connection = None
                time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        print("\n\n👋 終了します")
    finally:
        if connection:
            try:
                connection.disconnect()
            except Exception:
                pass


if __name__ == "__main__":
    main()
