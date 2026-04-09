import os
from pyrogram import filters
from pyrogram.enums import ChatType, ChatMemberStatus
from pyrogram.errors import MessageIdInvalid
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, Message

import config
from YUKIIMUSIC import app
from YUKIIMUSIC.misc import SUDOERS, mongodb
from YUKIIMUSIC.utils.decorators.language import language, languageCB
from config import BANNED_USERS

#
playerdb = mongodb.player_settings

async def get_player_style(chat_id):
    # Pehle group ka custom check karega
    user = await playerdb.find_one({"chat_id": chat_id})
    if user and "style" in user:
        return user["style"]
    # Agar group ka nahi hai, toh GLOBAL check karega
    if chat_id != "GLOBAL":
        global_user = await playerdb.find_one({"chat_id": "GLOBAL"})
        if global_user and "style" in global_user:
            return global_user["style"]
    return 1

async def set_player_style(chat_id, style: int):
    await playerdb.update_one({"chat_id": chat_id}, {"$set": {"style": style}}, upsert=True)

async def is_player_on(chat_id):
    user = await playerdb.find_one({"chat_id": chat_id})
    if user and "is_on" in user:
        return user["is_on"]
    if chat_id != "GLOBAL":
        global_user = await playerdb.find_one({"chat_id": "GLOBAL"})
        if global_user and "is_on" in global_user:
            return global_user["is_on"]
    return True

async def set_player_on(chat_id, is_on: bool):
    await playerdb.update_one({"chat_id": chat_id}, {"$set": {"is_on": is_on}}, upsert=True)


# 
def player_markup(style: int, is_on: bool, target_id):
    status = "✅ ᴏɴ" if is_on else "❌ ᴏғғ"
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(f"{'🔘' if style == 1 else ''} ᴅᴇsɪɢɴ 1", callback_data=f"set_player_1_{target_id}"),
                InlineKeyboardButton(f"{'🔘' if style == 2 else ''} ᴅᴇsɪɢɴ 2", callback_data=f"set_player_2_{target_id}"),
            ],
            [
                InlineKeyboardButton(f"{'🔘' if style == 3 else ''} ᴅᴇsɪɢɴ 3", callback_data=f"set_player_3_{target_id}"),
                InlineKeyboardButton(f"{'🔘' if style == 4 else ''} ᴅᴇsɪɢɴ 4", callback_data=f"set_player_4_{target_id}"),
            ],
            [
                InlineKeyboardButton(f"ᴘʟᴀʏᴇʀ sᴛᴀᴛᴜs : {status}", callback_data=f"toggle_player_{target_id}"),
            ],
            [
                InlineKeyboardButton("🗑 ᴄʟᴏsᴇ", callback_data="close_player_panel"),
            ]
        ]
    )

def get_digan_image(style: int):
    if style == 1:
        return getattr(config, "DIGAN_1", config.STATS_IMG_URL)
    elif style == 2:
        return getattr(config, "DIGAN_2", config.STATS_IMG_URL)
    elif style == 3:
        return getattr(config, "DIGAN_3", config.STATS_IMG_URL)
    elif style == 4:
        return getattr(config, "DIGAN_4", config.STATS_IMG_URL)
    return config.STATS_IMG_URL


# 
@app.on_message(filters.command(["player", "gcplayer", "songplayer", "globalplayer"]) & ~BANNED_USERS)
@language
async def player_command(client, message: Message, _):
    # Anonymous Admin Check
    if message.sender_chat:
        return await message.reply_text("❌ ᴘʟᴇᴀsᴇ ᴅɪsᴀʙʟᴇ ᴀɴᴏɴʏᴍᴏᴜs ᴀᴅᴍɪɴ ғɪʀsᴛ!")

    # DM Check & Global Logic
    if message.chat.type == ChatType.PRIVATE:
        if message.from_user.id in SUDOERS:
            target_id = "GLOBAL"
        else:
            return await message.reply_text("❌ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪs ᴏɴʟʏ ғᴏʀ ɢʀᴏᴜᴘs!")
    else:
        # Group Admin Check
        if message.from_user.id not in SUDOERS:
            member = await client.get_chat_member(message.chat.id, message.from_user.id)
            if member.status not in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
                return await message.reply_text("❌ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪs ᴏɴʟʏ ғᴏʀ ɢʀᴏᴜᴘ ᴀᴅᴍɪɴs ᴀɴᴅ ᴏᴡɴᴇʀs!")
        target_id = message.chat.id

    style = await get_player_style(target_id)
    is_on = await is_player_on(target_id)
    img = get_digan_image(style)
    
    panel_type = "ɢʟᴏʙᴀʟ" if target_id == "GLOBAL" else "ɢʀᴏᴜᴘ"
    
    caption = (
        f"**✨ {panel_type} ᴘʟᴀʏᴇʀ sᴇᴛᴛɪɴɢs ✨**\n\n"
        "ғʀᴏᴍ ʜᴇʀᴇ ʏᴏᴜ ᴄᴀɴ ᴄʜᴀɴɢᴇ ᴛʜᴇ ᴍᴜsɪᴄ ᴘʟᴀʏᴇʀ ᴅᴇsɪɢɴ. "
        "sᴇʟᴇᴄᴛ ʏᴏᴜʀ ғᴀᴠᴏʀɪᴛᴇ ᴅᴇsɪɢɴ ғʀᴏᴍ ᴛʜᴇ ʙᴜᴛᴛᴏɴs ʙᴇʟᴏᴡ!\n\n"
        f"**ᴄᴜʀʀᴇɴᴛ sᴛʏʟᴇ:** ᴅᴇsɪɢɴ {style}"
    )

    await message.reply_photo(
        photo=img,
        caption=caption,
        reply_markup=player_markup(style, is_on, target_id)
    )


