# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  2026 ʜᴇʟʟғɪʀᴇ ᴅᴇᴠs. ᴀʟʟ ʀɪɢʜᴛs ʀᴇsᴇʀᴠᴇᴅ.
#  ᴡᴀʀɴɪɴɢ: ᴅᴏ ɴᴏᴛ ᴄᴏᴘʏ, ᴍᴏᴅɪғʏ ᴏʀ ᴋᴀɴɢ ᴛʜɪs ᴄᴏᴅᴇ.
# ᴘʀᴏᴛᴇᴄᴛᴇᴅ ʙʏ ʜᴇʟʟғɪʀᴇ sᴇᴄᴜʀɪᴛʏ.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

import os
import json
import requests
import math
import base64
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery

from SHUKLAMUSIC import app
from SHUKLAMUSIC.core.call import SHUKLA
from SHUKLAMUSIC.utils.database import get_playmode, get_playtype, is_nonadmin_chat
from SHUKLAMUSIC.utils.decorators import language
from SHUKLAMUSIC.utils.inline.settings import playmode_users_markup
from config import BANNED_USERS

# ==========================================
# 🔠 HELLFIRE SMALL CAPS GENERATOR
# ==========================================
def small_caps(text: str) -> str:
    small_caps_dict = {
        'a': 'ᴀ', 'b': 'ʙ', 'c': 'ᴄ', 'd': 'ᴅ', 'e': 'ᴇ', 'f': 'ғ', 'g': 'ɢ', 'h': 'ʜ',
        'i': 'ɪ', 'j': 'ᴊ', 'k': 'ᴋ', 'l': 'ʟ', 'm': 'ᴍ', 'n': 'ɴ', 'o': 'ᴏ', 'p': 'ᴘ',
        'q': 'ǫ', 'r': 'ʀ', 's': 's', 't': 'ᴛ', 'u': 'ᴜ', 'v': 'ᴠ', 'w': 'ᴡ', 'x': 'x',
        'y': 'ʏ', 'z': 'ᴢ'
    }
    return "".join(small_caps_dict.get(c, c) for c in text.lower())

WATERMARK = small_caps("\n\n© ʜᴇʟʟғɪʀᴇ ᴅᴇᴠs | ᴅᴏ ɴᴏᴛ ᴄᴏᴘʏ ᴛʜɪs ʙᴏᴛ")

# ==========================================
# 📺 HELLFIRE LIVE TV LOGIC & CUSTOM DB
# ==========================================
IPTV_URL = "https://iptv-org.github.io/iptv/languages/hin.m3u"
CACHED_CHANNELS = {}
FLAT_CHANNELS = []

def load_iptv_data(force_reload=False):
    global CACHED_CHANNELS, FLAT_CHANNELS
    if CACHED_CHANNELS and not force_reload: 
        return CACHED_CHANNELS
        
    CACHED_CHANNELS = {}
    FLAT_CHANNELS = []
    
    hidden_urls = []
    if os.path.exists("hidden_channels.json"):
        with open("hidden_channels.json", "r") as f:
            hidden_urls = json.load(f)

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
                if line not in hidden_urls:
                    if current_cat not in CACHED_CHANNELS:
                        CACHED_CHANNELS[current_cat] = []
                    ch_data = {"name": current_name, "url": line, "cat": current_cat}
                    CACHED_CHANNELS[current_cat].append(ch_data)
                    FLAT_CHANNELS.append(ch_data)
    except: pass

    if os.path.exists("custom_channels.json"):
        with open("custom_channels.json", "r") as f:
            customs = json.load(f)
            for ch in customs:
                if ch["url"] not in hidden_urls:
                    if ch["cat"] not in CACHED_CHANNELS:
                        CACHED_CHANNELS[ch["cat"]] = []
                    CACHED_CHANNELS[ch["cat"]].append(ch)
                    FLAT_CHANNELS.append(ch)

    return CACHED_CHANNELS

