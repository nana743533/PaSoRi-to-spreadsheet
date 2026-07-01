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

- 製品詳細（個人向け）: https://www.sony.co.jp/Products/felica/consumer/products/RC-S300.html
- 法人向け製品比較: https://www.sony.co.jp/Products/felica/business/products/reader/comparison.html
- 法人向け RC-S300/S1: https://www.sony.co.jp/en/Products/felica/business/products/RC-S300S1.html
- 取扱説明書: https://www.sony.co.jp/Products/felica/consumer/support/download/pdf/RC-S300_manual.pdf
- セットアップ: https://www.sony.co.jp/Products/felica/consumer/support/setup/RC-S300.html
- ドライバ（NFCポートソフトウェア）: https://www.sony.co.jp/Products/felica/consumer/support/download/index.html

> **注**: RC-S300 は個人向け、RC-S300/S1 は法人向けの別製品。
> macOS 13 以降ではドライバ不要（OSが標準で認識）。

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
- Sony 公式の **NFC Port Software**（無料ドライバ）と **SDK for NFC Lite**（有償）は macOS にも対応している
  - ドライバ: https://www.sony.co.jp/en/Products/felica/business/products/RC-S300S1.html
  - SDK for NFC Lite: https://www.sony.co.jp/Products/felica/business/products/ICS-D004.html
  - 無料評価版 SDK（Starter Kit）も利用可能
- ただし SDK は有償ライセンスが必要なため、**pyscard + PC/SC** で標準対応する方針を採用

## 動作確認済みの成果

2026年6月29日時点で、以下が実機確認済み。

| 項目 | 結果 |
|------|------|
| PaSoRi 認識 | ✅ `SONY FeliCa Port/PaSoRi 4.0`（PC/SC 経由） |
| ドライバ | ✅ macOS 標準で不要（追加インストールなし） |
| NTAG215 UID 読み取り | ✅ `FF CA 00 00 00` コマンドで成功 |
| 実測 UID | `0440B2AA852190`（7バイト） |
| 実測 ATR | `3B8F8001804F0CA0000003060300030000000068` |

### 動作テストコード（最小構成）

```python
from smartcard.System import readers
from binascii import hexlify

reader = readers()[0]  # SONY FeliCa Port/PaSoRi 4.0
conn = reader.createConnection()
conn.connect()

resp, sw1, sw2 = conn.transmit([0xFF, 0xCA, 0x00, 0x00, 0x00])
if sw1 == 0x90 and sw2 == 0x00:
    print(f"UID: {hexlify(bytes(resp)).decode().upper()}")
# → UID: 0440B2AA852190
```

## 環境

| 項目 | 内容 |
|------|------|
| OS | macOS 26 |
| Python | 3.12.13（Homebrew） |
| 仮想環境 | `venv/` |
| 通信方式 | PC/SC（macOS 標準） + pyscard |
| スプレッドシート | gspread + Google API 認証 |

## システム仕様

### 全体アーキテクチャ

```
NTAG215 カード
    ↓ 13.56MHz（近距離無線）
PaSoRi RC-S300（Sony Port 400 チップ）
    ↓ USB（PC/SC プロトコル）
macOS PCSC.framework（OS 標準）
    ↓ pyscard（Python ラッパー）
attendance.py
    ↓ gspread（Google Sheets API）
Google スプレッドシート
```

### カード読み取り仕様

| 項目 | 内容 |
|------|------|
| カード種別 | NTAG215（NFC Forum Type 2 Tag） |
| 準拠規格 | ISO/IEC 14443 Type A |
| UID 長 | **7 バイト**（固定） |
| UID 例 | `0440B2AA852190` |
| ATR 例 | `3B8F8001804F0CA0000003060300030000000068` |

#### APDU コマンド

UID 取得に使用する PC/SC 疑似 APDU コマンド：

```
送信: FF CA 00 00 00
応答: [UID 7バイト] 90 00
       ~~~~~~~~~~~  ~~~~~
       固有ID       成功ステータス
```

| バイト | 意味 |
|--------|------|
| `FF` | PC/SC 疑似APDU クラス |
| `CA` | Get Data 命令 |
| `00 00` | パラメータ（UID 取得） |
| `00` | 期待応答長（0 = 自動） |
| `90 00` | 成功ステータスワード（SW1 SW2） |

### 打刻ロジック

```
カードタッチ
    │
    ├── 名簿に UID あり？
    │       │
    │       ├── YES → 出席シートを検索
    │       │       │
    │       │       ├── 同日・同人物・終了時刻空 → 終了時刻を更新（退勤）
    │       │       └── 該当なし → 新規行追加（出席）
    │       │
    │       └── NO → 未登録通知 → 登録するか確認
    │
    └── カードが離れるのを待つ → 待機中表示 → ループ
```

### PC/SC 接続フロー

```
1. SCardEstablishContext  （macOS が自動）
2. SCardListReaders       → "SONY FeliCa Port/PaSoRi 4.0"
3. SCardConnect           → カードが置かれるまで待機
4. SCardTransmit          → FF CA 00 00 00 を送信
5. SCardDisconnect        → 切断
6. 1秒待機（二重打刻防止）
7. 手順3に戻る
```

### 環境変数

| 変数名 | デフォルト値 | 説明 |
|--------|------------|------|
| `SPREADSHEET_KEY` | `your-spreadsheet-key` | Google Sheets のスプレッドシートID |
| `CREDENTIALS_FILE` | `credentials/your-credentials-file.json` | サービスアカウント認証JSON |

`.env` ファイルまたは `run.sh` 経由で設定。`.env` は Git 管理外。

### 動作モード

