 [نسخه فارسی اینجاست](./README_FA.md)

# Shahmoradi Bot

Inspired by the mind of a **legendary math genius**, built for entertainment, competition, and intelligent interaction.
A complete Telegram bot featuring points, leveling, betting, and **Gemini AI** integration.

---

## Overview

**Shahmoradi Bot** is an entertainment bot for Telegram groups that brings competition and engagement to chats.
Users earn points by sending messages, rolling dice, and solving math challenges, while also being able to place bets.
Additionally, it uses **Google Gemini** AI to provide intelligent responses to user questions.

---

## Features

### Games & Competition

* Dynamic point and level system
* Dice rolls with level-up rewards
* Smart math box challenges

### Betting

* `/bet [amount]` → Start a bet
* `/cancelbet` → Cancel an active bet
* `/mybets` → View active bets
* Bet types:

  * Even / Odd (×2)
  * Exact Number (×6)
  * Low Range 1–3 (×3)
  * High Range 4–6 (×3)

### Artificial Intelligence

* `/ai [text]` → Talk with **Google Gemini 2.5**

### Points & Levels

* `/points` → View your level and points
* `/leaderboard` → Show the top players

### Admin Commands

* `/addpoints [num]` → Add points
* `/removepoints [num]` → Remove points
* `/setpoints [num]` → Set points manually

---

## Installation

### Requirements

```bash
pip install pyrogram tgcrypto google-generativeai
```

### Run

```bash
python3 ShM.py
```

### Before Running

1. Insert your bot token in `app = Client("SM", bot_token="...")`.
2. Replace `GEMINI_API_KEY` with your actual Google API key.
3. Set admin IDs and group link at the top of the file.

---

## Project Structure

```
ShM.py
user_points.json
user_levels.json
active_bets.json
```

---

## Technical Highlights

* Dynamic leveling and point system
* Realistic betting mechanics with multipliers
* Local JSON-based storage (no database required)
* **Google Gemini AI** integration
* Modular, extendable design

---

## Developer

**Amirhossein Madani**
Telegram: [@The_Madani](https://t.me/The_Madani)
Powered by freedom, not licenses.
