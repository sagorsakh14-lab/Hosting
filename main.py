# main.py — TachZone Hosting Bot 🚀

import os
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater, CommandHandler, MessageHandler,
    CallbackQueryHandler, CallbackContext, Filters, ConversationHandler
)

from config import BOT_TOKEN, ADMIN_ID, BASE_DIR, MAX_BOTS
from database import (
    init_db, register_user, is_banned,
    get_user_bots, get_bot, add_bot, delete_bot,
    update_bot_status, rename_bot, count_user_bots,
    next_bot_id, get_all_users, get_all_bots,
    ban_user, unban_user
)
from bot_manager import (
    extract_zip, start_bot, stop_bot, restart_bot,
    is_running, get_logs, delete_bot_files, server_stats,
    get_bot_type
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

WAITING_NAME = 1
WAITING_FILE = 2

os.makedirs(BASE_DIR, exist_ok=True)


# ── Helpers ───────────────────────────────────────────────

def check_banned(user_id):
    return is_banned(user_id)

def is_admin(user_id):
    return user_id == ADMIN_ID

def get_main_reply_keyboard(user_id):
    """Reply Keyboard - মেইন মেনু"""
    keyboard = [
        [KeyboardButton("📤 বট আপলোড"), KeyboardButton("🤖 আমার বট")],
        [KeyboardButton("📊 স্ট্যাটাস"), KeyboardButton("❓ হেল্প")],
    ]
    if is_admin(user_id):
        keyboard.append([KeyboardButton("👑 অ্যাডমিন")])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_cancel_reply_keyboard():
    """Reply Keyboard - বাতিল"""
    return ReplyKeyboardMarkup([[KeyboardButton("❌ বাতিল")]], resize_keyboard=True)


# ── /start ────────────────────────────────────────────────

def cmd_start(update: Update, context: CallbackContext):
    user = update.effective_user
    register_user(user.id, user.username or "", user.full_name)
    context.user_data.clear()

    if check_banned(user.id):
        update.message.reply_text("⛔ আপনি ব্যান হয়েছেন।")
        return

    text = (
        f"👋 স্বাগতম, <b>{user.full_name}</b>!\n\n"
        f"🚀 <b>TachZone Hosting Bot</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"আপনার Telegram Bot ফাইল আপলোড করুন,\n"
        f"আমরা ২৪/৭ চালু রাখব!\n\n"
        f"📌 <b>বট আপলোড করতে:</b> /upload"
    )
    
    update.message.reply_text(
        text, 
        parse_mode='HTML',
        reply_markup=get_main_reply_keyboard(user.id)
    )


# ── /help ─────────────────────────────────────────────────

def cmd_help(update: Update, context: CallbackContext):
    user = update.effective_user
    text = (
        "📖 <b>সাহায্য - TachZone Hosting</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "<b>বট আপলোড করতে:</b>\n"
        "১. /upload কমান্ড দিন\n"
        "২. .zip, .py বা .js ফাইল পাঠান\n"
        "৩. বটের নাম দিন\n"
        "৪. অটো চালু হবে ✅\n\n"
        "<b>কমান্ড:</b>\n"
        "• /mybots — আপনার বট\n"
        "• /stats — সার্ভার স্ট্যাটাস\n"
        "• /bot ID — বট কন্ট্রোল"
    )
    update.message.reply_text(
        text, 
        parse_mode='HTML',
        reply_markup=get_main_reply_keyboard(user.id)
    )


# ── /upload ───────────────────────────────────────────────

def cmd_upload(update: Update, context: CallbackContext):
    user = update.effective_user
    
    if check_banned(user.id):
        update.message.reply_text("⛔ আপনি ব্যান হয়েছেন।")
        return ConversationHandler.END

    count = count_user_bots(user.id)
    if count >= MAX_BOTS:
        update.message.reply_text(
            f"⚠️ সর্বোচ্চ {MAX_BOTS}টা বট রাখা যাবে।",
            reply_markup=get_main_reply_keyboard(user.id)
        )
        return ConversationHandler.END

    context.user_data['uploading'] = True
    
    update.message.reply_text(
        "📁 এখন আপনার বটের <b>.zip</b>, <b>.py</b> বা <b>.js</b> ফাইল পাঠান।\n\n"
        "<i>বাতিল করতে /cancel লিখুন</i>",
        parse_mode='HTML',
        reply_markup=get_cancel_reply_keyboard()
    )
    return WAITING_FILE


# ── ফাইল গ্রহণ ───────────────────────────────────────────

def receive_file(update: Update, context: CallbackContext):
    user = update.effective_user
    
    logger.info(f"File upload started - User: {user.id}")
    
    if check_banned(user.id):
        return ConversationHandler.END

    doc = update.message.document
    if not doc:
        update.message.reply_text(
            "❌ দয়া করে একটি ফাইল পাঠান।",
            reply_markup=get_cancel_reply_keyboard()
        )
        return WAITING_FILE

    fname = doc.file_name or "unknown"
    file_size = doc.file_size / (1024 * 1024) if doc.file_size else 0
    
    # ফাইল টাইপ চেক
    allowed = ['.zip', '.py', '.js']
    if not any(fname.lower().endswith(ext) for ext in allowed):
        update.message.reply_text(
            "❌ শুধু .zip, .py বা .js ফাইল দিন।",
            reply_markup=get_cancel_reply_keyboard()
        )
        return WAITING_FILE

    status_msg = update.message.reply_text(
        f"⏳ ফাইল ডাউনলোড হচ্ছে...\n{fname} ({file_size:.1f}MB)"
    )

    try:
        # ফোল্ডার তৈরি
        bot_id = next_bot_id()
        folder = os.path.join(BASE_DIR, str(user.id), "bots", bot_id)
        os.makedirs(folder, exist_ok=True)
        
        # ফাইল ডাউনলোড
        file = doc.get_file()
        file_path = os.path.join(folder, fname)
        file.download(file_path)
        
        status_msg.edit_text(f"✅ ডাউনলোড সম্পন্ন!\n⏳ প্রসেসিং...")

        # ZIP এক্সট্রাক্ট
        if fname.lower().endswith('.zip'):
            try:
                extract_zip(file_path, folder)
                os.remove(file_path)
            except Exception as e:
                status_msg.edit_text(f"❌ ZIP এরর: {str(e)[:100]}")
                return ConversationHandler.END

        # ডাটা সেভ
        context.user_data['pending_bot_id'] = bot_id
        context.user_data['pending_folder'] = folder

        status_msg.edit_text(
            f"✅ ফাইল আপলোড সম্পন্ন!\n\n"
            f"📝 এখন বটের <b>নাম</b> দিন:\n"
            f"<i>বাতিল করতে /cancel</i>",
            parse_mode='HTML',
            reply_markup=get_cancel_reply_keyboard()
        )
        return WAITING_NAME

    except Exception as e:
        logger.error(f"Error: {e}")
        status_msg.edit_text(f"❌ এরর: {str(e)[:100]}")
        return ConversationHandler.END


# ── নাম গ্রহণ এবং বট স্টার্ট ─────────────────────────────

def receive_bot_name(update: Update, context: CallbackContext):
    user = update.effective_user
    name = update.message.text.strip()

    if not name or len(name) > 30:
        update.message.reply_text(
            "❌ নাম ১-৩০ অক্ষরের মধ্যে দিন।",
            reply_markup=get_cancel_reply_keyboard()
        )
        return WAITING_NAME

    bot_id = context.user_data.get('pending_bot_id')
    folder = context.user_data.get('pending_folder')

    if not bot_id or not folder:
        update.message.reply_text(
            "❌ কিছু সমস্যা হয়েছে। /upload দিন।",
            reply_markup=get_main_reply_keyboard(user.id)
        )
        return ConversationHandler.END

    # ডাটাবেজে সেভ
    add_bot(bot_id, user.id, name, folder)
    logger.info(f"Bot saved: {bot_id} - {name}")

    msg = update.message.reply_text(f"⚙️ <b>{name}</b> চালু হচ্ছে...", parse_mode='HTML')

    # বট স্টার্ট
    success, result = start_bot(bot_id)
    logger.info(f"Start result: {success}, {result}")

    if success:
        # Inline Keyboard (বট মেনুর জন্য)
        kb = [[InlineKeyboardButton("⚙️ বট মেনু", callback_data=f"botmenu:{bot_id}")]]
        msg.edit_text(
            f"🎉 <b>{name}</b> চালু হয়েছে!\n\n"
            f"🆔 ID: <code>{bot_id}</code>\n"
            f"📦 {result}",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(kb)
        )
    else:
        update_bot_status(bot_id, 'stopped')
        kb = [[InlineKeyboardButton("📋 লগ দেখুন", callback_data=f"logs:{bot_id}")]]
        msg.edit_text(
            f"⚠️ <b>{name}</b> চালু হয়নি!\n\n"
            f"🆔 ID: <code>{bot_id}</code>\n"
            f"❌ {result[:200]}",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(kb)
        )
    
    # Reply Keyboard ফেরত পাঠান
    update.message.reply_text(
        "✅ সম্পন্ন!",
        reply_markup=get_main_reply_keyboard(user.id)
    )

    context.user_data.clear()
    return ConversationHandler.END


# ── /cancel ───────────────────────────────────────────────

def cancel_upload(update: Update, context: CallbackContext):
    user = update.effective_user
    context.user_data.clear()
    update.message.reply_text(
        "❌ বাতিল করা হয়েছে।",
        reply_markup=get_main_reply_keyboard(user.id)
    )
    return ConversationHandler.END


# ── /mybots ──────────────────────────────────────────────

def cmd_mybots(update: Update, context: CallbackContext):
    user = update.effective_user
    bots = get_user_bots(user.id)
    
    if not bots:
        update.message.reply_text(
            "🤖 আপনার কোনো বট নেই।\n/upload দিয়ে আপলোড করুন।",
            reply_markup=get_main_reply_keyboard(user.id)
        )
        return

    response = "🤖 <b>আপনার বটগুলো:</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
    buttons = []
    
    for b in bots:
        running = is_running(b['bot_id'])
        emoji = "✅" if running else "❌"
        status = "চলছে" if running else "বন্ধ"
        bot_type = get_bot_type(b['bot_id'])
        response += f"{emoji} <b>{b['name']}</b> | <code>{b['bot_id']}</code> | {bot_type} | {status}\n"
        buttons.append([InlineKeyboardButton(f"⚙️ {b['name']}", callback_data=f"botmenu:{b['bot_id']}")])
    
    update.message.reply_text(
        response, 
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# ── /stats ───────────────────────────────────────────────

def cmd_stats(update: Update, context: CallbackContext):
    user = update.effective_user
    s = server_stats()
    bots = get_all_bots()
    running = sum(1 for b in bots if is_running(b['bot_id']))
    users = get_all_users()

    text = (
        f"📊 <b>সার্ভার অবস্থা</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🖥 CPU: {s['cpu']}%\n"
        f"💾 RAM: {s['ram_used']}GB / {s['ram_total']}GB\n"
        f"💿 Disk: {s['disk_used']}GB / {s['disk_total']}GB\n\n"
        f"👥 ইউজার: {len(users)}\n"
        f"🤖 বট: {len(bots)} (✅{running})"
    )
    update.message.reply_text(
        text, 
        parse_mode='HTML',
        reply_markup=get_main_reply_keyboard(user.id)
    )


# ── /bot ─────────────────────────────────────────────────

def cmd_bot(update: Update, context: CallbackContext):
    user = update.effective_user
    args = context.args
    
    if not args:
        update.message.reply_text("ব্যবহার: /bot TZ-0001")
        return
    
    bot_id = args[0].upper()
    bot = get_bot(bot_id)
    
    if not bot or (bot['user_id'] != user.id and not is_admin(user.id)):
        update.message.reply_text("❌ বট পাওয়া যায়নি।")
        return
    
    running = is_running(bot_id)
    emoji = "✅" if running else "❌"
    status = "চলছে" if running else "বন্ধ"
    bot_type = get_bot_type(bot_id)
    
    text = (
        f"⚙️ <b>{bot['name']}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 <code>{bot_id}</code>\n"
        f"📦 {bot_type}\n"
        f"{emoji} {status}\n"
    )

    # Inline Keyboard
    kb = [
        [
            InlineKeyboardButton("▶️ চালু", callback_data=f"start:{bot_id}"),
            InlineKeyboardButton("⏹ বন্ধ", callback_data=f"stop:{bot_id}"),
        ],
        [
            InlineKeyboardButton("🔄 Restart", callback_data=f"restart:{bot_id}"),
            InlineKeyboardButton("📋 Logs", callback_data=f"logs:{bot_id}"),
        ],
        [
            InlineKeyboardButton("🗑 Delete", callback_data=f"confirmdelete:{bot_id}"),
        ],
    ]
    
    update.message.reply_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(kb))


# ── Bot Menu Callback (Inline Buttons) ───────────────────

def bot_menu_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    data = query.data
    user = query.from_user

    logger.info(f"Callback: {data}")

    if data.startswith("botmenu:"):
        bot_id = data.split(":")[1]
        bot = get_bot(bot_id)
        if not bot:
            query.edit_message_text("❌ বট পাওয়া যায়নি।")
            return

        running = is_running(bot_id)
        emoji = "✅" if running else "❌"
        status = "চলছে" if running else "বন্ধ"
        bot_type = get_bot_type(bot_id)

        text = (
            f"⚙️ <b>{bot['name']}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 <code>{bot_id}</code>\n"
            f"📦 {bot_type}\n"
            f"{emoji} {status}\n"
        )

        kb = [
            [
                InlineKeyboardButton("▶️ চালু", callback_data=f"start:{bot_id}"),
                InlineKeyboardButton("⏹ বন্ধ", callback_data=f"stop:{bot_id}"),
            ],
            [
                InlineKeyboardButton("🔄 Restart", callback_data=f"restart:{bot_id}"),
                InlineKeyboardButton("📋 Logs", callback_data=f"logs:{bot_id}"),
            ],
            [
                InlineKeyboardButton("🗑 Delete", callback_data=f"confirmdelete:{bot_id}"),
            ],
        ]
        query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(kb))

    elif data.startswith("start:"):
        bot_id = data.split(":")[1]
        bot = get_bot(bot_id)
        success, result = start_bot(bot_id)
        msg = f"✅ <b>{bot['name']}</b> চালু হয়েছে!\n📦 {result}" if success else f"❌ {result[:200]}"
        kb = [[InlineKeyboardButton("🔙 ফিরুন", callback_data=f"botmenu:{bot_id}")]]
        query.edit_message_text(msg, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(kb))

    elif data.startswith("stop:"):
        bot_id = data.split(":")[1]
        bot = get_bot(bot_id)
        stop_bot(bot_id)
        kb = [[InlineKeyboardButton("🔙 ফিরুন", callback_data=f"botmenu:{bot_id}")]]
        query.edit_message_text(
            f"⏹ <b>{bot['name']}</b> বন্ধ হয়েছে।", 
            parse_mode='HTML', 
            reply_markup=InlineKeyboardMarkup(kb)
        )

    elif data.startswith("restart:"):
        bot_id = data.split(":")[1]
        bot = get_bot(bot_id)
        query.edit_message_text(f"🔄 <b>{bot['name']}</b> restart হচ্ছে...", parse_mode='HTML')
        success, result = restart_bot(bot_id)
        msg = f"✅ <b>{bot['name']}</b> restart হয়েছে!\n📦 {result}" if success else f"❌ {result[:200]}"
        kb = [[InlineKeyboardButton("🔙 ফিরুন", callback_data=f"botmenu:{bot_id}")]]
        query.edit_message_text(msg, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(kb))

    elif data.startswith("logs:"):
        bot_id = data.split(":")[1]
        bot = get_bot(bot_id)
        logs = get_logs(bot_id, 30)
        text = f"📋 <b>{bot['name']} - Logs:</b>\n<pre>{logs[-2000:]}</pre>" if logs else "📭 কোন লগ নেই"
        kb = [
            [InlineKeyboardButton("🔄 রিফ্রেশ", callback_data=f"logs:{bot_id}")],
            [InlineKeyboardButton("🔙 ফিরুন", callback_data=f"botmenu:{bot_id}")]
        ]
        query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(kb))

    elif data.startswith("confirmdelete:"):
        bot_id = data.split(":")[1]
        bot = get_bot(bot_id)
        kb = [
            [
                InlineKeyboardButton("✅ হ্যাঁ, মুছুন", callback_data=f"delete:{bot_id}"),
                InlineKeyboardButton("❌ না", callback_data=f"botmenu:{bot_id}"),
            ]
        ]
        query.edit_message_text(
            f"⚠️ <b>{bot['name']}</b> মুছে দেবেন?\nসব ফাইলও মুছে যাবে!",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(kb)
        )

    elif data.startswith("delete:"):
        bot_id = data.split(":")[1]
        bot = get_bot(bot_id)
        delete_bot_files(bot_id)
        delete_bot(bot_id)
        query.edit_message_text(f"🗑 <b>{bot['name']}</b> মুছে গেছে।", parse_mode='HTML')


