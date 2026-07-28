# Windows セットアップ

Windows では **macOS と違い、Sony 公式ドライバ（NFCポートソフトウェア）が必須**です。  
これが無いと PaSoRi は PC/SC リーダーとして見えません。

共通の説明（Google 認証・シート構造・使い方）はルートの [`README.md`](../README.md) を参照してください。

## 必要なもの

| 項目 | 備考 |
|------|------|
| Windows 10 / 11 | 64bit 推奨 |
| Python 3.12+ | [python.org](https://www.python.org/downloads/) でインストール時に **Add python.exe to PATH** にチェック |
| SONY PaSoRi RC-S300 | USB 接続 |
| NTAG215 カード | |
| **NFCポートソフトウェア** | Windows 専用ドライバ（必須） |
| Google 設定 | `.env` と `credentials\*.json`（[README の Google 側の準備](../README.md#google-側の準備共通)） |

## 手順

### 1. NFCポートソフトウェア（ドライバ）を入れる

1. [RC-S300 セットアップガイド（Windows）](https://www.sony.co.jp/Products/felica/consumer/support/setup/RC-S300.html) を開く  
2. **NFCポートソフトウェア**をダウンロードし、管理者としてインストール  
3. PaSoRi を USB 接続  
4. 自己診断などでリーダーが認識されていることを確認  

ドライバ配布:  
https://www.sony.co.jp/Products/felica/consumer/support/download/index.html

### 2. アプリのセットアップ

リポジトリのルートで、コマンドプロンプトまたはエクスプローラーから:

```bat
windows\setup.bat
```

実施内容:

- ルートに `venv\` 作成
- `requirements.txt` をインストール
- `.env` が無ければ `.env.example` から作成
- `credentials\` フォルダ作成

### 3. 設定ファイル

1. ルートの `.env` を編集

```env
SPREADSHEET_KEY=（スプレッドシート URL の /d/〜/edit の ID）
CREDENTIALS_FILE=credentials/your-credentials.json
```

2. サービスアカウントの JSON を `credentials\` に配置  
3. そのサービスアカウントをスプレッドシートの共有（編集者）に追加  

**Mac で動作確認済みの `.env` と JSON をそのままコピーして使えます。**  
`CREDENTIALS_FILE` のパスは `/` 区切りのままで問題ありません。

### 4. リーダー確認（推奨）

```bat
windows\check_reader.bat
```

`PaSoRi` / `FeliCa` / `SONY` を含む名前が出れば OK です。  
何も出ない・エラーのときは、ドライバと USB を再確認してください。

### 5. 起動

```bat
REM Web UI → http://127.0.0.1:5000
windows\run_web.bat

REM CLI 出席
windows\run.bat

REM CLI カード登録 / 一覧
windows\run.bat --register
windows\run.bat --list
```

## スクリプト一覧

| ファイル | 役割 |
|----------|------|
| `setup.bat` | venv・依存関係・`.env` 初期化 |
| `check_reader.bat` | PC/SC で PaSoRi が見えるか確認 |
| `run_web.bat` | Flask Web UI 起動 |
| `run.bat` | CLI（`attendance.py`）起動 |

## トラブルシュート

| 症状 | 確認 |
|------|------|
| `python` が見つからない | PATH に Python を追加し、ターミナルを開き直す |
| PaSoRi が見つからない | NFCポートソフトウェア、USB、`check_reader.bat` |
| スプレッドシートエラー | `.env`、JSON パス、シートへの共有 |
| 直近の出席日が空 | 出席の日付が日付セルとして入っているか |

## macOS との違い

| 項目 | macOS | Windows |
|------|--------|---------|
| ドライバ | 不要 | **NFCポートソフトウェア必須** |
| セットアップ | `macos/setup.sh` | `windows/setup.bat` |
| Web 起動 | `macos/run_web.sh` | `windows/run_web.bat` |
| CLI 起動 | `macos/run.sh` | `windows/run.bat` |
| アプリ本体 | 共通 | 同じ |

macOS 手順は [`../macos/README.md`](../macos/README.md) へ。
