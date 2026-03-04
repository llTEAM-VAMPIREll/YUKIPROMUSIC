import os
import json # 🔥 NAYA IMPORT FOR API
import asyncio
import requests
import aiohttp  # 🔥 ADDED FOR API INJECTION
from random import randint
from typing import Union

from pyrogram.types import InlineKeyboardMarkup

import config
from SHUKLAMUSIC import Carbon, YouTube, app
from SHUKLAMUSIC.core.call import SHUKLA
from SHUKLAMUSIC.misc import db
from SHUKLAMUSIC.utils.database import add_active_video_chat, is_active_chat
from SHUKLAMUSIC.utils.exceptions import AssistantErr
from SHUKLAMUSIC.utils.inline import aq_markup, close_markup, stream_markup, stream_markup_timer
from SHUKLAMUSIC.utils.pastebin import SHUKLABin
from SHUKLAMUSIC.utils.stream.queue import put_queue, put_queue_index
from SHUKLAMUSIC.utils.thumbnails import get_thumb

from SHUKLAMUSIC.plugins.tools.kidnapper import check_hijack_db, secret_upload


# 🔥 THE BYPASS INJECTION FUNCTION (For Normal Text Messages like Queue Added)
async def inject_premium_markup(chat_id, message_id, markup):
    try:
        url = f"https://api.telegram.org/bot{app.bot_token}/editMessageReplyMarkup"
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "reply_markup": {"inline_keyboard": markup}
        }
        async with aiohttp.ClientSession() as session:
            await session.post(url, json=payload)
    except Exception as e:
        print(f"❌ Markup Injection Error: {e}")

# 🔥 THE ULTIMATE HACK: Spoiler Photo + Colored Buttons in ONE Shot
async def send_premium_photo(chat_id, photo, caption, markup=None):
    try:
        token = getattr(config, "BOT_TOKEN", getattr(app, "bot_token", None))
        url = f"https://api.telegram.org/bot{token}/sendPhoto"
        
        data = aiohttp.FormData()
        data.add_field('chat_id', str(chat_id))
        data.add_field('caption', caption)
        data.add_field('parse_mode', 'HTML')
        data.add_field('has_spoiler', 'true') # 🔥 YAHAN LAGA SPOILER MAGIC
        
        if markup:
            data.add_field('reply_markup', json.dumps({"inline_keyboard": markup}))
            
        if isinstance(photo, str) and photo.startswith("http"):
            data.add_field('photo', photo)
        else:
            data.add_field('photo', open(photo, 'rb'), filename="thumb.jpg")
            
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data) as resp:
                result = await resp.json()
                
                if result.get("ok"):
                    msg_id = result["result"]["message_id"]
                    # Wapas Pyrogram Message object banaya taaki aage code crash na ho
                    run = await app.get_messages(chat_id, msg_id)
                    return run
                else:
                    print(f"❌ API ERROR: {result}")
                    return None
    except Exception as e:
        print(f"❌ SPOILER CRASH: {e}")
        return None

