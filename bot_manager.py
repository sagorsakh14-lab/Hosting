# bot_manager.py — TachZone Hosting Bot

import os
import subprocess
import signal
import shutil
import zipfile
import psutil
from database import get_bot, update_bot_status


def extract_zip(zip_path, dest_folder):
    """zip extract করে, main.py বা index.js খোঁজে"""
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


def detect_bot_type(folder):
    """
    বটের টাইপ detect করে।
    returns: ('python', 'main.py') or ('node', 'index.js') or (None, None)
    """
    # Python এর জন্য
    for name in ['main.py', 'bot.py', 'app.py', 'run.py', 'start.py']:
        if os.path.exists(os.path.join(folder, name)):
            return 'python', name

    # JavaScript এর জন্য
    for name in ['index.js', 'main.js', 'bot.js', 'app.js', 'server.js', 'start.js']:
        if os.path.exists(os.path.join(folder, name)):
            return 'node', name

    # যেকোনো .py
    for f in os.listdir(folder):
        if f.endswith('.py'):
            return 'python', f

    # যেকোনো .js
    for f in os.listdir(folder):
        if f.endswith('.js'):
            return 'node', f

    return None, None


def find_main(folder):
    """পুরনো ফাংশন — backward compatibility এর জন্য রাখা"""
    _, main_file = detect_bot_type(folder)
    return main_file


def install_requirements(folder, bot_type):
    """
    Python: requirements.txt থাকলে pip install
    Node.js: package.json থাকলে npm install
    """
    if bot_type == 'python':
        req = os.path.join(folder, 'requirements.txt')
        if os.path.exists(req):
            # pip3 আগে, না থাকলে pip
            pip_cmd = 'pip3' if shutil.which('pip3') else 'pip'
            subprocess.run(
                [pip_cmd, 'install', '-r', req, '-q'],
                timeout=120
            )

    elif bot_type == 'node':
        pkg = os.path.join(folder, 'package.json')
        if os.path.exists(pkg):
            subprocess.run(
                ['npm', 'install', '--prefix', folder, '--quiet'],
                timeout=180,
                cwd=folder
            )


def get_node_path():
    """Node.js এর path খোঁজে"""
    for path in ['node', '/usr/bin/node', '/usr/local/bin/node']:
        try:
            result = subprocess.run([path, '--version'], capture_output=True, timeout=5)
            if result.returncode == 0:
                return path
        except Exception:
            continue
    return None


def get_python_path():
    """Python এর সঠিক path খোঁজে — python3 আগে, তারপর python"""
    for path in ['python3', 'python', '/usr/bin/python3', '/usr/local/bin/python3']:
        try:
            result = subprocess.run([path, '--version'], capture_output=True, timeout=5)
            if result.returncode == 0:
                return path
        except Exception:
            continue
    return None


def start_bot(bot_id):
    """বট চালু করে, PID ফেরত দেয়"""
    bot = get_bot(bot_id)
    if not bot:
        return False, "বট পাওয়া যায়নি"

    folder = bot['folder']

    # টাইপ detect করো
    bot_type, main_file = detect_bot_type(folder)

    if not main_file:
        return False, "কোনো Python (.py) বা JavaScript (.js) ফাইল পাওয়া যায়নি"

    # requirements/packages install
    try:
        install_requirements(folder, bot_type)
    except Exception:
        pass

    log_file = os.path.join(folder, 'bot.log')

    try:
        if bot_type == 'python':
            python_path = get_python_path()
            if not python_path:
                return False, "Python ইন্সটল নেই সার্ভারে!"
            cmd = [python_path, '-u', main_file]

        elif bot_type == 'node':
            node_path = get_node_path()
            if not node_path:
                return False, "Node.js ইন্সটল নেই। সার্ভারে Node.js ইন্সটল করুন।"
            cmd = [node_path, main_file]

        else:
            return False, "অজানা বট টাইপ"

        # log file আগে থেকে তৈরি করো
        os.makedirs(folder, exist_ok=True)
        log_f = open(log_file, 'a', encoding='utf-8')

        kwargs = dict(cwd=folder, stdout=log_f, stderr=log_f)
        if os.name == 'nt':
            kwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            kwargs['start_new_session'] = True

        proc = subprocess.Popen(cmd, **kwargs)

        # ২ সেকেন্ড অপেক্ষা করে দেখো process আছে কিনা
        import time
        time.sleep(2)
        log_f.flush()

        if proc.poll() is not None:
            # process মরে গেছে — log থেকে error দেখাও
            try:
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    err = f.read()[-800:]
            except Exception:
                err = "log পড়া যায়নি"
            update_bot_status(bot_id, 'stopped')
            return False, f"বট চালু হয়েই বন্ধ:\n{err}"

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
