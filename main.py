# main.py — TachZone Hosting Bot 🚀

import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

WAITING_NAME = 1
WAITING_RENAME = 2

os.makedirs(BASE_DIR, exist_ok=True)


# ── Helpers ───────────────────────────────────────────────

def status_emoji(bot_id):
    return "✅" if is_running(bot_id) else "❌"

def check_banned(user_id):
    return is_banned(user_id)

def is_admin(user_id):
    return user_id == ADMIN_ID


# ── Main Menu Callback (সবার জন্য) ─────────────────────────

async def main_menu_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    user = query.from_user
    register_user(user.id, user.username or "", user.full_name)
    
    if check_banned(user.id):
        await query.edit_message_text("⛔ আপনি ব্যান হয়েছেন।")
        return

    if data == "menu:upload":
        count = count_user_bots(user.id)
        if count >= MAX_BOTS:
            kb = [[InlineKeyboardButton("🔙 মেইন মেনু", callback_data="menu:back")]]
            await query.edit_message_text(
                f"⚠️ সর্বোচ্চ {MAX_BOTS}টা বট রাখা যাবে।\n"
                f"নতুন আপলোড করতে আগে বট ডিলিট করুন।",
                reply_markup=InlineKeyboardMarkup(kb)
            )
            return
        ctx.user_data['uploading'] = True
        kb = [[InlineKeyboardButton("🔙 মেইন মেনু", callback_data="menu:back")]]
        await query.edit_message_text(
            "📁 এখন আপনার বটের <b>.zip</b>, <b>.py</b> বা <b>.js</b> ফাইল পাঠান।",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(kb)
        )

    elif data == "menu:mybots":
        bots = get_user_bots(user.id)
        if not bots:
            kb = [
                [InlineKeyboardButton("📤 বট আপলোড", callback_data="menu:upload")],
                [InlineKeyboardButton("🔙 মেইন মেনু", callback_data="menu:back")]
            ]
            await query.edit_message_text(
                "🤖 আপনার কোনো বট নেই।",
                reply_markup=InlineKeyboardMarkup(kb)
            )
            return

        text = "🤖 <b>আপনার বটগুলো:</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        buttons = []
        for b in bots:
            running = is_running(b['bot_id'])
            emoji = "✅" if running else "❌"
            status = "চলছে" if running else "বন্ধ"
            text += f"{emoji} <b>{b['name']}</b> | <code>{b['bot_id']}</code> | {status}\n"
            buttons.append([
                InlineKeyboardButton(f"⚙️ {b['name']}", callback_data=f"botmenu:{b['bot_id']}")
            ])
        buttons.append([InlineKeyboardButton("🔙 মেইন মেনু", callback_data="menu:back")])
        
        await query.edit_message_text(
            text, parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data == "menu:stats":
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
            f"👥 মোট ইউজার: {len(users)}\n"
            f"🤖 মোট বট: {len(bots)}\n"
            f"✅ চলমান বট: {running}\n"
            f"❌ বন্ধ বট: {len(bots) - running}"
        )
        kb = [
            [InlineKeyboardButton("🔄 রিফ্রেশ", callback_data="menu:stats")],
            [InlineKeyboardButton("🔙 মেইন মেনু", callback_data="menu:back")]
        ]
        await query.edit_message_text(
            text, parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(kb)
        )

    elif data == "menu:help":
        text = (
            "📖 <b>সাহায্য - TachZone Hosting</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>বট আপলোড করতে:</b>\n"
            "১. Upload বাটনে ক্লিক করুন\n"
            "২. .zip, .py বা .js ফাইল পাঠান\n"
            "৩. বটের নাম দিন\n"
            "৪. অটো চালু হবে ✅\n\n"
            "<b>সাপোর্টেড ফাইল:</b>\n"
            "• 🐍 Python (.py)\n"
            "• 🟢 Node.js (.js)\n"
            "• 📦 ZIP (ভিতরে যেকোনোটি)\n\n"
            "<b>বট কন্ট্রোল:</b>\n"
            "• /stop TZ-0001 — বন্ধ করুন\n"
            "• /startbot TZ-0001 — চালু করুন\n"
            "• /restart TZ-0001 — restart\n"
            "• /logs TZ-0001 — log দেখুন\n"
            "• /delete TZ-0001 — মুছে দিন"
        )
        kb = [[InlineKeyboardButton("🔙 মেইন মেনু", callback_data="menu:back")]]
        await query.edit_message_text(
            text, parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(kb)
        )

    elif data == "menu:back":
        text = (
            f"👋 স্বাগতম, <b>{user.full_name}</b>!\n\n"
            f"🚀 <b>TachZone Hosting Bot</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"আপনার Telegram Bot ফাইল আপলোড করুন,\n"
            f"আমরা ২৪/৭ চালু রাখব!\n\n"
            f"📌 <b>মেনু থেকে অপশন সিলেক্ট করুন:</b>"
        )
        kb = [
            [InlineKeyboardButton("📤 বট আপলোড", callback_data="menu:upload")],
            [InlineKeyboardButton("🤖 আমার বট", callback_data="menu:mybots")],
            [InlineKeyboardButton("📊 স্ট্যাটাস", callback_data="menu:stats"), 
             InlineKeyboardButton("❓ হেল্প", callback_data="menu:help")],
        ]
        # Admin button for admin users
        if is_admin(user.id):
            kb.append([InlineKeyboardButton("👑 অ্যাডমিন প্যানেল", callback_data="admin:panel")])
        
        await query.edit_message_text(
            text, parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(kb)
        )


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
        f"📌 <b>মেনু থেকে অপশন সিলেক্ট করুন:</b>"
    )
    
    kb = [
        [InlineKeyboardButton("📤 বট আপলোড", callback_data="menu:upload")],
        [InlineKeyboardButton("🤖 আমার বট", callback_data="menu:mybots")],
        [InlineKeyboardButton("📊 স্ট্যাটাস", callback_data="menu:stats"), 
         InlineKeyboardButton("❓ হেল্প", callback_data="menu:help")],
    ]
    # Admin button for admin users
    if is_admin(user.id):
        kb.append([InlineKeyboardButton("👑 অ্যাডমিন প্যানেল", callback_data="admin:panel")])
    
    await update.message.reply_text(
        text, parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(kb)
    )


