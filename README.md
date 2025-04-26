# Homework Forwarder Bot

> Automating the bridge between Student Groups and Parent Groups on Telegram — seamless, secure, and smart.

---

## 🚀 Project Overview

Homework Forwarder Bot is designed to:
- **Listen** for homework-related keywords in a student Telegram group.
- **Forward** only valid homework messages to the parent Telegram group.
- **Auto-delete** spam or unrelated messages to maintain a clean environment.
- **Notify Admin** about any actions or errors transparently.

---

## 🛠️ Tech Stack

- **Python 3.11+**
- **python-telegram-bot (v20.7)** — Telegram Bot Framework
- **dotenv** — Environment variable management
- **Render** — Cloud hosting and deployment
- **GitHub** — Version control & CI/CD integration
- **UptimeRobot** — Bot health monitoring

---

## 📂 Project Structure

```plaintext
telegram-bot/
│
├── main.py            # Core bot logic and message handling
├── start_bot.bat      # Optional script to start bot (for Windows users)
├── .env               # Environment variables (KEEP SECRET)
├── .gitignore         # Git ignored files/folders
├── requirements.txt   # Python dependencies
└── README.md          # Project documentation

```

---

## ⚙️ Installation Guide

```plaintext

1.Clone this Repository

git clone https://github.com/yourusername/telegram-bot.git
cd telegram-bot


2.Set Up Virtual Environment

- python -m venv venv
venv\Scripts\activate # Windows
OR
source venv/bin/activate # Linux/Mac


3.Install Dependencies:

pip install -r requirements.txt


4.Create .env File
(or set Environment Variables manually):

- TOKEN=your-telegram-bot-token
- SOURCE_GROUP_ID=your-student-group-id
- TARGET_CHAT_ID=your-parent-group-id
- ADMIN_CHAT_ID=your-admin-user-id


5.Run the Bot: python main.py

```

---

## ☁️ Deployment Guide (Render.com)

```plaintext

- Connect GitHub repository to Render.

- Add Environment Variables inside Render Dashboard.

- Set build command: pip install -r requirements.txt

- Set start command: python main.py

- Deploy and monitor bot 24/7!

```

---

## 📈 System Architecture Diagram

> (COMING SOON... stay tuned!)


---

## ✨ Future Enhancements

```plaintext

- Add command-based interactions for teachers (e.g., /announce Homework...)

- AI spam detection for better filtering

- Web Dashboard for monitoring bot activities

- Secret management using HashiCorp Vault (Corporate Level)

```

---

## 🤝 Contributing

```plaintext

Pull requests are welcome!
For major changes, please open an issue first to discuss what you would like to change.

```

---

# 📄 License

This project is open-sourced under the MIT License.


---

# 👩‍💻 Author

```plaintext

- Tenzin — Assistant Manager (Accounts) 
- aspiring Tech Innovator.


 Connect with me on:
- Telegram: བསྟེན་འཛིན། [Meto Mother]
- GitHub: Tdema604
- Email: tenzidem97@gmail.com

```

---