# 
@app.on_callback_query(filters.regex(r"^(set_player_|toggle_player_)") & ~BANNED_USERS)
async def player_callbacks(client, CallbackQuery: CallbackQuery):
    data = CallbackQuery.data.split("_")
    action = data[0]
    
    # Target ID extraction
    if action == "set":
        new_style = int(data[2])
        target_id = data[3]
    else: # toggle
        target_id = data[2]

    if target_id != "GLOBAL":
        target_id = int(target_id)

    # Security Checks
    if CallbackQuery.sender_chat:
        return await CallbackQuery.answer("❌ ᴘʟᴇᴀsᴇ ᴅɪsᴀʙʟᴇ ᴀɴᴏɴʏᴍᴏᴜs ᴀᴅᴍɪɴ ғɪʀsᴛ!", show_alert=True)
        
    if target_id == "GLOBAL":
        if CallbackQuery.from_user.id not in SUDOERS:
            return await CallbackQuery.answer("❌ ᴏɴʟʏ ʙᴏᴛ ᴏᴡɴᴇʀ ᴄᴀɴ ᴄʜᴀɴɢᴇ ɢʟᴏʙᴀʟ sᴇᴛᴛɪɴɢs!", show_alert=True)
    else:
        if CallbackQuery.from_user.id not in SUDOERS:
            member = await client.get_chat_member(CallbackQuery.message.chat.id, CallbackQuery.from_user.id)
            if member.status not in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
                return await CallbackQuery.answer("❌ ᴏɴʟʏ ɢʀᴏᴜᴘ ᴀᴅᴍɪɴs ᴄᴀɴ ᴄʜᴀɴɢᴇ ᴛʜᴇsᴇ sᴇᴛᴛɪɴɢs!", show_alert=True)

    # Execute Actions
    current_style = await get_player_style(target_id)
    is_on = await is_player_on(target_id)
    panel_type = "ɢʟᴏʙᴀʟ" if target_id == "GLOBAL" else "ɢʀᴏᴜᴘ"

    if action == "set":
        if new_style == current_style:
            return await CallbackQuery.answer(f"ᴅᴇsɪɢɴ {new_style} ɪs ᴀʟʀᴇᴀᴅʏ sᴇᴛ!", show_alert=True)
        
        await set_player_style(target_id, new_style)
        await CallbackQuery.answer(f"✅ sᴜᴄᴄᴇssғᴜʟʟʏ sᴇᴛ ᴛᴏ ᴅᴇsɪɢɴ {new_style}!")
        
        img = get_digan_image(new_style)
        caption = (
            f"**✨ {panel_type} ᴘʟᴀʏᴇʀ sᴇᴛᴛɪɴɢs ✨**\n\n"
            "ғʀᴏᴍ ʜᴇʀᴇ ʏᴏᴜ ᴄᴀɴ ᴄʜᴀɴɢᴇ ᴛʜᴇ ᴍᴜsɪᴄ ᴘʟᴀʏᴇʀ ᴅᴇsɪɢɴ. "
            "sᴇʟᴇᴄᴛ ʏᴏᴜʀ ғᴀᴠᴏʀɪᴛᴇ ᴅᴇsɪɢɴ ғʀᴏᴍ ᴛʜᴇ ʙᴜᴛᴛᴏɴs ʙᴇʟᴏᴡ!\n\n"
            f"**ᴄᴜʀʀᴇɴᴛ sᴛʏʟᴇ:** ᴅᴇsɪɢɴ {new_style}"
        )
        
        med = InputMediaPhoto(media=img, caption=caption)
        try:
            await CallbackQuery.edit_message_media(media=med, reply_markup=player_markup(new_style, is_on, target_id))
        except MessageIdInvalid:
            pass

    elif action == "toggle":
        new_status = not is_on
        await set_player_on(target_id, new_status)
        
        status_text = "ᴏɴ ✅" if new_status else "ᴏғғ ❌"
        await CallbackQuery.answer(f"✅ {panel_type} ᴘʟᴀʏᴇʀ sᴛᴀᴛᴜs ɪs ɴᴏᴡ {status_text}!")
        
        try:
            await CallbackQuery.edit_message_reply_markup(reply_markup=player_markup(current_style, new_status, target_id))
        except MessageIdInvalid:
            pass

@app.on_callback_query(filters.regex("close_player_panel") & ~BANNED_USERS)
async def close_player_cb(client, CallbackQuery: CallbackQuery):
    if CallbackQuery.sender_chat:
        return await CallbackQuery.answer("❌ ᴘʟᴇᴀsᴇ ᴅɪsᴀʙʟᴇ ᴀɴᴏɴʏᴍᴏᴜs ᴀᴅᴍɪɴ ғɪʀsᴛ!", show_alert=True)

    if CallbackQuery.message.chat.type != ChatType.PRIVATE and CallbackQuery.from_user.id not in SUDOERS:
        member = await client.get_chat_member(CallbackQuery.message.chat.id, CallbackQuery.from_user.id)
        if member.status not in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
            return await CallbackQuery.answer("❌ ʏᴏᴜ ᴄᴀɴɴᴏᴛ ᴄʟᴏsᴇ ᴛʜɪs!", show_alert=True)

    try:
        await CallbackQuery.message.delete()
    except:
        pass

