import os
import subprocess
import signal
import zipfile
import psutil
import shutil
from config import BASE_DIR
from database import get_bot, update_bot_status

# Running processes track করা
running_processes = {}

def extract_zip(zip_path, extract_to):
    """Zip ফাইল extract করুন"""
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    return True

def find_main_file(bot_folder):
    """
    Python বা Node.js বটের মেইন ফাইল খুঁজুন
    Returns: (runner, file_path)
    runner = 'python3' অথবা 'node'
    """
    # Python ফাইল খোঁজা (priority)
    python_files = ['main.py', 'bot.py', 'app.py', 'run.py', 'index.py']
    for f in python_files:
        file_path = os.path.join(bot_folder, f)
        if os.path.exists(file_path):
            return ('python3', file_path)
    
    # যেকোনো .py ফাইল
    for f in os.listdir(bot_folder):
        if f.endswith('.py'):
            return ('python3', os.path.join(bot_folder, f))
    
    # Node.js ফাইল খোঁজা
    js_files = ['index.js', 'bot.js', 'main.js', 'app.js', 'server.js']
    for f in js_files:
        file_path = os.path.join(bot_folder, f)
        if os.path.exists(file_path):
            return ('node', file_path)
    
    # যেকোনো .js ফাইল
    for f in os.listdir(bot_folder):
        if f.endswith('.js'):
            return ('node', os.path.join(bot_folder, f))
    
    return (None, None)

def check_package_json(bot_folder):
    """package.json থাকলে npm install চালান"""
    package_json = os.path.join(bot_folder, 'package.json')
    if os.path.exists(package_json):
        try:
            subprocess.run(
                ['npm', 'install'],
                cwd=bot_folder,
                capture_output=True,
                timeout=120
            )
            return True
        except Exception as e:
            return False
    return True

def check_requirements_txt(bot_folder):
    """requirements.txt থাকলে pip install চালান"""
    req_file = os.path.join(bot_folder, 'requirements.txt')
    if os.path.exists(req_file):
        try:
            subprocess.run(
                ['pip', 'install', '-r', 'requirements.txt'],
                cwd=bot_folder,
                capture_output=True,
                timeout=120
            )
            return True
        except Exception as e:
            return False
    return True

def start_bot(bot_id):
    """বট স্টার্ট করুন (Python বা Node.js)"""
    try:
        stop_bot(bot_id)
        
        bot = get_bot(bot_id)
        if not bot:
            return False, "Bot not found in database"
        
        bot_folder = bot['folder']
        
        # মেইন ফাইল খুঁজুন
        runner, main_file = find_main_file(bot_folder)
        
        if not main_file:
            update_bot_status(bot_id, 'stopped')
            return False, "কোনো main.py বা index.js ফাইল পাওয়া যায়নি!"
        
        # Dependencies ইন্সটল করুন
        if runner == 'python3':
            check_requirements_txt(bot_folder)
        elif runner == 'node':
            check_package_json(bot_folder)
        
        # বট রান করুন
        log_file = open(os.path.join(bot_folder, "bot.log"), "a")
        process = subprocess.Popen(
            [runner, main_file],
            cwd=bot_folder,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            preexec_fn=os.setsid
        )
        
        running_processes[bot_id] = process
        update_bot_status(bot_id, 'running', process.pid)
        
        bot_type = "Python" if runner == 'python3' else "Node.js"
        return True, f"Bot started successfully ({bot_type})"
        
    except Exception as e:
        update_bot_status(bot_id, 'stopped')
        return False, str(e)

def stop_bot(bot_id):
    """বট বন্ধ করুন"""
    try:
        if bot_id in running_processes:
            process = running_processes[bot_id]
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            process.wait(timeout=5)
            del running_processes[bot_id]
        update_bot_status(bot_id, 'stopped')
        return True
    except Exception as e:
        try:
            if bot_id in running_processes:
                running_processes[bot_id].kill()
                del running_processes[bot_id]
        except:
            pass
        update_bot_status(bot_id, 'stopped')
        return True

def restart_bot(bot_id):
    """বট রিস্টার্ট করুন"""
    stop_bot(bot_id)
    return start_bot(bot_id)

def is_running(bot_id):
    """বট চলছে কিনা চেক করুন"""
    if bot_id in running_processes:
        process = running_processes[bot_id]
        return process.poll() is None
    return False

def get_logs(bot_id, lines=30):
    """বটের লগ ফাইল পড়ুন"""
    try:
        bot = get_bot(bot_id)
        if not bot:
            return "Bot not found"
        
        log_path = os.path.join(bot['folder'], "bot.log")
        if not os.path.exists(log_path):
            return "No logs available yet"
        
        with open(log_path, 'r') as f:
            all_lines = f.readlines()
            return ''.join(all_lines[-lines:])
    except Exception as e:
        return f"Error reading logs: {e}"

def delete_bot_files(bot_id):
    """বটের সব ফাইল ডিলিট করুন"""
    try:
        stop_bot(bot_id)
        bot = get_bot(bot_id)
        if bot and os.path.exists(bot['folder']):
            shutil.rmtree(bot['folder'])
        return True
    except Exception as e:
        return False

def server_stats():
    """সার্ভার স্ট্যাটাস"""
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    return {
        'cpu': cpu,
        'ram_used': round(ram.used / (1024**3), 1),
        'ram_total': round(ram.total / (1024**3), 1),
        'disk_used': round(disk.used / (1024**3), 1),
        'disk_total': round(disk.total / (1024**3), 1)
    }

def get_bot_type(bot_id):
    """বটের টাইপ চেক করুন (Python/Node.js)"""
    bot = get_bot(bot_id)
    if not bot:
        return "Unknown"
    
    bot_folder = bot['folder']
    if not os.path.exists(bot_folder):
        return "Unknown"
        
    runner, _ = find_main_file(bot_folder)
    
    if runner == 'python3':
        return "🐍 Python"
    elif runner == 'node':
        return "🟢 Node.js"
    return "❓ Unknown"