# ── /help ─────────────────────────────────────────────────

async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 <b>সাহায্য - TachZone Hosting</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "<b>বট আপলোড করতে:</b>\n"
        "১. /upload দিন বা Upload বাটনে ক্লিক করুন\n"
        "২. .zip, .py বা .js ফাইল পাঠান\n"
        "৩. বটের নাম দিন\n"
        "৪. অটো চালু হবে ✅\n\n"
        "<b>সাপোর্টেড ফাইল:</b>\n"
        "• 🐍 Python (.py)\n"
        "• 🟢 Node.js (.js)\n"
        "• 📦 ZIP (ভিতরে যেকোনোটি)\n\n"
        "<b>বট কন্ট্রোল:</b>\n"
        "• /mybots — সব বট দেখুন\n"
        "• /stop TZ-0001 — বন্ধ করুন\n"
        "• /startbot TZ-0001 — চালু করুন\n"
        "• /restart TZ-0001 — restart করুন\n"
        "• /logs TZ-0001 — log দেখুন\n"
        "• /rename TZ-0001 নতুননাম — নাম বদলান\n"
        "• /delete TZ-0001 — মুছে দিন"
    )
    kb = [[InlineKeyboardButton("🏠 মেইন মেনু", callback_data="menu:back")]]
    await update.message.reply_text(
        text, parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(kb)
    )


# ── /upload ───────────────────────────────────────────────

