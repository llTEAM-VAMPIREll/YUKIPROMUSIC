import time
import random
import asyncio
import traceback
import aiohttp 
import json
from pyrogram import Client, filters
from pyrogram.enums import ChatType
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from youtubesearchpython.__future__ import VideosSearch
from pyrogram.types import CallbackQuery

import config
from SHUKLAMUSIC import app
from SHUKLAMUSIC.misc import _boot_
from SHUKLAMUSIC.plugins.sudo.sudoers import sudoers_list
from SHUKLAMUSIC.utils.database import get_served_chats, get_served_users, get_sudoers
from SHUKLAMUSIC.utils import bot_sys_stats
from SHUKLAMUSIC.utils.database import (
    add_served_chat,
    add_served_user,
    blacklisted_chats,
    get_lang,
    is_banned_user,
    is_on_off,
)
from SHUKLAMUSIC.utils.decorators.language import LanguageStart
from SHUKLAMUSIC.utils.formatters import get_readable_time
from SHUKLAMUSIC.utils.inline import help_pannel, private_panel, start_panel
from config import BANNED_USERS
from strings import get_string

YUMI_PICS = [
    "https://files.catbox.moe/v0v41s.jpg",
    "https://files.catbox.moe/v0v41s.jpg",
    "https://files.catbox.moe/sbaei4.jpg",
    "https://files.catbox.moe/csyzob.jpg",
]

# 🔥 PROMO MEIN CUSTOM EMOJIS
PROMO =  "───────────────────────\n<emoji id='5999100917645841519'>💀</emoji> <b>ᴘᴧɪᴅ ᴘʀσϻσᴛɪση ᴧᴠᴧɪʟᴧʙʟє</b> <emoji id='5999100917645841519'>💀</emoji>\n───────────────────────\n<blockquote><emoji id='6080189526532167993'>😉</emoji> ᴄʜᴧᴛᴛɪηɢ ɢʀσυᴘ's\n<emoji id='5413546177683539369'>😈</emoji> ᴄσʟσʀ ᴛʀᴧᴅɪηɢ ɢᴧϻє's\n<emoji id='6080176744709495278'>🐾</emoji> ᴄʜᴧηηєʟ's | ɢʀσυᴘ's .....\n<emoji id='5415586682286128590'>🔫</emoji> ʙєᴛᴛɪηɢ ᴧᴅs σʀ ᴧηʏᴛʜɪηɢ</blockquote>\n\n───────────────────────\n<emoji id='6080202089311507876'>😎</emoji> <b>ᴘʟᴧηꜱ -</b>\n<blockquote>||<emoji id='5413415116756500503'>☠️</emoji> ᴅᴧɪʟʏ\n<emoji id='5413415116756500503'>☠️</emoji> ᴡєєᴋʟʏ\n<emoji id='5413415116756500503'>☠️</emoji> ϻσηᴛʜʟʏ||</blockquote>\n───────────────────────\n<emoji id='6001132493011425597'>💖</emoji> <b>ᴄσηᴛᴧᴄᴛ -</b> <a href='https://t.me/hehe_stalker'>愛 | 𝗦𝗧么𝗟𝗞𝚵𝗥</a>\n───────────────────────"

GREET = ["💞", "🥂", "🔍", "🧪", "🥂", "⚡️", "🔥"]

# 🔥 INJECT PREMIUM BUTTONS
async def inject_premium_markup(chat_id, message_id, markup):
    try:
        token = getattr(config, "BOT_TOKEN", getattr(app, "bot_token", None))
        url = f"https://api.telegram.org/bot{token}/editMessageReplyMarkup"
        payload = {"chat_id": chat_id, "message_id": message_id, "reply_markup": {"inline_keyboard": markup}}
        async with aiohttp.ClientSession() as session:
            await session.post(url, json=payload)
    except Exception as e:
        print(f"❌ CODE CRASH: {e}")

