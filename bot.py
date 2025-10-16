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
def has_role_allowed():
    async def predicate(ctx):
        return any(role.id == ROLE_ID_ALLOWED for role in ctx.author.roles)
    return commands.check(predicate)


def generate_saitama_key(custom: str = None):
    """Tạo key SAITAMA-XXXXX hoặc custom."""
    if custom:
        return f"SAITAMA-{custom.upper()}"
    return f"SAITAMA-{''.join(random.choices(string.ascii_uppercase + string.digits, k=5))}"


async def call_create_key(session: aiohttp.ClientSession, key: str, expiry: str):
    """Gọi API PHP tạo key."""
    expiry = expiry.lower()

    if expiry == "permanent":
        params = {
            "action": "create",
            "plan": "permanent",
            "custom_key": key
        }
    else:
        match = re.match(r"^\+?(\d+)d$", expiry)
        duration_days = int(match.group(1)) if match else 1
        params = {
            "action": "create",
            "plan": f"{duration_days}d",
            "duration_days": duration_days,
            "custom_key": key
        }

    try:
        async with session.get(CREATE_URL, params=params, timeout=20) as resp:
            return resp.status, await resp.json(content_type=None)
    except Exception as e:
        return -1, {"status": "error", "message": str(e)}


async def call_reset_key(session: aiohttp.ClientSession, key: str):
    """Gọi API reset key."""
    url = RESET_URL_TEMPLATE.format(key=aiohttp.helpers.quote(key, safe=''))
    try:
        async with session.get(url, timeout=20) as resp:
            return resp.status, await resp.text()
    except Exception as e:
        return -1, str(e)


# =====================
# 🚀 COMMANDS
# =====================
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} ({bot.user.id})")
    await bot.change_presence(activity=discord.Game(name=f"{BOT_PREFIX}helpkeys để xem hướng dẫn"))


# ----- CREATEKEY -----
@bot.command(name="createkey")
@has_role_allowed()
async def createkey(ctx, quantity: int = 1, expiry: str = None, custom: str = None):
    """Tạo key: !createkey <số lượng> [thời hạn] [custom_key]"""
    async with ctx.typing():
        if quantity < 1 or quantity > MAX_KEYS_PER_COMMAND:
            await ctx.reply(f"❌ Số lượng phải từ 1 tới {MAX_KEYS_PER_COMMAND}.")
            return

        expiry_norm = expiry.lower() if expiry else "+1d"

        # Nếu có custom → chỉ tạo 1 key custom
        if custom:
            keys_to_create = [generate_saitama_key(custom)]
        else:
            keys_to_create = [generate_saitama_key() for _ in range(quantity)]

        results = []
        async with aiohttp.ClientSession() as session:
            for k in keys_to_create:
                status, data = await call_create_key(session, k, expiry_norm)
                results.append((k, data))

        success_keys = [d.get('license_key', k) for k, d in results if d.get("status") == "success"]
        failed_keys = [k for k, d in results if d.get("status") != "success"]

        embed = discord.Embed(
            title="✨ TẠO KEY THÀNH CÔNG ✨" if success_keys else "⚠️ TẠO KEY THẤT BẠI ⚠️",
            description=f"👤 **Người yêu cầu:** {ctx.author.mention}\n🕓 **Thời hạn:** `{expiry_norm}`\n🔢 **Số lượng:** `{len(keys_to_create)}`",
            color=0x2ecc71 if success_keys else 0xe74c3c,
            timestamp=datetime.utcnow()
        )

        if success_keys:
            embed.add_field(name="✅ Key(s) thành công", value="\n".join(f"`{k}`" for k in success_keys), inline=False)
        if failed_keys:
            embed.add_field(name="❌ Key(s) thất bại", value="\n".join(f"`{k}`" for k in failed_keys), inline=False)

        embed.set_thumbnail(url=ICON_VIP if expiry_norm == "permanent" else ICON_KEY)
        embed.set_footer(text="Hệ thống KeyAuth • SAITAMA VN", icon_url=ICON_LOGO)
        await ctx.send(embed=embed)


# ----- RESETKEY -----
@bot.command(name="resetkey")
@has_role_allowed()
async def resetkey(ctx, *keys: str):
    if not keys:
        await ctx.reply("❌ Vui lòng nhập ít nhất 1 key để reset.")
        return

    async with ctx.typing():
        results = []
        async with aiohttp.ClientSession() as session:
            for k in keys:
                status, text = await call_reset_key(session, k)
                if "not found" in text.lower() or status != 200:
                    results.append((k, "fail"))
                else:
                    results.append((k, "success"))

        success_keys = [k for k, s in results if s == "success"]
        failed_keys = [k for k, s in results if s == "fail"]

        embed = discord.Embed(
            title="♻️ KẾT QUẢ RESET KEY ♻️",
            description=f"👤 **Yêu cầu bởi:** {ctx.author.mention}",
            color=0x3498db,
            timestamp=datetime.utcnow()
        )

        if success_keys:
            embed.add_field(name="✅ Thành công", value="\n".join(f"`{k}`" for k in success_keys), inline=False)
        if failed_keys:
            embed.add_field(name="⚠️ Thất bại", value="\n".join(f"`{k}`" for k in failed_keys), inline=False)

        embed.set_thumbnail(url=ICON_RESET)
        embed.set_footer(text="Hệ thống KeyAuth • SAITAMA VN", icon_url=ICON_LOGO)
        await ctx.send(embed=embed)


# ----- HELPKEYS -----
@bot.command(name="helpkeys")
async def helpkeys(ctx):
    embed = discord.Embed(
        title="📘 HƯỚNG DẪN HỆ THỐNG KEYAUTH",
        description="Hệ thống quản lý key tự động dành cho **SAITAMA VN Team** 🚀",
        color=0xf1c40f,
        timestamp=datetime.utcnow()
    )

    embed.add_field(
        name="🔑 !createkey `<số lượng>` `[thời hạn]` `[tùy chọn]`",
        value=(
            "▫️ `!createkey 3 +7d` → tạo 3 key random, hạn 7 ngày\n"
            "▫️ `!createkey 1 +7d VIPUSER` → tạo 1 key tên `SAITAMA-VIPUSER`, hạn 7 ngày\n"
            "▫️ `!createkey 1 permanent` → tạo 1 key vĩnh viễn\n"
            "▫️ `!createkey 1 permanent VIPUSER` → tạo key `SAITAMA-VIPUSER` vĩnh viễn"
        ),
        inline=False
    )

    embed.add_field(
        name="♻️ !resetkey `<key1>` `[key2] ...`",
        value="Reset một hoặc nhiều key cùng lúc.\nVí dụ: `!resetkey SAITAMA-ABC SAITAMA-XYZ`",
        inline=False
    )

    embed.set_footer(text="Hệ thống KeyAuth • SAITAMA VN", icon_url=ICON_LOGO)
    await ctx.send(embed=embed)


# =====================
# 🏁 RUN BOT
# =====================
if __name__ == "__main__":
    keep_alive()  # ✅ Giữ bot online 24/7 trên Replit
    bot.run(BOT_TOKEN)
