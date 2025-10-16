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
import secrets
import asyncio

# =====================
# ⚙️ CONFIG
# =====================
BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_PREFIX = "/"
ROLE_ID_ALLOWED = 1420109032319881266

CREATE_URL = "https://keyauth.x10.mx/api/apiv1.php"
RESET_URL_TEMPLATE = "https://keyauth.x10.mx/api/reset.php?key={key}"
MAX_KEYS_PER_COMMAND = 50
INTERACTIVE_TIMEOUT = 60  # giây cho mỗi câu hỏi trong flow tương tác

# =====================
# 🎞 GIF ICONS
# =====================
ICON_KEY = "https://i.imgur.com/poj70Ye.gif"
ICON_RESET = "https://i.imgur.com/PZgDnbB.gif"
ICON_VIP = "https://i.imgur.com/bIvsLKH.gif"
ICON_LOGO = "https://i.imgur.com/ZOajx1X.gif"

# =====================
# 🌐 KEEP ALIVE SERVER (Replit/Render)
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
    hex_part = secrets.token_hex(7).upper()[:13]
    if custom:
        safe = re.sub(r'[^A-Za-z0-9\-_]', '', custom)[:12].upper()
        return f"{hex_part}/{safe}"
    return hex_part


# ✅ ĐÃ SỬA Ở ĐÂY — đổi từ GET → POST để Render không lỗi 415
async def call_create_key(session: aiohttp.ClientSession, key: str, expiry: str, app_id: str, allowed_devices: int):
    expiry = expiry.lower()

    params = {
        "action": "create",
        "custom_key": key,
        "app_id": app_id or "",
    }

    if allowed_devices == -1:
        params["unlimited_devices"] = "1"
        params["allowed_devices"] = "-1"
    else:
        params["allowed_devices"] = str(max(1, int(allowed_devices)))

    if expiry == "permanent":
        params["plan"] = "permanent"
    else:
        m = re.match(r"^\+?(\d+)d$", expiry)
        if m:
            days = int(m.group(1))
            params["plan"] = f"{days}d"
            params["duration_days"] = str(days)
        else:
            params["plan"] = "1d"
            params["duration_days"] = "1"

    try:
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        async with session.post(CREATE_URL, data=params, headers=headers, timeout=20) as resp:
            text = await resp.text()
            try:
                data = await resp.json(content_type=None)
            except Exception:
                data = {}
                for line in text.splitlines():
                    if '=' in line:
                        k, v = line.split('=', 1)
                        data[k.strip()] = v.strip()
                if not data:
                    data = {"status": "error", "message": text}
            return resp.status, data
    except Exception as e:
        return -1, {"status": "error", "message": str(e)}


