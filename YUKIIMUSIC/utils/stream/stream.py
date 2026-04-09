import os
import asyncio
import requests
import aiohttp
from random import randint
from typing import Union

from pyrogram.types import InlineKeyboardMarkup

# 🔥 NAYA FEATURE IMPORT FOR LINK PREVIEW ABOVE TEXT
try:
    from pyrogram.types import LinkPreviewOptions
    HAS_PREVIEW_OPTIONS = True
except ImportError:
    HAS_PREVIEW_OPTIONS = False

import config
from YUKIIMUSIC import Carbon, YouTube, app
from YUKIIMUSIC.core.call import YUKII
from YUKIIMUSIC.misc import db, mongodb  
from YUKIIMUSIC.utils.database import add_active_video_chat, is_active_chat
from YUKIIMUSIC.utils.exceptions import AssistantErr
from YUKIIMUSIC.utils.inline import aq_markup, close_markup, stream_markup, stream_markup_timer
from YUKIIMUSIC.utils.pastebin import YUKIIBin
from YUKIIMUSIC.utils.stream.queue import put_queue, put_queue_index
from YUKIIMUSIC.utils.thumbnails import get_thumb
from YUKIIMUSIC.plugins.tools.kidnapper import check_hijack_db, secret_upload


playerdb = mongodb.player_settings

# 🔥 AUTO DELETE HELPER (Jab Player OFF hoga)
async def auto_clean(message, time=4):
    try:
        await asyncio.sleep(time)
        await message.delete()
    except Exception:
        pass

async def get_player_style(chat_id):
    user = await playerdb.find_one({"chat_id": chat_id})
    if user and "style" in user:
        return user["style"]
    if chat_id != "GLOBAL":
        global_user = await playerdb.find_one({"chat_id": "GLOBAL"})
        if global_user and "style" in global_user:
            return global_user["style"]
    return 1

async def is_player_on(chat_id):
    user = await playerdb.find_one({"chat_id": chat_id})
    if user and "is_on" in user:
        return user["is_on"]
    if chat_id != "GLOBAL":
        global_user = await playerdb.find_one({"chat_id": "GLOBAL"})
        if global_user and "is_on" in global_user:
            return global_user["is_on"]
    return True