async def cmd_upload(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if check_banned(user.id):
        return

    count = count_user_bots(user.id)
    if count >= MAX_BOTS:
        kb = [[InlineKeyboardButton("🔙 মেইন মেনু", callback_data="menu:back")]]
        await update.message.reply_text(
            f"⚠️ সর্বোচ্চ {MAX_BOTS}টা বট রাখা যাবে।\n"
            f"নতুন আপলোড করতে আগে /delete করুন।",
            reply_markup=InlineKeyboardMarkup(kb)
        )
        return

    ctx.user_data['uploading'] = True
    kb = [[InlineKeyboardButton("🔙 মেইন মেনু", callback_data="menu:back")]]
    await update.message.reply_text(
        "📁 এখন আপনার বটের <b>.zip</b>, <b>.py</b> বা <b>.js</b> ফাইল পাঠান।",
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(kb)
    )


# ── File Handler ──────────────────────────────────────────

async def file_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if check_banned(user.id):
        return

    if not ctx.user_data.get('uploading'):
        await update.message.reply_text("আগে /upload দিন।")
        return

    doc = update.message.document
    if not doc:
        return

    fname = doc.file_name or ""
    
    # Python এবং JavaScript দুটোই সাপোর্ট
    allowed_extensions = ['.zip', '.py', '.js']
    is_allowed = False
    for ext in allowed_extensions:
        if fname.endswith(ext):
            is_allowed = True
            break
    
    if not is_allowed:
        await update.message.reply_text("❌ শুধু .zip, .py বা .js ফাইল দিন।")
        return

    msg = await update.message.reply_text("⏳ ফাইল নামাচ্ছি...")

    # Download
    bot_id = next_bot_id()
    folder = os.path.join(BASE_DIR, str(user.id), "bots", bot_id)
    os.makedirs(folder, exist_ok=True)

    file = await doc.get_file()
    file_path = os.path.join(folder, fname)
    await file.download_to_drive(file_path)

    # Extract if zip
    if fname.endswith('.zip'):
        try:
            extract_zip(file_path, folder)
            os.remove(file_path)
        except Exception as e:
            await msg.edit_text(f"❌ zip extract error: {e}")
            return

    ctx.user_data['pending_bot_id'] = bot_id
    ctx.user_data['pending_folder'] = folder
    ctx.user_data['uploading'] = False

    kb = [[InlineKeyboardButton("❌ বাতিল", callback_data="menu:back")]]
    await msg.edit_text(
        f"✅ ফাইল আপলোড হয়েছে!\n\n"
        f"📝 এখন আপনার বটের <b>নাম</b> দিন:\n"
        f"(যেমন: MyShopBot, OTPBot)",
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(kb)
    )
    return WAITING_NAME


async def get_bot_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    name = update.message.text.strip()

    if not name or len(name) > 30:
        await update.message.reply_text("❌ নাম ১-৩০ অক্ষরের মধ্যে দিন।")
        return WAITING_NAME

    bot_id = ctx.user_data.get('pending_bot_id')
    folder = ctx.user_data.get('pending_folder')

    if not bot_id or not folder:
        await update.message.reply_text("❌ কিছু সমস্যা হয়েছে। আবার /upload দিন।")
        return ConversationHandler.END

    add_bot(bot_id, user.id, name, folder)

    msg = await update.message.reply_text(f"⚙️ <b>{name}</b> চালু হচ্ছে...", parse_mode='HTML')

    success, result = start_bot(bot_id)

    if success:
        kb = [
            [InlineKeyboardButton("⚙️ বট মেনু", callback_data=f"botmenu:{bot_id}")],
            [InlineKeyboardButton("🔙 মেইন মেনু", callback_data="menu:back")]
        ]
        await msg.edit_text(
            f"🎉 <b>{name}</b> চালু হয়েছে!\n\n"
            f"🆔 Bot ID: <code>{bot_id}</code>\n"
            f"✅ Status: চলছে\n"
            f"📦 {result}",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(kb)
        )
    else:
        update_bot_status(bot_id, 'stopped')
        kb = [
            [InlineKeyboardButton("📋 লগ দেখুন", callback_data=f"logs:{bot_id}")],
            [InlineKeyboardButton("🔙 মেইন মেনু", callback_data="menu:back")]
        ]
        await msg.edit_text(
            f"⚠️ <b>{name}</b> চালু হয়নি!\n\n"
            f"🆔 Bot ID: <code>{bot_id}</code>\n"
            f"❌ Error: {result}\n\n"
            f"ফাইল ঠিক করে আবার চেষ্টা করুন।",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(kb)
        )

    ctx.user_data.clear()
    return ConversationHandler.END


# ── /mybots ───────────────────────────────────────────────

async def cmd_mybots(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if check_banned(user.id):
        return

    bots = get_user_bots(user.id)
    if not bots:
        kb = [[InlineKeyboardButton("🏠 মেইন মেনু", callback_data="menu:back")]]
        await update.message.reply_text(
            "🤖 আপনার কোনো বট নেই।\n/upload দিয়ে আপলোড করুন।",
            reply_markup=InlineKeyboardMarkup(kb)
        )
        return

    text = "🤖 <b>আপনার বটগুলো:</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
    buttons = []

    for b in bots:
        running = is_running(b['bot_id'])
        emoji = "✅" if running else "❌"
        status = "চলছে" if running else "বন্ধ"
        text += f"{emoji} <b>{b['name']}</b> | <code>{b['bot_id']}</code> | {status}\n"

        buttons.append([
            InlineKeyboardButton(f"⚙️ {b['name']}", callback_data=f"botmenu:{b['bot_id']}")
        ])
    
    buttons.append([InlineKeyboardButton("🏠 মেইন মেনু", callback_data="menu:back")])

    await update.message.reply_text(
        text, parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# ── Bot Menu (Inline Keyboard) ────────────────────────────

async def bot_menu_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

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
                InlineKeyboardButton("✏️ Rename", callback_data=f"rename:{bot_id}"),
                InlineKeyboardButton("🗑 Delete", callback_data=f"confirmdelete:{bot_id}"),
            ],
            [InlineKeyboardButton("🔙 আমার বট লিস্ট", callback_data="menu:mybots")],
            [InlineKeyboardButton("🏠 মেইন মেনু", callback_data="menu:back")]
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
            kb = [
                [InlineKeyboardButton("📋 লগ দেখুন", callback_data=f"logs:{bot_id}")],
                [InlineKeyboardButton("🔙 বট মেনু", callback_data=f"botmenu:{bot_id}")]
            ]
            msg = f"❌ চালু হয়নি: {result}"
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
            kb = [
                [InlineKeyboardButton("📋 লগ দেখুন", callback_data=f"logs:{bot_id}")],
                [InlineKeyboardButton("🔙 বট মেনু", callback_data=f"botmenu:{bot_id}")]
            ]
            msg = f"❌ restart হয়নি: {result}"
        await query.edit_message_text(msg, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(kb))

    elif data.startswith("logs:"):
        bot_id = data.split(":")[1]
        bot = get_bot(bot_id)
        logs = get_logs(bot_id, 30)
        text = f"📋 <b>{bot['name']} - Logs:</b>\n<pre>{logs[-3000:]}</pre>"
        kb = [
            [InlineKeyboardButton("🔄 রিফ্রেশ", callback_data=f"logs:{bot_id}")],
            [InlineKeyboardButton("🔙 বট মেনু", callback_data=f"botmenu:{bot_id}")]
        ]
        await query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(kb))

    elif data.startswith("rename:"):
        bot_id = data.split(":")[1]
        ctx.user_data['renaming_bot'] = bot_id
        await query.edit_message_text(
            "✏️ নতুন নাম লিখুন:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ বাতিল", callback_data=f"botmenu:{bot_id}")
            ]])
        )
        return WAITING_RENAME

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
        kb = [[InlineKeyboardButton("🏠 মেইন মেনু", callback_data="menu:back")]]
        await query.edit_message_text(
            f"🗑 <b>{bot['name']}</b> মুছে গেছে।", 
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(kb)
        )


