# main.py тАФ TachZone Hosting Bot ЁЯЪА

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
    ban_user, unban_user
)
from bot_manager import (
    extract_zip, start_bot, stop_bot, restart_bot,
    is_running, get_logs, delete_bot_files, server_stats
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

WAITING_NAME = 1
WAITING_RENAME = 2

os.makedirs(BASE_DIR, exist_ok=True)


# тФАтФА Helpers тФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФА

def status_emoji(bot_id):
    return "тЬЕ" if is_running(bot_id) else "тЭМ"

def check_banned(user_id):
    return is_banned(user_id)

def is_admin(user_id):
    return user_id == ADMIN_ID


# тФАтФА /start тФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФА

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    register_user(user.id, user.username or "", user.full_name)

    if check_banned(user.id):
        await update.message.reply_text("тЫФ ржЖржкржирж┐ ржмрзНржпрж╛ржи рж╣ржпрж╝рзЗржЫрзЗржиред")
        return

    text = (
        f"ЁЯСЛ рж╕рзНржмрж╛ржЧрждржо, <b>{user.full_name}</b>!\n\n"
        f"ЁЯЪА <b>TachZone Hosting Bot</b>\n"
        f"тФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБ\n"
        f"ржЖржкржирж╛рж░ Telegram Bot ржлрж╛ржЗрж▓ ржЖржкрж▓рзЛржб ржХрж░рзБржи,\n"
        f"ржЖржорж░рж╛ рзирзк/рзн ржЪрж╛рж▓рзБ рж░рж╛ржЦржм!\n\n"
        f"ЁЯУМ <b>ржХржорж╛ржирзНржб рж╕ржорзВрж╣:</b>\n"
        f"тАв /upload тАФ ржирждрзБржи ржмржЯ ржЖржкрж▓рзЛржб\n"
        f"тАв /mybots тАФ ржЖржкржирж╛рж░ ржмржЯржЧрзБрж▓рзЛ ржжрзЗржЦрзБржи\n"
        f"тАв /stats тАФ рж╕рж╛рж░рзНржнрж╛рж░ ржЕржмрж╕рзНржерж╛\n"
        f"тАв /help тАФ рж╕рж╛рж╣рж╛ржпрзНржп"
    )
    await update.message.reply_text(text, parse_mode='HTML')


# тФАтФА /help тФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФА

async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = (
        "ЁЯУЦ <b>рж╕рж╛рж╣рж╛ржпрзНржп - TachZone Hosting</b>\n"
        "тФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБ\n\n"
        "<b>ржмржЯ ржЖржкрж▓рзЛржб ржХрж░рждрзЗ:</b>\n"
        "рзз. /upload ржжрж┐ржи\n"
        "рзи. .zip ржмрж╛ .py ржлрж╛ржЗрж▓ ржкрж╛ржарж╛ржи\n"
        "рзй. ржмржЯрзЗрж░ ржирж╛ржо ржжрж┐ржи\n"
        "рзк. ржЕржЯрзЛ ржЪрж╛рж▓рзБ рж╣ржмрзЗ тЬЕ\n\n"
        "<b>ржмржЯ ржХржирзНржЯрзНрж░рзЛрж▓:</b>\n"
        "тАв /mybots тАФ рж╕ржм ржмржЯ ржжрзЗржЦрзБржи\n"
        "тАв /stop TZ-0001 тАФ ржмржирзНржз ржХрж░рзБржи\n"
        "тАв /startbot TZ-0001 тАФ ржЪрж╛рж▓рзБ ржХрж░рзБржи\n"
        "тАв /restart TZ-0001 тАФ restart ржХрж░рзБржи\n"
        "тАв /logs TZ-0001 тАФ log ржжрзЗржЦрзБржи\n"
        "тАв /rename TZ-0001 ржирждрзБржиржирж╛ржо тАФ ржирж╛ржо ржмржжрж▓рж╛ржи\n"
        "тАв /delete TZ-0001 тАФ ржорзБржЫрзЗ ржжрж┐ржи\n"
    )
    await update.message.reply_text(text, parse_mode='HTML')


# тФАтФА /upload тФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФА

async def cmd_upload(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if check_banned(user.id):
        return

    count = count_user_bots(user.id)
    if count >= MAX_BOTS:
        await update.message.reply_text(
            f"тЪая╕П рж╕рж░рзНржмрзЛржЪрзНржЪ {MAX_BOTS}ржЯрж╛ ржмржЯ рж░рж╛ржЦрж╛ ржпрж╛ржмрзЗред\n"
            f"ржирждрзБржи ржЖржкрж▓рзЛржб ржХрж░рждрзЗ ржЖржЧрзЗ /delete ржХрж░рзБржиред"
        )
        return

    ctx.user_data['uploading'] = True
    await update.message.reply_text(
        "ЁЯУБ ржПржЦржи ржЖржкржирж╛рж░ ржмржЯрзЗрж░ <b>.zip</b> ржмрж╛ <b>.py</b> ржлрж╛ржЗрж▓ ржкрж╛ржарж╛ржиред",
        parse_mode='HTML'
    )


# тФАтФА File Handler тФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФА

async def file_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if check_banned(user.id):
        return

    if not ctx.user_data.get('uploading'):
        await update.message.reply_text("ржЖржЧрзЗ /upload ржжрж┐ржиред")
        return

    doc = update.message.document
    if not doc:
        return

    fname = doc.file_name or ""
    if not (fname.endswith('.zip') or fname.endswith('.py')):
        await update.message.reply_text("тЭМ рж╢рзБржзрзБ .zip ржмрж╛ .py ржлрж╛ржЗрж▓ ржжрж┐ржиред")
        return

    msg = await update.message.reply_text("тП│ ржлрж╛ржЗрж▓ ржирж╛ржорж╛ржЪрзНржЫрж┐...")

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
            await msg.edit_text(f"тЭМ zip extract error: {e}")
            return

    ctx.user_data['pending_bot_id'] = bot_id
    ctx.user_data['pending_folder'] = folder
    ctx.user_data['uploading'] = False

    await msg.edit_text(
        f"тЬЕ ржлрж╛ржЗрж▓ ржЖржкрж▓рзЛржб рж╣ржпрж╝рзЗржЫрзЗ!\n\n"
        f"ЁЯУЭ ржПржЦржи ржЖржкржирж╛рж░ ржмржЯрзЗрж░ <b>ржирж╛ржо</b> ржжрж┐ржи:\n"
        f"(ржпрзЗржоржи: MyShopBot, OTPBot)",
        parse_mode='HTML'
    )
    return WAITING_NAME


async def get_bot_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    name = update.message.text.strip()

    if not name or len(name) > 30:
        await update.message.reply_text("тЭМ ржирж╛ржо рзз-рзйрзж ржЕржХрзНрж╖рж░рзЗрж░ ржоржзрзНржпрзЗ ржжрж┐ржиред")
        return WAITING_NAME

    bot_id = ctx.user_data.get('pending_bot_id')
    folder = ctx.user_data.get('pending_folder')

    if not bot_id or not folder:
        await update.message.reply_text("тЭМ ржХрж┐ржЫрзБ рж╕ржорж╕рзНржпрж╛ рж╣ржпрж╝рзЗржЫрзЗред ржЖржмрж╛рж░ /upload ржжрж┐ржиред")
        return ConversationHandler.END

    add_bot(bot_id, user.id, name, folder)

    msg = await update.message.reply_text(f"тЪЩя╕П <b>{name}</b> ржЪрж╛рж▓рзБ рж╣ржЪрзНржЫрзЗ...", parse_mode='HTML')

    success, result = start_bot(bot_id)

    if success:
        await msg.edit_text(
            f"ЁЯОЙ <b>{name}</b> ржЪрж╛рж▓рзБ рж╣ржпрж╝рзЗржЫрзЗ!\n\n"
            f"ЁЯЖФ Bot ID: <code>{bot_id}</code>\n"
            f"тЬЕ Status: ржЪрж▓ржЫрзЗ\n\n"
            f"ржХржирзНржЯрзНрж░рзЛрж▓ ржХрж░рждрзЗ /mybots ржжрж┐ржиред",
            parse_mode='HTML'
        )
    else:
        update_bot_status(bot_id, 'stopped')
        await msg.edit_text(
            f"тЪая╕П <b>{name}</b> ржЪрж╛рж▓рзБ рж╣ржпрж╝ржирж┐!\n\n"
            f"ЁЯЖФ Bot ID: <code>{bot_id}</code>\n"
            f"тЭМ Error: {result}\n\n"
            f"ржлрж╛ржЗрж▓ ржарж┐ржХ ржХрж░рзЗ ржЖржмрж╛рж░ ржЪрзЗрж╖рзНржЯрж╛ ржХрж░рзБржиред\n"
            f"/logs {bot_id} ржжрж┐ржпрж╝рзЗ error ржжрзЗржЦрзБржиред",
            parse_mode='HTML'
        )

    ctx.user_data.clear()
    return ConversationHandler.END


# тФАтФА /mybots тФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФА

async def cmd_mybots(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if check_banned(user.id):
        return

    bots = get_user_bots(user.id)
    if not bots:
        await update.message.reply_text(
            "ЁЯдЦ ржЖржкржирж╛рж░ ржХрзЛржирзЛ ржмржЯ ржирзЗржЗред\n/upload ржжрж┐ржпрж╝рзЗ ржЖржкрж▓рзЛржб ржХрж░рзБржиред"
        )
        return

    text = "ЁЯдЦ <b>ржЖржкржирж╛рж░ ржмржЯржЧрзБрж▓рзЛ:</b>\nтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБ\n\n"
    buttons = []

    for b in bots:
        running = is_running(b['bot_id'])
        emoji = "тЬЕ" if running else "тЭМ"
        status = "ржЪрж▓ржЫрзЗ" if running else "ржмржирзНржз"
        text += f"{emoji} <b>{b['name']}</b> | <code>{b['bot_id']}</code> | {status}\n"

        buttons.append([
            InlineKeyboardButton(f"тЪЩя╕П {b['name']}", callback_data=f"botmenu:{b['bot_id']}")
        ])

    await update.message.reply_text(
        text, parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# тФАтФА Bot Menu (Inline Keyboard) тФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФА

async def bot_menu_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("botmenu:"):
        bot_id = data.split(":")[1]
        bot = get_bot(bot_id)
        if not bot:
            await query.edit_message_text("тЭМ ржмржЯ ржкрж╛ржУржпрж╝рж╛ ржпрж╛ржпрж╝ржирж┐ред")
            return

        running = is_running(bot_id)
        emoji = "тЬЕ" if running else "тЭМ"
        status = "ржЪрж▓ржЫрзЗ" if running else "ржмржирзНржз"

        text = (
            f"тЪЩя╕П <b>{bot['name']}</b>\n"
            f"тФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБ\n"
            f"ЁЯЖФ ID: <code>{bot_id}</code>\n"
            f"{emoji} Status: {status}\n"
            f"ЁЯУЕ рждрзИрж░рж┐: {bot['created_at'][:10]}\n"
        )

        kb = [
            [
                InlineKeyboardButton("тЦ╢я╕П ржЪрж╛рж▓рзБ", callback_data=f"start:{bot_id}"),
                InlineKeyboardButton("тП╣ ржмржирзНржз", callback_data=f"stop:{bot_id}"),
                InlineKeyboardButton("ЁЯФД Restart", callback_data=f"restart:{bot_id}"),
            ],
            [
                InlineKeyboardButton("ЁЯУЛ Logs", callback_data=f"logs:{bot_id}"),
                InlineKeyboardButton("тЬПя╕П Rename", callback_data=f"rename:{bot_id}"),
                InlineKeyboardButton("ЁЯЧС Delete", callback_data=f"confirmdelete:{bot_id}"),
            ],
            [InlineKeyboardButton("ЁЯФЩ ржкрж┐ржЫржирзЗ", callback_data="back")]
        ]
        await query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(kb))

    elif data.startswith("start:"):
        bot_id = data.split(":")[1]
        bot = get_bot(bot_id)
        success, result = start_bot(bot_id)
        msg = f"тЬЕ <b>{bot['name']}</b> ржЪрж╛рж▓рзБ рж╣ржпрж╝рзЗржЫрзЗ!" if success else f"тЭМ ржЪрж╛рж▓рзБ рж╣ржпрж╝ржирж┐: {result}"
        await query.edit_message_text(msg, parse_mode='HTML')

    elif data.startswith("stop:"):
        bot_id = data.split(":")[1]
        bot = get_bot(bot_id)
        stop_bot(bot_id)
        await query.edit_message_text(f"тП╣ <b>{bot['name']}</b> ржмржирзНржз рж╣ржпрж╝рзЗржЫрзЗред", parse_mode='HTML')

    elif data.startswith("restart:"):
        bot_id = data.split(":")[1]
        bot = get_bot(bot_id)
        await query.edit_message_text(f"ЁЯФД <b>{bot['name']}</b> restart рж╣ржЪрзНржЫрзЗ...", parse_mode='HTML')
        success, result = restart_bot(bot_id)
        msg = f"тЬЕ <b>{bot['name']}</b> restart рж╣ржпрж╝рзЗржЫрзЗ!" if success else f"тЭМ restart рж╣ржпрж╝ржирж┐: {result}"
        await query.edit_message_text(msg, parse_mode='HTML')

    elif data.startswith("logs:"):
        bot_id = data.split(":")[1]
        bot = get_bot(bot_id)
        logs = get_logs(bot_id, 30)
        text = f"ЁЯУЛ <b>{bot['name']} - Logs:</b>\n<pre>{logs[-3000:]}</pre>"
        await query.edit_message_text(text, parse_mode='HTML')

    elif data.startswith("rename:"):
        bot_id = data.split(":")[1]
        ctx.user_data['renaming_bot'] = bot_id
        await query.edit_message_text(
            "тЬПя╕П ржирждрзБржи ржирж╛ржо рж▓рж┐ржЦрзБржи:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("тЭМ ржмрж╛рждрж┐рж▓", callback_data="back")]])
        )
        return WAITING_RENAME

    elif data.startswith("confirmdelete:"):
        bot_id = data.split(":")[1]
        bot = get_bot(bot_id)
        kb = [
            [
                InlineKeyboardButton("тЬЕ рж╣рзНржпрж╛ржБ, ржорзБржЫрзБржи", callback_data=f"delete:{bot_id}"),
                InlineKeyboardButton("тЭМ ржирж╛", callback_data=f"botmenu:{bot_id}"),
            ]
        ]
        await query.edit_message_text(
            f"тЪая╕П <b>{bot['name']}</b> ржорзБржЫрзЗ ржжрзЗржмрзЗржи?\nрж╕ржм ржлрж╛ржЗрж▓ржУ ржорзБржЫрзЗ ржпрж╛ржмрзЗ!",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(kb)
        )

    elif data.startswith("delete:"):
        bot_id = data.split(":")[1]
        bot = get_bot(bot_id)
        delete_bot_files(bot_id)
        delete_bot(bot_id)
        await query.edit_message_text(f"ЁЯЧС <b>{bot['name']}</b> ржорзБржЫрзЗ ржЧрзЗржЫрзЗред", parse_mode='HTML')

    elif data == "back":
        await query.edit_message_text("ЁЯФЩ /mybots ржжрж┐ржпрж╝рзЗ ржмржЯ рж▓рж┐рж╕рзНржЯ ржжрзЗржЦрзБржиред")


async def get_rename(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    bot_id = ctx.user_data.get('renaming_bot')
    new_name = update.message.text.strip()

    if not bot_id:
        return ConversationHandler.END

    rename_bot(bot_id, new_name)
    await update.message.reply_text(f"тЬЕ ржирж╛ржо ржкрж░рж┐ржмрж░рзНрждржи рж╣ржпрж╝рзЗржЫрзЗ: <b>{new_name}</b>", parse_mode='HTML')
    ctx.user_data.clear()
    return ConversationHandler.END


# тФАтФА /stats тФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФА

async def cmd_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    s = server_stats()
    bots = get_all_bots()
    running = sum(1 for b in bots if is_running(b['bot_id']))
    users = get_all_users()

    text = (
        f"ЁЯУК <b>рж╕рж╛рж░рзНржнрж╛рж░ ржЕржмрж╕рзНржерж╛</b>\n"
        f"тФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБ\n"
        f"ЁЯЦе CPU: {s['cpu']}%\n"
        f"ЁЯТ╛ RAM: {s['ram_used']}GB / {s['ram_total']}GB\n"
        f"ЁЯТ┐ Disk: {s['disk_used']}GB / {s['disk_total']}GB\n\n"
        f"ЁЯСе ржорзЛржЯ ржЗржЙржЬрж╛рж░: {len(users)}\n"
        f"ЁЯдЦ ржорзЛржЯ ржмржЯ: {len(bots)}\n"
        f"тЬЕ ржЪрж▓ржорж╛ржи ржмржЯ: {running}\n"
        f"тЭМ ржмржирзНржз ржмржЯ: {len(bots) - running}"
    )
    await update.message.reply_text(text, parse_mode='HTML')


# тФАтФА ржХржорж╛ржирзНржб ржжрж┐ржпрж╝рзЗ ржмржЯ ржХржирзНржЯрзНрж░рзЛрж▓ тФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФА

async def cmd_stop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = ctx.args
    if not args:
        await update.message.reply_text("ржмрзНржпржмрж╣рж╛рж░: /stop TZ-0001")
        return
    bot_id = args[0].upper()
    bot = get_bot(bot_id)
    if not bot or bot['user_id'] != user.id:
        await update.message.reply_text("тЭМ ржмржЯ ржкрж╛ржУржпрж╝рж╛ ржпрж╛ржпрж╝ржирж┐ред")
        return
    stop_bot(bot_id)
    await update.message.reply_text(f"тП╣ <b>{bot['name']}</b> ржмржирзНржз рж╣ржпрж╝рзЗржЫрзЗред", parse_mode='HTML')

async def cmd_startbot(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = ctx.args
    if not args:
        await update.message.reply_text("ржмрзНржпржмрж╣рж╛рж░: /startbot TZ-0001")
        return
    bot_id = args[0].upper()
    bot = get_bot(bot_id)
    if not bot or bot['user_id'] != user.id:
        await update.message.reply_text("тЭМ ржмржЯ ржкрж╛ржУржпрж╝рж╛ ржпрж╛ржпрж╝ржирж┐ред")
        return
    success, result = start_bot(bot_id)
    msg = f"тЬЕ <b>{bot['name']}</b> ржЪрж╛рж▓рзБ рж╣ржпрж╝рзЗржЫрзЗ!" if success else f"тЭМ ржЪрж╛рж▓рзБ рж╣ржпрж╝ржирж┐: {result}"
    await update.message.reply_text(msg, parse_mode='HTML')

async def cmd_restart(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = ctx.args
    if not args:
        await update.message.reply_text("ржмрзНржпржмрж╣рж╛рж░: /restart TZ-0001")
        return
    bot_id = args[0].upper()
    bot = get_bot(bot_id)
    if not bot or bot['user_id'] != user.id:
        await update.message.reply_text("тЭМ ржмржЯ ржкрж╛ржУржпрж╝рж╛ ржпрж╛ржпрж╝ржирж┐ред")
        return
    success, result = restart_bot(bot_id)
    msg = f"тЬЕ <b>{bot['name']}</b> restart рж╣ржпрж╝рзЗржЫрзЗ!" if success else f"тЭМ restart рж╣ржпрж╝ржирж┐: {result}"
    await update.message.reply_text(msg, parse_mode='HTML')

async def cmd_logs(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = ctx.args
    if not args:
        await update.message.reply_text("ржмрзНржпржмрж╣рж╛рж░: /logs TZ-0001")
        return
    bot_id = args[0].upper()
    bot = get_bot(bot_id)
    if not bot or bot['user_id'] != user.id:
        await update.message.reply_text("тЭМ ржмржЯ ржкрж╛ржУржпрж╝рж╛ ржпрж╛ржпрж╝ржирж┐ред")
        return
    logs = get_logs(bot_id, 30)
    await update.message.reply_text(
        f"ЁЯУЛ <b>{bot['name']} - Logs:</b>\n<pre>{logs[-3000:]}</pre>",
        parse_mode='HTML'
    )

async def cmd_delete(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = ctx.args
    if not args:
        await update.message.reply_text("ржмрзНржпржмрж╣рж╛рж░: /delete TZ-0001")
        return
    bot_id = args[0].upper()
    bot = get_bot(bot_id)
    if not bot or bot['user_id'] != user.id:
        await update.message.reply_text("тЭМ ржмржЯ ржкрж╛ржУржпрж╝рж╛ ржпрж╛ржпрж╝ржирж┐ред")
        return
    delete_bot_files(bot_id)
    delete_bot(bot_id)
    await update.message.reply_text(f"ЁЯЧС <b>{bot['name']}</b> ржорзБржЫрзЗ ржЧрзЗржЫрзЗред", parse_mode='HTML')

async def cmd_rename(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = ctx.args
    if len(args) < 2:
        await update.message.reply_text("ржмрзНржпржмрж╣рж╛рж░: /rename TZ-0001 ржирждрзБржиржирж╛ржо")
        return
    bot_id = args[0].upper()
    new_name = args[1]
    bot = get_bot(bot_id)
    if not bot or bot['user_id'] != user.id:
        await update.message.reply_text("тЭМ ржмржЯ ржкрж╛ржУржпрж╝рж╛ ржпрж╛ржпрж╝ржирж┐ред")
        return
    rename_bot(bot_id, new_name)
    await update.message.reply_text(f"тЬЕ ржирж╛ржо ржкрж░рж┐ржмрж░рзНрждржи рж╣ржпрж╝рзЗржЫрзЗ: <b>{new_name}</b>", parse_mode='HTML')


# тФАтФА Admin Commands тФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФА

async def cmd_adminpanel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    s = server_stats()
    users = get_all_users()
    bots = get_all_bots()
    running = sum(1 for b in bots if is_running(b['bot_id']))

    text = (
        f"ЁЯСС <b>Admin Panel тАФ TachZone Hosting</b>\n"
        f"тФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБ\n"
        f"ЁЯСе ржорзЛржЯ ржЗржЙржЬрж╛рж░: {len(users)}\n"
        f"ЁЯдЦ ржЪрж▓ржорж╛ржи ржмржЯ: {running} / {len(bots)}\n"
        f"ЁЯЦе CPU: {s['cpu']}% | RAM: {s['ram_used']}GB/{s['ram_total']}GB\n"
        f"ЁЯТ┐ Disk: {s['disk_used']}GB/{s['disk_total']}GB"
    )
    kb = [
        [
            InlineKeyboardButton("ЁЯСе ржЗржЙржЬрж╛рж░ рж▓рж┐рж╕рзНржЯ", callback_data="admin:users"),
            InlineKeyboardButton("ЁЯдЦ ржмржЯ рж▓рж┐рж╕рзНржЯ", callback_data="admin:bots"),
        ],
        [InlineKeyboardButton("ЁЯУК рж╕рж╛рж░рзНржнрж╛рж░ рж╕рзНржЯрзНржпрж╛ржЯрж╕", callback_data="admin:stats")]
    ]
    await update.message.reply_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(kb))

async def admin_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        return
    await query.answer()
    data = query.data

    if data == "admin:users":
        users = get_all_users()
        text = "ЁЯСе <b>рж╕ржм ржЗржЙржЬрж╛рж░:</b>\nтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБ\n\n"
        for u in users[:20]:
            bots = get_user_bots(u['user_id'])
            banned = "тЫФ" if u['banned'] else "тЬЕ"
            name = u['full_name'] or "Unknown"
            text += f"{banned} <b>{name}</b> | ID: <code>{u['user_id']}</code> | ЁЯдЦ {len(bots)}ржЯрж╛\n"
        await query.edit_message_text(text, parse_mode='HTML')

    elif data == "admin:bots":
        bots = get_all_bots()
        text = "ЁЯдЦ <b>рж╕ржм ржмржЯ:</b>\nтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБ\n\n"
        for b in bots[:20]:
            running = is_running(b['bot_id'])
            emoji = "тЬЕ" if running else "тЭМ"
            text += f"{emoji} <b>{b['name']}</b> | <code>{b['bot_id']}</code> | UID: {b['user_id']}\n"
        await query.edit_message_text(text, parse_mode='HTML')

    elif data == "admin:stats":
        s = server_stats()
        text = (
            f"ЁЯУК <b>рж╕рж╛рж░рзНржнрж╛рж░ рж╕рзНржЯрзНржпрж╛ржЯрж╕:</b>\n"
            f"ЁЯЦе CPU: {s['cpu']}%\n"
            f"ЁЯТ╛ RAM: {s['ram_used']}GB / {s['ram_total']}GB\n"
            f"ЁЯТ┐ Disk: {s['disk_used']}GB / {s['disk_total']}GB"
        )
        await query.edit_message_text(text, parse_mode='HTML')

async def cmd_ban(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    args = ctx.args
    if not args: return
    uid = int(args[0])
    ban_user(uid)
    await update.message.reply_text(f"тЫФ {uid} ржмрзНржпрж╛ржи рж╣ржпрж╝рзЗржЫрзЗред")

async def cmd_unban(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    args = ctx.args
    if not args: return
    uid = int(args[0])
    unban_user(uid)
    await update.message.reply_text(f"тЬЕ {uid} ржЖржиржмрзНржпрж╛ржи рж╣ржпрж╝рзЗржЫрзЗред")

async def cmd_broadcast(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not ctx.args:
        await update.message.reply_text("ржмрзНржпржмрж╣рж╛рж░: /broadcast ржорзЗрж╕рзЗржЬ")
        return
    msg = ' '.join(ctx.args)
    users = get_all_users()
    sent = 0
    for u in users:
        try:
            await ctx.bot.send_message(u['user_id'], f"ЁЯУв <b>TachZone:</b>\n{msg}", parse_mode='HTML')
            sent += 1
        except Exception:
            pass
    await update.message.reply_text(f"тЬЕ {sent}ржЬржиржХрзЗ ржкрж╛ржарж╛ржирзЛ рж╣ржпрж╝рзЗржЫрзЗред")

async def cmd_killbot(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    args = ctx.args
    if not args: return
    bot_id = args[0].upper()
    bot = get_bot(bot_id)
    if not bot:
        await update.message.reply_text("тЭМ ржмржЯ ржкрж╛ржУржпрж╝рж╛ ржпрж╛ржпрж╝ржирж┐ред")
        return
    stop_bot(bot_id)
    await update.message.reply_text(f"тП╣ <b>{bot['name']}</b> ({bot_id}) ржмржирзНржз рж╣ржпрж╝рзЗржЫрзЗред", parse_mode='HTML')

async def cmd_allbots(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    bots = get_all_bots()
    text = "ЁЯдЦ <b>рж╕ржм ржмржЯ:</b>\nтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБ\n\n"
    for b in bots:
        running = is_running(b['bot_id'])
        emoji = "тЬЕ" if running else "тЭМ"
        text += f"{emoji} <b>{b['name']}</b> | <code>{b['bot_id']}</code>\n"
    await update.message.reply_text(text or "ржХрзЛржирзЛ ржмржЯ ржирзЗржЗред", parse_mode='HTML')

async def cmd_allusers(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    users = get_all_users()
    text = "ЁЯСе <b>рж╕ржм ржЗржЙржЬрж╛рж░:</b>\nтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБтФБ\n\n"
    for u in users:
        banned = "тЫФ" if u['banned'] else "тЬЕ"
        text += f"{banned} <b>{u['full_name']}</b> | <code>{u['user_id']}</code>\n"
    await update.message.reply_text(text or "ржХрзЛржирзЛ ржЗржЙржЬрж╛рж░ ржирзЗржЗред", parse_mode='HTML')


# тФАтФА Main тФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФА

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

    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(admin_callback, pattern="^admin:"))
    app.add_handler(CallbackQueryHandler(bot_menu_callback))

    logger.info("ЁЯЪА TachZone Hosting Bot ржЪрж╛рж▓рзБ рж╣ржпрж╝рзЗржЫрзЗ!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
