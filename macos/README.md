# macOS セットアップ

macOS 13 以降では RC-S300 の**追加ドライバは不要**です。OS が PC/SC デバイスとして認識します。

共通の説明（Google 認証・シート構造・使い方）はルートの [`README.md`](../README.md) を参照してください。

## 必要なもの

| 項目 | 備考 |
|------|------|
| macOS 13+ | ドライバ不要 |
| Python 3.12+ | Homebrew 推奨（`brew install python`） |
| SONY PaSoRi RC-S300 | USB 接続 |
| NTAG215 カード | |
| Google 設定 | `.env` と `credentials/*.json`（[README の Google 側の準備](../README.md#google-側の準備共通)） |

## 手順

リポジトリの**ルート**で実行します。

### 1. 一括セットアップ

```bash
./macos/setup.sh
```

実施内容:

- `venv/` 作成
- `requirements.txt` のインストール
- `.env` が無ければ `.env.example` から作成
- `credentials/` フォルダ作成

### 2. 設定ファイル

1. ルートの `.env` を編集

```env
SPREADSHEET_KEY=（スプレッドシート URL の /d/〜/edit の ID）
CREDENTIALS_FILE=credentials/your-credentials.json
```

2. サービスアカウントの JSON を `credentials/` に配置  
3. そのサービスアカウントをスプレッドシートの共有（編集者）に追加

Windows で動いていた `.env` / JSON をそのままコピーしても構いません。

### 3. リーダー確認

```bash
source venv/bin/activate
python3 -c "from smartcard.System import readers; print(readers())"
```

`SONY FeliCa Port/PaSoRi 4.0` のような名前が出れば OK です。

### 4. 起動

```bash
# Web UI → http://127.0.0.1:5000
./macos/run_web.sh

# CLI 出席
./macos/run.sh

# CLI カード登録 / 一覧
./macos/run.sh --register
./macos/run.sh --list
```

## 手動セットアップ（参考）

```bash
cd /path/to/Pasori_spreadsheet
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# .env と credentials/ を編集してから
python app.py
```

## トラブルシュート

| 症状 | 確認 |
|------|------|
| PaSoRi が見つからない | USB 接続、`readers()` の出力 |
| スプレッドシートエラー | `.env` の KEY、JSON パス、シート共有 |
| 直近の出席日が空 | 出席の日付が日付セルとして入っているか（アプリは `USER_ENTERED` で書き込み） |

## Windows との違い

| 項目 | macOS | Windows |
|------|--------|---------|
| ドライバ | 不要 | NFCポートソフトウェア必須 |
| セットアップ | `macos/setup.sh` | `windows/setup.bat` |
| Web 起動 | `macos/run_web.sh` | `windows/run_web.bat` |

アプリ本体のコードは共通です。Windows 手順は [`../windows/README.md`](../windows/README.md) へ。