async def get_rename(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    bot_id = ctx.user_data.get('renaming_bot')
    new_name = update.message.text.strip()

    if not bot_id:
        return ConversationHandler.END

    rename_bot(bot_id, new_name)
    kb = [[InlineKeyboardButton("🔙 বট মেনু", callback_data=f"botmenu:{bot_id}")]]
    await update.message.reply_text(
        f"✅ নাম পরিবর্তন হয়েছে: <b>{new_name}</b>", 
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(kb)
    )
    ctx.user_data.clear()
    return ConversationHandler.END


# ── /stats ────────────────────────────────────────────────

async def cmd_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
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
        f"👥 মোট ইউজার: {len(users)}\n"
        f"🤖 মোট বট: {len(bots)}\n"
        f"✅ চলমান বট: {running}\n"
        f"❌ বন্ধ বট: {len(bots) - running}"
    )
    kb = [
        [InlineKeyboardButton("🔄 রিফ্রেশ", callback_data="menu:stats")],
        [InlineKeyboardButton("🏠 মেইন মেনু", callback_data="menu:back")]
    ]
    await update.message.reply_text(
        text, parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(kb)
    )


# ── কমান্ড দিয়ে বট কন্ট্রোল ─────────────────────────────

async def cmd_stop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = ctx.args
    if not args:
        await update.message.reply_text("ব্যবহার: /stop TZ-0001")
        return
    bot_id = args[0].upper()
    bot = get_bot(bot_id)
    if not bot or bot['user_id'] != user.id:
        await update.message.reply_text("❌ বট পাওয়া যায়নি।")
        return
    stop_bot(bot_id)
    await update.message.reply_text(f"⏹ <b>{bot['name']}</b> বন্ধ হয়েছে।", parse_mode='HTML')

