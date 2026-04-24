# 📋 Task Logger LINE Bot

LINEで行動記録・時間管理ができるチャットボットです。  
お姉さんキャラのAIが、あなたの生産性をやさしく見守ります。

## ✨ 機能一覧

| コマンド | 説明 |
|---------|------|
| `記録 〇〇` | タスクの計測を開始 |
| `終了` / `中断` | タスクの計測を終了し記録 |
| `今日の分析` | 1日のタイムラインとAI評価を表示 |
| `目標 〇〇` | 目標を設定 |
| その他のメッセージ | AIお姉さんとフリートーク |

## 🛡️ 30分パトロール機能

タスク終了後、30分以上新しい記録がないと自動で警告メッセージを送信。  
最大3回まで警告し、それ以降は監視を一時停止します。

## 🔧 技術スタック

- **Python** / Flask
- **LINE Messaging API** (v3 SDK)
- **Google Gemini AI** (gemini-2.5-flash)
- **Firebase Firestore** (データベース)

## 🚀 セットアップ

### 1. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 2. 環境変数の設定

`.env.example` を `.env` にコピーして、各APIキーを入力してください。

```bash
cp .env.example .env
```

必要な環境変数：
- `LINE_CHANNEL_ACCESS_TOKEN` — LINE Developers で取得
- `LINE_CHANNEL_SECRET` — LINE Developers で取得
- `GEMINI_API_KEY` — Google AI Studio で取得
- `ALLOWED_USER_ID` — （任意）アクセスを許可するLINEユーザーID

### 3. Firebase認証ファイル

Firebase Consoleからサービスアカウントキーをダウンロードし、`firebase-key.json` として配置してください。

### 4. 起動

```bash
python app.py
```

## 📝 注意

- `firebase-key.json` と `.env` はセキュリティのためGitには含まれていません
- 本番環境では ngrok や Render などでWebhook URLを公開してください
