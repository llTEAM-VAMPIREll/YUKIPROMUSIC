import os
import time
import sys
import requests
import math
import aiohttp
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery

from SHUKLAMUSIC import app
from SHUKLAMUSIC.core.call import SHUKLA
from SHUKLAMUSIC.utils.database import get_playmode, get_playtype, is_nonadmin_chat
from SHUKLAMUSIC.utils.decorators import language
from SHUKLAMUSIC.utils.inline.settings import playmode_users_markup
from config import BANNED_USERS

# ==========================================
# 🔥 HELLFIRE DEVS HACK: Raw API Functions
# ==========================================
def api_btn(text, callback_data=None, url=None, style=None, custom_emoji_id=None):
    btn = {"text": text}
    if callback_data: btn["callback_data"] = callback_data
    if url: btn["url"] = str(url)
    if style in ["primary", "danger", "success"]: btn["style"] = style  
    if custom_emoji_id: btn["icon_custom_emoji_id"] = str(custom_emoji_id) 
    return btn

async def inject_premium_markup(chat_id, message_id, markup):
    try:
        url = f"https://api.telegram.org/bot{app.bot_token}/editMessageReplyMarkup"
        payload = {"chat_id": chat_id, "message_id": message_id}
        if markup:  # Only add if markup is not empty
            payload["reply_markup"] = {"inline_keyboard": markup}
            
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                if resp.status != 200:
                    print(f"❌ API Injection Error: {await resp.text()}")
    except Exception as e: 
        print(f"❌ Exception in inject_premium_markup: {e}")

async def edit_premium_text(chat_id, message_id, text, markup=None):
    try:
        url = f"https://api.telegram.org/bot{app.bot_token}/editMessageText"
        payload = {
            "chat_id": chat_id, 
            "message_id": message_id, 
            "text": text, 
            "parse_mode": "HTML"
        }
        if markup:  # Only add if markup is not empty
            payload["reply_markup"] = {"inline_keyboard": markup}
            
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                if resp.status != 200:
                    print(f"❌ API Edit Error: {await resp.text()}")
    except Exception as e: 
        print(f"❌ Exception in edit_premium_text: {e}")

# ==========================================
# 🎛️ PLAYMODE COMMAND (Cleaned)
# ==========================================
@app.on_message(filters.command(["playmode", "mode"], prefixes=["/", "!", "%", ",", ".", "@", "#"]) & filters.group & ~BANNED_USERS)
@language
async def playmode_(client, message: Message, _):
    playmode = await get_playmode(message.chat.id)
    Direct = True if playmode == "Direct" else None
    
    is_non_admin = await is_nonadmin_chat(message.chat.id)
    Group = None if is_non_admin else True
    
    playty = await get_playtype(message.chat.id)
    Playtype = None if playty == "Everyone" else True
    
    buttons = playmode_users_markup(_, Direct, Group, Playtype)
    original_text = f"<blockquote><b><emoji id='6080202089311507876'>😎</emoji> ᴘʟᴀʏᴍᴏᴅᴇ sᴇᴛᴛɪɴɢs ғᴏʀ:</b> {message.chat.title}</blockquote>"
    
    await message.reply_text(
        text=original_text,
        reply_markup=InlineKeyboardMarkup(buttons),
    )

# ==========================================
# 📺 HELLFIRE LIVE TV LOGIC & PARSING
# ==========================================
IPTV_URL = "https://iptv-org.github.io/iptv/languages/hin.m3u"
CACHED_CHANNELS = {}

def load_iptv_data():
    global CACHED_CHANNELS
    if CACHED_CHANNELS: return CACHED_CHANNELS
    try:
        response = requests.get(IPTV_URL)
        lines = response.text.splitlines()
        current_cat = "Other"
        current_name = "Unknown"
        
        for line in lines:
            if line.startswith("#EXTINF"):
                if 'group-title="' in line:
                    cat_start = line.find('group-title="') + 13
                    cat_end = line.find('"', cat_start)
                    current_cat = line[cat_start:cat_end]
                current_name = line.split(",")[-1].strip()
            elif line.startswith("http"):
                if current_cat not in CACHED_CHANNELS:
                    CACHED_CHANNELS[current_cat] = []
                CACHED_CHANNELS[current_cat].append({"name": current_name, "url": line})
        return CACHED_CHANNELS
    except: return {}

# 🔥 DM (PRIVATE MESSAGE) BLOCKER
@app.on_message(filters.command(["playtv", "tv", "livestop", "stoplive"], prefixes=["/", "!", "%", ",", ".", "@", "#"]) & filters.private & ~BANNED_USERS)
async def playtv_pm_block(client, message: Message):
    await message.reply_text("<blockquote><emoji id='6001602353843672777'>⚠️</emoji> <b>ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ᴏɴʟʏ ᴡᴏʀᴋs ɪɴ ɢʀᴏᴜᴘs!</b></blockquote>")

