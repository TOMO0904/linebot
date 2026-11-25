[English](README.md) | **日本語**

# Task Logger LINE Bot

今取り組んでいる作業を記録して時間を測り、記録が途切れると声をかけてくれるLINEのチャットボットです。AIキャラクター（Gemini）が、その日の過ごし方に親しみやすいフィードバックを返します。

## 課題

時間管理アプリは、使うこと自体を忘れがちです。いつも開いているチャットアプリから記録でき、記録が止まったら知らせてくれれば、手間の大半がなくなります。

## 解決方法

LINEで短いコマンドを送ると、ボットがFirestoreに時刻を記録し、1日のタイムラインを作ります。さらに **30分パトロール** を行い、作業が終わってから30分間新しい記録がないと警告を送ります（最大3回まで。その後は止まります）。

| コマンド | 内容 |
|---|---|
| `記録 <タスク名>` | タスクの計測を開始 |
| `終了` / `中断` | 計測を止めて記録 |
| `今日の分析` | 1日のタイムラインとAIによる評価 |
| `目標 <目標>` | 目標を設定 |
| それ以外 | AIキャラクターとの自由な会話 |

## 技術スタック

Python · Flask · LINE Messaging API（v3 SDK） · Google Gemini（`gemini-2.5-flash`） · Firebase Firestore · gunicorn

## セットアップ

```bash
pip install -r requirements.txt
cp .env.example .env
```

`.env` に `LINE_CHANNEL_ACCESS_TOKEN`、`LINE_CHANNEL_SECRET`、`GEMINI_API_KEY` を記入します。利用者を限定したい場合は `ALLOWED_USER_ID` も設定します。Firebaseコンソールからサービスアカウントの鍵をダウンロードし、手元に `firebase-key.json` として保存してください（gitの管理対象外です。絶対にコミットしないでください）。そのあと次を実行します。

```bash
python app.py
```

WebhookをHTTPSで公開し（ngrok、Renderなど）、LINE Developersに登録します。

## 補足

ボットの会話画面とキャラクターは日本語です。機能のより詳しい説明は [docs/DETAILS.ja.md](docs/DETAILS.ja.md) にあります。