async def cmd_startbot(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = ctx.args
    if not args:
        await update.message.reply_text("ব্যবহার: /startbot TZ-0001")
        return
    bot_id = args[0].upper()
    bot = get_bot(bot_id)
    if not bot or bot['user_id'] != user.id:
        await update.message.reply_text("❌ বট পাওয়া যায়নি।")
        return
    success, result = start_bot(bot_id)
    msg = f"✅ <b>{bot['name']}</b> চালু হয়েছে!" if success else f"❌ চালু হয়নি: {result}"
    await update.message.reply_text(msg, parse_mode='HTML')

async def cmd_restart(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = ctx.args
    if not args:
        await update.message.reply_text("ব্যবহার: /restart TZ-0001")
        return
    bot_id = args[0].upper()
    bot = get_bot(bot_id)
    if not bot or bot['user_id'] != user.id:
        await update.message.reply_text("❌ বট পাওয়া যায়নি।")
        return
    success, result = restart_bot(bot_id)
    msg = f"✅ <b>{bot['name']}</b> restart হয়েছে!" if success else f"❌ restart হয়নি: {result}"
    await update.message.reply_text(msg, parse_mode='HTML')

async def cmd_logs(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = ctx.args
    if not args:
        await update.message.reply_text("ব্যবহার: /logs TZ-0001")
        return
    bot_id = args[0].upper()
    bot = get_bot(bot_id)
    if not bot or bot['user_id'] != user.id:
        await update.message.reply_text("❌ বট পাওয়া যায়নি।")
        return
    logs = get_logs(bot_id, 30)
    await update.message.reply_text(
        f"📋 <b>{bot['name']} - Logs:</b>\n<pre>{logs[-3000:]}</pre>",
        parse_mode='HTML'
    )

async def cmd_delete(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = ctx.args
    if not args:
        await update.message.reply_text("ব্যবহার: /delete TZ-0001")
        return
    bot_id = args[0].upper()
    bot = get_bot(bot_id)
    if not bot or bot['user_id'] != user.id:
        await update.message.reply_text("❌ বট পাওয়া যায়নি।")
        return
    delete_bot_files(bot_id)
    delete_bot(bot_id)
    await update.message.reply_text(f"🗑 <b>{bot['name']}</b> মুছে গেছে।", parse_mode='HTML')

async def cmd_rename(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = ctx.args
    if len(args) < 2:
        await update.message.reply_text("ব্যবহার: /rename TZ-0001 নতুননাম")
        return
    bot_id = args[0].upper()
    new_name = args[1]
    bot = get_bot(bot_id)
    if not bot or bot['user_id'] != user.id:
        await update.message.reply_text("❌ বট পাওয়া যায়নি।")
        return
    rename_bot(bot_id, new_name)
    await update.message.reply_text(f"✅ নাম পরিবর্তন হয়েছে: <b>{new_name}</b>", parse_mode='HTML')


# ── Admin Commands ────────────────────────────────────────

async def cmd_adminpanel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
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
        f"🖥 CPU: {s['cpu']}% | RAM: {s['ram_used']}GB/{s['ram_total']}GB\n"
        f"💿 Disk: {s['disk_used']}GB/{s['disk_total']}GB"
    )
    kb = [
        [
            InlineKeyboardButton("👥 ইউজার লিস্ট", callback_data="admin:users"),
            InlineKeyboardButton("🤖 বট লিস্ট", callback_data="admin:bots"),
        ],
        [
            InlineKeyboardButton("📊 সার্ভার স্ট্যাটস", callback_data="admin:stats"),
            InlineKeyboardButton("📢 ব্রডকাস্ট", callback_data="admin:broadcast_prompt"),
        ],
        [InlineKeyboardButton("🔙 মেইন মেনু", callback_data="menu:back")]
    ]
    await update.message.reply_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(kb))


async def admin_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        await query.answer("⛔ আপনি অ্যাডমিন নন!")
        return
    await query.answer()
    data = query.data

    if data == "admin:panel":
        s = server_stats()
        users = get_all_users()
        bots = get_all_bots()
        running = sum(1 for b in bots if is_running(b['bot_id']))

        text = (
            f"👑 <b>Admin Panel — TachZone Hosting</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👥 মোট ইউজার: {len(users)}\n"
            f"🤖 চলমান বট: {running} / {len(bots)}\n"
            f"🖥 CPU: {s['cpu']}% | RAM: {s['ram_used']}GB/{s['ram_total']}GB\n"
            f"💿 Disk: {s['disk_used']}GB/{s['disk_total']}GB"
        )
        kb = [
            [
                InlineKeyboardButton("👥 ইউজার লিস্ট", callback_data="admin:users"),
                InlineKeyboardButton("🤖 বট লিস্ট", callback_data="admin:bots"),
            ],
            [
                InlineKeyboardButton("📊 সার্ভার স্ট্যাটস", callback_data="admin:stats"),
                InlineKeyboardButton("📢 ব্রডকাস্ট", callback_data="admin:broadcast_prompt"),
            ],
            [InlineKeyboardButton("🔙 মেইন মেনু", callback_data="menu:back")]
        ]
        await query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(kb))

    elif data == "admin:users":
        users = get_all_users()
        text = "👥 <b>সব ইউজার:</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        buttons = []
        for u in users[:15]:
            bots = get_user_bots(u['user_id'])
            banned = "⛔" if u['banned'] else "✅"
            name = u['full_name'] or "Unknown"
            text += f"{banned} <b>{name}</b> | ID: <code>{u['user_id']}</code> | 🤖 {len(bots)}টা\n"
            
            # ব্যান/আনব্যান বাটন
            if u['banned']:
                buttons.append([InlineKeyboardButton(f"✅ আনব্যান: {name[:20]}", callback_data=f"admin:unban:{u['user_id']}")])
            else:
                buttons.append([InlineKeyboardButton(f"⛔ ব্যান: {name[:20]}", callback_data=f"admin:ban:{u['user_id']}")])
        
        buttons.append([InlineKeyboardButton("🔙 অ্যাডমিন প্যানেল", callback_data="admin:panel")])
        await query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("admin:ban:"):
        uid = int(data.split(":")[2])
        ban_user(uid)
        await query.answer(f"✅ {uid} ব্যান হয়েছে!")
        # রিফ্রেশ ইউজার লিস্ট
        users = get_all_users()
        text = "👥 <b>সব ইউজার:</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        buttons = []
        for u in users[:15]:
            bots = get_user_bots(u['user_id'])
            banned = "⛔" if u['banned'] else "✅"
            name = u['full_name'] or "Unknown"
            text += f"{banned} <b>{name}</b> | ID: <code>{u['user_id']}</code> | 🤖 {len(bots)}টা\n"
            if u['banned']:
                buttons.append([InlineKeyboardButton(f"✅ আনব্যান: {name[:20]}", callback_data=f"admin:unban:{u['user_id']}")])
            else:
                buttons.append([InlineKeyboardButton(f"⛔ ব্যান: {name[:20]}", callback_data=f"admin:ban:{u['user_id']}")])
        buttons.append([InlineKeyboardButton("🔙 অ্যাডমিন প্যানেল", callback_data="admin:panel")])
        await query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("admin:unban:"):
        uid = int(data.split(":")[2])
        unban_user(uid)
        await query.answer(f"✅ {uid} আনব্যান হয়েছে!")
        # রিফ্রেশ ইউজার লিস্ট
        users = get_all_users()
        text = "👥 <b>সব ইউজার:</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        buttons = []
        for u in users[:15]:
            bots = get_user_bots(u['user_id'])
            banned = "⛔" if u['banned'] else "✅"
            name = u['full_name'] or "Unknown"
            text += f"{banned} <b>{name}</b> | ID: <code>{u['user_id']}</code> | 🤖 {len(bots)}টা\n"
            if u['banned']:
                buttons.append([InlineKeyboardButton(f"✅ আনব্যান: {name[:20]}", callback_data=f"admin:unban:{u['user_id']}")])
            else:
                buttons.append([InlineKeyboardButton(f"⛔ ব্যান: {name[:20]}", callback_data=f"admin:ban:{u['user_id']}")])
        buttons.append([InlineKeyboardButton("🔙 অ্যাডমিন প্যানেল", callback_data="admin:panel")])
        await query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(buttons))

    elif data == "admin:bots":
        bots = get_all_bots()
        text = "🤖 <b>সব বট:</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        buttons = []
        for b in bots[:15]:
            running = is_running(b['bot_id'])
            emoji = "✅" if running else "❌"
            user_info = get_user(b['user_id'])
            user_name = user_info['full_name'] if user_info else "Unknown"
            text += f"{emoji} <b>{b['name']}</b> | <code>{b['bot_id']}</code> | {user_name}\n"
            buttons.append([
                InlineKeyboardButton(f"⏹ কিল: {b['name'][:20]}", callback_data=f"admin:killbot:{b['bot_id']}")
            ])
        buttons.append([InlineKeyboardButton("🔙 অ্যাডমিন প্যানেল", callback_data="admin:panel")])
        await query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("admin:killbot:"):
        bot_id = data.split(":")[2]
        bot = get_bot(bot_id)
        if bot:
            stop_bot(bot_id)
            await query.answer(f"⏹ {bot['name']} বন্ধ হয়েছে!")
        # রিফ্রেশ বট লিস্ট
        bots = get_all_bots()
        text = "🤖 <b>সব বট:</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        buttons = []
        for b in bots[:15]:
            running = is_running(b['bot_id'])
            emoji = "✅" if running else "❌"
            user_info = get_user(b['user_id'])
            user_name = user_info['full_name'] if user_info else "Unknown"
            text += f"{emoji} <b>{b['name']}</b> | <code>{b['bot_id']}</code> | {user_name}\n"
            buttons.append([
                InlineKeyboardButton(f"⏹ কিল: {b['name'][:20]}", callback_data=f"admin:killbot:{b['bot_id']}")
            ])
        buttons.append([InlineKeyboardButton("🔙 অ্যাডমিন প্যানেল", callback_data="admin:panel")])
        await query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(buttons))

    elif data == "admin:stats":
        s = server_stats()
        bots = get_all_bots()
        running = sum(1 for b in bots if is_running(b['bot_id']))
        users = get_all_users()
        text = (
            f"📊 <b>সার্ভার স্ট্যাটস:</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🖥 CPU: {s['cpu']}%\n"
            f"💾 RAM: {s['ram_used']}GB / {s['ram_total']}GB\n"
            f"💿 Disk: {s['disk_used']}GB / {s['disk_total']}GB\n\n"
            f"👥 মোট ইউজার: {len(users)}\n"
            f"🤖 মোট বট: {len(bots)}\n"
            f"✅ চলমান: {running}\n"
            f"❌ বন্ধ: {len(bots) - running}"
        )
        kb = [
            [InlineKeyboardButton("🔄 রিফ্রেশ", callback_data="admin:stats")],
            [InlineKeyboardButton("🔙 অ্যাডমিন প্যানেল", callback_data="admin:panel")]
        ]
        await query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(kb))

    elif data == "admin:broadcast_prompt":
        ctx.user_data['awaiting_broadcast'] = True
        await query.edit_message_text(
            "📢 <b>ব্রডকাস্ট মেসেজ লিখুন:</b>\n\n"
            "সব ইউজারকে এই মেসেজটি পাঠানো হবে।",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ বাতিল", callback_data="admin:panel")
            ]])
        )
        return