# 🔥 THE MAGIC START FUNCTION (WITH FAIL-SAFE)
async def send_magic_start(chat_id, photo_url, caption, markup):
    try:
        token = getattr(config, "BOT_TOKEN", getattr(app, "bot_token", None))
        url = f"https://api.telegram.org/bot{token}/sendPhoto"
        
        payload = {
            "chat_id": chat_id,
            "photo": photo_url,
            "caption": caption,
            "parse_mode": "HTML",
            "message_effect_id": "5104861875154336188", # ❤️ Flying Hearts Effect ID
            "reply_markup": {"inline_keyboard": markup}
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                res = await resp.json()
                
                # Agar API ne Magic Effect reject kar diya, toh normal message bhejega
                if not res.get("ok"):
                    run = await app.send_photo(chat_id, photo=photo_url, caption=caption)
                    await inject_premium_markup(chat_id, run.id, markup)
                    
    except Exception as e:
        # Crash hone par bhi normal message bhejega
        run = await app.send_photo(chat_id, photo=photo_url, caption=caption)
        await inject_premium_markup(chat_id, run.id, markup)


@app.on_message(filters.command(["start"]) & filters.private & ~BANNED_USERS)
@LanguageStart
async def start_pm(client, message: Message, _):
    
    # 🔥 STEP 1: MESSAGE PE REACTION (❤️)
    try:
        await client.send_reaction(chat_id=message.chat.id, message_id=message.id, emoji="❤️")
    except: pass
        
    # 🔥 STEP 2: STICKER BHEJNA + 5 SEC WAIT + DELETE
    try:
        stk = await message.reply_sticker("CAACAgUAAxkBAAFD0UBpqDbTjoP_CXF7Ce6oZykP4r64jQACxAcAArligFU4dyG-LQJBjDoE")
        await asyncio.sleep(5) # 5 Second Wait Karega
        await stk.delete()     # 5 Second baad delete kar dega
    except: pass

    # 🔥 STEP 3: LOADING ANIMATION
    loading_1 = await message.reply_text(random.choice(GREET))
    await add_served_user(message.from_user.id)
    
    await asyncio.sleep(0.1)
    await loading_1.edit_text("<emoji id='5413546177683539369'>😈</emoji> <b>ᴅɪηɢ ᴅᴏηɢ.</b>")
    await asyncio.sleep(0.1)
    await loading_1.edit_text("<emoji id='5413546177683539369'>😈</emoji> <b>ᴅɪηɢ ᴅᴏηɢ..</b>")
    await asyncio.sleep(0.1)
    await loading_1.edit_text("<emoji id='5413546177683539369'>😈</emoji> <b>ᴅɪηɢ ᴅᴏηɢ...</b>")
    await asyncio.sleep(0.1)
    await loading_1.edit_text("<emoji id='6080202089311507876'>😎</emoji> <b>sᴛᴧʀᴛɪηɢ.</b>")
    await asyncio.sleep(0.1)
    await loading_1.edit_text("<emoji id='6080202089311507876'>😎</emoji> <b>sᴛᴧʀᴛɪηɢ..</b>")
    await asyncio.sleep(0.1)
    await loading_1.edit_text("<emoji id='6080202089311507876'>😎</emoji> <b>sᴛᴧʀᴛɪηɢ...</b>")
    await asyncio.sleep(0.1)
    await loading_1.edit_text("<emoji id='6001132493011425597'>💖</emoji> <b>ʜєʏ ʙᴧʙʏ!</b>")
    await asyncio.sleep(0.1)
    await loading_1.edit_text("<emoji id='5413840936994097463'>🌺</emoji> <b>ᴍɪᴍɪ ꭙ ϻᴜsɪᴄ ♪\nsᴛᴧʀᴛed!</b>")
    await asyncio.sleep(0.1)
    await loading_1.delete()
    
    # 🔥 STEP 4: FINAL START MESSAGE
    if len(message.text.split()) > 1:
        name = message.text.split(None, 1)[1]
        if name[0:4] == "help":
            keyboard = help_pannel(_)
            run = await message.reply_photo(
                random.choice(YUMI_PICS),
                caption=_["help_1"].format(config.SUPPORT_CHAT),
            )
            return await inject_premium_markup(message.chat.id, run.id, keyboard)
            
        if name[0:3] == "sud":
            await sudoers_list(client=client, message=message, _=_)
            if await is_on_off(2):
                return await app.send_message(
                    chat_id=config.LOGGER_ID,
                    text=f"<blockquote><emoji id='6080176744709495278'>🐾</emoji> {message.from_user.mention} ᴊᴜsᴛ sᴛᴀʀᴛᴇᴅ ᴛʜᴇ ʙᴏᴛ ᴛᴏ ᴄʜᴇᴄᴋ <b>sᴜᴅᴏʟɪsᴛ</b>.\n\n<b><emoji id='5413415116756500503'>☠️</emoji> ᴜsᴇʀ ɪᴅ ➠</b> <code>{message.from_user.id}</code>\n<b><emoji id='5999100917645841519'>💀</emoji> ᴜsᴇʀɴᴀᴍᴇ ➠</b> @{message.from_user.username}</blockquote>",
                )
            return
            
        if name[0:3] == "inf":
            m = await message.reply_text("🔎")
            query = (str(name)).replace("info_", "", 1)
            query = f"https://www.youtube.com/watch?v={query}"
            results = VideosSearch(query, limit=1)
            for result in (await results.next())["result"]:
                title = result["title"]
                duration = result["duration"]
                views = result["viewCount"]["short"]
                thumbnail = result["thumbnails"][0]["url"].split("?")[0]
                channellink = result["channel"]["link"]
                channel = result["channel"]["name"]
                link = result["link"]
                published = result["publishedTime"]
            searched_text = _["start_6"].format(
                title, duration, views, published, channellink, channel, app.mention
            )
            
            key = [
                [
                    {"text": _["S_B_8"], "url": link, "style": "primary", "icon_custom_emoji_id": "6080202089311507876"},
                    {"text": _["S_B_9"], "url": config.SUPPORT_CHAT, "style": "danger", "icon_custom_emoji_id": "5999100917645841519"},
                ]
            ]
            await m.delete()
            run = await app.send_photo(
                chat_id=message.chat.id,
                photo=thumbnail,
                caption=searched_text,
            )
            await inject_premium_markup(message.chat.id, run.id, key)
            
            if await is_on_off(2):
                return await app.send_message(
                    chat_id=config.LOGGER_ID,
                    text=f"<emoji id='6080176744709495278'>🐾</emoji> {message.from_user.mention} ᴊᴜsᴛ sᴛᴀʀᴛᴇᴅ ᴛʜᴇ ʙᴏᴛ ᴛᴏ ᴄʜᴇᴄᴋ <b>ᴛʀᴀᴄᴋ ɪɴғᴏʀᴍᴀᴛɪᴏɴ</b>.\n\n<emoji id='5413415116756500503'>☠️</emoji> <b>ᴜsᴇʀ ɪᴅ ➠</b> <code>{message.from_user.id}</code>\n<emoji id='5999100917645841519'>💀</emoji> <b>ᴜsᴇʀɴᴀᴍᴇ ➠</b> @{message.from_user.username}",
                )
    else:
        out = private_panel(_)
        served_chats = len(await get_served_chats())
        served_users = len(await get_served_users())
        UP, CPU, RAM, DISK = await bot_sys_stats()
        
        caption_text = _["start_2"].format(message.from_user.mention, app.mention, UP, DISK, CPU, RAM,served_users,served_chats)
        
        # 🔥 STEP 4: YAHAN MAGIC START CALL HOGA BINA CRASH KIYE
        await send_magic_start(
            chat_id=message.chat.id,
            photo_url=random.choice(YUMI_PICS),
            caption=caption_text,
            markup=out
        )
        
        if await is_on_off(2):
            return await app.send_message(
                chat_id=config.LOGGER_ID,
                text=f"<emoji id='6080176744709495278'>🐾</emoji> {message.from_user.mention} ᴊᴜsᴛ sᴛᴀʀᴛᴇᴅ ᴛʜᴇ ʙᴏᴛ.\n\n<emoji id='5413415116756500503'>☠️</emoji> <b>ᴜsᴇʀ ɪᴅ ➠</b> <code>{message.from_user.id}</code>\n<emoji id='5999100917645841519'>💀</emoji> <b>ᴜsᴇʀɴᴀᴍᴇ ➠</b> @{message.from_user.username}",
            )

@app.on_message(filters.command(["start"]) & filters.group & ~BANNED_USERS)
@LanguageStart
async def start_gp(client, message: Message, _):
    # 🔥 GROUP MEIN BHI REACTION AAYEGA
    try:
        await client.send_reaction(chat_id=message.chat.id, message_id=message.id, emoji="❤️")
    except: pass
    
    out = start_panel(_)
    uptime = int(time.time() - _boot_)
    
    run = await message.reply_photo(
        random.choice(YUMI_PICS),
        caption=_["start_1"].format(app.mention, get_readable_time(uptime)),
    )
    await inject_premium_markup(message.chat.id, run.id, out)

@app.on_message(filters.command("promo") & filters.private)
async def about_command(client: Client, message: Message):
    await message.reply_photo(
        random.choice(YUMI_PICS),
        caption=PROMO
    )

@app.on_message(filters.new_chat_members, group=-1)
async def welcome(client, message: Message):
    for member in message.new_chat_members:
        try:
            language = await get_lang(message.chat.id)
            _ = get_string(language)
            if await is_banned_user(member.id):
                try:
                    await message.chat.ban_member(member.id)
                except:
                    pass
            
            if member.id == app.id:
                if message.chat.type != ChatType.SUPERGROUP:
                    await message.reply_text(_["start_4"])
                    return await app.leave_chat(message.chat.id)
                if message.chat.id in await blacklisted_chats():
                    await message.reply_text(
                        _["start_5"].format(
                            app.mention,
                            f"https://t.me/{app.username}?start=sudolist",
                            config.SUPPORT_CHAT,
                        ),
                        disable_web_page_preview=True,
                    )
                    return await app.leave_chat(message.chat.id)

                out = start_panel(_)
                bot_welcome = f"<emoji id='6080202089311507876'>😎</emoji> <b>𝖶𝖾𝗅𝖼𝗈𝗆𝖾 𝖳𝗈 {message.chat.title}</b>\n<emoji id='6001132493011425597'>💖</emoji> 𝖳𝗁𝖺𝗇𝗄𝗌 𝖿𝗈𝗋 𝖺𝖽𝖽𝗂𝗇𝗀 𝗆𝖾, 𝖨 𝖺𝗆 𝗋𝖾𝖺𝖽𝗒 𝗍𝗈 𝗉𝗅𝖺𝗒!"
                
                run = await message.reply_text(text=bot_welcome, disable_web_page_preview=True)
                await inject_premium_markup(message.chat.id, run.id, out)
                
                await add_served_chat(message.chat.id)
                
                async def delete_bot_msg():
                    await asyncio.sleep(10)
                    try: await run.delete()
                    except: pass
                asyncio.create_task(delete_bot_msg())
                
                await message.stop_propagation()
            else:
                user_welcome = f"<emoji id='5413840936994097463'>🌺</emoji> <b>𝖶𝖾𝗅𝖼𝗈𝗆𝖾 𝖳𝗈 {message.chat.title}, {member.mention}!</b>"
                run = await message.reply_text(text=user_welcome, disable_web_page_preview=True)
                
                async def delete_user_msg():
                    await asyncio.sleep(10)
                    try: await run.delete()
                    except: pass
                asyncio.create_task(delete_user_msg())

        except Exception as ex:
            pass
            
