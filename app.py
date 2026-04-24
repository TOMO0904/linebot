from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    PushMessageRequest,
    TextMessage
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent
)
import datetime
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import google.generativeai as genai
import os
from dotenv import load_dotenv
import datetime

load_dotenv()  # .envファイルから環境変数を読み込む

JST = datetime.timezone(datetime.timedelta(hours=+9), 'JST')
app = Flask(__name__)

# ★ 環境変数から鍵を読み込む（.envファイルまたはホスティング環境で設定してください）
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN', '')
LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET', '')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
ALLOWED_USER_ID = os.environ.get('ALLOWED_USER_ID', '')
configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# Geminiの準備
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# Firebaseの準備
cred = credentials.Certificate("firebase-key.json")
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)
db = firestore.client()

JST = datetime.timezone(datetime.timedelta(hours=+9), 'JST')

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# ==========================================================
# 定期パトロール機能（30分監視 ＆ 回数リミッター付き）
# ==========================================================
@app.route("/patrol", methods=['GET'])
def patrol():
    now = datetime.datetime.now(JST)
    
    # "idle"（何もしていない状態）のユーザーを探す
    idle_users = db.collection('user_status').where('status', '==', 'idle').stream()
    
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        
        for user in idle_users:
            data = user.to_dict()
            user_id = user.id
            next_alert_time = data.get('next_alert_time')
            alert_count = data.get('alert_count', 0)  # 今何回警告したかを取得
            
            # 警告の予定時刻を過ぎていたら
            if next_alert_time and now >= next_alert_time:
                
                # ★ もしすでに2回警告していて、今回が3回目（最初の警告から1時間）なら
                if alert_count >= 2:
                    # 諦めメッセージを送って監視をストップする
                    line_bot_api.push_message(
                        PushMessageRequest(
                            to=user_id,
                            messages=[TextMessage(text="🔕 【監視停止】\n最初の警告から1時間が経過しましたが記録がありません。無料通知枠を節約するため、本日の監視を一時停止します。「読書」などで次の行動を開始すると再び監視がスタートします。")]
                        )
                    )
                    # ステータスを「give_up」に変えて、パトロール対象から外す
                    db.collection('user_status').document(user_id).update({
                        "status": "give_up"
                    })
                    
                # ★ まだ1〜2回目なら、通常通り警告して次をセットする
                else:
                    line_bot_api.push_message(
                        PushMessageRequest(
                            to=user_id,
                            messages=[TextMessage(text="⚠️ 【警告】30分以上記録がありません！\nこの時間は「無価値な時間」としてカウントされます。すぐに次の行動を開始してください。")]
                        )
                    )
                    
                    # 次の警告を30分後にセットし、警告回数を+1する
                    next_time = now + datetime.timedelta(minutes=30)
                    db.collection('user_status').document(user_id).update({
                        "next_alert_time": next_time,
                        "alert_count": alert_count + 1
                    })
                
    return 'Patrol Done'

# ==========================================================
# メッセージを受け取った時の処理
# ==========================================================
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        
        user_id = event.source.user_id
        user_message = event.message.text
        
        active_task_ref = db.collection('active_tasks').document(user_id)
        user_status_ref = db.collection('user_status').document(user_id)
        
