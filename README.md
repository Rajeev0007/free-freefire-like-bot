# 🔍 Free Fire Like Bot

![Status](https://img.shields.io/badge/status-active-brightgreen)

A Discord bot and Flask server that allows you to automatically like Free Fire profiles via their user ID.  
Includes advanced features like channel restrictions, cooldowns, JSON config, and support for both RapidAPI and a self-hosted API.

---

## 📌 Table of Contents

- [🚀 Features](#-features)
- [🧰 Requirements](#-requirements)
- [⚙️ Installation](#-installation)
- [💬 Usage](#-usage)
- [🤖 Create a Discord Bot](#-create-a-discord-bot)
- [🌐 Custom or Public API](#-custom-or-public-api)
- [📤 Example Output](#-example-output)
- [🛠 Technologies Used](#-technologies-used)
- [📄 License](#-license)
- [👨‍💻 Author](#-author)

---

## 🚀 Features

- ✅ `/like <uid>`: Send likes to Free Fire users.
- 🔐 `/setlikechannel <channel>`: Restrict usage to selected channels.
- 🔁 Per-user cooldown (30 seconds).
- 🧠 Channel config saved in `like_channels.json`.
- 📡 Flask web server at `http://localhost:10000` for status.
- 🔑 Secure token/key storage via `.env`.
- 🌐 Choose between RapidAPI or your own hosted API.
- 📊 Embedded responses with like count before/after.

---

## 🧰 Requirements

- Python 3.10+
- A Discord bot token with **Message Content Intent** enabled (Developer Portal → Bot → Privileged Gateway Intents)
- A RapidAPI key **or** a self-hosted API server
- A `.env` file containing:

```ini
TOKEN=your_discord_bot_token
RAPIDAPI_KEY=your_rapidapi_key_or_custom_api_key
# Optional: use your own API instead of RapidAPI
# API_HOST=http://localhost:5000
 ```

## Installation

1. Clone this repository:
   ```sh
   git clone https://github.com/Rajeev0007/free-freefire-like-bot
   cd free-freefire-like-bot
   ```
2. Create and activate a virtual environment:
   ```sh
   python -m venv .venv
   source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```



4. Copy `.env.example` to `.env` and fill it in:
   ```sh
   cp .env.example .env      # Windows: copy .env.example .env
   ```

5. Run the bot:
   ```sh
   python app.py
   ```





## Usage

- Use `/like <user_id> [region]` in a Discord server where the bot is present. The region is optional (default comes from `DEFAULT_REGION`).
- Use `/setlikechannel <channel>`  to toggle allowed channels for the like command.

    


## 🛠️ Create a Discord Bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications).
2. Click **"New Application"**, and give your bot a name.
3. In the left sidebar, go to the **"Bot"** section and click **"Add Bot"**, then confirm with **"Yes, do it!"**.
4. Under the **Token** section, click **"Reset Token"** or **"Copy"** to get your `TOKEN`.
   On the same page, turn on **Message Content Intent** (needed for `!like`). Without it the bot cannot log in.
5. Go to **"General Information"** and copy the `APPLICATION_ID`.
6. Paste both values into your `.env` file:
      ```ini
   TOKEN=your_bot_token
   
   ```
6. If you don't have api like you can go to rapid api to create account in link  `.env` file: https://rapidapi.com/greatthug/api/free-fire-like1
      ```ini
   RAPIDAPI_KEY=your api key from rapid api
   
   ```

## 🌐 Custom or Public API

### ✅ Option 1: Use RapidAPI

1. Go to [Free Fire Like API on RapidAPI](https://rapidapi.com/greatthug/api/free-fire-like1).
2. Subscribe and get your API key.
3. Paste it in your `.env` file:

```ini
RAPIDAPI_KEY=your_key_here
```


### ✅ Option 2: Use Your Own API

**1. Download and install the API** (in a separate folder from the bot):

```sh
git clone https://github.com/paulafredo/free-fire-like-api
cd free-fire-like-api
pip install -r requirements.txt
```

**2. Add fresh tokens.** The token files in `tokens/` expired in August 2025, so replace them with tokens from Free Fire guest accounts you own:

| Region | File |
|--------|------|
| IND | `tokens/token_ind.json` |
| BR, US, SAC, NA | `tokens/token_br.json` |
| Everything else | `tokens/token_bd.json` |

Each file looks like `[{"token": "eyJ..."}, {"token": "eyJ..."}]`. Tokens expire, so you will need to replace them from time to time. The author's tutorials are linked in that repo's README.

**3. Start the API:**

```sh
python app.py
```

Check it works by opening `http://127.0.0.1:5000/like?uid=YOUR_UID&server=IND` in your browser.

**4. Point the bot at it** in the bot's `.env`:

```ini
API_HOST=http://127.0.0.1:5000
RAPIDAPI_KEY=
DEFAULT_REGION=IND
```

Users can then run `/like 123456789` (uses `DEFAULT_REGION`) or `/like 123456789 BR`.

If the API suddenly stops working after a Free Fire update, change `"ReleaseVersion": "OB51"` in its `app.py` to the new game version.

> ⚠ This sends likes through Free Fire's game servers using many accounts. That breaks Garena's terms of service, and the accounts you use can be banned.

## Example Output
![image](https://github.com/user-attachments/assets/de73e78c-cb1b-4ce4-8795-474ba685fa06)



## Technologies Used

- Python
- Discord.py
- Flask
- dotenv
- aiohttp

## License

This project is licensed under the MIT License. Feel free to use and modify it.

## Author

[Paul Alfredo](https://github.com/paulafredo)

