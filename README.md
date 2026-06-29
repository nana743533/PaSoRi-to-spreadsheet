# PaSoRi 出席管理システム

SONY PaSoRi **RC-S300** に **NTAG215 カード**をかざして、出席・退勤を Google スプレッドシートに自動記録します。

## 必要なもの

| 機器 | 備考 |
|------|------|
| SONY PaSoRi RC-S300 | USB-C 変換アダプタで接続 |
| NTAG215 カード | NFC Forum Type 2 Tag |
| macOS 13+ | ドライバ不要（OS標準で認識） |
| Python 3.12+ | |

## セットアップ

```bash
# 1. 仮想環境を作成
python3 -m venv venv
source venv/bin/activate

# 2. 依存パッケージをインストール
pip install pyscard gspread google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client

# 3. 環境変数を設定（.env.example をコピーして編集）
cp .env.example .env
# .env にスプレッドシートキーと認証ファイルパスを記入

# 4. Google サービスアカウントの認証JSONを credentials/ に配置
```

## 使い方

```bash
source venv/bin/activate

# 出席モード（デフォルト）
python attendance.py

# カード登録モード
python attendance.py --register

# 登録済みカード一覧
python attendance.py --list
```

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
| カード通信 | PC/SC（macOS 標準） |
| Python ラッパー | pyscard |
| データ保存 | Google Sheets（gspread） |
| 認証 | Google サービスアカウント |

## 免責事項

- RC-S300 は Sony の登録商標です
- NTAG215 は NXP Semiconductors の登録商標です
- 本ソフトウェアは非公式の個人プロジェクトです

## ライセンス

MIT License