# ==========================================
# ➕ CUSTOM ADD / REMOVE COMMANDS
# ==========================================
@app.on_message(filters.command(["cadd"], prefixes=["/", "!", "%", ",", ".", "@", "#"]) & filters.group & ~BANNED_USERS)
async def add_channel_cmd(client, message: Message):
    try:
        text = message.text.split(" ", 1)[1]
        parts = text.split("|")
        if len(parts) != 3:
            return await message.reply_text("❌ Sahi format use karo:\n`/cadd Link | Channel Name | Category`" + WATERMARK)
            
        url, name, cat = parts[0].strip(), parts[1].strip(), parts[2].strip()
        
        customs = []
        if os.path.exists("custom_channels.json"):
            with open("custom_channels.json", "r") as f:
                customs = json.load(f)
        customs.append({"name": name, "url": url, "cat": cat})
        with open("custom_channels.json", "w") as f:
            json.dump(customs, f)
            
        load_iptv_data(force_reload=True)
        await message.reply_text(f"✅ **Channel Added!**\n📺 `{name}` added to `{cat}` category." + WATERMARK)
    except IndexError:
        await message.reply_text("❌ Sahi format use karo:\n`/cadd Link | Channel Name | Category`" + WATERMARK)

@app.on_message(filters.command(["crm"], prefixes=["/", "!", "%", ",", ".", "@", "#"]) & filters.group & ~BANNED_USERS)
async def rm_channel_cmd(client, message: Message):
    try:
        ch_num = int(message.text.split(" ", 1)[1])
        if ch_num < 1 or ch_num > len(FLAT_CHANNELS):
            return await message.reply_text(f"❌ Invalid Number! 1 se {len(FLAT_CHANNELS)} ke beech dalo." + WATERMARK)
            
        target = FLAT_CHANNELS[ch_num - 1]
        
        hidden = []
        if os.path.exists("hidden_channels.json"):
            with open("hidden_channels.json", "r") as f:
                hidden = json.load(f)
        hidden.append(target["url"])
        with open("hidden_channels.json", "w") as f:
            json.dump(hidden, f)
            
        load_iptv_data(force_reload=True)
        await message.reply_text(f"🗑 **Channel Removed!**\n❌ `{target['name']}` (No. {ch_num}) successfully deleted." + WATERMARK)
    except (IndexError, ValueError):
        await message.reply_text("❌ Sahi format use karo:\n`/crm <channel_number>`" + WATERMARK)

# ==========================================
# 📺 MAIN PLAY COMMAND
# ==========================================
@app.on_message(filters.command(["playtv", "tv"], prefixes=["/", "!", "%", ",", ".", "@", "#"]) & filters.group & ~BANNED_USERS)
async def playtv_cmd(client, message: Message):
    data = load_iptv_data()
    if not data:
        return await message.reply_text("❌ Failed to load IPTV channels." + WATERMARK)
    
    if len(message.command) > 1:
        try:
            ch_num = int(message.command[1])
            if ch_num < 1 or ch_num > len(FLAT_CHANNELS):
                return await message.reply_text(f"❌ Bhai, Channel number 1 se {len(FLAT_CHANNELS)} ke beech hona chahiye!" + WATERMARK)
            
            channel = FLAT_CHANNELS[ch_num - 1]
            ch_name, raw_url = channel["name"], channel["url"]
            chat_id = message.chat.id
            
            status_msg = await message.reply_text(f"⏳ **HellfireDevs:** Loading Channel No. `{ch_num}`: `{ch_name}`..." + WATERMARK)
            
            try:
                try: await SHUKLA.force_stop_stream(chat_id)
                except: pass 
                
                # 🔥 BASE64 HACK: Encode karke '=' hata do
                safe_url = base64.urlsafe_b64encode(raw_url.encode('utf-8')).decode('utf-8').rstrip("=")
                local_bypass_link = f"http://127.0.0.1:5000/play/{safe_url}.m3u8"

                os.makedirs("downloads", exist_ok=True)
                clean_id = str(chat_id).replace("-", "G")
                file_path = f"downloads/live_{clean_id}.m3u8"
                
                with open(file_path, "w") as f:
                    f.write(f"#EXTM3U\n#EXTINF:-1, {ch_name}\n{local_bypass_link}\n")

                await SHUKLA.join_call(chat_id, chat_id, file_path, video=True)
                
                await status_msg.edit_text(f"✅ **Hellfire TV Live!**\n\n📺 **Channel:** {ch_name} (No. {ch_num})\n🚀 Direct Stream Active!" + WATERMARK)
            except Exception as e:
                await status_msg.edit_text(f"❌ **Stream Failed!**\nChannel dead hai.\n`{str(e)}`" + WATERMARK)
            return
        except ValueError:
            pass 

    buttons = []
    for cat in list(data.keys())[:10]: 
        buttons.append([InlineKeyboardButton(text=f"📺 {cat}", callback_data=f"tvcat_{cat}_0")])
    buttons.append([InlineKeyboardButton(text="❌ Close", callback_data="close_tv")])
    
    text = f"**🔥 HELLFIRE TV IS LIVE! 🔥**\nTotal Channels: `{len(FLAT_CHANNELS)}`\n\nSelect a category or type `/playtv <number>`:" + WATERMARK
    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))

