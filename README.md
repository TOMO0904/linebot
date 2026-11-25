[English](README.md) | [日本語](README.ja.md)

# Task Logger LINE Bot

A LINE chatbot that logs what you are working on, tracks time, and nudges you when you go quiet. An AI persona (Gemini) gives friendly feedback on your day.

## Problem

Time-tracking apps are easy to forget. Logging from the chat app you already have open — and getting a reminder when you stop logging — removes most of the friction.

## Solution

Send short commands in LINE; the bot records timestamps in Firestore, builds a daily timeline, and runs a **30-minute patrol**: if no new record appears for 30 minutes after a task ends, it sends a warning (up to 3, then pauses).

| Command (Japanese UI) | What it does |
|---|---|
| `記録 <task>` | Start timing a task |
| `終了` / `中断` | Stop and record the task |
| `今日の分析` | Daily timeline plus AI evaluation |
| `目標 <goal>` | Set a goal |
| anything else | Free chat with the AI persona |

## Tech stack

Python · Flask · LINE Messaging API (v3 SDK) · Google Gemini (`gemini-2.5-flash`) · Firebase Firestore · gunicorn

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env`: `LINE_CHANNEL_ACCESS_TOKEN`, `LINE_CHANNEL_SECRET`, `GEMINI_API_KEY`, and optionally `ALLOWED_USER_ID` to restrict access. Download a Firebase service-account key from the Firebase console and save it locally as `firebase-key.json` (it is git-ignored — never commit it). Then:

```bash
python app.py
```

Expose the webhook over HTTPS (ngrok, Render, etc.) and register it in LINE Developers.

## Notes

The bot's chat UI and persona are in Japanese. A Japanese README is available: [README.ja.md](README.ja.md).
