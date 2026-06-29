#!/usr/bin/env python3
"""
FeliCa カードリーダー for 出席管理
PaSoRi (RC-S380) で FeliCa カードを読み取り、Google Spreadsheet に打刻します。
libusb1 を直接使用（nfcpy 非依存）。
"""
import sys
import os
import time
import struct
from datetime import datetime
from binascii import hexlify

if "DYLD_LIBRARY_PATH" not in os.environ:
    os.environ["DYLD_LIBRARY_PATH"] = "/opt/homebrew/opt/expat/lib"

import usb1
import gspread
from google.oauth2.service_account import Credentials

# ── 設定 ─────────────────────────────────────────────────
SPREADSHEET_KEY = "your-spreadsheet-key"
CREDENTIALS_FILE = "credentials/your-credentials-file.json"
PASORI_VID = 0x054C
PASORI_PID = 0x0DC9
# ────────────────────────────────────────────────────────

SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]


# ── RC-S380 通信プロトコル ──────────────────────────────

def send_frame(handle, cmd_code, cmd_data=b""):
    """RC-S380 にコマンドを送信し、応答データを返す"""
    cmd = bytearray([0xD6, cmd_code]) + bytearray(cmd_data)
    length = len(cmd)
    header_chk = (256 - (length & 0xFF) - ((length >> 8) & 0xFF)) & 0xFF
    data_chk = (256 - sum(cmd)) & 0xFF
    frame = bytearray(b"\x00\x00\xff\xff\xff")
    frame += struct.pack("<H", length)
    frame += bytearray([header_chk])
    frame += cmd
    frame += bytearray([data_chk, 0x00])

    handle.bulkWrite(0x02, bytes(frame), timeout=2000)

    # ACK 受信
    ack = bytearray(handle.bulkRead(0x82, 300, timeout=2000))
    if ack != bytearray(b"\x00\x00\xff\x00\xff\x00"):
        raise IOError(f"ACK expected, got {hexlify(ack).decode()}")

    # 応答受信
    resp = bytearray(handle.bulkRead(0x82, 300, timeout=2000))
    if resp[0:3] != bytearray(b"\x00\x00\xff"):
        raise IOError(f"Invalid response: {hexlify(resp).decode()}")

    resp_len = struct.unpack("<H", bytes(resp[5:7]))[0]
    resp_data = resp[8:8+resp_len]
    return resp_data


# InSetProtocol のデフォルト値
SET_PROTOCOL_DEFAULTS = bytearray.fromhex(
    "0018 0101 0201 0300 0400 0500 0600 0708 0800 0900"
    "0A00 0B00 0C00 0E04 0F00 1000 1100 1200 1306"
)


class PaSoRi:
    """Sony PaSoRi (RC-S380) FeliCa リーダー"""

    def __init__(self):
        self.ctx = None
        self.handle = None

    def open(self):
        self.ctx = usb1.USBContext()
        for dev in self.ctx.getDeviceList(skip_on_error=True):
            if (dev.getVendorID() == PASORI_VID and
                dev.getProductID() == PASORI_PID):
                self.handle = dev.open()
                self.handle.setConfiguration(1)
                self.handle.claimInterface(1)
                print("✅ PaSoRi 接続OK")
                self._init_device()
                return True
        raise IOError("PaSoRi が見つかりません")

    def _init_device(self):
        """デバイス初期化"""
        handle = self.handle
        # ACK 送信（ソフトリセット）
        handle.bulkWrite(0x02, b"\x00\x00\xff\x00\xff\x00", timeout=2000)
        time.sleep(0.05)
        # ゴミデータクリア
        try:
            while True:
                handle.bulkRead(0x82, 300, timeout=10)
        except usb1.USBErrorTimeout:
            pass

        # SetCommandType (type 1)
        send_frame(handle, 0x2A, bytearray([0x01]))

        # GetFirmwareVersion
        fw = send_frame(handle, 0x20)
        print(f"  ファームウェア: {hexlify(fw).decode()}")

        # InSetProtocol (デフォルト)
        send_frame(handle, 0x02, SET_PROTOCOL_DEFAULTS)

    def in_set_rf(self):
        """InSetRF: FeliCa 212kbps"""
        send_frame(self.handle, 0x00, bytearray([0x01, 0x01, 0x0F, 0x01]))

    def poll_card(self, timeout_sec=2.0):
        """FeliCa カードをポーリング。IDm を返す（見つからなければ None）"""
        handle = self.handle

        # FeliCa Polling コマンド
        poll_cmd = bytearray([0x06, 0x00, 0xFF, 0xFF, 0x01, 0x00])

        deadline = time.time() + timeout_sec
        while time.time() < deadline:
            try:
                self.in_set_rf()
                time.sleep(0.02)

                # InCommRF: timeout を 200ms (= 2000 * 100us) に設定
                comm_timeout = 2000  # 200ms (in 100us units)
                data = struct.pack("<H", comm_timeout) + poll_cmd

                resp = send_frame(handle, 0x04, data)

                if len(resp) < 5:
                    time.sleep(0.1)
                    continue

                # resp[0:4] = ステータスフラグ（すべて0なら成功）
                # resp[4] = レスポンスデータ長？
                # resp[5:] = 実際のFeliCa応答データ
                if resp[0:4] != b"\x00\x00\x00\x00":
                    time.sleep(0.1)
                    continue

                felica_data = resp[5:] if len(resp) > 5 else resp[4:]

                if len(felica_data) >= 9 and felica_data[0] == 0x07:
                    # Polling Response: IDm は 1-8 バイト目
                    idm = hexlify(felica_data[1:9]).decode().upper()
                    return idm

            except (usb1.USBErrorTimeout, IOError):
                pass
            except usb1.USBErrorNoDevice:
                raise IOError("PaSoRi が切断されました")
            except usb1.USBErrorPipe:
                try:
                    self._init_device()
                except:
                    pass

            time.sleep(0.1)

        return None

    def close(self):
        if self.handle:
            try:
                self.handle.releaseInterface(1)
                self.handle.close()
            except:
                pass
            self.handle = None
        if self.ctx:
            self.ctx.exit()
            self.ctx = None