async def call_reset_key(session: aiohttp.ClientSession, key: str):
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
async def createkey(ctx, *args):
    """
    Usage examples:
    /createkey 3 +7d app:aimbot devices:3
    /createkey 1 permanent app:silent devices:unlimited VIPUSER
    Or just /createkey (interactive mode)
    """
    async with ctx.typing():
        # parse positional args first
        # we support interactive mode if no args
        if len(args) == 0:
            # interactive flow
            author = ctx.author

            def check(m):
                return m.author == author and m.channel == ctx.channel

            await ctx.send(f"{author.mention} Nhập số lượng (1-{MAX_KEYS_PER_COMMAND}):")
            try:
                msg = await bot.wait_for('message', check=check, timeout=INTERACTIVE_TIMEOUT)
                quantity = int(msg.content.strip())
                if quantity < 1 or quantity > MAX_KEYS_PER_COMMAND:
                    await ctx.send(f"❌ Số lượng không hợp lệ, sử dụng 1.")
                    quantity = 1
            except Exception:
                quantity = 1

            await ctx.send("Nhập thời hạn (ví dụ: +1d, +7d, permanent). Mặc định +1d:")
            try:
                msg = await bot.wait_for('message', check=check, timeout=INTERACTIVE_TIMEOUT)
                expiry = msg.content.strip() or "+1d"
            except Exception:
                expiry = "+1d"

            await ctx.send("Chọn app (ví dụ: aimbot, silent, esp, premium). Gõ 'default' nếu bỏ qua:")
            try:
                msg = await bot.wait_for('message', check=check, timeout=INTERACTIVE_TIMEOUT)
                app_id = msg.content.strip() or ""
            except Exception:
                app_id = ""

            await ctx.send("Giới hạn thiết bị (số nguyên như 1,3) hoặc 'unlimited'. Mặc định 1:")
            try:
                msg = await bot.wait_for('message', check=check, timeout=INTERACTIVE_TIMEOUT)
                dev_raw = msg.content.strip().lower() or "1"
            except Exception:
                dev_raw = "1"

            if dev_raw == "unlimited":
                allowed_devices = -1
            else:
                try:
                    allowed_devices = max(1, int(dev_raw))
                except:
                    allowed_devices = 1

            await ctx.send("Nếu cần custom key, gõ chuỗi custom (no spaces). Nếu không, gõ 'no':")
            try:
                msg = await bot.wait_for('message', check=check, timeout=INTERACTIVE_TIMEOUT)
                custom = msg.content.strip()
                if custom.lower() == 'no' or custom == '':
                    custom = None
            except Exception:
                custom = None

        else:
            # parse inline args
            # args example: 3 +7d app:aimbot devices:3 VIPUSER
            quantity = 1
            expiry = "+1d"
            app_id = ""
            allowed_devices = 1
            custom = None

            # first token that is integer -> quantity
            for a in list(args):
                if re.fullmatch(r"\d+", a):
                    quantity = int(a)
                    continue
                if a.lower().startswith('+') or a.lower() == 'permanent' or re.fullmatch(r"\d+d", a.lower()):
                    expiry = a
                    continue
                if a.lower().startswith("app:"):
                    app_id = a.split(":",1)[1]
                    continue
                if a.lower().startswith("devices:"):
                    dv = a.split(":",1)[1]
                    if dv.lower() == "unlimited":
                        allowed_devices = -1
                    else:
                        try:
                            allowed_devices = int(dv)
                        except:
                            allowed_devices = 1
                    continue
                # last free token -> custom
                custom = a

            # normalize expiry
            expiry = expiry or "+1d"

            # ensure quantity bounds
            quantity = max(1, min(MAX_KEYS_PER_COMMAND, int(quantity)))

        # Build keys to create
        keys_to_create = []
        if custom:
            # when custom provided, only create one with that custom
            keys_to_create = [generate_saitama_key(custom)]
            quantity = 1
        else:
            for _ in range(quantity):
                keys_to_create.append(generate_saitama_key())

        results = []
        async with aiohttp.ClientSession() as session:
            for k in keys_to_create:
                status, data = await call_create_key(session, k, expiry, app_id, allowed_devices)
                results.append((k, data))

        success_keys = [ (d.get('license_key') or k) for k,d in results if d.get("status") in ("success","ok", True) or d.get("success") == True ]
        failed = [ (k, d) for k,d in results if d.get("status") not in ("success","ok", True) and d.get("success") != True ]

        embed = discord.Embed(
            title="✨ TẠO KEY THÀNH CÔNG ✨" if success_keys else "⚠️ TẠO KEY THẤT BẠI ⚠️",
            description=f"👤 **Người yêu cầu:** {ctx.author.mention}\n🕓 **Thời hạn:** `{expiry}`\n🔢 **Số lượng yêu cầu:** `{len(keys_to_create)}`\n🔧 **App:** `{app_id or 'none'}`\n📱 **Giới hạn thiết bị:** `{('Không giới hạn' if allowed_devices==-1 else allowed_devices)}`",
            color=0x2ecc71 if success_keys else 0xe74c3c,
            timestamp=datetime.utcnow()
        )

        if success_keys:
            embed.add_field(name="✅ Key(s) thành công", value="\n".join(f"`{k}`" for k in success_keys), inline=False)
        if failed:
            embed.add_field(name="❌ Key(s) thất bại", value="\n".join(f"`{k}` ({(d.get('message') or d)})" for k,d in failed), inline=False)

        embed.set_thumbnail(url=ICON_VIP if expiry == "permanent" else ICON_KEY)
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
        name="🔑 /createkey `<số lượng>` `[thời hạn]` `[tùy chọn]`",
        value=(
            "▫️ `/createkey 3 +7d app:aimbot devices:3` → tạo 3 key random, hạn 7 ngày, app aimbot, tối đa 3 thiết bị\n"
            "▫️ `/createkey 1 +7d app:aimbot devices:3 VIPUSER` → tạo 1 key custom `VIPUSER`\n"
            "▫️ `/createkey` → chạy interactive flow để nhập từng thông tin\n"
            "▫️ `/createkey 1 permanent app:silent devices:unlimited` → tạo key vĩnh viễn cho silent không giới hạn thiết bị\n"
        ),
        inline=False
    )

    embed.add_field(
        name="♻️ /resetkey `<key1>` `[key2] ...`",
        value="Reset một hoặc nhiều key cùng lúc.\nVí dụ: `/resetkey SAITAMA-ABC SAITAMA-XYZ`",
        inline=False
    )

    embed.set_footer(text="Hệ thống KeyAuth • SAITAMA VN", icon_url=ICON_LOGO)
    await ctx.send(embed=embed)

# =====================
# 🏁 RUN BOT
# =====================
if __name__ == "__main__":
    keep_alive()
    bot.run(BOT_TOKEN)
    