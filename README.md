# Mbot - Telegram AI Bot

This repository contains a simple Telegram AI bot that forwards user messages to OpenAI's Chat API and returns replies.

Files added:
- bot.py - main bot program (Python)
- requirements.txt - Python dependencies
- README.md - setup and deployment instructions (Arabic)
- .env.example - example environment variables (DO NOT commit secrets)
- .gitignore - ignore .env and pycache
- Dockerfile - container image
- Procfile - for Heroku-style deployments

Important security note: I did NOT commit any secret tokens or API keys. You must set TELEGRAM_TOKEN and OPENAI_API_KEY in environment variables or GitHub/host secrets before running.