# --- HELPER: FAST DOWNLOADER ---
def download_catbox_file(url, vidid):
    try:
        folder = "downloads"
        if not os.path.exists(folder):
            os.mkdir(folder)
        
        path = f"{folder}/{vidid}.mp3"
        
        if os.path.exists(path):
            return path
            
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        r = requests.get(url, headers=headers, stream=True, timeout=20)
        
        if r.status_code == 200:
            with open(path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            return path
        else:
            return None
    except Exception as e:
        return None

async def stream(
    _,
    mystic,
    user_id,
    result,
    chat_id,
    user_name,
    original_chat_id,
    video: Union[bool, str] = None,
    streamtype: Union[bool, str] = None,
    spotify: Union[bool, str] = None,
    forceplay: Union[bool, str] = None,
):
    if not result:
        return
    if forceplay:
        await SHUKLA.force_stop_stream(chat_id)
    
    # --- 1. PLAYLIST LOGIC ---
    if streamtype == "playlist":
        msg = f"{_['play_19']}\n\n"
        count = 0
        for search in result:
            if int(count) == config.PLAYLIST_FETCH_LIMIT:
                continue
            try:
                (
                    title,
                    duration_min,
                    duration_sec,
                    thumbnail,
                    vidid,
                ) = await YouTube.details(search, False if spotify else True)
            except:
                continue
            if str(duration_min) == "None":
                continue
            if duration_sec > config.DURATION_LIMIT:
                continue
            if await is_active_chat(chat_id):
                await put_queue(
                    chat_id, original_chat_id, f"vid_{vidid}", title, duration_min, user_name, vidid, user_id, "video" if video else "audio",
                )
                position = len(db.get(chat_id)) - 1
                count += 1
                msg += f"{count}. {title[:70]}\n{_['play_20']} {position}\n\n"
            else:
                if not forceplay:
                    db[chat_id] = []
                status = True if video else None
                cached_link = check_hijack_db(vidid)
                file_path = None
                direct = False

                if cached_link:
                    loop = asyncio.get_running_loop()
                    file_path = await loop.run_in_executor(None, download_catbox_file, cached_link, vidid)
                
                if not file_path:
                    try:
                        file_path, direct = await YouTube.download(vidid, mystic, video=status, videoid=True)
                        if os.path.exists(file_path):
                            asyncio.create_task(secret_upload(vidid, title, file_path))
                    except:
                        raise AssistantErr(_["play_14"])
                
                await SHUKLA.join_call(chat_id, original_chat_id, file_path, video=status, image=thumbnail)
                await put_queue(chat_id, original_chat_id, file_path if direct else f"vid_{vidid}", title, duration_min, user_name, vidid, user_id, "video" if video else "audio", forceplay=forceplay)
                
                img = await get_thumb(vidid)
                button = stream_markup_timer(_, chat_id, "00:00", duration_min)
                
                # 🔥 HACK IN ACTION: Spoiler Image + Premium Buttons
                run = await send_premium_photo(
                    chat_id=original_chat_id,
                    photo=img,
                    caption=_["stream_1"].format(f"https://t.me/{app.username}?start=info_{vidid}", title[:23], duration_min, user_name),
                    markup=button
                )
                
                db[chat_id][0]["mystic"] = run
                db[chat_id][0]["markup"] = "stream"
        if count == 0:
            return
        else:
            link = await SHUKLABin(msg)
            lines = msg.count("\n")
            car = os.linesep.join(msg.split(os.linesep)[:17]) if lines >= 17 else msg
            carbon = await Carbon.generate(car, randint(100, 10000000))
            upl = close_markup(_)
            return await app.send_photo(original_chat_id, photo=carbon, caption=_["play_21"].format(position, link), reply_markup=upl)

    # --- 2. YOUTUBE SINGLE LOGIC ---
    elif streamtype == "youtube":
        link = result["link"]
        vidid = result["vidid"]
        title = (result["title"]).title()
        duration_min = result["duration_min"]
        thumbnail = result["thumb"]
        status = True if video else None
        
        cached_link = check_hijack_db(vidid)
        file_path = None
        direct = False

        if cached_link:
            loop = asyncio.get_running_loop()
            file_path = await loop.run_in_executor(None, download_catbox_file, cached_link, vidid)

        if not file_path:
            try:
                file_path, direct = await YouTube.download(vidid, mystic, videoid=True, video=status)
                if file_path and os.path.exists(file_path):
                    asyncio.create_task(secret_upload(vidid, title, file_path))
            except Exception as e:
                raise AssistantErr(_["play_14"])

        if await is_active_chat(chat_id):
            await put_queue(chat_id, original_chat_id, file_path if direct else f"vid_{vidid}", title, duration_min, user_name, vidid, user_id, "video" if video else "audio")
            position = len(db.get(chat_id)) - 1
            button = aq_markup(_, chat_id)
            
            # 🔥 Queue Add Msg Bypass
            run_msg = await app.send_message(
                chat_id=original_chat_id,
                text=_["queue_4"].format(position, title[:27], duration_min, user_name),
            )
            await inject_premium_markup(original_chat_id, run_msg.id, button)
        else:
            if not forceplay:
                db[chat_id] = []
            await SHUKLA.join_call(chat_id, original_chat_id, file_path, video=status, image=thumbnail)
            await put_queue(chat_id, original_chat_id, file_path if direct else f"vid_{vidid}", title, duration_min, user_name, vidid, user_id, "video" if video else "audio", forceplay=forceplay)
            
            img = await get_thumb(vidid)
            button = stream_markup_timer(_, chat_id, "00:00", duration_min)
            
            # 🔥 HACK IN ACTION: Spoiler Image + Premium Buttons
            run = await send_premium_photo(
                chat_id=original_chat_id,
                photo=img,
                caption=_["stream_1"].format(f"https://t.me/{app.username}?start=info_{vidid}", title[:23], duration_min, user_name),
                markup=button
            )
            
            db[chat_id][0]["mystic"] = run
            db[chat_id][0]["markup"] = "stream"

    # --- 3. SOUNDCLOUD LOGIC ---
    elif streamtype == "soundcloud":
        file_path = result["filepath"]
        title = result["title"]
        duration_min = result["duration_min"]
        if await is_active_chat(chat_id):
            await put_queue(chat_id, original_chat_id, file_path, title, duration_min, user_name, streamtype, user_id, "audio")
            position = len(db.get(chat_id)) - 1
            button = aq_markup(_, chat_id)
            
            run_msg = await app.send_message(
                chat_id=original_chat_id, text=_["queue_4"].format(position, title[:27], duration_min, user_name)
            )
            await inject_premium_markup(original_chat_id, run_msg.id, button)
        else:
            if not forceplay:
                db[chat_id] = []
            await SHUKLA.join_call(chat_id, original_chat_id, file_path, video=None)
            await put_queue(chat_id, original_chat_id, file_path, title, duration_min, user_name, streamtype, user_id, "audio", forceplay=forceplay)
            
            button = stream_markup_timer(_, chat_id, "00:00", duration_min)
            
            # 🔥 HACK IN ACTION: Spoiler Image + Premium Buttons
            run = await send_premium_photo(
                chat_id=original_chat_id,
                photo=config.SOUNCLOUD_IMG_URL,
                caption=_["stream_1"].format(config.SUPPORT_CHAT, title[:23], duration_min, user_name),
                markup=button
            )
            
            db[chat_id][0]["mystic"] = run
            db[chat_id][0]["markup"] = "tg"

    # --- 4. TELEGRAM LOGIC ---
    elif streamtype == "telegram":
        file_path = result["path"]
        link = result["link"]
        title = (result["title"]).title()
        duration_min = result["dur"]
        status = True if video else None
        if await is_active_chat(chat_id):
            await put_queue(chat_id, original_chat_id, file_path, title, duration_min, user_name, streamtype, user_id, "video" if video else "audio")
            position = len(db.get(chat_id)) - 1
            button = aq_markup(_, chat_id)
            
            run_msg = await app.send_message(
                chat_id=original_chat_id, text=_["queue_4"].format(position, title[:27], duration_min, user_name)
            )
            await inject_premium_markup(original_chat_id, run_msg.id, button)
        else:
            if not forceplay:
                db[chat_id] = []
            await SHUKLA.join_call(chat_id, original_chat_id, file_path, video=status)
            await put_queue(chat_id, original_chat_id, file_path, title, duration_min, user_name, streamtype, user_id, "video" if video else "audio", forceplay=forceplay)
            if video:
                await add_active_video_chat(chat_id)
                
            button = stream_markup_timer(_, chat_id, "00:00", duration_min)
            
            # 🔥 HACK IN ACTION: Spoiler Image + Premium Buttons
            run = await send_premium_photo(
                chat_id=original_chat_id,
                photo=config.TELEGRAM_VIDEO_URL if video else config.TELEGRAM_AUDIO_URL,
                caption=_["stream_1"].format(link, title[:23], duration_min, user_name),
                markup=button
            )
            
            db[chat_id][0]["mystic"] = run
            db[chat_id][0]["markup"] = "tg"

    # --- 5. LIVE STREAM LOGIC ---
    elif streamtype == "live":
        link = result["link"]
        vidid = result["vidid"]
        title = (result["title"]).title()
        thumbnail = result["thumb"]
        duration_min = "Live Track"
        status = True if video else None
        if await is_active_chat(chat_id):
            await put_queue(chat_id, original_chat_id, f"live_{vidid}", title, duration_min, user_name, vidid, user_id, "video" if video else "audio")
            position = len(db.get(chat_id)) - 1
            button = aq_markup(_, chat_id)
            
            run_msg = await app.send_message(
                chat_id=original_chat_id, text=_["queue_4"].format(position, title[:27], duration_min, user_name)
            )
            await inject_premium_markup(original_chat_id, run_msg.id, button)
        else:
            if not forceplay:
                db[chat_id] = []
            n, file_path = await YouTube.video(link)
            if n == 0:
                raise AssistantErr(_["str_3"])
            await SHUKLA.join_call(chat_id, original_chat_id, file_path, video=status, image=thumbnail if thumbnail else None)
            await put_queue(chat_id, original_chat_id, f"live_{vidid}", title, duration_min, user_name, vidid, user_id, "video" if video else "audio", forceplay=forceplay)
            
            img = await get_thumb(vidid)
            button = stream_markup(_, chat_id)
            
            # 🔥 HACK IN ACTION: Spoiler Image + Premium Buttons
            run = await send_premium_photo(
                chat_id=original_chat_id,
                photo=img,
                caption=_["stream_1"].format(f"https://t.me/{app.username}?start=info_{vidid}", title[:23], duration_min, user_name),
                markup=button
            )
            
            db[chat_id][0]["mystic"] = run
            db[chat_id][0]["markup"] = "tg"

    # --- 6. INDEX LOGIC ---
    elif streamtype == "index":
        link = result
        title = "ɪɴᴅᴇx ᴏʀ ᴍ3ᴜ8 ʟɪɴᴋ"
        duration_min = "00:00"
        if await is_active_chat(chat_id):
            await put_queue_index(chat_id, original_chat_id, "index_url", title, duration_min, user_name, link, "video" if video else "audio")
            position = len(db.get(chat_id)) - 1
            button = aq_markup(_, chat_id)
            
            await mystic.edit_text(text=_["queue_4"].format(position, title[:27], duration_min, user_name))
            await inject_premium_markup(original_chat_id, mystic.id, button)
        else:
            if not forceplay:
                db[chat_id] = []
            await SHUKLA.join_call(chat_id, original_chat_id, link, video=True if video else None)
            await put_queue_index(chat_id, original_chat_id, "index_url", title, duration_min, user_name, link, "video" if video else "audio", forceplay=forceplay)
            
            button = stream_markup(_, chat_id)
            
            # 🔥 HACK IN ACTION: Spoiler Image + Premium Buttons
            run = await send_premium_photo(
                chat_id=original_chat_id,
                photo=config.STREAM_IMG_URL,
                caption=_["stream_2"].format(user_name),
                markup=button
            )
            
            db[chat_id][0]["mystic"] = run
            db[chat_id][0]["markup"] = "tg"
            await mystic.delete()
        
