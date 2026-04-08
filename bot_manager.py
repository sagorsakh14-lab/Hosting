import os
import signal
import subprocess
import psutil
import zipfile
import shutil
from config import BASE_DIR

def extract_zip(zip_path, extract_to):
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    return True

def start_bot(bot_id):
    from database import get_bot, update_bot_status
    bot_data = get_bot(bot_id)
    if not bot_data:
        return False, "Bot not found"
    
    folder = bot_data['folder']
    main_py = os.path.join(folder, "main.py")
    
    if not os.path.exists(main_py):
        for file in os.listdir(folder):
            if file.endswith('.py'):
                os.rename(os.path.join(folder, file), main_py)
                break
    
    try:
        process = subprocess.Popen(
            ['python', '-u', main_py],
            cwd=folder,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            preexec_fn=os.setsid if hasattr(os, 'setsid') else None
        )
        update_bot_status(bot_id, 'running')
        return True, f"Started with PID: {process.pid}"
    except Exception as e:
        return False, str(e)

def stop_bot(bot_id):
    from database import get_bot, update_bot_status
    bot_data = get_bot(bot_id)
    if not bot_data:
        return False
    
    pid = bot_data.get('pid', 0)
    if pid and pid > 0:
        try:
            if hasattr(os, 'killpg'):
                os.killpg(os.getpgid(pid), signal.SIGTERM)
            else:
                os.kill(pid, signal.SIGTERM)
            update_bot_status(bot_id, 'stopped')
            return True
        except:
            pass
    
    update_bot_status(bot_id, 'stopped')
    return False

def restart_bot(bot_id):
    stop_bot(bot_id)
    import time
    time.sleep(2)
    return start_bot(bot_id)

def is_running(bot_id):
    from database import get_bot
    bot_data = get_bot(bot_id)
    if not bot_data or bot_data['status'] != 'running':
        return False
    pid = bot_data.get('pid', 0)
    if pid and psutil.pid_exists(pid):
        return True
    return False

def get_logs(bot_id, lines=50):
    from database import get_bot
    bot_data = get_bot(bot_id)
    if not bot_data:
        return "Bot not found"
    log_file = os.path.join(bot_data['folder'], "bot.log")
    if not os.path.exists(log_file):
        return "No logs yet"
    try:
        with open(log_file, 'r') as f:
            logs = f.readlines()
            return ''.join(logs[-lines:])
    except:
        return "Error reading logs"

def delete_bot_files(bot_id):
    from database import get_bot
    bot_data = get_bot(bot_id)
    if bot_data and os.path.exists(bot_data['folder']):
        shutil.rmtree(bot_data['folder'])
    return True

def server_stats():
    return {
        'cpu': psutil.cpu_percent(),
        'ram_used': round(psutil.virtual_memory().used / (1024**3), 1),
        'ram_total': round(psutil.virtual_memory().total / (1024**3), 1),
        'disk_used': round(psutil.disk_usage('/').used / (1024**3), 1),
        'disk_total': round(psutil.disk_usage('/').total / (1024**3), 1)
    }