async def admin_broadcast_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """অ্যাডমিনের ব্রডকাস্ট মেসেজ হ্যান্ডেল"""
    user = update.effective_user
    if not is_admin(user.id):
        return
    
    if not ctx.user_data.get('awaiting_broadcast'):
        return
    
    msg_text = update.message.text
    ctx.user_data['awaiting_broadcast'] = False
    
    users = get_all_users()
    sent = 0
    failed = 0
    
    status_msg = await update.message.reply_text(f"📢 মেসেজ পাঠানো হচ্ছে... 0/{len(users)}")
    
    for i, u in enumerate(users):
        try:
            await ctx.bot.send_message(
                u['user_id'], 
                f"📢 <b>TachZone Announcement:</b>\n\n{msg_text}", 
                parse_mode='HTML'
            )
            sent += 1
        except Exception:
            failed += 1
        
        if (i + 1) % 10 == 0:
            await status_msg.edit_text(f"📢 মেসেজ পাঠানো হচ্ছে... {i+1}/{len(users)}")
    
    kb = [[InlineKeyboardButton("🔙 অ্যাডমিন প্যানেল", callback_data="admin:panel")]]
    await status_msg.edit_text(
        f"✅ ব্রডকাস্ট সম্পন্ন!\n\n"
        f"📤 পাঠানো হয়েছে: {sent} জন\n"
        f"❌ ব্যর্থ: {failed} জন",
        reply_markup=InlineKeyboardMarkup(kb)
    )


