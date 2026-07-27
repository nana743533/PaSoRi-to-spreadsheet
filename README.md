# PaSoRi 出席管理システム

SONY PaSoRi **RC-S300** に **NTAG215 カード**をかざして、出席・退勤を Google スプレッドシートに自動記録します。

アプリ本体（`app.py` / `attendance.py`）は共通です。**OS ごとのセットアップはフォルダを分けています。**

| OS | フォルダ | ドライバ |
|----|----------|----------|
| **macOS** | [`macos/`](macos/README.md) | 不要（OS 標準） |
| **Windows** | [`windows/`](windows/README.md) | **NFCポートソフトウェア必須** |

## 必要なもの（共通）

| 機器 | 備考 |
|------|------|
| SONY PaSoRi RC-S300 | USB 接続 |
| NTAG215 カード | NFC Forum Type 2 Tag |
| Python 3.12+ | |
| Google サービスアカウント | `credentials/` に JSON を配置 |

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
先に Sony の **NFCポートソフトウェア** をインストールしてください。

```bat
windows\setup.bat
REM .env を編集し、credentials\ に JSON を配置
windows\check_reader.bat
windows\run_web.bat
```

## 使い方（起動後）

- **Web UI**: ブラウザで http://127.0.0.1:5000 （出席 / 退勤 / UID確認）
- **CLI**: `macos/run.sh` または `windows/run.bat`（`--register` / `--list` 可）

## スプレッドシート構造

### 名簿シート
| A: 会員番号 | B: 氏名 | ... | J: カードID |
|------------|---------|-----|-------------|

### 出席シート
| A: 日付 | B: 氏名 | C: 開始時刻 | D: 終了時刻 |
|---------|---------|------------|------------|

## 技術構成

| 層 | 技術 |
|----|------|
| カード通信 | PC/SC（macOS 標準 / Windows は NFCポートソフトウェア経由） |
| Python ラッパー | pyscard |
| Web UI | Flask |
| データ保存 | Google Sheets（gspread） |
| 認証 | Google サービスアカウント |

## 免責事項

- RC-S300 は Sony の登録商標です
- NTAG215 は NXP Semiconductors の登録商標です
- 本ソフトウェアは非公式の個人プロジェクトです

## ライセンス

MIT License