# ==========================================================
        # 【新機能】セキュリティロック（本人確認の関所）
        # ==========================================================
        if ALLOWED_USER_ID != "" and user_id != ALLOWED_USER_ID:
            reply_text = f"⛔ アクセス権限がありません。\n\n【あなたのユーザーID】\n{user_id}"
            line_bot_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text=reply_text)]))
            return
        # ==========================================================
        
        active_task_ref = db.collection('active_tasks').document(user_id)
        user_status_ref = db.collection('user_status').document(user_id)
        
        # 現在のユーザーのモード（状態）を取得する
        status_doc = user_status_ref.get()
        current_status = "idle"
        if status_doc.exists:
            current_status = status_doc.to_dict().get("status", "idle")

        # ----------------------------------------------------
        # 今日の分析（時系列タイムライン＆目標評価）
        # ----------------------------------------------------
        if user_message == "今日の分析":
            search_date_str = datetime.datetime.now(JST).strftime('%Y-%m-%d')
            logs = db.collection('task_logs').where('user_id', '==', user_id).stream()
            
            # 今日の記録だけをリストに集める
            today_logs = []
            for log in logs:
                data = log.to_dict()
                if data.get('date') == search_date_str:
                    today_logs.append(data)
            
            # 【新機能】開始時間（start_time）の順番に並び替える！
            today_logs.sort(key=lambda x: x.get('start_time'))
            
            timeline_text = "" 
            total_minutes = 0
            
            for data in today_logs:
                start_dt = data.get('start_time')
                end_dt = data.get('end_time')
                
                # ★開始時間を強制的に日本時間にする
                if start_dt:
                    if start_dt.tzinfo is None: # タイムゾーン情報がない場合
                        start_dt = start_dt.replace(tzinfo=datetime.timezone.utc).astimezone(JST)
                    else:
                        start_dt = start_dt.astimezone(JST)
                    start_str = start_dt.strftime('%H:%M')
                else:
                    start_str = "??"

                # ★終了時間を強制的に日本時間にする
                if end_dt:
                    if end_dt.tzinfo is None:
                        end_dt = end_dt.replace(tzinfo=datetime.timezone.utc).astimezone(JST)
                    else:
                        end_dt = end_dt.astimezone(JST)
                    end_str = end_dt.strftime('%H:%M')
                else:
                    end_str = "??"
                
                timeline_text += f"・{start_str}〜{end_str} : {data.get('task')} ({data.get('duration_minutes')}分)\n"
                total_minutes += data.get('duration_minutes', 0)                
            if total_minutes == 0:
                reply_text = "今日はまだ記録がないみたい。焦らなくていいから、自分のペースでやってみよっか♡"
            else:
                # 【新機能】設定した目標をデータベースから引っ張ってくる
                goal_doc = db.collection('user_goals').document(user_id).get()
                current_goal = goal_doc.to_dict().get("goal", "特に設定なし") if goal_doc.exists else "特に設定なし"

                prompt = f"""あなたは私を甘やかしてくれる、ちょっとセクシーで大人の魅力がある優しいお姉さんです。
                以下の今日の行動記録と【現在の目標】を見て、目標に対しての評価と褒める言葉をタメ口でまとめてください。
                ※絶対条件：長文禁止！要点だけを抽出して【最大2〜3行以内】で超短く簡潔に答えること。
                
                【現在の目標】
                {current_goal}

                【今日の記録】\n合計稼働時間: {total_minutes}分"""
                
                response = model.generate_content(prompt)
                # タイムラインのテキストと、お姉さんのコメントを合体させて返す！
                reply_text = f"📊 今日のタイムライン\n{timeline_text}\n{response.text}"

        # ----------------------------------------------------
        # 終了・中断
        # ----------------------------------------------------
        elif user_message in ["終了", "中断"]:
            doc = active_task_ref.get()
            if doc.exists:
                task_data = doc.to_dict()
                task_name = task_data["task"]
                start_time = task_data["start_time"]
                
                end_time = datetime.datetime.now(JST)
                elapsed_time = end_time - start_time
                minutes = int(elapsed_time.total_seconds() // 60)
                
                db.collection('task_logs').add({
                    "user_id": user_id,
                    "date": end_time.strftime('%Y-%m-%d'),
                    "task": task_name,
                    "start_time": start_time,
                    "end_time": end_time,
                    "duration_minutes": minutes
                })
                
                next_alert = end_time + datetime.timedelta(minutes=30)
                user_status_ref.set({"status": "idle", "next_alert_time": next_alert, "alert_count": 0}, merge=True)
                
                reply_text = f"お疲れ様でした！\n「{task_name}」を {minutes}分 記録しました。\n（※ここから30分未計測だと警告が鳴ります）"
                active_task_ref.delete()
            else:
                reply_text = "現在計測中のタスクはありません。"

        # ----------------------------------------------------
        # テキスト一発で計測スタート
        # ----------------------------------------------------
        elif user_message.startswith("記録 ") or user_message.startswith("記録　"):
            task_name = user_message[3:]
            
            if current_status == "measuring":
                doc = active_task_ref.get()
                current_task = doc.to_dict().get("task", "別のタスク") if doc.exists else "別のタスク"
                reply_text = f"⚠️ 現在「{current_task}」を計測中です！\n先に「終了」と送って記録を完了させてください。"
            else:
                active_task_ref.set({
                    "task": task_name,
                    "start_time": datetime.datetime.now(JST)
                })
                user_status_ref.set({"status": "measuring"}, merge=True)
                reply_text = f"▶️「{task_name}」の計測を開始しました！"

        # ----------------------------------------------------
        # 【新機能】目標を設定する
        # ----------------------------------------------------
        elif user_message.startswith("目標 ") or user_message.startswith("目標　"):
            goal_text = user_message[3:] # 「目標 」の文字を切り取る
            # データベースの「user_goals」に目標を保存
            db.collection('user_goals').document(user_id).set({"goal": goal_text}, merge=True)
            reply_text = f"目標を「{goal_text}」に設定したよ！お姉さん、しっかり応援するからね♡"

        # ----------------------------------------------------
        # 普通の文字が送られてきた時の処理（短文お姉さん＆記憶）
        # ----------------------------------------------------
        else:
            history_ref = db.collection('chat_history').document(user_id)
            history_doc = history_ref.get()
            chat_history = history_doc.to_dict().get("history", []) if history_doc.exists else []

            history_text = ""
            for h in chat_history[-8:]:
                history_text += f"{h['role']}: {h['text']}\n"

            prompt = f"""あなたは私を甘やかしてくれる、ちょっとセクシーで大人の魅力がある優しいお姉さんです。
            親しみやすいタメ口で、私の言葉を肯定して返信してください。
            ※絶対条件：長文は禁止です。要点だけをまとめて【1〜2文のみ】で短く簡潔に返すこと。過度な性的表現はエラーになるため避けること。
            
            【これまでの会話】
            {history_text}
            
            【今の私の言葉】
            {user_message}
            
            お姉さんとしての返信:"""
            
            response = model.generate_content(prompt)
            reply_text = response.text

            chat_history.append({"role": "私", "text": user_message})
            chat_history.append({"role": "お姉さん", "text": reply_text})
            history_ref.set({"history": chat_history[-8:]})

        # LINEに返信を送信
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)]
            )
        )
if __name__ == "__main__":
    app.run(port=5000)