@app.on_message(filters.command(["playtv", "tv"], prefixes=["/", "!", "%", ",", ".", "@", "#"]) & filters.group & ~BANNED_USERS)
async def playtv_cmd(client, message: Message):
    data = load_iptv_data()
    if not data:
        return await message.reply_text("<blockquote><emoji id='5999100917645841519'>💀</emoji> <b>ғᴀɪʟᴇᴅ ᴛᴏ ʟᴏᴀᴅ ɪᴘᴛᴠ ᴄʜᴀɴɴᴇʟs.</b></blockquote>")
    
    buttons = []
    for cat in list(data.keys())[:10]: 
        buttons.append([api_btn(text=cat, callback_data=f"tvcat_{cat}_0", style="primary", custom_emoji_id="6001270898332538659")])
    buttons.append([api_btn(text="ᴄʟᴏsᴇ", callback_data="close_tv", style="danger", custom_emoji_id="5999100917645841519")])
    
    text = "<blockquote><b><emoji id='6080202089311507876'>😎</emoji> ʜᴇʟʟғɪʀᴇ ᴛᴠ ɪs ʟɪᴠᴇ!</b>\n<b>sᴇʟᴇᴄᴛ ᴀ ᴄᴀᴛᴇɢᴏʀʏ:</b></blockquote>"
    run = await message.reply_text("ʟᴏᴀᴅɪɴɢ ᴛᴠ ᴍᴇɴᴜ...")
    await edit_premium_text(message.chat.id, run.id, text, buttons)

