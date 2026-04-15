import os
import sqlite3
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# ---------------- CONFIG ----------------
BOT_TOKEN = os.getenv("8700904545:AAEPG5zIwwlIPSMklc4QtIKbzJ_-VAizjB4")
ADMIN_GROUP_ID = -1003967160997  # حط ID القروب هنا

# ---------------- DATABASE ----------------
conn = sqlite3.connect("tickets.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS tickets (
    ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    message TEXT,
    status TEXT DEFAULT 'open',
    created_at INTEGER
)
""")
conn.commit()

# ---------------- ANTI SPAM ----------------
last_message_time = {}
SPAM_DELAY = 5

# ---------------- START ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "مرحباً 👋\nارسل شكواك وسيتم تحويلها للدعم."
    )

# ---------------- HANDLE USER MESSAGE ----------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    text = update.message.text
    now = time.time()

    # anti spam
    if user.id in last_message_time:
        if now - last_message_time[user.id] < SPAM_DELAY:
            await update.message.reply_text("🚫 الرجاء عدم الإرسال بسرعة")
            return
    last_message_time[user.id] = now

    # username check
    if not user.username:
        await update.message.reply_text("لازم تضيف username في حسابك")
        return

    # save ticket
    cursor.execute(
        "INSERT INTO tickets (user_id, username, message, created_at) VALUES (?, ?, ?, ?)",
        (user.id, user.username, text, int(now))
    )
    conn.commit()

    ticket_id = cursor.lastrowid

    # buttons
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📩 رد", callback_data=f"reply_{ticket_id}"),
            InlineKeyboardButton("❌ إغلاق", callback_data=f"close_{ticket_id}")
        ]
    ])

    msg = f"""🎫 شكوى جديدة #{ticket_id}
👤 @{user.username}
🆔 {user.id}

💬 {text}"""

    await context.bot.send_message(
        chat_id=ADMIN_GROUP_ID,
        text=msg,
        reply_markup=keyboard
    )

    await update.message.reply_text(f"تم إرسال شكواك رقم #{ticket_id} 👍")

# ---------------- CALLBACK ----------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    # close ticket
    if data.startswith("close_"):
        ticket_id = int(data.split("_")[1])

        cursor.execute("UPDATE tickets SET status='closed' WHERE ticket_id=?", (ticket_id,))
        conn.commit()

        await query.edit_message_text(query.message.text + "\n\n✅ تم إغلاق التذكرة")

    # reply mode
    elif data.startswith("reply_"):
        ticket_id = int(data.split("_")[1])

        cursor.execute("SELECT user_id FROM tickets WHERE ticket_id=?", (ticket_id,))
        row = cursor.fetchone()

        if not row:
            await query.message.reply_text("التذكرة غير موجودة")
            return

        context.user_data["reply_to"] = row[0]
        context.user_data["ticket_id"] = ticket_id

        await query.message.reply_text("✍️ اكتب ردك الآن")

# ---------------- ADMIN REPLY ----------------
async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.id != ADMIN_GROUP_ID:
        return

    if "reply_to" not in context.user_data:
        return

    user_id = context.user_data["reply_to"]
    ticket_id = context.user_data["ticket_id"]
    text = update.message.text

    await context.bot.send_message(
        chat_id=user_id,
        text=f"📩 رد على شكواك #{ticket_id}:\n\n{text}"
    )

    await update.message.reply_text("✅ تم إرسال الرد")

    del context.user_data["reply_to"]
    del context.user_data["ticket_id"]

# ---------------- APP ----------------
app = Application.builder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(MessageHandler(filters.TEXT & filters.Chat(ADMIN_GROUP_ID), admin_reply))

# ---------------- RUN ----------------
if __name__ == "__main__":
    print("BOT STARTED")
    app.run_polling(drop_pending_updates=True)
