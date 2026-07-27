# Windows セットアップ

Windows では **macOS と違い、Sony 公式ドライバのインストールが必須**です。

## 必要なもの

| 項目 | 備考 |
|------|------|
| Windows 10 / 11 | 64bit 推奨 |
| Python 3.12+ | [python.org](https://www.python.org/downloads/)（インストール時に「Add python.exe to PATH」にチェック） |
| SONY PaSoRi RC-S300 | USB 接続 |
| NTAG215 カード | NFC Forum Type 2 Tag |
| **NFCポートソフトウェア** | Windows 専用ドライバ（必須） |

## 1. NFCポートソフトウェア（ドライバ）を入れる

macOS では不要ですが、Windows ではこれがないと PaSoRi が認識されません。

1. Sony のセットアップガイドを開く  
   https://www.sony.co.jp/Products/felica/consumer/support/setup/RC-S300.html
2. **NFCポートソフトウェア** をダウンロードしてインストール（管理者として実行）
3. PaSoRi を USB 接続する
4. インストール後の自己診断などでリーダーが認識されていることを確認

ドライバ配布ページ:  
https://www.sony.co.jp/Products/felica/consumer/support/download/index.html

## 2. アプリのセットアップ

エクスプローラーでこの `windows` フォルダを開き、次をダブルクリック（またはコマンドプロンプトから実行）します。

```bat
windows\setup.bat
```

内容:

1. リポジトリルートに `venv` を作成
2. `requirements.txt` から依存パッケージをインストール
3. `.env.example` から `.env` を作成（なければ）
4. `credentials` フォルダを作成

その後:

1. リポジトリルートの `.env` を編集（`SPREADSHEET_KEY` / `CREDENTIALS_FILE`）
2. Google サービスアカウントの認証 JSON を `credentials\` に配置

## 3. リーダー確認（推奨）

```bat
windows\check_reader.bat
```

PaSoRi を含むリーダー名が表示されれば OK です。何も出ない／エラーの場合は、ドライバと USB 接続を再確認してください。

## 4. 使い方

```bat
REM Web UI（ブラウザで http://127.0.0.1:5000 ）
windows\run_web.bat

REM CLI 出席モード
windows\run.bat

REM CLI カード登録
windows\run.bat --register

REM CLI 登録済み一覧
windows\run.bat --list
```

## macOS との違い（まとめ）

| 項目 | macOS | Windows |
|------|--------|---------|
| ドライバ | 不要 | **NFCポートソフトウェア必須** |
| セットアップ | `macos\setup.sh` | `windows\setup.bat` |
| Web 起動 | `macos\run_web.sh` | `windows\run_web.bat` |
| CLI 起動 | `macos\run.sh` | `windows\run.bat` |
| アプリ本体 | 共通（ルートの `app.py` / `attendance.py`） | 同じ |

Python コード自体は共通です。OS ごとの違いは主に **ドライバ** と **起動スクリプト** です。