@app.on_callback_query(filters.regex(r"^(tvcat_|playtv_|retrytv_|close_tv|playtv_main)"))
async def tv_callback(client, query: CallbackQuery):
    data = query.data
    
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
            ch_num = FLAT_CHANNELS.index(ch) + 1
            buttons.append([InlineKeyboardButton(text=f"▶️ {ch['name']}", callback_data=f"playtv_{category}_{page}_{ch_num-1}")])
            
        nav = []
        if page > 0: nav.append(InlineKeyboardButton(text="⬅️ Back", callback_data=f"tvcat_{category}_{page-1}"))
        if page < total_pages - 1: nav.append(InlineKeyboardButton(text="Next ➡️", callback_data=f"tvcat_{category}_{page+1}"))
        if nav: buttons.append(nav)
        
        buttons.append([InlineKeyboardButton(text="🔙 Main Menu", callback_data="playtv_main")])
        text = f"**📺 {category}** (Page {page+1}/{total_pages})" + WATERMARK
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

    elif data == "playtv_main":
        data = load_iptv_data()
        buttons = [[InlineKeyboardButton(text=f"📺 {cat}", callback_data=f"tvcat_{cat}_0")] for cat in list(data.keys())[:10]]
        buttons.append([InlineKeyboardButton(text="❌ Close", callback_data="close_tv")])
        text = f"**🔥 HELLFIRE TV IS LIVE! 🔥**\nTotal Channels: `{len(FLAT_CHANNELS)}`\n\nSelect a category or type `/playtv <number>`:" + WATERMARK
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("playtv_") or data.startswith("retrytv_"):
        parts = data.split("_")
        category, page, ch_idx = parts[1], parts[2], int(parts[3])
        channel = FLAT_CHANNELS[ch_idx]
        ch_name, raw_url = channel["name"], channel["url"]
        chat_id = query.message.chat.id
        
        await query.message.edit_text(f"⏳ **HellfireDevs:** Bypassing blocks & Loading `{ch_name}`..." + WATERMARK)
        
        try:
            try: await SHUKLA.force_stop_stream(chat_id)
            except: pass 

            # 🔥 BASE64 HACK: Encode karke '=' hata do
            safe_url = base64.urlsafe_b64encode(raw_url.encode('utf-8')).decode('utf-8').rstrip("=")
            local_bypass_link = f"http://127.0.0.1:5000/play/{safe_url}.m3u8"

            os.makedirs("downloads", exist_ok=True)
            clean_id = str(chat_id).replace("-", "G")
            file_path = f"downloads/live_{clean_id}.m3u8"
            
            with open(file_path, "w") as f:
                f.write(f"#EXTM3U\n#EXTINF:-1, {ch_name}\n{local_bypass_link}\n")

            await SHUKLA.join_call(chat_id, chat_id, file_path, video=True)
            
            text = f"✅ **Hellfire TV Live!**\n\n📺 **Channel:** {ch_name} (No. {ch_idx+1})\n🚀 Stream Skipped & Active!" + WATERMARK
            await query.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(text="🔙 Back to Channels", callback_data=f"tvcat_{category}_{page}")]
                ])
            )
        except Exception as e:
            text = f"❌ **Stream Failed!**\nChannel `{ch_name}` offline hai.\n`{str(e)}`" + WATERMARK
            await query.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(text="🔄 Retry", callback_data=f"retrytv_{category}_{page}_{ch_idx}")],
                    [InlineKeyboardButton(text="🔙 Back", callback_data=f"tvcat_{category}_{page}")]
                ])
    )
            
