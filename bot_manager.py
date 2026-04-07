# bot_manager.py — TachZone Hosting Bot

import os
import subprocess
import signal
import shutil
import zipfile
import psutil
from database import get_bot, update_bot_status

def extract_zip(zip_path, dest_folder):
    """zip extract করে, main.py খোঁজে"""
    os.makedirs(dest_folder, exist_ok=True)
    with zipfile.ZipFile(zip_path, 'r') as z:
        z.extractall(dest_folder)

    # যদি সব ফাইল একটা subfolder এ থাকে, সেটা উপরে আনো
    items = os.listdir(dest_folder)
    if len(items) == 1 and os.path.isdir(os.path.join(dest_folder, items[0])):
        sub = os.path.join(dest_folder, items[0])
        for f in os.listdir(sub):
            shutil.move(os.path.join(sub, f), dest_folder)
        os.rmdir(sub)

def find_main(folder):
    """main.py বা যেকোনো .py ফাইল খোঁজে"""
    for name in ['main.py', 'bot.py', 'app.py', 'run.py', 'start.py']:
        if os.path.exists(os.path.join(folder, name)):
            return name
    # যেকোনো .py
    for f in os.listdir(folder):
        if f.endswith('.py'):
            return f
    return None

def install_requirements(folder):
    """requirements.txt থাকলে install করে"""
    req = os.path.join(folder, 'requirements.txt')
    if os.path.exists(req):
        subprocess.run(
            ['pip', 'install', '-r', req, '-q'],
            timeout=120
        )

def start_bot(bot_id):
    """বট চালু করে, PID ফেরত দেয়"""
    bot = get_bot(bot_id)
    if not bot:
        return False, "বট পাওয়া যায়নি"

    folder = bot['folder']
    main_file = find_main(folder)
    if not main_file:
        return False, "কোনো Python ফাইল পাওয়া যায়নি"

    # requirements install
    try:
        install_requirements(folder)
    except Exception:
        pass

    log_file = os.path.join(folder, 'bot.log')
    try:
        proc = subprocess.Popen(
            ['python', '-u', main_file],
            cwd=folder,
            stdout=open(log_file, 'a'),
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
        )
        update_bot_status(bot_id, 'running', proc.pid)
        return True, proc.pid
    except Exception as e:
        return False, str(e)

def stop_bot(bot_id):
    """বট বন্ধ করে"""
    bot = get_bot(bot_id)
    if not bot:
        return False, "বট পাওয়া যায়নি"

    pid = bot['pid']
    if pid:
        try:
            if os.name == 'nt':
                subprocess.call(['taskkill', '/F', '/T', '/PID', str(pid)])
            else:
                os.killpg(os.getpgid(pid), signal.SIGTERM)
        except Exception:
            pass

    update_bot_status(bot_id, 'stopped')
    return True, "বন্ধ হয়েছে"

def restart_bot(bot_id):
    """বট restart করে"""
    stop_bot(bot_id)
    return start_bot(bot_id)

def is_running(bot_id):
    """বট আসলেই চলছে কিনা চেক করে"""
    bot = get_bot(bot_id)
    if not bot or not bot['pid']:
        return False
    try:
        p = psutil.Process(bot['pid'])
        return p.is_running() and p.status() != psutil.STATUS_ZOMBIE
    except Exception:
        return False

def get_logs(bot_id, lines=50):
    """বটের শেষ N লাইন log দেয়"""
    bot = get_bot(bot_id)
    if not bot:
        return "বট পাওয়া যায়নি"

    log_file = os.path.join(bot['folder'], 'bot.log')
    if not os.path.exists(log_file):
        return "কোনো log নেই এখনো"

    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        all_lines = f.readlines()
    return ''.join(all_lines[-lines:]) or "Log খালি"

def delete_bot_files(bot_id):
    """বটের সব ফাইল মুছে দেয়"""
    bot = get_bot(bot_id)
    if not bot:
        return
    stop_bot(bot_id)
    if os.path.exists(bot['folder']):
        shutil.rmtree(bot['folder'])

def server_stats():
    """PC এর CPU/RAM/Disk অবস্থা"""
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage('.')
    return {
        'cpu': cpu,
        'ram_used': round(ram.used / 1024**3, 1),
        'ram_total': round(ram.total / 1024**3, 1),
        'disk_used': round(disk.used / 1024**3, 1),
        'disk_total': round(disk.total / 1024**3, 1),
    }
