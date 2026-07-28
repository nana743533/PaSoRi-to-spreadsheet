# PaSoRi 出席管理システム

SONY PaSoRi **RC-S300** に **NTAG215 カード**をかざして、**出席時刻だけ**を Google スプレッドシートに記録します。

退勤打刻はありません。出席のたびに「出席」シートへ 1 行追加します。

## 動作の流れ

```text
ブラウザ / CLI
    ↓
app.py または attendance.py（PaSoRi が刺さっている PC 上）
    ↓ USB / PC/SC
PaSoRi RC-S300 ← NTAG215（UID で個人識別）
    ↓ gspread
Google スプレッドシート（名簿・出席）
```

### Web UI（推奨）

1. **出席** または **UID確認** を押す
2. カードをタッチ（最大 30 秒。キャンセル可）
3. 名簿のカード ID と照合
4. 出席なら「出席」シートに日付・氏名・出席時刻を追加
5. 未登録カードなら氏名入力モーダルで名簿に登録可能

履歴は「履歴を見る」→「出席」シートを新しい順に最大 50 件表示します。

### CLI

カードをかざすと出席記録（または `--register` で名簿登録）。

---

## 必要なもの

| 項目 | 備考 |
|------|------|
| SONY PaSoRi RC-S300 | USB 接続 |
| NTAG215 カード | NFC Forum Type 2 Tag（UID で識別） |
| Python 3.12+ | |
| Google スプレッドシート | 名簿・出席シートがあること |
| Google サービスアカウント | Sheets への書き込み用 |

| OS | ドライバ | セットアップ手順 |
|----|----------|------------------|
| **macOS 13+** | 不要（OS 標準で認識） | [`macos/README.md`](macos/README.md) |
| **Windows 10/11** | **NFCポートソフトウェア必須** | [`windows/README.md`](windows/README.md) |

アプリ本体（`app.py` / `attendance.py` / `templates/`）は OS 共通です。  
**`.env` と credentials JSON は Mac / Windows で同じものをコピーして使えます。**

---

## リポジトリ構成

```text
├── app.py                 # Web UI（Flask）
├── attendance.py          # CLI
├── templates/             # 画面（出席・履歴）
├── requirements.txt
├── .env.example           # 環境変数のひな形
├── credentials/           # サービスアカウント JSON（Git 管理外）
├── macos/                 # macOS 用セットアップ・起動スクリプト
└── windows/               # Windows 用セットアップ・起動スクリプト
```

---

## Google 側の準備（共通）

セットアップでいちばん忘れやすいのがここです。

### 1. スプレッドシート KEY

シート URL の例:

`https://docs.google.com/spreadsheets/d/`**`xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`**`/edit`

`/d/` と `/edit` のあいだが **`SPREADSHEET_KEY`** です。

### 2. サービスアカウント

プログラム専用の Google アカウント（ロボット）です。

1. Google Cloud でサービスアカウントを作成
2. JSON 鍵を発行して `credentials/` に置く
3. そのサービスアカウントのメールアドレスを、対象スプレッドシートの**共有（編集者）**に追加

### 3. credentials（認証 JSON）

サービスアカウントの身分証（秘密鍵ファイル）です。パスワード相当なので **Git にコミットしない**でください（`.gitignore` 済み）。

### 4. `.env`

リポジトリルートに `.env.example` をコピーして作成します。

```env
SPREADSHEET_KEY=（上記のシート ID）
CREDENTIALS_FILE=credentials/（JSON のファイル名）
```

パスは `credentials/foo.json` のようにスラッシュで書いて問題ありません（Windows の Python でも可）。

---

## セットアップ（OS 別）

### macOS

詳細は [`macos/README.md`](macos/README.md)

```bash
./macos/setup.sh
# .env を編集し、credentials/ に JSON を配置
./macos/run_web.sh
```

### Windows

詳細は [`windows/README.md`](windows/README.md)

**先に** [NFCポートソフトウェア](https://www.sony.co.jp/Products/felica/consumer/support/setup/RC-S300.html) をインストールしてから:

```bat
windows\setup.bat
REM .env を編集し、credentials\ に JSON を配置
windows\check_reader.bat
windows\run_web.bat
```

起動後、ブラウザで http://127.0.0.1:5000 を開きます。

---

## スプレッドシート構造

対象例: 「日報2026」系（シート名 `名簿` / `出席`）

### 名簿

| 列 | ヘッダー | 役割 |
|----|----------|------|
| A | （番号） | 連番 |
| B | 氏名 | 出席シートの「名前」と**同じ表記**にする |
| C〜I | フリガナ・入会日 など | 既存業務用（アプリは触らない） |
| J | 直近の出席日 | 出席シート参照の数式 |
| K | カードID | NTAG215 の UID。**無ければアプリがヘッダーを自動追加** |

### 出席

| 列 | ヘッダー例 | 役割 |
|----|------------|------|
| A | （日付列。ヘッダーが日付でも可） | 出席日 |
| B | 名前 | 名簿の氏名と一致 |
| C | 開始時間 | 出席時刻 |
| D | 終了時間 | 未使用（空で追加） |

打刻のたびに 1 行追加します。履歴画面もこのシートを列位置で読みます。

---

## 使い方まとめ

| 操作 | macOS | Windows |
|------|--------|---------|
| Web UI | `./macos/run_web.sh` | `windows\run_web.bat` |
| CLI 出席 | `./macos/run.sh` | `windows\run.bat` |
| CLI カード登録 | `./macos/run.sh --register` | `windows\run.bat --register` |
| CLI 登録一覧 | `./macos/run.sh --list` | `windows\run.bat --list` |
| リーダー確認 | 下記 | `windows\check_reader.bat` |

リーダー確認（macOS 例）:

```bash
source venv/bin/activate
python3 -c "from smartcard.System import readers; print(readers())"
```

`PaSoRi` / `FeliCa` / `SONY` を含む名前が出れば OK です。

### Web 画面の機能

| ボタン | 動作 |
|--------|------|
| 出席 | カード待機 → 名簿照合 → 出席シートに記録 |
| UID確認 | カードの UID と登録有無を表示。未登録なら登録モーダル |
| 履歴を見る | 出席シートの直近履歴 |
| キャンセル | カード待ちを中断 |

PaSoRi が未接続のときは「PaSoRi が見つかりません」と表示されます。

---

## 技術構成

| 層 | 技術 |
|----|------|
| カード通信 | PC/SC（macOS 標準 / Windows は NFCポートソフトウェア） |
| Python ラッパー | pyscard |
| Web UI | Flask |
| スプレッドシート | gspread |
| 認証 | Google サービスアカウント |

詳細な技術メモは [`PROJECT.md`](PROJECT.md) を参照してください。

---

## 免責事項

- RC-S300 は Sony の登録商標です
- NTAG215 は NXP Semiconductors の登録商標です
- 本ソフトウェアは非公式の個人プロジェクトです

## ライセンス

MIT License