| モード | コマンド | 説明 |
|--------|---------|------|
| 出席 | `python attendance.py` | カードタッチで出席/退勤を記録 |
| 登録 | `python attendance.py --register` | カードUID を名簿に紐付け |
| 一覧 | `python attendance.py --list` | 登録済みカード一覧を表示 |

### ポーリング仕様

| 項目 | 値 |
|------|-----|
| ポーリング間隔 | 0.5 秒 |
| 二重打刻防止 | カード離脱後 1 秒待機 |
| カード接続タイムアウト | OS 既定値 |
| 終了方法 | `Ctrl+C`（KeyboardInterrupt） |

## Google スプレッドシート構造

### シート①「名簿」

メンバーの情報と、配布したカードの UID を紐付ける台帳。

| カラム | 内容 | 例 |
|--------|------|-----|
| A: 会員番号 | 連番 | 1 |
| B: 氏名 | フルネーム | 山田 太郎 |
| ... | （その他属性） | |
| J: カードID | NTAG215 の UID（7バイト16進数） | `0440B2AA852190` |

### シート②「出席」

日々の打刻を記録する。

| カラム | 内容 | 例 |
|--------|------|-----|
| A: 日付 | 打刻日（YYYY/MM/DD） | 2026/06/29 |
| B: 氏名 | 名簿と一致する氏名 | 山田 太郎 |
| C: 開始時刻 | 出席時のタッチ時刻（HH:MM） | 09:03 |
| D: 終了時刻 | 退勤時のタッチ時刻（HH:MM） | 17:45 |

## ライブラリ比較と技術選定

RC-S300 で NTAG215 カードを読み取るために検討したライブラリ一覧。

### 比較表

| ライブラリ | 言語 | RC-S300対応 | 通信方式 | 選定 |
|-----------|------|------------|---------|------|
| **pyscard** | Python | ✅ | PC/SC（OS標準） | **採用** |
| nfcpy | Python | ❌ | libusb1（USB直） | 非採用 |
| libnfc | C | ❌ | libusb（USB直） | 非採用 |
| libusb1 | Python | △ | USB直（要自作） | 予備 |

---

### pyscard（PC/SC） — ✅ 採用

- **リポジトリ**: https://github.com/LudovicRousseau/pyscard
- **通信方式**: PC/SC（Personal Computer / Smart Card）
- **役割**: スマートカードリーダーと APDU コマンドで通信する Python ラッパー
- **macOS 対応**: macOS 標準の PC/SC フレームワーク（PCSC.framework）上で動作
- **必要なもの**: 特になし（macOS 13+ は RC-S300 のドライバ不要）

選定理由：
- macOS が RC-S300 を標準で PC/SC デバイスとして認識する（`SONY FeliCa Port/PaSoRi 4.0`）
- APDU コマンドで Type A（NTAG215）の UID を取得できる
- 余計な依存がなく安定している

### nfcpy — ❌ 非採用

- **リポジトリ**: https://github.com/nfcpy/nfcpy
- **通信方式**: libusb1（USB を直接制御）
- **役割**: NFC タグの読み書き、FeliCa / Type A / Type B / Type V 対応
- **対応リーダー**: RC-S330/360/370（rcs956）, RC-S380（rcs380 / Port 100）
- **最終更新**: 2023年（メンテナンス停止状態）

非採用理由：
- RC-S300 のチップセット **Port 400** に未対応（ドライバ不在）
- Port 100 向けの `rcs380.py` は存在するが、Port 400 とはプロトコルが異なる
- GitHub Issue（#214, #240）で対応待ちだが進捗なし

### libnfc — ❌ 非採用

- **リポジトリ**: https://github.com/nfc-tools/libnfc
- **通信方式**: libusb（C 言語で USB を直接制御）
- **役割**: NFC リーダーのハードウェア抽象化ライブラリ
- **macOS 対応**: Homebrew でインストール可能（`brew install libnfc`）

非採用理由：
- Sony Port シリーズ（Port 100 / Port 400）全般に未対応（libnfc 1.8.0 時点）
- 対応しているのは NXP PN53x 系チップが中心

### libusb1 — △ 予備

- **リポジトリ**: https://github.com/vpelletier/python-libusb1
- **通信方式**: USB エンドポイントへの生データ送受信
- **役割**: USB デバイスとの低レベル通信（Python ラッパー）
- **macOS 対応**: Homebrew の libusb 経由で動作

非採用理由：
- RC-S300 の Port 400 チップのプロトコルは**仕様非公開**
- FeliCa / Type A のポーリング、コマンド送信をすべて自作する必要がある
- 実装に数週間〜数月かかる現実的でない選択肢
- PC/SC（pyscard）で解決できるため不要

## インストール済みパッケージ

| パッケージ | 用途 |
|-----------|------|
| pyscard | PC/SC 経由で RC-S300 と通信・カード読み取り |
| gspread | Google Sheets の読み書き |
| google-auth | Google API 認証 |
| google-auth-oauthlib | OAuth 認証 |
| google-auth-httplib2 | HTTP 認証 |
| google-api-python-client | Google API 全般 |
| libusb1 | USB 通信（予備・デバッグ用） |

## 過去に解決した問題

### expat シンボルエラー
macOS の古い expat ライブラリと Python の互換性問題。
→ `install_name_tool` で Homebrew の expat に差し替え + 再署名で恒久解決済み。

## ファイル構成

```
Pasori_spreadsheet/
├── PROJECT.md                  # このファイル（プロジェクトの仕様書）
├── attendance.py               # メインプログラム
├── run.sh                      # 起動スクリプト
├── credentials/                # Google API 認証情報（Git管理外）
└── venv/                       # Python 仮想環境（Git管理外）
```

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
