# Telegram Homework Forwarder Bot

A professional, automated Telegram bot system that forwards homework messages from a **Student Group** to a **Parent Group** based on specific keywords, ensuring streamlined communication between teachers and parents.  
Spam and non-homework messages are automatically filtered and deleted to maintain a clean environment.

---

## 🚀 Features

- **Keyword-Based Forwarding:**  
  Forwards only homework-related messages (e.g., containing "homework", "assignment", "worksheet").

- **Spam Filtering:**  
  Deletes irrelevant messages automatically from the Student Group.

- **Admin Notification:**  
  Notifies the admin when inappropriate content is deleted.

- **Environment-Based Secrets:**  
  Uses a `.env` file to manage sensitive credentials securely.

- **Auto-Deployment:**  
  Powered by **GitHub**, **Render.com**, and **UptimeRobot** for 24/7 uptime without manual restarts.

---

## 🛠️ Tech Stack

- Python 3.11+
- python-telegram-bot 20.7
- Flask 2.3.3 (for potential webhook support)
- Gunicorn 20.1.0
- Render.com (Hosting)
- GitHub (Version Control)
- UptimeRobot (Monitoring)

---

## 🛡️ Environment Variables

Create a `.env` file in your project root:

- TOKEN=your-telegram-bot-token

- SOURCE_GROUP_ID=your-student-group-id

- TARGET_CHAT_ID=your-parent-group-id

- ADMIN_CHAT_ID=your-admin-user-id

`(Keep this file secret — 
never push it to GitHub.)`

---

## 📂 Project Structure


telegram-bot/
│
├── main.py            # Main bot logic
├── start_bot.bat      # Script to easily run the bot locally
├── .env               # Environment file (not pushed to GitHub)
├── .gitignore         # Ignore sensitive files like .env
├── requirements.txt   # Project dependencies
└── README.md          # You are here!


---

## 🚀 Local Setup Guide

**1. Clone the repository:**

git clone
 https://github.com/your-username/telegram-bot.git

cd telegram-bot


2. Create virtual environment:

python -m venv venv

venv\Scripts\activate # (Windows)


** 3. Install dependencies:**

pip install -r requirements.txt


** 4. Run the bot locally:**

python main.py

---

## 🌎 Deployment (Render.com)

-**Connect GitHub to Render.com.**

-**Create a new Web Service.**

-**Set the build and start commands.**

-*"Configure environment variables in
 Render dashboard.

-**Monitor status using Render and
 UptimeRobot.

---

## 👑 Author

> Tenzin
-Assistant Manager (Accounts) 
-Visionary Technophile 
-Full-time Supermom 
-Part-time Bot Engineer