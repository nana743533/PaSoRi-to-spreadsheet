# 出席管理システム プロジェクト概要

## やりたいこと

PaSoRi（SONY RC-S300）に **NTAG215 カード**をかざして、**出席・退勤を自動記録**し、Google スプレッドシートに書き込む。

### 運用イメージ

1. 入会者一人ひとりに **NTAG215 IDカード** を配布
2. **出席時**：カードを PaSoRi にタッチ → 自動で「開始時刻」を記録
3. **退勤時**：もう一度同じカードをタッチ → 自動で「終了時刻」を記録
4. タッチするだけで個人識別され、スプレッドシートに時刻が入力される

### 読み取りたいカード

- **NTAG215**（NFC Forum Type 2 Tag、ISO/IEC 14443 Type A 準拠）
- 7バイトの UID（固有ID）で個人を識別
- 入会者一人ひとりに配布する

### 使う機器

| 機器 | 型番 |
|------|------|
| カードリーダー | SONY PaSoRi **RC-S300** |
| USB ID | VID=0x054C, PID=0x0DC9 |
| 接続 | USB-C 変換アダプタ経由 |
| チップセット | Sony NFC Port-100 |

## 環境

| 項目 | 内容 |
|------|------|
| OS | macOS 26 |
| Python | 3.12.13（Homebrew） |
| 仮想環境 | `venv/` |
| USB通信 | libusb1（直接制御、nfcpy 非依存） |
| スプレッドシート | gspread + Google API 認証 |

## 現在の状態

`attendance.py` は **完成に近い**：
- ✅ PaSoRi との USB 通信（libusb1 直接制御）
- ✅ Google スプレッドシートへの打刻
- ✅ カード登録モード
- ❌ NTAG215（Type A）カードの UID 読み取りが未対応 ← ここをやる
  - 今の `poll_card()` は FeliCa 用のコマンド（`0x06`）を使っている
  - Type A 用の InListPassiveTarget コマンドに変更する必要がある

### なぜ nfcpy を使わなかったか

1. nfcpy が libusb1 3.x の API 変更（`getInterfaceNumber()` → `getNumber()`）に未対応
2. PaSoRi 4.0（PID=0x0DC9）が nfcpy のデバイス対応表に未登録
3. nfcpy の最終更新は 2023 年でメンテナンス停止状態

→ **libusb1 を直接使う方針**に切り替えて `attendance.py` を書いた

## ファイル構成

```
Pasori_spreadsheet/
├── attendance.py              # メインのプログラム
├── run.sh                     # 起動スクリプト（expatパス設定済み）
├── credentials/               # Google API 認証情報
├── venv/                      # Python 仮想環境
└── PROJECT.md                 # このファイル
```

## インストール済みパッケージ

| パッケージ | 用途 |
|-----------|------|
| libusb1 | USB 通信（PaSoRi 操作） |
| gspread | Google Sheets の読み書き |
| google-auth | Google API 認証 |
| google-auth-oauthlib | OAuth 認証 |
| google-auth-httplib2 | HTTP 認証 |
| google-api-python-client | Google API 全般 |

## 過去に解決した問題

### expat シンボルエラー
macOS の古い expat ライブラリと Python の互換性問題。
→ `install_name_tool` で Homebrew の expat に差し替え + 再署名で恒久解決済み。

### DYLD_LIBRARY_PATH
仮想環境内では不要になった（上記で解決済み）。

## 使い方

```bash
cd Pasori_spreadsheet
source venv/bin/activate

# 出席モード（デフォルト）
python attendance.py

# カード登録モード
python attendance.py --register

# 登録済みカード一覧
python attendance.py --list
```