# ── Message Handler (Reply Keyboard) ─────────────────────

def handle_message(update: Update, context: CallbackContext):
    user = update.effective_user
    text = update.message.text
    
    if check_banned(user.id):
        update.message.reply_text("⛔ আপনি ব্যান হয়েছেন।")
        return

    register_user(user.id, user.username or "", user.full_name)
    
    # Conversation চললে ইগনোর
    if context.user_data.get('uploading'):
        return

    if text == "📤 বট আপলোড":
        update.message.reply_text(
            "📤 বট আপলোড করতে /upload কমান্ড দিন।",
            reply_markup=get_main_reply_keyboard(user.id)
        )

    elif text == "🤖 আমার বট":
        cmd_mybots(update, context)

    elif text == "📊 স্ট্যাটাস":
        cmd_stats(update, context)

    elif text == "❓ হেল্প":
        cmd_help(update, context)

    elif text == "👑 অ্যাডমিন":
        if not is_admin(user.id):
            update.message.reply_text("⛔ আপনি অ্যাডমিন নন!")
            return
        s = server_stats()
        users = get_all_users()
        bots = get_all_bots()
        running = sum(1 for b in bots if is_running(b['bot_id']))
        text = (
            f"👑 <b>Admin Panel</b>\n━━━━━━━━━━━━━━━━━━━━\n"
            f"👥 ইউজার: {len(users)}\n"
            f"🤖 বট: {running}/{len(bots)}\n"
            f"🖥 CPU: {s['cpu']}%\n"
            f"💾 RAM: {s['ram_used']}GB/{s['ram_total']}GB"
        )
        update.message.reply_text(text, parse_mode='HTML', reply_markup=get_main_reply_keyboard(user.id))

    elif text == "❌ বাতিল":
        context.user_data.clear()
        update.message.reply_text(
            "✅ বাতিল করা হয়েছে।", 
            reply_markup=get_main_reply_keyboard(user.id)
        )

    elif text == "🏠 মেইন মেনু":
        context.user_data.clear()
        update.message.reply_text(
            "🏠 মেইন মেনু", 
            reply_markup=get_main_reply_keyboard(user.id)
        )


