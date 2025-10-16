#!/usr/bin/env python3
import os
import aiohttp
import discord
from discord.ext import commands
from datetime import datetime
import random
import string
import re
from flask import Flask
from threading import Thread

# =====================
# ⚙️ CONFIG
# =====================
BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_PREFIX = "!"
ROLE_ID_ALLOWED = 1420109032319881266

CREATE_URL = "https://keyauth.x10.mx/api/apiv1.php"
RESET_URL_TEMPLATE = "https://keyauth.x10.mx/api/reset.php?key={key}"
MAX_KEYS_PER_COMMAND = 50

# =====================
# 🎞 GIF ICONS
# =====================
ICON_KEY = "https://i.imgur.com/poj70Ye.gif"
ICON_RESET = "https://i.imgur.com/PZgDnbB.gif"
ICON_VIP = "https://i.imgur.com/bIvsLKH.gif"
ICON_LOGO = "https://i.imgur.com/ZOajx1X.gif"

# =====================
# 🌐 KEEP ALIVE SERVER (Replit 24/7)
# =====================
app = Flask('')

@app.route('/')
def home():
    return "✅ SAITAMA BOT đang hoạt động 24/7!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# =====================
# 🤖 BOT SETUP
# =====================
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=BOT_PREFIX, intents=intents)

# =====================
# 🧩 UTILS
# =====================
