import os
import sqlite3
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, CommandHandler, ContextTypes, CallbackQueryHandler, filters

# التوكن من Render (Environment Variable)
import os
print("TOKEN =", os.getenv("8700904545:AAHn99LM5iIgl2m3o_T5BPsQPpCTVLqV8bY"))

ADMIN_GROUP_ID = -1003967160997

# DB
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

last_message_time = {}
SPAM_DELAY = 5


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("مرحباً 👋\nارسل شكواك وسيتم تحويلها للدعم.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    text = update.message.text

    now = time.time()

    if user.id in last_message_time:
        if now - last_message_time[user.id] < SPAM_DELAY:
            await update.message.reply_text("🚫 لا ترسل بسرعة")
            return

    last_message_time[user.id] = now

    if not user.username:
        await update.message.reply_text("لازم تضيف @username")
        return

    cursor.execute(
        "INSERT INTO tickets (user_id, username, message, created_at) VALUES (?, ?, ?, ?)",
        (user.id, user.username, text, int(now))
    )
    conn.commit()

    ticket_id = cursor.lastrowid

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📩 رد", callback_data=f"reply_{ticket_id}"),
            InlineKeyboardButton("❌ إغلاق", callback_data=f"close_{ticket_id}")
        ]
    ])

    msg = f"🎫 شكوى #{ticket_id}\n@{user.username}\n\n{text}"

    await context.bot.send_message(ADMIN_GROUP_ID, msg, reply_markup=keyboard)

    await update.message.reply_text(f"تم إرسال شكواك #{ticket_id}")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data.startswith("close_"):
        ticket_id = int(data.split("_")[1])
        cursor.execute("UPDATE tickets SET status='closed' WHERE ticket_id=?", (ticket_id,))
        conn.commit()

        await query.edit_message_text(query.message.text + "\n\n✅ تم الإغلاق")

    elif data.startswith("reply_"):
        ticket_id = int(data.split("_")[1])

        cursor.execute("SELECT user_id FROM tickets WHERE ticket_id=?", (ticket_id,))
        user_id = cursor.fetchone()[0]

        context.user_data["reply_to"] = user_id
        context.user_data["ticket_id"] = ticket_id

        await query.message.reply_text("✍️ اكتب ردك الآن")


async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.id != ADMIN_GROUP_ID:
        return

    if "reply_to" not in context.user_data:
        return

    user_id = context.user_data["reply_to"]
    ticket_id = context.user_data["ticket_id"]

    await context.bot.send_message(
        chat_id=user_id,
        text=f"📩 رد الدعم #{ticket_id}:\n\n{update.message.text}"
    )

    await update.message.reply_text("تم الإرسال ✅")

    context.user_data.clear()


app = Application.builder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(MessageHandler(filters.TEXT & filters.Chat(ADMIN_GROUP_ID), admin_reply))

app.run_polling(drop_pending_updates=True)