# ── Main ─────────────────────────────────────────────────

def main():
    init_db()
    
    updater = Updater(BOT_TOKEN)
    dp = updater.dispatcher

    # Conversation Handler
    conv = ConversationHandler(
        entry_points=[CommandHandler("upload", cmd_upload)],
        states={
            WAITING_FILE: [
                MessageHandler(Filters.document, receive_file),
                CommandHandler("cancel", cancel_upload),
            ],
            WAITING_NAME: [
                MessageHandler(Filters.text & ~Filters.command, receive_bot_name),
                CommandHandler("cancel", cancel_upload),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_upload)],
        allow_reentry=True
    )

    # Commands
    dp.add_handler(CommandHandler("start", cmd_start))
    dp.add_handler(CommandHandler("help", cmd_help))
    dp.add_handler(CommandHandler("mybots", cmd_mybots))
    dp.add_handler(CommandHandler("stats", cmd_stats))
    dp.add_handler(CommandHandler("bot", cmd_bot))
    
    # Conversation
    dp.add_handler(conv)
    
    # Callbacks (Inline Buttons)
    dp.add_handler(CallbackQueryHandler(bot_menu_callback))
    
    # Message Handler (Reply Buttons) - সবার শেষে
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    logger.info("🚀 TachZone Hosting Bot Started!")
    updater.start_polling(drop_pending_updates=True)
    updater.idle()

if __name__ == "__main__":
    main()