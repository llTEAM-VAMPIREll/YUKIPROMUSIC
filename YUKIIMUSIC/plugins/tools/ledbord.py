import os
import time
import asyncio
from io import BytesIO
from datetime import datetime, timedelta

from PIL import Image, ImageDraw, ImageFont
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto

from YUKIIMUSIC import app
from YUKIIMUSIC.misc import mongodb

# Database
db = mongodb.leaderboard_db
message_collection = db.message_counts

LEADERBOARD_CACHE = {}
CACHE_TIME = 300 # 5 minutes cache

# ----------------- DB FUNCTIONS -----------------
async def update_message_count(chat_id: int, user_id: int, name: str):
    today = datetime.utcnow().strftime("%Y-%m-%d")
    await message_collection.update_one(
        {"chat_id": chat_id, "user_id": user_id, "date": today},
        {"$inc": {"count": 1}, "$set": {"name": name}},
        upsert=True
    )

async def get_leaderboard_data(chat_id: int, timeframe: str):
    """Database se Top 10 users aur Total Messages nikalega"""
    match_query = {"chat_id": chat_id}
    
    if timeframe == "today":
        today = datetime.utcnow().strftime("%Y-%m-%d")
        match_query["date"] = today
    elif timeframe == "week":
        seven_days_ago = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
        match_query["date"] = {"$gte": seven_days_ago}
    
    # 1. Get Top 10 Users
    pipeline_top = [
        {"$match": match_query},
        {"$group": {"_id": "$user_id", "name": {"$first": "$name"}, "total_messages": {"$sum": "$count"}}},
        {"$sort": {"total_messages": -1}},
        {"$limit": 10}
    ]
    cursor = message_collection.aggregate(pipeline_top)
    top_users = await cursor.to_list(length=10)

    # 2. Get Total Messages in this timeframe
    pipeline_total = [
        {"$match": match_query},
        {"$group": {"_id": None, "grand_total": {"$sum": "$count"}}}
    ]
    total_cursor = message_collection.aggregate(pipeline_total)
    total_data = await total_cursor.to_list(length=1)
    total_messages = total_data[0]['grand_total'] if total_data else 0

    return top_users, total_messages

# ----------------- FORMATTING HELPER -----------------
def build_caption(data: list, total_messages: int) -> str:
    text = "📈 LEADERBOARD\n"
    
    for index, user in enumerate(data):
        score = f"{user['total_messages']:,}".replace(",", ".") 
        name = str(user['name'])[:15] + "..." if len(str(user['name'])) > 15 else str(user['name'])
        text += f"{index+1}. 👤 {name} • {score}\n"
        
    formatted_total = f"{total_messages:,}".replace(",", ".")
    text += f"\n✉️ Total messages: {formatted_total}\n\n"
    text += "Enable AI Summary in this group using the /upgrade command."
    
    return text

# ----------------- IMAGE GENERATION -----------------
def generate_leaderboard_image(data: list, timeframe: str) -> BytesIO:
    template_path = "assets/template.png"
    if not os.path.exists(template_path):
        return None
        
    img = Image.open(template_path).convert("RGBA")
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype("assets/font.ttf", 24)
        font_small = ImageFont.truetype("assets/font.ttf", 18)
    except:
        font = ImageFont.load_default()
        font_small = ImageFont.load_default()

    bar_color = (41, 121, 255, 200) 
    text_color = (255, 255, 255, 255)
    
    start_x, start_y, gap, max_bar_width = 150, 200, 45, 500 
    
    if data:
        highest_score = data[0]['total_messages']
        for index, user in enumerate(data):
            score = user['total_messages']
            name = str(user['name'])[:15] + "..." if len(str(user['name'])) > 15 else str(user['name'])
            bar_width = int((score / highest_score) * max_bar_width) if highest_score > 0 else 10
            y_pos = start_y + (index * gap)
            draw.rounded_rectangle([(start_x, y_pos), (start_x + bar_width, y_pos + 30)], radius=10, fill=bar_color)
            draw.text((start_x + 10, y_pos + 2), f"{index+1}. {name}", fill=text_color, font=font_small)
            draw.text((start_x + bar_width + 15, y_pos + 2), str(score), fill=text_color, font=font_small)

    image_stream = BytesIO()
    img.save(image_stream, format="PNG")
    image_stream.name = f"leaderboard_{timeframe}.png"
    image_stream.seek(0)
    return image_stream