# ── Google Sheets ──────────────────────────────────────

def get_client():
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPE)
    return gspread.authorize(creds)


def load_members(client):
    ws = client.open_by_key(SPREADSHEET_KEY).worksheet("名簿")
    records = ws.get_all_records()
    members = {}
    for r in records:
        card_id = str(r.get("カードID", "") or "").strip()
        if card_id:
            members[card_id] = r
    return members


def record_attendance(client, member):
    ws = client.open_by_key(SPREADSHEET_KEY).worksheet("出席")
    now = datetime.now()
    date_str = now.strftime("%Y/%m/%d")
    time_str = now.strftime("%H:%M")
    name = member.get("氏名", "")
    ws.append_row([date_str, name, time_str, ""])
    print(f"  ✅ {name} さん  {date_str} {time_str} に出勤打刻しました")


def register_card(client, card_id):
    ws = client.open_by_key(SPREADSHEET_KEY).worksheet("名簿")
    records = ws.get_all_records()
    print(f"\nカードID: {card_id}")
    name = input("氏名を入力してください: ").strip()
    if not name:
        print("  ⚠ 登録をキャンセルしました")
        return

    for i, r in enumerate(records):
        if r.get("氏名", "") == name:
            ws.update_cell(i + 2, 10, card_id)
            print(f"  ✅ {name} さんにカードを紐付けました")
            return

    print(f"  {name} さんは名簿にまだ登録されていません")
    yn = input("名簿に新規追加しますか？ (y/n): ").strip().lower()
    if yn == "y":
        ws.update_cell(len(records) + 2, 2, name)
        ws.update_cell(len(records) + 2, 10, card_id)
        print(f"  ✅ {name} さんを新規登録しました")


# ── メイン ──────────────────────────────────────────────

def main():
    mode = "attendance"
    if len(sys.argv) > 1 and sys.argv[1] in ("--register", "-r"):
        mode = "register"
    elif len(sys.argv) > 1 and sys.argv[1] in ("--list", "-l"):
        mode = "list"

    print("=" * 50)
    print("  FeliCa 出席管理システム")
    print("=" * 50)

    client = get_client()

    if mode == "list":
        cards = load_members(client)
        print(f"\n登録済みカード: {len(cards)} 件")
        for cid, m in sorted(cards.items(), key=lambda x: x[1].get("会員番号", 0)):
            print(f"  {m.get('氏名',''):>8s} → {cid}")
        return

    members = load_members(client)
    print(f"\n登録者数: {len(members)} 人")

    pasori = PaSoRi()
    try:
        pasori.open()
    except IOError as e:
        print(f"\n❌ {e}")
        print("  PaSoRi が USB に接続されているか確認してください")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ エラー: {e}")
        sys.exit(1)

    print("PaSoRi にカードをかざしてください...\n")

    try:
        while True:
            idm = pasori.poll_card(timeout_sec=0.5)
            if idm:
                now = datetime.now().strftime("%H:%M:%S")
                print(f"\n📱 [{now}] カード検出: {idm}")

                if mode == "register":
                    if idm in members:
                        print(f"  このカードは既に {members[idm].get('氏名','')} さんに登録されています")
                    else:
                        register_card(client, idm)
                        members.clear()
                        members.update(load_members(client))
                else:
                    if idm in members:
                        record_attendance(client, members[idm])
                    else:
                        print(f"  ⚠ 未登録のカードです")
                        yn = input("  このカードを今登録しますか？ (y/n): ").strip().lower()
                        if yn == "y":
                            register_card(client, idm)
                            members.clear()
                            members.update(load_members(client))

                # カードが離れるまで待つ
                time.sleep(1)
                while pasori.poll_card(timeout_sec=0.3):
                    time.sleep(0.5)
                print("  待機中...")
    except KeyboardInterrupt:
        print("\n\n終了します")
    except Exception as e:
        print(f"\nエラー: {e}")
    finally:
        pasori.close()


if __name__ == "__main__":
    main()
