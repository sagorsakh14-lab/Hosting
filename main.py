# main.py — TachZone Hosting Bot 🚀

import os
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters, ConversationHandler
)

from config import BOT_TOKEN, ADMIN_ID, BASE_DIR, MAX_BOTS
from database import (
    init_db, register_user, is_banned,
    get_user_bots, get_bot, add_bot, delete_bot,
    update_bot_status, rename_bot, count_user_bots,
    next_bot_id, get_all_users, get_all_bots,
    ban_user, unban_user, get_user
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

# Conversation states
WAITING_NAME = 1
WAITING_RENAME = 2
WAITING_FILE = 3

os.makedirs(BASE_DIR, exist_ok=True)


# ── Reply Keyboards ───────────────────────────────────────

def get_main_keyboard(user_id):
    """মেইন মেনু Reply Keyboard"""
    keyboard = [
        [KeyboardButton("📤 বট আপলোড"), KeyboardButton("🤖 আমার বট")],
        [KeyboardButton("📊 স্ট্যাটাস"), KeyboardButton("❓ হেল্প")],
    ]
    if is_admin(user_id):
        keyboard.append([KeyboardButton("👑 অ্যাডমিন প্যানেল")])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_cancel_keyboard():
    """বাতিল করার জন্য Reply Keyboard"""
    keyboard = [[KeyboardButton("❌ বাতিল")]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# ── Helpers ───────────────────────────────────────────────

def check_banned(user_id):
    return is_banned(user_id)

def is_admin(user_id):
    return user_id == ADMIN_ID


# ── /start ────────────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    register_user(user.id, user.username or "", user.full_name)

    if check_banned(user.id):
        await update.message.reply_text("⛔ আপনি ব্যান হয়েছেন।")
        return

    text = (
        f"👋 স্বাগতম, <b>{user.full_name}</b>!\n\n"
        f"🚀 <b>TachZone Hosting Bot</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"আপনার Telegram Bot ফাইল আপলোড করুন,\n"
        f"আমরা ২৪/৭ চালু রাখব!\n\n"
        f"📌 <b>নিচের বাটন থেকে অপশন সিলেক্ট করুন:</b>"
    )
    
    await update.message.reply_text(
        text, 
        parse_mode='HTML',
        reply_markup=get_main_keyboard(user.id)
    )


# ── /help ─────────────────────────────────────────────────

async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (
        "📖 <b>সাহায্য - TachZone Hosting</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "<b>বট আপলোড করতে:</b>\n"
        "১. '📤 বট আপলোড' বাটনে ক্লিক করুন\n"
        "২. .zip, .py বা .js ফাইল পাঠান\n"
        "৩. বটের নাম দিন\n"
        "৪. অটো চালু হবে ✅\n\n"
        "<b>সাপোর্টেড ফাইল:</b>\n"
        "• 🐍 Python (.py)\n"
        "• 🟢 Node.js (.js)\n"
        "• 📦 ZIP (ভিতরে যেকোনোটি)\n\n"
        "<b>বট কন্ট্রোল:</b>\n"
        "• '🤖 আমার বট' — সব বট দেখুন\n"
        "• /bot ID — বট মেনু খুলুন\n"
        "• /stop ID — বন্ধ করুন\n"
        "• /startbot ID — চালু করুন"
    )
    await update.message.reply_text(
        text, 
        parse_mode='HTML',
        reply_markup=get_main_keyboard(user.id)
    )


# ── /upload কমান্ড (Conversation শুরু) ───────────────────

async def cmd_upload(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if check_banned(user.id):
        return ConversationHandler.END

    count = count_user_bots(user.id)
    if count >= MAX_BOTS:
        await update.message.reply_text(
            f"⚠️ সর্বোচ্চ {MAX_BOTS}টা বট রাখা যাবে।\n"
            f"নতুন আপলোড করতে আগে /delete করুন।",
            reply_markup=get_main_keyboard(user.id)
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "📁 এখন আপনার বটের <b>.zip</b>, <b>.py</b> বা <b>.js</b> ফাইল পাঠান।\n\n"
        "<i>বাতিল করতে /cancel লিখুন</i>",
        parse_mode='HTML',
        reply_markup=get_cancel_keyboard()
    )
    return WAITING_FILE


# ── ফাইল গ্রহণ করার হ্যান্ডলার ───────────────────────────

async def receive_file(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """আপলোড করা ফাইল গ্রহণ করুন"""
    user = update.effective_user
    
    logger.info(f"Received file from user {user.id}")
    
    if check_banned(user.id):
        return ConversationHandler.END

    doc = update.message.document
    if not doc:
        await update.message.reply_text(
            "❌ দয়া করে একটি ফাইল পাঠান।",
            reply_markup=get_cancel_keyboard()
        )
        return WAITING_FILE

    fname = doc.file_name or ""
    file_size = doc.file_size / (1024 * 1024)  # MB
    
    logger.info(f"File: {fname}, Size: {file_size:.2f}MB")
    
    # ফাইল টাইপ চেক
    allowed_extensions = ['.zip', '.py', '.js']
    is_allowed = any(fname.lower().endswith(ext) for ext in allowed_extensions)
    
    if not is_allowed:
        await update.message.reply_text(
            "❌ শুধু .zip, .py বা .js ফাইল দিন।",
            reply_markup=get_cancel_keyboard()
        )
        return WAITING_FILE
    
    # ফাইল সাইজ চেক (50MB)
    if file_size > 50:
        await update.message.reply_text(
            f"❌ ফাইল সাইজ {file_size:.1f}MB, সর্বোচ্চ 50MB আপলোড করা যাবে।",
            reply_markup=get_cancel_keyboard()
        )
        return WAITING_FILE

    # স্ট্যাটাস মেসেজ
    status_msg = await update.message.reply_text(
        f"⏳ ফাইল নামাচ্ছি... ({file_size:.1f}MB)\n"
        f"অনুগ্রহ করে অপেক্ষা করুন...",
        reply_markup=get_cancel_keyboard()
    )

    try:
        # বট ID এবং ফোল্ডার তৈরি
        bot_id = next_bot_id()
        folder = os.path.join(BASE_DIR, str(user.id), "bots", bot_id)
        os.makedirs(folder, exist_ok=True)
        
        logger.info(f"Created folder: {folder}")

        # ফাইল ডাউনলোড
        file = await doc.get_file()
        file_path = os.path.join(folder, fname)
        
        await status_msg.edit_text(f"⏳ ডাউনলোড হচ্ছে... (0%)")
        await file.download_to_drive(file_path)
        await status_msg.edit_text(f"✅ ডাউনলোড সম্পন্ন!\n⏳ ফাইল প্রসেস করা হচ্ছে...")

        # ZIP এক্সট্রাক্ট
        if fname.lower().endswith('.zip'):
            try:
                extract_zip(file_path, folder)
                os.remove(file_path)
                await status_msg.edit_text(f"✅ ZIP এক্সট্রাক্ট সম্পন্ন!")
            except Exception as e:
                logger.error(f"ZIP extract error: {e}")
                await status_msg.edit_text(f"❌ ZIP এক্সট্রাক্ট এরর: {e}")
                return ConversationHandler.END

        # ফোল্ডারের ফাইল দেখান
        files = os.listdir(folder)
        files_list = "\n".join([f"• {f}" for f in files[:5]])
        if len(files) > 5:
            files_list += f"\n• ... আরো {len(files)-5}টি"

        # ডাটা সেভ করুন
        ctx.user_data['pending_bot_id'] = bot_id
        ctx.user_data['pending_folder'] = folder

        await status_msg.edit_text(
            f"✅ ফাইল আপলোড সম্পন্ন!\n\n"
            f"📁 ফাইলসমূহ:\n{files_list}\n\n"
            f"📝 এখন আপনার বটের <b>নাম</b> দিন:\n"
            f"(যেমন: MyShopBot, OTPBot)\n\n"
            f"<i>বাতিল করতে /cancel লিখুন</i>",
            parse_mode='HTML',
            reply_markup=get_cancel_keyboard()
        )
        return WAITING_NAME

    except Exception as e:
        logger.error(f"File processing error: {e}", exc_info=True)
        await status_msg.edit_text(
            f"❌ এরর হয়েছে: {str(e)[:200]}\n\n"
            f"আবার চেষ্টা করুন বা ছোট ফাইল আপলোড করুন।",
            reply_markup=get_main_keyboard(user.id)
        )
        return ConversationHandler.END


# ── বটের নাম গ্রহণ ───────────────────────────────────────

async def receive_bot_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """বটের নাম গ্রহণ করুন"""
    user = update.effective_user
    name = update.message.text.strip()
    
    logger.info(f"Received bot name: {name}")

    if not name or len(name) > 30:
        await update.message.reply_text(
            "❌ নাম ১-৩০ অক্ষরের মধ্যে দিন।",
            reply_markup=get_cancel_keyboard()
        )
        return WAITING_NAME

    bot_id = ctx.user_data.get('pending_bot_id')
    folder = ctx.user_data.get('pending_folder')

    if not bot_id or not folder:
        await update.message.reply_text(
            "❌ কিছু সমস্যা হয়েছে। আবার /upload দিন।",
            reply_markup=get_main_keyboard(user.id)
        )
        return ConversationHandler.END

    # ডাটাবেজে সেভ
    add_bot(bot_id, user.id, name, folder)

    msg = await update.message.reply_text(
        f"⚙️ <b>{name}</b> চালু হচ্ছে...", 
        parse_mode='HTML'
    )

    # বট স্টার্ট
    success, result = start_bot(bot_id)

    if success:
        kb = [[InlineKeyboardButton("⚙️ বট মেনু", callback_data=f"botmenu:{bot_id}")]]
        await msg.edit_text(
            f"🎉 <b>{name}</b> চালু হয়েছে!\n\n"
            f"🆔 Bot ID: <code>{bot_id}</code>\n"
            f"✅ Status: চলছে\n"
            f"📦 Type: {result}",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(kb)
        )
    else:
        update_bot_status(bot_id, 'stopped')
        kb = [[InlineKeyboardButton("📋 লগ দেখুন", callback_data=f"logs:{bot_id}")]]
        await msg.edit_text(
            f"⚠️ <b>{name}</b> চালু হয়নি!\n\n"
            f"🆔 Bot ID: <code>{bot_id}</code>\n"
            f"❌ Error: {result[:200]}",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(kb)
        )
    
    await update.message.reply_text(
        "✅ বট তৈরি সম্পন্ন!",
        reply_markup=get_main_keyboard(user.id)
    )

    ctx.user_data.clear()
    return ConversationHandler.END


# ── ক্যান্সেল হ্যান্ডলার ─────────────────────────────────

async def cancel_upload(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """আপলোড ক্যান্সেল করুন"""
    user = update.effective_user
    ctx.user_data.clear()
    await update.message.reply_text(
        "❌ অপারেশন বাতিল করা হয়েছে।",
        reply_markup=get_main_keyboard(user.id)
    )
    return ConversationHandler.END


# ── Message Handler (Reply Buttons) ──────────────────────

async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """সাধারণ মেসেজ হ্যান্ডেল (Reply Keyboard বাটন)"""
    user = update.effective_user
    text = update.message.text
    
    if check_banned(user.id):
        await update.message.reply_text("⛔ আপনি ব্যান হয়েছেন।")
        return

    register_user(user.id, user.username or "", user.full_name)

    if text == "📤 বট আপলোড":
        count = count_user_bots(user.id)
        if count >= MAX_BOTS:
            await update.message.reply_text(
                f"⚠️ সর্বোচ্চ {MAX_BOTS}টা বট রাখা যাবে।",
                reply_markup=get_main_keyboard(user.id)
            )
            return
        
        # Conversation শুরু করার বদলে সরাসরি মেসেজ
        await update.message.reply_text(
            "📤 /upload কমান্ডটি ব্যবহার করুন বট আপলোড করতে।",
            reply_markup=get_main_keyboard(user.id)
        )

    elif text == "🤖 আমার বট":
        bots = get_user_bots(user.id)
        if not bots:
            await update.message.reply_text(
                "🤖 আপনার কোনো বট নেই।\n/upload দিয়ে আপলোড করুন।",
                reply_markup=get_main_keyboard(user.id)
            )
            return

        response = "🤖 <b>আপনার বটগুলো:</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        for b in bots:
            running = is_running(b['bot_id'])
            emoji = "✅" if running else "❌"
            status = "চলছে" if running else "বন্ধ"
            bot_type = get_bot_type(b['bot_id'])
            response += f"{emoji} <b>{b['name']}</b>\n"
            response += f"   🆔 <code>{b['bot_id']}</code>\n"
            response += f"   📦 {bot_type} | {status}\n\n"
        
        response += "⚙️ <b>বট কন্ট্রোল:</b>\n/bot ID — বট মেনু খুলুন"
        
        await update.message.reply_text(
            response, 
            parse_mode='HTML',
            reply_markup=get_main_keyboard(user.id)
        )

    elif text == "📊 স্ট্যাটাস":
        s = server_stats()
        bots = get_all_bots()
        running = sum(1 for b in bots if is_running(b['bot_id']))
        users = get_all_users()

        response = (
            f"📊 <b>সার্ভার অবস্থা</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🖥 CPU: {s['cpu']}%\n"
            f"💾 RAM: {s['ram_used']}GB / {s['ram_total']}GB ({s['ram_percent']}%)\n"
            f"💿 Disk: {s['disk_used']}GB / {s['disk_total']}GB ({s['disk_percent']}%)\n\n"
            f"👥 মোট ইউজার: {len(users)}\n"
            f"🤖 মোট বট: {len(bots)}\n"
            f"✅ চলমান: {running}\n"
            f"❌ বন্ধ: {len(bots) - running}"
        )
        await update.message.reply_text(
            response, 
            parse_mode='HTML',
            reply_markup=get_main_keyboard(user.id)
        )

    elif text == "❓ হেল্প":
        await cmd_help(update, ctx)

    elif text == "👑 অ্যাডমিন প্যানেল":
        if not is_admin(user.id):
            await update.message.reply_text(
                "⛔ আপনি অ্যাডমিন নন!", 
                reply_markup=get_main_keyboard(user.id)
            )
            return
        await show_admin_panel(update, ctx)

    elif text == "🏠 মেইন মেনু":
        await update.message.reply_text(
            "🏠 মেইন মেনুতে ফিরে এসেছেন।",
            reply_markup=get_main_keyboard(user.id)
        )


async def show_admin_panel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """অ্যাডমিন প্যানেল"""
    user = update.effective_user
    if not is_admin(user.id):
        return
    
    s = server_stats()
    users = get_all_users()
    bots = get_all_bots()
    running = sum(1 for b in bots if is_running(b['bot_id']))

    text = (
        f"👑 <b>Admin Panel — TachZone Hosting</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 মোট ইউজার: {len(users)}\n"
        f"🤖 চলমান বট: {running} / {len(bots)}\n"
        f"🖥 CPU: {s['cpu']}%\n"
        f"💾 RAM: {s['ram_used']}GB/{s['ram_total']}GB\n"
        f"💿 Disk: {s['disk_used']}GB/{s['disk_total']}GB\n\n"
        f"<b>কমান্ড:</b>\n"
        f"/allusers — সব ইউজার\n"
        f"/allbots — সব বট\n"
        f"/ban ID — ব্যান\n"
        f"/unban ID — আনব্যান\n"
        f"/killbot ID — বট বন্ধ\n"
        f"/broadcast মেসেজ — ব্রডকাস্ট"
    )
    
    await update.message.reply_text(
        text, 
        parse_mode='HTML',
        reply_markup=get_main_keyboard(user.id)
    )


# ── /bot কমান্ড ──────────────────────────────────────────

async def cmd_bot(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = ctx.args
    
    if not args:
        await update.message.reply_text(
            "ব্যবহার: /bot TZ-0001",
            reply_markup=get_main_keyboard(user.id)
        )
        return
    
    bot_id = args[0].upper()
    bot = get_bot(bot_id)
    
    if not bot or (bot['user_id'] != user.id and not is_admin(user.id)):
        await update.message.reply_text(
            "❌ বট পাওয়া যায়নি বা এটি আপনার নয়।",
            reply_markup=get_main_keyboard(user.id)
        )
        return
    
    running = is_running(bot_id)
    emoji = "✅" if running else "❌"
    status = "চলছে" if running else "বন্ধ"
    bot_type = get_bot_type(bot_id)
    
    text = (
        f"⚙️ <b>{bot['name']}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 ID: <code>{bot_id}</code>\n"
        f"📦 Type: {bot_type}\n"
        f"{emoji} Status: {status}\n"
        f"📅 তৈরি: {bot['created_at'][:10]}\n"
    )

    kb = [
        [
            InlineKeyboardButton("▶️ চালু", callback_data=f"start:{bot_id}"),
            InlineKeyboardButton("⏹ বন্ধ", callback_data=f"stop:{bot_id}"),
            InlineKeyboardButton("🔄 Restart", callback_data=f"restart:{bot_id}"),
        ],
        [
            InlineKeyboardButton("📋 Logs", callback_data=f"logs:{bot_id}"),
            InlineKeyboardButton("🗑 Delete", callback_data=f"confirmdelete:{bot_id}"),
        ],
    ]
    
    await update.message.reply_text(
        text, 
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(kb)
    )


# ── Bot Menu Callback ────────────────────────────────────

async def bot_menu_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user

    logger.info(f"Callback data: {data}")

    if data.startswith("botmenu:"):
        bot_id = data.split(":")[1]
        bot = get_bot(bot_id)
        if not bot:
            await query.edit_message_text("❌ বট পাওয়া যায়নি।")
            return

        running = is_running(bot_id)
        emoji = "✅" if running else "❌"
        status = "চলছে" if running else "বন্ধ"
        bot_type = get_bot_type(bot_id)

        text = (
            f"⚙️ <b>{bot['name']}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 ID: <code>{bot_id}</code>\n"
            f"📦 Type: {bot_type}\n"
            f"{emoji} Status: {status}\n"
            f"📅 তৈরি: {bot['created_at'][:10]}\n"
        )

        kb = [
            [
                InlineKeyboardButton("▶️ চালু", callback_data=f"start:{bot_id}"),
                InlineKeyboardButton("⏹ বন্ধ", callback_data=f"stop:{bot_id}"),
                InlineKeyboardButton("🔄 Restart", callback_data=f"restart:{bot_id}"),
            ],
            [
                InlineKeyboardButton("📋 Logs", callback_data=f"logs:{bot_id}"),
                InlineKeyboardButton("🗑 Delete", callback_data=f"confirmdelete:{bot_id}"),
            ],
        ]
        await query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(kb))

    elif data.startswith("start:"):
        bot_id = data.split(":")[1]
        bot = get_bot(bot_id)
        success, result = start_bot(bot_id)
        if success:
            kb = [[InlineKeyboardButton("🔙 বট মেনু", callback_data=f"botmenu:{bot_id}")]]
            msg = f"✅ <b>{bot['name']}</b> চালু হয়েছে!\n📦 {result}"
        else:
            kb = [[InlineKeyboardButton("📋 লগ দেখুন", callback_data=f"logs:{bot_id}")]]
            msg = f"❌ চালু হয়নি: {result[:200]}"
        await query.edit_message_text(msg, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(kb))

    elif data.startswith("stop:"):
        bot_id = data.split(":")[1]
        bot = get_bot(bot_id)
        stop_bot(bot_id)
        kb = [[InlineKeyboardButton("🔙 বট মেনু", callback_data=f"botmenu:{bot_id}")]]
        await query.edit_message_text(
            f"⏹ <b>{bot['name']}</b> বন্ধ হয়েছে।", 
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(kb)
        )

    elif data.startswith("restart:"):
        bot_id = data.split(":")[1]
        bot = get_bot(bot_id)
        await query.edit_message_text(f"🔄 <b>{bot['name']}</b> restart হচ্ছে...", parse_mode='HTML')
        success, result = restart_bot(bot_id)
        if success:
            kb = [[InlineKeyboardButton("🔙 বট মেনু", callback_data=f"botmenu:{bot_id}")]]
            msg = f"✅ <b>{bot['name']}</b> restart হয়েছে!\n📦 {result}"
        else:
            kb = [[InlineKeyboardButton("📋 লগ দেখুন", callback_data=f"logs:{bot_id}")]]
            msg = f"❌ restart হয়নি: {result[:200]}"
        await query.edit_message_text(msg, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(kb))

    elif data.startswith("logs:"):
        bot_id = data.split(":")[1]
        bot = get_bot(bot_id)
        logs = get_logs(bot_id, 30)
        text = f"📋 <b>{bot['name']} - Logs:</b>\n<pre>{logs[-2000:]}</pre>"
        kb = [
            [InlineKeyboardButton("🔄 রিফ্রেশ", callback_data=f"logs:{bot_id}")],
            [InlineKeyboardButton("🔙 বট মেনু", callback_data=f"botmenu:{bot_id}")]
        ]
        await query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(kb))

    elif data.startswith("confirmdelete:"):
        bot_id = data.split(":")[1]
        bot = get_bot(bot_id)
        kb = [
            [
                InlineKeyboardButton("✅ হ্যাঁ, মুছুন", callback_data=f"delete:{bot_id}"),
                InlineKeyboardButton("❌ না", callback_data=f"botmenu:{bot_id}"),
            ]
        ]
        await query.edit_message_text(
            f"⚠️ <b>{bot['name']}</b> মুছে দেবেন?\nসব ফাইলও মুছে যাবে!",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(kb)
        )

    elif data.startswith("delete:"):
        bot_id = data.split(":")[1]
        bot = get_bot(bot_id)
        delete_bot_files(bot_id)
        delete_bot(bot_id)
        await query.edit_message_text(f"🗑 <b>{bot['name']}</b> মুছে গেছে।", parse_mode='HTML')


# ── Admin Commands ────────────────────────────────────────

async def cmd_allusers(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    users = get_all_users()
    text = "👥 <b>সব ইউজার:</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
    for u in users[:20]:
        banned = "⛔" if u['banned'] else "✅"
        text += f"{banned} <b>{u['full_name']}</b> | <code>{u['user_id']}</code>\n"
    await update.message.reply_text(text, parse_mode='HTML')

async def cmd_allbots(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    bots = get_all_bots()
    text = "🤖 <b>সব বট:</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
    for b in bots[:20]:
        running = is_running(b['bot_id'])
        emoji = "✅" if running else "❌"
        text += f"{emoji} <b>{b['name']}</b> | <code>{b['bot_id']}</code>\n"
    await update.message.reply_text(text or "কোনো বট নেই।", parse_mode='HTML')

async def cmd_ban(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    args = ctx.args
    if not args: return
    uid = int(args[0])
    ban_user(uid)
    await update.message.reply_text(f"⛔ {uid} ব্যান হয়েছে।")

async def cmd_unban(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    args = ctx.args
    if not args: return
    uid = int(args[0])
    unban_user(uid)
    await update.message.reply_text(f"✅ {uid} আনব্যান হয়েছে।")

async def cmd_killbot(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    args = ctx.args
    if not args: return
    bot_id = args[0].upper()
    bot = get_bot(bot_id)
    if not bot: return
    stop_bot(bot_id)
    await update.message.reply_text(f"⏹ {bot['name']} বন্ধ হয়েছে।")

async def cmd_broadcast(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not ctx.args: return
    msg = ' '.join(ctx.args)
    users = get_all_users()
    sent = 0
    for u in users:
        try:
            await ctx.bot.send_message(u['user_id'], f"📢 <b>TachZone:</b>\n{msg}", parse_mode='HTML')
            sent += 1
        except: pass
    await update.message.reply_text(f"✅ {sent}জনকে পাঠানো হয়েছে।")


# ── Main ──────────────────────────────────────────────────

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    # Conversation Handler (শুধু /upload দিয়ে শুরু)
    conv = ConversationHandler(
        entry_points=[CommandHandler("upload", cmd_upload)],
        states={
            WAITING_FILE: [
                MessageHandler(filters.Document.ALL, receive_file),
                CommandHandler("cancel", cancel_upload)
            ],
            WAITING_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_bot_name),
                CommandHandler("cancel", cancel_upload)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_upload)],
        per_user=True,
    )

    # Command Handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("bot", cmd_bot))
    app.add_handler(CommandHandler("allusers", cmd_allusers))
    app.add_handler(CommandHandler("allbots", cmd_allbots))
    app.add_handler(CommandHandler("ban", cmd_ban))
    app.add_handler(CommandHandler("unban", cmd_unban))
    app.add_handler(CommandHandler("killbot", cmd_killbot))
    app.add_handler(CommandHandler("broadcast", cmd_broadcast))

    # Conversation Handler
    app.add_handler(conv)
    
    # Message Handler (সাধারণ টেক্সট মেসেজ)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Callback Handler (ইনলাইন বাটন)
    app.add_handler(CallbackQueryHandler(bot_menu_callback))

    logger.info("🚀 TachZone Hosting Bot চালু হয়েছে!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()