# ----------------- BUTTONS -----------------
def lb_buttons(current_timeframe="overall"):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Overall ✅" if current_timeframe == "overall" else "Overall", callback_data="lb_overall"),
            InlineKeyboardButton("Today ✅" if current_timeframe == "today" else "Today", callback_data="lb_today"),
            InlineKeyboardButton("Week ✅" if current_timeframe == "week" else "Week", callback_data="lb_week")
        ],
        [
            InlineKeyboardButton("Close", callback_data="lb_close")
        ]
    ])

# ----------------- HANDLERS -----------------

# 1. Message Counter Listener
@app.on_message(filters.group & ~filters.bot, group=10)
async def count_messages(client, message: Message):
    if not message.from_user:
        return
    asyncio.create_task(update_message_count(message.chat.id, message.from_user.id, message.from_user.first_name))

# 2. Main Command Handler
@app.on_message(filters.command(["rank", "rankings"], prefixes=["/", "."]) & filters.group)
async def leaderboard_cmd(client, message: Message):
    chat_id = message.chat.id
    
    # Command delete kar de (Taki group clean rahe)
    try:
        await message.delete()
    except:
        pass # Agar bot ke paas delete ki permission nahi hui toh error ignore kar dega

    timeframe = "overall"
    cache_key = f"{chat_id}_{timeframe}"
    
    # Check Cache first
    if cache_key in LEADERBOARD_CACHE and time.time() < LEADERBOARD_CACHE[cache_key]["expiry"]:
        cache_data = LEADERBOARD_CACHE[cache_key]
        # Direct send_photo use kar rahe hain (reply nahi)
        return await app.send_photo(
            chat_id=chat_id,
            photo=cache_data["image"], 
            caption=cache_data["caption"], 
            reply_markup=lb_buttons(timeframe),
            has_spoiler=True
        )

    data, total_msgs = await get_leaderboard_data(chat_id, timeframe)
    img_stream = generate_leaderboard_image(data, timeframe)
    caption_text = build_caption(data, total_msgs)
    
    if img_stream:
        # Direct send_photo
        sent_msg = await app.send_photo(
            chat_id=chat_id,
            photo=img_stream, 
            caption=caption_text, 
            reply_markup=lb_buttons(timeframe),
            has_spoiler=True
        )
        LEADERBOARD_CACHE[cache_key] = {
            "image": sent_msg.photo.file_id,
            "caption": caption_text,
            "expiry": time.time() + CACHE_TIME
        }
    else:
        await app.send_message(chat_id, "❌ Template image not found in assets folder!")

# 3. Timeframe Buttons Handler
@app.on_callback_query(filters.regex(r"^lb_(overall|today|week)$"))
async def leaderboard_callback(client, query):
    timeframe = query.data.split("_")[1]
    chat_id = query.message.chat.id
    cache_key = f"{chat_id}_{timeframe}"
    
    if cache_key in LEADERBOARD_CACHE and time.time() < LEADERBOARD_CACHE[cache_key]["expiry"]:
        cache_data = LEADERBOARD_CACHE[cache_key]
        try:
            await query.edit_message_media(
                media=InputMediaPhoto(
                    media=cache_data["image"], 
                    caption=cache_data["caption"],
                    has_spoiler=True
                ),
                reply_markup=lb_buttons(timeframe)
            )
            return await query.answer(f"{timeframe.capitalize()} Leaderboard Loaded")
        except:
            return await query.answer()

    await query.answer("Fetching data...", show_alert=False)
    
    data, total_msgs = await get_leaderboard_data(chat_id, timeframe)
    img_stream = generate_leaderboard_image(data, timeframe)
    caption_text = build_caption(data, total_msgs)
    
    if img_stream:
        await query.edit_message_media(
            media=InputMediaPhoto(
                media=img_stream, 
                caption=caption_text,
                has_spoiler=True
            ),
            reply_markup=lb_buttons(timeframe)
        )
        LEADERBOARD_CACHE[cache_key] = {
            "image": img_stream,
            "caption": caption_text,
            "expiry": time.time() + CACHE_TIME
        }
    else:
        await query.answer("Error generating image.", show_alert=True)

# 4. Close Button Handler
@app.on_callback_query(filters.regex(r"^lb_close$"))
async def close_leaderboard_callback(client, query):
    try:
        await query.message.delete()
    except:
        await query.answer("❌ Failed to delete message.", show_alert=True)