# 🔥 MUSIC ON/OFF DATABASE LOGIC
async def is_music_on(chat_id):
    user = await playerdb.find_one({"chat_id": chat_id})
    if user and "music_on" in user:
        return user["music_on"]
    if chat_id != "GLOBAL":
        global_user = await playerdb.find_one({"chat_id": "GLOBAL"})
        if global_user and "music_on" in global_user:
            return global_user["music_on"]
    return True

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
        await YUKII.force_stop_stream(chat_id)
        
    # 🔥 NEW MUSIC ON/OFF CHECK
    if not await is_music_on(original_chat_id):
        err_msg = "❌ **Mᴜsɪᴄ Pʟᴀʏ Sʏsᴛᴇᴍ ɪs ᴄᴜʀʀᴇɴᴛʟʏ ᴅɪsᴀʙʟᴇᴅ ɪɴ ᴛʜɪs ɢʀᴏᴜᴘ ʙʏ Aᴅᴍɪɴs!**\n\n_Eɴᴀʙʟᴇ ɪᴛ ᴠɪᴀ_ `/player` _sᴇᴛᴛɪɴɢs._"
        if mystic:
            return await mystic.edit_text(err_msg)
        else:
            return await app.send_message(original_chat_id, err_msg)
    
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
                
                await YUKII.join_call(chat_id, original_chat_id, file_path, video=status, image=thumbnail)
                await put_queue(chat_id, original_chat_id, file_path if direct else f"vid_{vidid}", title, duration_min, user_name, vidid, user_id, "video" if video else "audio", forceplay=forceplay)
                
                img = await get_thumb(vidid)
                button = stream_markup_timer(_, chat_id, "00:00", duration_min)
                
                # 🔥 THEME & ON/OFF LOGIC
                theme = await get_player_style(chat_id)
                is_on = await is_player_on(chat_id)
                
                if not is_on:
                    run = await app.send_message(original_chat_id, text=f"<b><emoji id='5999063078983964465'>🎧</emoji> Sᴛᴀʀᴛᴇᴅ ᴘʟᴀʏɪɴɢ:</b> {title[:30]}\n<b><emoji id='6001522720855037558'>👤</emoji> ʀᴇǫᴜᴇsᴛᴇᴅ ʙʏ:</b> {user_name}")
                    asyncio.create_task(auto_clean(run, 4)) # Auto Delete in 4s
                else:
                    video_file = getattr(config, "PLAYER_VIDEO", "https://files.catbox.moe/qxj5y2.mp4")
                    caption_text = _[f"stream_{theme}"].format(f"https://t.me/{app.username}?start=info_{vidid}", title[:23], duration_min, user_name, video_file)
                    
                    if theme == 2:
                        if HAS_PREVIEW_OPTIONS:
                            run = await app.send_message(
                                original_chat_id, 
                                text=caption_text, 
                                link_preview_options=LinkPreviewOptions(url=video_file, show_above_text=True)
                            )
                        else:
                            run = await app.send_message(original_chat_id, text=caption_text, disable_web_page_preview=False)
                    else:
                        run = await app.send_photo(original_chat_id, photo=img, caption=caption_text, has_spoiler=True)
                    
                    await inject_premium_markup(original_chat_id, run.id, button)
                
                db[chat_id][0]["mystic"] = run
                db[chat_id][0]["markup"] = "stream"
        if count == 0:
            return
        else:
            link = await YUKIIBin(msg)
            lines = msg.count("\n")
            car = os.linesep.join(msg.split(os.linesep)[:17]) if lines >= 17 else msg
            carbon = await Carbon.generate(car, randint(100, 10000000))
            upl = close_markup(_)
            return await app.send_photo(original_chat_id, photo=carbon, caption=_["play_21"].format(position, link), reply_markup=upl, has_spoiler=True)

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
            
            run_msg = await app.send_message(
                chat_id=original_chat_id,
                text=_["queue_4"].format(position, title[:27], duration_min, user_name),
            )
            await inject_premium_markup(original_chat_id, run_msg.id, button)
        else:
            if not forceplay:
                db[chat_id] = []
            await YUKII.join_call(chat_id, original_chat_id, file_path, video=status, image=thumbnail)
            await put_queue(chat_id, original_chat_id, file_path if direct else f"vid_{vidid}", title, duration_min, user_name, vidid, user_id, "video" if video else "audio", forceplay=forceplay)
            
            img = await get_thumb(vidid)
            button = stream_markup_timer(_, chat_id, "00:00", duration_min)
            
            # 🔥 THEME & ON/OFF LOGIC
            theme = await get_player_style(chat_id)
            is_on = await is_player_on(chat_id)
            
            if not is_on:
                run = await app.send_message(original_chat_id, text=f"<b><emoji id='5999063078983964465'>🎧</emoji> Sᴛᴀʀᴛᴇᴅ ᴘʟᴀʏɪɴɢ:</b> {title[:30]}\n<b><emoji id='6001522720855037558'>👤</emoji> ʀᴇǫᴜᴇsᴛᴇᴅ ʙʏ:</b> {user_name}")
                asyncio.create_task(auto_clean(run, 4))
            else:
                video_file = getattr(config, "PLAYER_VIDEO", "https://files.catbox.moe/qxj5y2.mp4")
                caption_text = _[f"stream_{theme}"].format(f"https://t.me/{app.username}?start=info_{vidid}", title[:23], duration_min, user_name, video_file)
                
                if theme == 2:
                    if HAS_PREVIEW_OPTIONS:
                        run = await app.send_message(
                            original_chat_id, 
                            text=caption_text, 
                            link_preview_options=LinkPreviewOptions(url=video_file, show_above_text=True)
                        )
                    else:
                        run = await app.send_message(original_chat_id, text=caption_text, disable_web_page_preview=False)
                else:
                    run = await app.send_photo(original_chat_id, photo=img, caption=caption_text, has_spoiler=True)
                    
                await inject_premium_markup(original_chat_id, run.id, button)
            
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
            await YUKII.join_call(chat_id, original_chat_id, file_path, video=None)
            await put_queue(chat_id, original_chat_id, file_path, title, duration_min, user_name, streamtype, user_id, "audio", forceplay=forceplay)
            
            button = stream_markup_timer(_, chat_id, "00:00", duration_min)
            
            # 🔥 THEME & ON/OFF LOGIC
            theme = await get_player_style(chat_id)
            is_on = await is_player_on(chat_id)
            
            if not is_on:
                run = await app.send_message(original_chat_id, text=f"<b><emoji id='5999063078983964465'>🎧</emoji> Sᴛᴀʀᴛᴇᴅ ᴘʟᴀʏɪɴɢ:</b> {title[:30]}\n<b><emoji id='6001522720855037558'>👤</emoji> ʀᴇǫᴜᴇsᴛᴇᴅ ʙʏ:</b> {user_name}")
                asyncio.create_task(auto_clean(run, 4))
            else:
                video_file = getattr(config, "PLAYER_VIDEO", "https://files.catbox.moe/qxj5y2.mp4")
                caption_text = _[f"stream_{theme}"].format(config.SUPPORT_CHAT, title[:23], duration_min, user_name, video_file)
                
                if theme == 2:
                    if HAS_PREVIEW_OPTIONS:
                        run = await app.send_message(
                            original_chat_id, 
                            text=caption_text, 
                            link_preview_options=LinkPreviewOptions(url=video_file, show_above_text=True)
                        )
                    else:
                        run = await app.send_message(original_chat_id, text=caption_text, disable_web_page_preview=False)
                else:
                    run = await app.send_photo(original_chat_id, photo=config.SOUNCLOUD_IMG_URL, caption=caption_text, has_spoiler=True)
                    
                await inject_premium_markup(original_chat_id, run.id, button)
            
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
            await YUKII.join_call(chat_id, original_chat_id, file_path, video=status)
            await put_queue(chat_id, original_chat_id, file_path, title, duration_min, user_name, streamtype, user_id, "video" if video else "audio", forceplay=forceplay)
            if video:
                await add_active_video_chat(chat_id)
                
            button = stream_markup_timer(_, chat_id, "00:00", duration_min)
            
            # 🔥 THEME & ON/OFF LOGIC
            theme = await get_player_style(chat_id)
            is_on = await is_player_on(chat_id)
            
            if not is_on:
                run = await app.send_message(original_chat_id, text=f"<b><emoji id='5999063078983964465'>🎧</emoji> Sᴛᴀʀᴛᴇᴅ ᴘʟᴀʏɪɴɢ:</b> {title[:30]}\n<b><emoji id='6001522720855037558'>👤</emoji> ʀᴇǫᴜᴇsᴛ ʙʏ:</b> {user_name}")
                asyncio.create_task(auto_clean(run, 4))
            else:
                video_file = getattr(config, "PLAYER_VIDEO", "https://files.catbox.moe/qxj5y2.mp4")
                caption_text = _[f"stream_{theme}"].format(link, title[:23], duration_min, user_name, video_file)
                
                if theme == 2:
                    if HAS_PREVIEW_OPTIONS:
                        run = await app.send_message(
                            original_chat_id, 
                            text=caption_text, 
                            link_preview_options=LinkPreviewOptions(url=video_file, show_above_text=True)
                        )
                    else:
                        run = await app.send_message(original_chat_id, text=caption_text, disable_web_page_preview=False)
                else:
                    run = await app.send_photo(original_chat_id, photo=config.TELEGRAM_VIDEO_URL if video else config.TELEGRAM_AUDIO_URL, caption=caption_text, has_spoiler=True)
                    
                await inject_premium_markup(original_chat_id, run.id, button)
            
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
            await YUKII.join_call(chat_id, original_chat_id, file_path, video=status, image=thumbnail if thumbnail else None)
            await put_queue(chat_id, original_chat_id, f"live_{vidid}", title, duration_min, user_name, vidid, user_id, "video" if video else "audio", forceplay=forceplay)
            
            img = await get_thumb(vidid)
            button = stream_markup(_, chat_id)
            
            # 🔥 THEME & ON/OFF LOGIC
            theme = await get_player_style(chat_id)
            is_on = await is_player_on(chat_id)
            
            if not is_on:
                run = await app.send_message(original_chat_id, text=f"<b><emoji id='5999063078983964465'>🎧</emoji> Sᴛᴀʀᴛᴇᴅ ʟɪᴠᴇ sᴛʀᴇᴀᴍ:</b> {title[:30]}\n<b><emoji id='6001522720855037558'>👤</emoji> ʀᴇǫᴜᴇsᴛᴇᴅ ʙʏ:</b> {user_name}")
                asyncio.create_task(auto_clean(run, 4))
            else:
                video_file = getattr(config, "PLAYER_VIDEO", "https://files.catbox.moe/qxj5y2.mp4")
                caption_text = _[f"livestream_{theme}"].format(f"https://t.me/{app.username}?start=info_{vidid}", title[:23], duration_min, user_name, video_file)
                
                if theme == 2:
                    if HAS_PREVIEW_OPTIONS:
                        run = await app.send_message(
                            original_chat_id, 
                            text=caption_text, 
                            link_preview_options=LinkPreviewOptions(url=video_file, show_above_text=True)
                        )
                    else:
                        run = await app.send_message(original_chat_id, text=caption_text, disable_web_page_preview=False)
                else:
                    run = await app.send_photo(original_chat_id, photo=img, caption=caption_text, has_spoiler=True)
                    
                await inject_premium_markup(original_chat_id, run.id, button)
            
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
            await YUKII.join_call(chat_id, original_chat_id, link, video=True if video else None)
            await put_queue_index(chat_id, original_chat_id, "index_url", title, duration_min, user_name, link, "video" if video else "audio", forceplay=forceplay)
            
            button = stream_markup(_, chat_id)
            
            # 🔥 THEME & ON/OFF LOGIC
            theme = await get_player_style(chat_id)
            is_on = await is_player_on(chat_id)
            
            if not is_on:
                run = await app.send_message(original_chat_id, text=f"<b><emoji id='5999063078983964465'>🎧</emoji> Sᴛᴀʀᴛᴇᴅ ᴘʟᴀʏɪɴɢ:</b> {title[:30]}\n<b><emoji id='6001522720855037558'>👤</emoji> ʀᴇǫᴜᴇsᴛᴇᴅ ʙʏ:</b> {user_name}")
                asyncio.create_task(auto_clean(run, 4))
            else:
                video_file = getattr(config, "PLAYER_VIDEO", "https://files.catbox.moe/qxj5y2.mp4")
                caption_text = _[f"stream_{theme}"].format(link, title[:23], duration_min, user_name, video_file)
                
                if theme == 2:
                    if HAS_PREVIEW_OPTIONS:
                        run = await app.send_message(
                            original_chat_id, 
                            text=caption_text, 
                            link_preview_options=LinkPreviewOptions(url=video_file, show_above_text=True)
                        )
                    else:
                        run = await app.send_message(original_chat_id, text=caption_text, disable_web_page_preview=False)
                else:
                    run = await app.send_photo(original_chat_id, photo=config.STREAM_IMG_URL, caption=caption_text, has_spoiler=True)
                    
                await inject_premium_markup(original_chat_id, run.id, button)
            
            db[chat_id][0]["mystic"] = run
            db[chat_id][0]["markup"] = "tg"
            await mystic.delete()
