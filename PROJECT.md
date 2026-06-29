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

| 項目 | 内容 |
|------|------|
| 製品名 | SONY PaSoRi **RC-S300** |
| USB 表示名 | "FeliCa Port/PaSoRi 4.0"（macOS での認識名） |
| USB ID | VID=0x054C, PID=0x0DC9 |
| チップセット | **Sony Port 400**（完全新設計） |
| 世代 | RC-S380（Port 100）の後継、最新モデル |
| 接続 | USB-C 変換アダプタ経由 |

### RC-S300 の正体：なぜ既存ライブラリで動かないのか

RC-S300 は **Port 400** という Sony 独自の完全新チップを搭載しており、従来の PaSoRi とは内部プロトコルが異なる。

```
RC-S330/360/370  →  チップ: RC-S956    →  nfcpy rcs956.py ✅
RC-S380          →  チップ: Port 100   →  nfcpy rcs380.py ✅
RC-S300          →  チップ: Port 400   →  nfcpy 未対応 ❌ （新チップ）
```

- nfcpy の GitHub に Issue（#214, #240）が立っているが、まだ誰も Port 400 用ドライバを書いていない
- Sony 公式 SDK は **Windows のみ**提供。macOS 用のドライバ・SDK は存在しない
- Port 400 の仕様は公開されておらず、リバースエンジニアリングが必要

## 環境

| 項目 | 内容 |
|------|------|
| OS | macOS 26 |
| Python | 3.12.13（Homebrew） |
| 仮想環境 | `venv/` |
| USB 通信 | libusb1（PaSoRi を直接制御） |
| スプレッドシート | gspread + Google API 認証 |

## Google スプレッドシート構造

### シート①「名簿」

メンバーの情報と、配布したカードの UID を紐付ける台帳。

| カラム | 内容 | 例 |
|--------|------|-----|
| A: 会員番号 | 連番 | 1 |
| B: 氏名 | フルネーム | 山田 太郎 |
| ... | （その他属性） | |
| J: カードID | NTAG215 の UID（7バイト16進数） | `04A1B2C3D4E5F6` |

### シート②「出席」

日々の打刻を記録する。

| カラム | 内容 | 例 |
|--------|------|-----|
| A: 日付 | 打刻日 | 2026/06/29 |
| B: 氏名 | 名簿と一致する氏名 | 山田 太郎 |
| C: 開始時刻 | 出席時のタッチ時刻 | 09:03 |
| D: 終了時刻 | 退勤時のタッチ時刻（2回目） | 17:45 |

### 打刻ロジック

- 1回目のタッチ → 新規行を追加し、日付・氏名・**開始時刻**を記録
- 2回目のタッチ（同日・同人物） → 既存行の **終了時刻**を更新

## 選択した技術的理由

### nfcpy を採用しなかった理由

- RC-S300 のチップセット **Port 400** は nfcpy が**根本的に未対応**（ドライバが存在しない）
- nfcpy が対応しているのは RC-S380（Port 100）まで
- GitHub に Issue（#214, #240）があるが、2026年6月時点で誰も Port 400 ドライバを書いていない

→ **libusb1 を直接使って PaSoRi と通信する方針**を採用した

### libnfc を採用しなかった理由

- libnfc は Port 400 チップセットに未対応（Port 100 も未対応）
- libnfc 1.8.0 時点で Sony Port シリーズ全般のサポートがない

### pyscard（PC/SC）を採用しなかった理由

- macOS に RC-S300 用の PC/SC ドライバが存在しない

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

## ファイル構成

```
Pasori_spreadsheet/
├── PROJECT.md                  # このファイル（プロジェクトの仕様書）
├── run.sh                      # 起動スクリプト
├── credentials/                # Google API 認証情報（Git管理外）
└── venv/                       # Python 仮想環境（Git管理外）
```
