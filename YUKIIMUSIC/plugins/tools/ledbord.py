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
CACHE_TIME = 0 # TEST KARTE TIME ISKO 0 RAKHA HAI. BAAD MEIN 300 (5 mins) KAR DENA!

# ----------------- ANTI-SPAM LOGIC -----------------
USER_MESSAGE_HISTORY = {} 
USER_LAST_MESSAGE = {} # Repeated words check karne ke liye
BLOCKED_USERS = {}
spam_lock = asyncio.Lock() 

SPAM_THRESHOLD = 5 
SPAM_WINDOW = 2 
BLOCK_DURATION = 1200 
REPEAT_THRESHOLD = 6 

# ----------------- MILESTONE LOGIC -----------------
MILESTONES_REACHED = {} 

# ----------------- LIVE TEST SESSIONS -----------------
COUNT_TEST_SESSIONS = {} # Format: {(chat_id, user_id): current_count}

# ----------------- DB FUNCTIONS -----------------
async def update_message_count_and_check_milestone(chat_id: int, user_id: int, name: str):
    today = datetime.utcnow().strftime("%Y-%m-%d")
    
    # 1. Update user count
    await message_collection.update_one(
        {"chat_id": chat_id, "user_id": user_id, "date": today},
        {"$inc": {"count": 1}, "$set": {"name": name}},
        upsert=True
    )
    
    # 2. Check total messages today for milestone
    pipeline_total = [
        {"$match": {"chat_id": chat_id, "date": today}},
        {"$group": {"_id": None, "total": {"$sum": "$count"}}}
    ]
    cursor = message_collection.aggregate(pipeline_total)
    data = await cursor.to_list(length=1)
    
    if data:
        total_today = data[0]['total']
        
        # Check if total is a multiple of 1000
        if total_today > 0 and total_today % 1000 == 0:
            if chat_id not in MILESTONES_REACHED:
                MILESTONES_REACHED[chat_id] = []
                
            # Avoid sending same milestone twice
            if total_today not in MILESTONES_REACHED[chat_id]:
                MILESTONES_REACHED[chat_id].append(total_today)
                
                # Format time as HH:MM
                current_time_str = datetime.now().strftime("%H:%M")
                msg_text = f"💪 {total_today} messages reached today! ({current_time_str})"
                
                try:
                    await app.send_message(chat_id, msg_text)
                except Exception as e:
                    print(f"Failed to send milestone msg: {e}")

async def get_leaderboard_data(chat_id: int, timeframe: str):
    match_query = {"chat_id": chat_id}
    
    if timeframe == "today":
        today = datetime.utcnow().strftime("%Y-%m-%d")
        match_query["date"] = today
    elif timeframe == "week":
        seven_days_ago = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
        match_query["date"] = {"$gte": seven_days_ago}
    
    pipeline_top = [
        {"$match": match_query},
        {"$group": {"_id": "$user_id", "name": {"$first": "$name"}, "total_messages": {"$sum": "$count"}}},
        {"$sort": {"total_messages": -1}},
        {"$limit": 10}
    ]
    cursor = message_collection.aggregate(pipeline_top)
    top_users = await cursor.to_list(length=10)

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
    if not data or total_messages == 0:
        return "📈 LEADERBOARD\n\n✉️ Total messages: 0\n\nEnable AI Summary in this group using the /upgrade command."
        
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
    if not data:
        return None 
        
    template_path = "YUKIIMUSIC/assets/template.png"
    if not os.path.exists(template_path):
        return None
        
    img = Image.open(template_path).convert("RGBA")
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype("YUKIIMUSIC/assets/font.ttf", 24)
        font_small = ImageFont.truetype("YUKIIMUSIC/assets/font.ttf", 18)
    except:
        font = ImageFont.load_default()
        font_small = ImageFont.load_default()

    bar_color = (41, 121, 255, 200) 
    text_color = (255, 255, 255, 255)
    start_x, start_y, gap, max_bar_width = 150, 200, 45, 500 
    
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

