# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  2026 ʜᴇʟʟғɪʀᴇ ᴅᴇᴠs. ᴀʟʟ ʀɪɢʜᴛs ʀᴇsᴇʀᴠᴇᴅ.
#  ᴡᴀʀɴɪɴɢ: ᴅᴏ ɴᴏᴛ ᴄᴏᴘʏ, ᴍᴏᴅɪғʏ ᴏʀ ᴋᴀɴɢ ᴛʜɪs ᴄᴏᴅᴇ.
# ᴘʀᴏᴛᴇᴄᴛᴇᴅ ʙʏ ʜᴇʟʟғɪʀᴇ sᴇᴄᴜʀɪᴛʏ.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

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

WATERMARK = small_caps("\n\n© NOW LIVE ")

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
    original_text = _["play_22"].format(message.chat.title)
    
    await message.reply_text(
        text=original_text + WATERMARK,
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

@app.on_message(filters.command(["playtv", "tv"], prefixes=["/", "!", "%", ",", ".", "@", "#"]) & filters.group & ~BANNED_USERS)
async def playtv_cmd(client, message: Message):
    data = load_iptv_data()
    if not data:
        return await message.reply_text("❌ Failed to load IPTV channels." + WATERMARK)
    
    buttons = []
    for cat in list(data.keys())[:10]: 
        buttons.append([InlineKeyboardButton(text=f"📺 {cat}", callback_data=f"tvcat_{cat}_0")])
    buttons.append([InlineKeyboardButton(text="❌ Close", callback_data="close_tv")])
    
    text = "**🔥 HELLFIRE TV IS LIVE! 🔥**\nSelect a category:" + WATERMARK
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
            buttons.append([InlineKeyboardButton(text=f"▶️ {ch['name']}", callback_data=f"playtv_{category}_{page}_{real_idx}")])
            
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
        text = "**🔥 HELLFIRE TV IS LIVE! 🔥**\nSelect a category:" + WATERMARK
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("playtv_") or data.startswith("retrytv_"):
        parts = data.split("_")
        category, page, ch_idx = parts[1], parts[2], int(parts[3])
        channel = load_iptv_data()[category][ch_idx]
        ch_name, raw_url = channel["name"], channel["url"]
        chat_id = query.message.chat.id
        
        await query.message.edit_text(f"⏳ **HellfireDevs:** Bypassing blocks & Loading `{ch_name}`..." + WATERMARK)
        
        try:
            # 🔥 SWITCH/SKIP LOGIC: Purana stream turant band karega
            try:
                await SHUKLA.force_stop_stream(chat_id)
            except Exception:
                pass 

            # 🧠 BASE64 HACK: URL ko encrypt kiya taaki koi special char (%, ?) engine ko confuse na kare
            safe_url = base64.urlsafe_b64encode(raw_url.encode('utf-8')).decode('utf-8')
            
            # Ekdum neat and clean proxy link jo engine ko .m3u8 file lagega
            local_bypass_link = f"http://127.0.0.1:5000/play/{safe_url}.m3u8"

            # 🚀 Engine ko direct clean link feed kar diya (No local file created!)
            await SHUKLA.join_call(
                chat_id, 
                chat_id, 
                local_bypass_link, 
                video=True
            )
            
            text = f"✅ **Hellfire TV Live!**\n\n📺 **Channel:** {ch_name}\n🚀 Stream Skipped & Active!" + WATERMARK
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
            