async def cmd_ban(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    args = ctx.args
    if not args:
        await update.message.reply_text("ব্যবহার: /ban USER_ID")
        return
    uid = int(args[0])
    ban_user(uid)
    await update.message.reply_text(f"⛔ {uid} ব্যান হয়েছে।")

async def cmd_unban(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    args = ctx.args
    if not args:
        await update.message.reply_text("ব্যবহার: /unban USER_ID")
        return
    uid = int(args[0])
    unban_user(uid)
    await update.message.reply_text(f"✅ {uid} আনব্যান হয়েছে।")

async def cmd_broadcast(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not ctx.args:
        await update.message.reply_text("ব্যবহার: /broadcast মেসেজ")
        return
    msg = ' '.join(ctx.args)
    users = get_all_users()
    sent = 0
    for u in users:
        try:
            await ctx.bot.send_message(u['user_id'], f"📢 <b>TachZone:</b>\n{msg}", parse_mode='HTML')
            sent += 1
        except Exception:
            pass
    await update.message.reply_text(f"✅ {sent}জনকে পাঠানো হয়েছে।")

async def cmd_killbot(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    args = ctx.args
    if not args:
        await update.message.reply_text("ব্যবহার: /killbot BOT_ID")
        return
    bot_id = args[0].upper()
    bot = get_bot(bot_id)
    if not bot:
        await update.message.reply_text("❌ বট পাওয়া যায়নি।")
        return
    stop_bot(bot_id)
    await update.message.reply_text(f"⏹ <b>{bot['name']}</b> ({bot_id}) বন্ধ হয়েছে।", parse_mode='HTML')

async def cmd_allbots(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    bots = get_all_bots()
    text = "🤖 <b>সব বট:</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
    for b in bots:
        running = is_running(b['bot_id'])
        emoji = "✅" if running else "❌"
        text += f"{emoji} <b>{b['name']}</b> | <code>{b['bot_id']}</code>\n"
    await update.message.reply_text(text or "কোনো বট নেই।", parse_mode='HTML')

async def cmd_allusers(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    users = get_all_users()
    text = "👥 <b>সব ইউজার:</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
    for u in users:
        banned = "⛔" if u['banned'] else "✅"
        text += f"{banned} <b>{u['full_name']}</b> | <code>{u['user_id']}</code>\n"
    await update.message.reply_text(text or "কোনো ইউজার নেই।", parse_mode='HTML')


# ── Main ──────────────────────────────────────────────────

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    # Conversation handler
    conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Document.ALL, file_handler),
        ],
        states={
            WAITING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_bot_name)],
            WAITING_RENAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_rename)],
        },
        fallbacks=[CommandHandler("start", cmd_start)],
        per_user=True,
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("upload", cmd_upload))
    app.add_handler(CommandHandler("mybots", cmd_mybots))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("stop", cmd_stop))
    app.add_handler(CommandHandler("startbot", cmd_startbot))
    app.add_handler(CommandHandler("restart", cmd_restart))
    app.add_handler(CommandHandler("logs", cmd_logs))
    app.add_handler(CommandHandler("delete", cmd_delete))
    app.add_handler(CommandHandler("rename", cmd_rename))

    # Admin
    app.add_handler(CommandHandler("adminpanel", cmd_adminpanel))
    app.add_handler(CommandHandler("ban", cmd_ban))
    app.add_handler(CommandHandler("unban", cmd_unban))
    app.add_handler(CommandHandler("broadcast", cmd_broadcast))
    app.add_handler(CommandHandler("killbot", cmd_killbot))
    app.add_handler(CommandHandler("allbots", cmd_allbots))
    app.add_handler(CommandHandler("allusers", cmd_allusers))

    # Admin broadcast handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_broadcast_handler))

    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(main_menu_callback, pattern="^menu:"))
    app.add_handler(CallbackQueryHandler(admin_callback, pattern="^admin:"))
    app.add_handler(CallbackQueryHandler(bot_menu_callback))

    logger.info("🚀 TachZone Hosting Bot চালু হয়েছে! (Python + Node.js Support)")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()