# 1. Message Counter Listener & Spam Checker (Group 112)
@app.on_message(filters.group & ~filters.bot, group=112)
async def count_messages(client, message: Message):
    if not message.from_user:
        return
        
    user_id = message.from_user.id
    current_time = time.time()
    
    # Check Block Status
    if user_id in BLOCKED_USERS:
        if current_time < BLOCKED_USERS[user_id]:
            return 
        else:
            del BLOCKED_USERS[user_id] 

    async with spam_lock:
        is_spammer = False
        spam_reason = ""
        
        # --- LOGIC A: Same Message Repeated 6 Times ---
        msg_text = message.text or message.caption
        if msg_text:
            msg_text = msg_text.lower().strip() 
            if user_id not in USER_LAST_MESSAGE:
                USER_LAST_MESSAGE[user_id] = {"text": msg_text, "count": 1}
            else:
                if USER_LAST_MESSAGE[user_id]["text"] == msg_text:
                    USER_LAST_MESSAGE[user_id]["count"] += 1
                else:
                    USER_LAST_MESSAGE[user_id] = {"text": msg_text, "count": 1}
            
            if USER_LAST_MESSAGE[user_id]["count"] >= REPEAT_THRESHOLD:
                is_spammer = True
                spam_reason = "repeating the same message"
                USER_LAST_MESSAGE[user_id] = {"text": "", "count": 0} 
                
        # --- LOGIC B: Time Window Spam (7 msgs in 10s) ---
        if user_id not in USER_MESSAGE_HISTORY:
            USER_MESSAGE_HISTORY[user_id] = []
            
        USER_MESSAGE_HISTORY[user_id].append(current_time)
        USER_MESSAGE_HISTORY[user_id] = [msg_time for msg_time in USER_MESSAGE_HISTORY[user_id] if current_time - msg_time <= SPAM_WINDOW]
        
        if len(USER_MESSAGE_HISTORY[user_id]) >= SPAM_THRESHOLD:
            is_spammer = True
            spam_reason = "flooding"
            USER_MESSAGE_HISTORY[user_id] = [] 
            
        # --- ACTION: Block if spammer ---
        if is_spammer:
            BLOCKED_USERS[user_id] = current_time + BLOCK_DURATION
            try:
                warning_msg = await message.reply_text(f"⛔️ {message.from_user.mention} is {spam_reason}: blocked for 20 minutes from the leaderboard.")
                async def delete_warn():
                    await asyncio.sleep(10)
                    try:
                        await warning_msg.delete()
                    except:
                        pass
                asyncio.create_task(delete_warn())
            except:
                pass
            return 
            
    # Normal User -> Count Update
    asyncio.create_task(update_message_count_and_check_milestone(message.chat.id, message.from_user.id, message.from_user.first_name))

    # --- LIVE TEST LOGIC INTERCEPTOR ---
    session_key = (message.chat.id, message.from_user.id)
    if session_key in COUNT_TEST_SESSIONS:
        # Ignore command messages from increasing the live test count reply
        if msg_text and msg_text.startswith(("/", ".")):
            return
            
        COUNT_TEST_SESSIONS[session_key] += 1
        count = COUNT_TEST_SESSIONS[session_key]
        
        btn = InlineKeyboardMarkup([[
            InlineKeyboardButton("🛑 End Count", callback_data=f"endct_{message.from_user.id}")
        ]])
        
        try:
            await message.reply_text(f"📝 Message {count} | Database Updated ✅", reply_markup=btn)
        except:
            pass

# ----------------- LIVE TEST COMMAND -----------------
@app.on_message(filters.command(["cunttest", "counttest"], prefixes=["/", "."]) & filters.group)
async def start_count_test(client, message: Message):
    session_key = (message.chat.id, message.from_user.id)
    
    # Initialize count to 0
    COUNT_TEST_SESSIONS[session_key] = 0
    
    btn = InlineKeyboardMarkup([[
        InlineKeyboardButton("🛑 End Count", callback_data=f"endct_{message.from_user.id}")
    ]])
    
    await message.reply_text(
        f"✅ **Test Started for {message.from_user.mention}!**\n\n"
        "Ab tu jo bhi message bhejega, main uski live counting aur database update report doonga.\n"
        "Jab test khatam karna ho toh neeche 'End Count' daba dena.",
        reply_markup=btn
    )

# ----------------- LIVE TEST END BUTTON -----------------
@app.on_callback_query(filters.regex(r"^endct_(\d+)$"))
async def end_count_cb(client, query):
    user_id = int(query.matches[0].group(1))
    
    if query.from_user.id != user_id:
        return await query.answer("Ye test tumhara nahi hai!", show_alert=True)
        
    session_key = (query.message.chat.id, user_id)
    
    if session_key in COUNT_TEST_SESSIONS:
        del COUNT_TEST_SESSIONS[session_key]
        try:
            await query.message.edit_text("✅ **Count test ended manually.** Ab main aage test count ke messages nahi bhejunga.")
        except:
            pass
    else:
        await query.answer("Test already ended!", show_alert=True)