@app.on_callback_query(filters.regex(r"^(tvcat_|playtv_|retrytv_|close_tv|playtv_main)"))
async def tv_callback(client, query: CallbackQuery):
    data = query.data
    try: await query.answer() 
    except: pass
    
    if data == "close_tv":
        return await query.message.delete()
        
    elif data.startswith("tvcat_"):
        parts = data.split("_")
        category, page = parts[1], int(parts[2])
        channels = load_iptv_data().get(category, [])
        
        per_page = 10
        total_pages = math.ceil(len(channels) / per_page)
        start_idx = page * per_page
        current_channels = channels[start_idx:start_idx + per_page]
        
        buttons = []
        for idx, ch in enumerate(current_channels):
            real_idx = start_idx + idx
            buttons.append([api_btn(text=ch['name'], callback_data=f"playtv_{category}_{page}_{real_idx}", style="primary", custom_emoji_id="6001270898332538659")])
            
        nav = []
        if page > 0: nav.append(api_btn(text="ʙᴀᴄᴋ", callback_data=f"tvcat_{category}_{page-1}", style="primary", custom_emoji_id="6001419401121765310"))
        if page < total_pages - 1: nav.append(api_btn(text="ɴᴇxᴛ", callback_data=f"tvcat_{category}_{page+1}", style="primary", custom_emoji_id="6001483331709966655"))
        if nav: buttons.append(nav)
        
        buttons.append([api_btn(text="ᴍᴀɪɴ ᴍᴇɴᴜ", callback_data="playtv_main", style="danger", custom_emoji_id="6001419401121765310")])
        text = f"<blockquote><b><emoji id='6080202089311507876'>😎</emoji> {category}</b> (ᴘᴀɢᴇ {page+1}/{total_pages})</blockquote>"
        await edit_premium_text(query.message.chat.id, query.message.id, text, buttons)

    elif data == "playtv_main":
        data = load_iptv_data()
        buttons = [[api_btn(text=cat, callback_data=f"tvcat_{cat}_0", style="primary", custom_emoji_id="6001270898332538659")] for cat in list(data.keys())[:10]]
        buttons.append([api_btn(text="ᴄʟᴏsᴇ", callback_data="close_tv", style="danger", custom_emoji_id="5999100917645841519")])
        text = "<blockquote><b><emoji id='6080202089311507876'>😎</emoji> ʜᴇʟʟғɪʀᴇ ᴛᴠ ɪs ʟɪᴠᴇ!</b>\n<b>sᴇʟᴇᴄᴛ ᴀ ᴄᴀᴛᴇɢᴏʀʏ:</b></blockquote>"
        await edit_premium_text(query.message.chat.id, query.message.id, text, buttons)

    elif data.startswith("playtv_") or data.startswith("retrytv_"):
        parts = data.split("_")
        category, page, ch_idx = parts[1], parts[2], int(parts[3])
        channel = load_iptv_data()[category][ch_idx]
        ch_name, raw_url = channel["name"], channel["url"]
        chat_id = query.message.chat.id
        
        # 🔥 CLEAN LOADING MESSAGE
        await edit_premium_text(chat_id, query.message.id, f"<blockquote><emoji id='6001419401121765310'>⏳</emoji> <b>ʟᴏᴀᴅɪɴɢ</b> `{ch_name}`...\n<b>ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ...</b></blockquote>", [])
        
        try:
            try: await SHUKLA.force_stop_stream(chat_id)
            except Exception: pass 

            clean_name = "".join(e for e in ch_name if e.isalnum()).lower()
            if not clean_name: clean_name = "stream"
                
            port = 50000 + (abs(chat_id) % 10000)
            pipe_file = f"temp_pipe_{abs(chat_id)}.py"
            log_file = f"pipe_log_{abs(chat_id)}.txt"

            pipe_code = f"""import subprocess
from flask import Flask, Response
import logging

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)

@app.route('/ping')
def ping(): return "PONG", 200

@app.route('/{clean_name}.m3u8')
def stream_tv():
    master = "{raw_url}"
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-reconnect", "1", "-reconnect_streamed", "1", "-reconnect_delay_max", "5",
        "-headers", "Referer: https://google.com/\\r\\n", 
        "-user_agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "-allowed_extensions", "ALL",
        "-protocol_whitelist", "file,http,https,tcp,tls,crypto",
        "-i", master, "-c", "copy", "-f", "mpegts", "pipe:1"
    ]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    return Response(process.stdout, mimetype="video/MP2T")

if __name__ == '__main__':
    app.run(host='127.0.0.1', port={port}, threaded=True)
"""
            with open(pipe_file, "w") as f: f.write(pipe_code)
            os.system(f"pkill -f {pipe_file}")
            time.sleep(0.5)

            os.system(f"nohup {sys.executable} {pipe_file} > {log_file} 2>&1 &")
            
            ping_link = f"http://127.0.0.1:{port}/ping"
            local_bypass_link = f"http://127.0.0.1:{port}/{clean_name}.m3u8"

            server_ready = False
            for i in range(12): 
                try:
                    res = requests.get(ping_link, timeout=1) 
                    if res.status_code == 200:
                        server_ready = True
                        break
                except Exception: pass
                time.sleep(1)

            if not server_ready:
                err_msg = "Proxy Boot Error."
                try:
                    with open(log_file, "r") as lf: err_msg += f"\\n`{lf.read()[-300:]}`"
                except: pass
                raise Exception(err_msg)

            await SHUKLA.join_call(chat_id, chat_id, local_bypass_link, video=True)
            
            text = f"<blockquote><b><emoji id='6001483331709966655'>✅</emoji> ʜᴇʟʟғɪʀᴇ ᴛᴠ ʟɪᴠᴇ!</b>\n\n<b><emoji id='6001270898332538659'>▶</emoji> ᴄʜᴀɴɴᴇʟ:</b> {ch_name}\n<b><emoji id='5999025042753590996'>🦋</emoji> ᴅɪʀᴇᴄᴛ sᴛʀᴇᴀᴍ ᴄᴏɴɴᴇᴄᴛᴇᴅ!</b></blockquote>"
            buttons = [[api_btn(text="ʙᴀᴄᴋ ᴛᴏ ᴄʜᴀɴɴᴇʟs", callback_data=f"tvcat_{category}_{page}", style="danger", custom_emoji_id="6001419401121765310")]]
            await edit_premium_text(chat_id, query.message.id, text, buttons)

        except Exception as e:
            # 🔥 CLEAN ERROR MESSAGE
            text = f"<blockquote><b><emoji id='5999100917645841519'>💀</emoji> ᴛʜɪs ᴄʜᴀɴɴᴇʟ ɪs ᴄᴜʀʀᴇɴᴛʟʏ ᴅᴏᴡɴ.</b>\n\n<b><emoji id='6001602353843672777'>⚠️</emoji> ᴘʟᴇᴀsᴇ ᴛʀʏ ᴀɴᴏᴛʜᴇʀ ᴄʜᴀɴɴᴇʟ.</b></blockquote>"
            buttons = [
                [api_btn(text="ʀᴇᴛʀʏ", callback_data=f"retrytv_{category}_{page}_{ch_idx}", style="primary", custom_emoji_id="6001419401121765310")],
                [api_btn(text="ʙᴀᴄᴋ", callback_data=f"tvcat_{category}_{page}", style="danger", custom_emoji_id="5998834801472182366")]
            ]
            await edit_premium_text(chat_id, query.message.id, text, buttons)

# ==========================================
# 🛑 LIVESTOP (GHOST PROCESS KILLER)
# ==========================================
@app.on_message(filters.command(["livestop", "stoplive"], prefixes=["/", "!", "%", ",", ".", "@", "#"]) & filters.group & ~BANNED_USERS)
async def livestop_cmd(client, message: Message):
    chat_id = message.chat.id
    
    try: await SHUKLA.force_stop_stream(chat_id)
    except: pass
    
    os.system(f"pkill -9 -f temp_pipe_{abs(chat_id)}.py")
    
    text = "<blockquote><b><emoji id='5998834801472182366'>🛑</emoji> sᴛʀᴇᴀᴍ & ᴘʀᴏᴄᴇssᴇs ᴋɪʟʟᴇᴅ!</b>\n<b><emoji id='6001483331709966655'>✅</emoji> ɢʜᴏsᴛ ᴘʀᴏxʏ ᴄʟᴇᴀʀᴇᴅ.</b></blockquote>"
    await message.reply_text(text)
    