# 2. Main Command Handler (Leaderboard)
@app.on_message(filters.command(["rank", "rankings"], prefixes=["/", "."]) & filters.group)
async def leaderboard_cmd(client, message: Message):
    chat_id = message.chat.id
    try:
        await message.delete()
    except:
        pass 

    timeframe = "overall"
    cache_key = f"{chat_id}_{timeframe}"
    
    if cache_key in LEADERBOARD_CACHE and time.time() < LEADERBOARD_CACHE[cache_key]["expiry"]:
        cache_data = LEADERBOARD_CACHE[cache_key]
        if cache_data.get("is_text_only"):
            return await app.send_message(chat_id, cache_data["caption"], reply_markup=lb_buttons(timeframe))
        else:
            return await app.send_photo(chat_id, photo=cache_data["image"], caption=cache_data["caption"], reply_markup=lb_buttons(timeframe), has_spoiler=True)

    data, total_msgs = await get_leaderboard_data(chat_id, timeframe)
    caption_text = build_caption(data, total_msgs)
    
    if not data or total_msgs == 0:
        sent_msg = await app.send_message(chat_id, caption_text, reply_markup=lb_buttons(timeframe))
        LEADERBOARD_CACHE[cache_key] = {"is_text_only": True, "caption": caption_text, "expiry": time.time() + CACHE_TIME}
    else:
        img_stream = generate_leaderboard_image(data, timeframe)
        if img_stream:
            sent_msg = await app.send_photo(chat_id, photo=img_stream, caption=caption_text, reply_markup=lb_buttons(timeframe), has_spoiler=True)
            LEADERBOARD_CACHE[cache_key] = {"is_text_only": False, "image": sent_msg.photo.file_id, "caption": caption_text, "expiry": time.time() + CACHE_TIME}
        else:
            await app.send_message(chat_id, "❌ Template image not found!")

# ----------------- FORCE UPDATE COMMAND -----------------
@app.on_message(filters.command(["force", "fc"], prefixes=["/", "."]) & filters.group)
async def force_leaderboard_update(client, message: Message):
    chat_id = message.chat.id
    try:
        await message.delete()
    except:
        pass
        
    for tf in ["overall", "today", "week"]:
        cache_key = f"{chat_id}_{tf}"
        if cache_key in LEADERBOARD_CACHE:
            del LEADERBOARD_CACHE[cache_key]
            
    timeframe = "overall"
    data, total_msgs = await get_leaderboard_data(chat_id, timeframe)
    caption_text = build_caption(data, total_msgs)
    
    if not data or total_msgs == 0:
        sent_msg = await app.send_message(chat_id, caption_text, reply_markup=lb_buttons(timeframe))
        LEADERBOARD_CACHE[f"{chat_id}_{timeframe}"] = {"is_text_only": True, "caption": caption_text, "expiry": time.time() + CACHE_TIME}
    else:
        img_stream = generate_leaderboard_image(data, timeframe)
        if img_stream:
            sent_msg = await app.send_photo(chat_id, photo=img_stream, caption=caption_text, reply_markup=lb_buttons(timeframe), has_spoiler=True)
            LEADERBOARD_CACHE[f"{chat_id}_{timeframe}"] = {"is_text_only": False, "image": sent_msg.photo.file_id, "caption": caption_text, "expiry": time.time() + CACHE_TIME}
        else:
            await app.send_message(chat_id, "❌ Template image not found!")

# 3. Timeframe Buttons Handler
@app.on_callback_query(filters.regex(r"^lb_(overall|today|week)$"))
async def leaderboard_callback(client, query):
    timeframe = query.data.split("_")[1]
    chat_id = query.message.chat.id
    cache_key = f"{chat_id}_{timeframe}"
    is_current_msg_photo = bool(query.message.photo)

    await query.answer("Fetching data...", show_alert=False)
    
    data, total_msgs = await get_leaderboard_data(chat_id, timeframe)
    caption_text = build_caption(data, total_msgs)
    
    if not data or total_msgs == 0:
        if is_current_msg_photo:
            await query.message.delete()
            await app.send_message(chat_id, caption_text, reply_markup=lb_buttons(timeframe))
        else:
            await query.edit_message_text(caption_text, reply_markup=lb_buttons(timeframe))
    else:
        img_stream = generate_leaderboard_image(data, timeframe)
        if img_stream:
            if not is_current_msg_photo:
                await query.message.delete()
                await app.send_photo(chat_id, photo=img_stream, caption=caption_text, reply_markup=lb_buttons(timeframe), has_spoiler=True)
            else:
                await query.edit_message_media(media=InputMediaPhoto(media=img_stream, caption=caption_text, has_spoiler=True), reply_markup=lb_buttons(timeframe))
        else:
            await query.answer("Error generating image.", show_alert=True)

# 4. Close Button Handler
@app.on_callback_query(filters.regex(r"^lb_close$"))
async def close_leaderboard_callback(client, query):
    try:
        await query.message.delete()
    except:
        await query.answer("❌ Failed to delete message.", show_alert=True)

# ----------------- TESTER COMMAND -----------------
@app.on_message(filters.command(["spamtest", "testspam"], prefixes=["/", "."]) & filters.group)
async def manual_spam_trigger(client, message: Message):
    user_id = message.from_user.id
    current_time = time.time()
    
    BLOCKED_USERS[user_id] = current_time + BLOCK_DURATION
    USER_MESSAGE_HISTORY[user_id] = []
    
    try:
        await message.delete()
        warning_msg = await message.reply_text(f"⛔️ [TEST] {message.from_user.mention} is flooding: blocked for 20 minutes from the leaderboard.")
        
        async def delete_warn():
            await asyncio.sleep(10)
            try:
                await warning_msg.delete()
            except:
                pass
        asyncio.create_task(delete_warn())
        
    except:
        pass
