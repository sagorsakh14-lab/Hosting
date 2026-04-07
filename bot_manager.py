# bot_manager.py — TachZone Hosting Bot

import os
import subprocess
import signal
import zipfile
import psutil
import shutil
import logging
from config import BASE_DIR
from database import get_bot, update_bot_status

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Running processes track করা
running_processes = {}


def extract_zip(zip_path, extract_to):
    """Zip ফাইল extract করুন"""
    try:
        logger.info(f"Extracting {zip_path} to {extract_to}")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        logger.info(f"Extraction complete: {extract_to}")
        return True
    except Exception as e:
        logger.error(f"ZIP extraction error: {e}")
        raise e


def find_main_file(bot_folder):
    """
    Python বা Node.js বটের মেইন ফাইল খুঁজুন
    Returns: (runner, file_path)
    runner = 'python3' অথবা 'node'
    """
    logger.info(f"Searching for main file in: {bot_folder}")
    
    # ফোল্ডার চেক
    if not os.path.exists(bot_folder):
        logger.error(f"Folder does not exist: {bot_folder}")
        return (None, None)
    
    files = os.listdir(bot_folder)
    logger.info(f"Files in folder: {files}")
    
    # Python ফাইল খোঁজা (priority)
    python_files = ['main.py', 'bot.py', 'app.py', 'run.py', 'index.py', 'core.py']
    for f in python_files:
        file_path = os.path.join(bot_folder, f)
        if os.path.exists(file_path):
            logger.info(f"Found Python main file: {f}")
            return ('python3', file_path)
    
    # যেকোনো .py ফাইল
    for f in files:
        if f.endswith('.py'):
            logger.info(f"Found Python file: {f}")
            return ('python3', os.path.join(bot_folder, f))
    
    # Node.js ফাইল খোঁজা
    js_files = ['index.js', 'bot.js', 'main.js', 'app.js', 'server.js', 'core.js']
    for f in js_files:
        file_path = os.path.join(bot_folder, f)
        if os.path.exists(file_path):
            logger.info(f"Found Node.js main file: {f}")
            return ('node', file_path)
    
    # যেকোনো .js ফাইল
    for f in files:
        if f.endswith('.js'):
            logger.info(f"Found Node.js file: {f}")
            return ('node', os.path.join(bot_folder, f))
    
    logger.error(f"No Python or Node.js file found in {bot_folder}")
    return (None, None)


def check_package_json(bot_folder):
    """package.json থাকলে npm install চালান"""
    package_json = os.path.join(bot_folder, 'package.json')
    if os.path.exists(package_json):
        try:
            logger.info(f"Running npm install in {bot_folder}")
            result = subprocess.run(
                ['npm', 'install'],
                cwd=bot_folder,
                capture_output=True,
                text=True,
                timeout=180  # 3 মিনিট টাইমআউট
            )
            if result.returncode == 0:
                logger.info("npm install completed successfully")
                return True
            else:
                logger.error(f"npm install failed: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            logger.error("npm install timeout")
            return False
        except FileNotFoundError:
            logger.error("npm not found in system")
            return False
        except Exception as e:
            logger.error(f"npm install error: {e}")
            return False
    logger.info("No package.json found, skipping npm install")
    return True


def check_requirements_txt(bot_folder):
    """requirements.txt থাকলে pip install চালান"""
    req_file = os.path.join(bot_folder, 'requirements.txt')
    if os.path.exists(req_file):
        try:
            logger.info(f"Running pip install -r requirements.txt in {bot_folder}")
            result = subprocess.run(
                ['pip', 'install', '-r', 'requirements.txt'],
                cwd=bot_folder,
                capture_output=True,
                text=True,
                timeout=180  # 3 মিনিট টাইমআউট
            )
            if result.returncode == 0:
                logger.info("pip install completed successfully")
                return True
            else:
                logger.error(f"pip install failed: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            logger.error("pip install timeout")
            return False
        except FileNotFoundError:
            logger.error("pip not found in system")
            return False
        except Exception as e:
            logger.error(f"pip install error: {e}")
            return False
    logger.info("No requirements.txt found, skipping pip install")
    return True


def start_bot(bot_id):
    """বট স্টার্ট করুন (Python বা Node.js)"""
    try:
        logger.info(f"Starting bot: {bot_id}")
        
        # আগের প্রসেস বন্ধ করুন
        stop_bot(bot_id)
        
        bot = get_bot(bot_id)
        if not bot:
            logger.error(f"Bot not found in database: {bot_id}")
            return False, "Bot not found in database"
        
        bot_folder = bot['folder']
        logger.info(f"Bot folder: {bot_folder}")
        
        # ফোল্ডার চেক করুন
        if not os.path.exists(bot_folder):
            logger.error(f"Bot folder does not exist: {bot_folder}")
            update_bot_status(bot_id, 'stopped')
            return False, f"Bot folder not found: {bot_folder}"
        
        # ফোল্ডারের কনটেন্ট দেখুন
        files = os.listdir(bot_folder)
        logger.info(f"Bot folder contents ({len(files)} files): {files[:10]}")
        
        # মেইন ফাইল খুঁজুন
        runner, main_file = find_main_file(bot_folder)
        
        if not main_file:
            logger.error(f"No main file found in {bot_folder}")
            update_bot_status(bot_id, 'stopped')
            return False, f"কোনো main.py বা index.js ফাইল পাওয়া যায়নি!\n\nফোল্ডারের ফাইলসমূহ:\n" + "\n".join(files[:10])
        
        logger.info(f"Found main file: {main_file}, runner: {runner}")
        
        # Dependencies ইন্সটল করুন
        if runner == 'python3':
            pip_ok = check_requirements_txt(bot_folder)
            if not pip_ok:
                logger.warning("pip install had issues, continuing anyway...")
        elif runner == 'node':
            npm_ok = check_package_json(bot_folder)
            if not npm_ok:
                logger.warning("npm install had issues, continuing anyway...")
        
        # লগ ফাইল তৈরি করুন
        log_path = os.path.join(bot_folder, "bot.log")
        log_file = open(log_path, "a")
        log_file.write(f"\n--- Bot started at {subprocess.run(['date'], capture_output=True, text=True).stdout.strip()} ---\n")
        log_file.flush()
        
        # বট রান করুন
        logger.info(f"Starting process: {runner} {main_file}")
        
        # Windows/Linux compatibility
        if os.name == 'nt':  # Windows
            process = subprocess.Popen(
                [runner, main_file],
                cwd=bot_folder,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )
        else:  # Linux/Mac
            process = subprocess.Popen(
                [runner, main_file],
                cwd=bot_folder,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                preexec_fn=os.setsid
            )
        
        running_processes[bot_id] = process
        update_bot_status(bot_id, 'running', process.pid)
        
        bot_type = "🐍 Python" if runner == 'python3' else "🟢 Node.js"
        logger.info(f"Bot {bot_id} started successfully, PID: {process.pid}")
        
        return True, f"{bot_type}"
        
    except FileNotFoundError as e:
        logger.error(f"Runner not found: {e}")
        update_bot_status(bot_id, 'stopped')
        return False, f"{runner} পাওয়া যায়নি! সিস্টেমে ইন্সটল করা আছে কিনা চেক করুন।"
    except PermissionError as e:
        logger.error(f"Permission error: {e}")
        update_bot_status(bot_id, 'stopped')
        return False, f"পারমিশন এরর: ফাইল এক্সিকিউট করা যাচ্ছে না।"
    except Exception as e:
        logger.error(f"Start bot error: {e}")
        update_bot_status(bot_id, 'stopped')
        return False, str(e)


def stop_bot(bot_id):
    """বট বন্ধ করুন"""
    try:
        logger.info(f"Stopping bot: {bot_id}")
        
        if bot_id in running_processes:
            process = running_processes[bot_id]
            pid = process.pid
            logger.info(f"Terminating process PID: {pid}")
            
            if os.name == 'nt':  # Windows
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
            else:  # Linux/Mac
                os.killpg(os.getpgid(pid), signal.SIGTERM)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(os.getpgid(pid), signal.SIGKILL)
            
            del running_processes[bot_id]
            logger.info(f"Bot {bot_id} stopped successfully")
        else:
            logger.info(f"Bot {bot_id} was not running")
        
        update_bot_status(bot_id, 'stopped')
        return True
        
    except ProcessLookupError:
        logger.info(f"Process for {bot_id} already gone")
        if bot_id in running_processes:
            del running_processes[bot_id]
        update_bot_status(bot_id, 'stopped')
        return True
    except Exception as e:
        logger.error(f"Stop bot error: {e}")
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
    logger.info(f"Restarting bot: {bot_id}")
    stop_bot(bot_id)
    return start_bot(bot_id)


def is_running(bot_id):
    """বট চলছে কিনা চেক করুন"""
    if bot_id in running_processes:
        process = running_processes[bot_id]
        is_alive = process.poll() is None
        if not is_alive:
            # প্রসেস মারা গেছে, ডিকশনারি থেকে রিমুভ
            logger.warning(f"Bot {bot_id} process died, removing from tracker")
            del running_processes[bot_id]
            update_bot_status(bot_id, 'stopped')
        return is_alive
    return False


def get_logs(bot_id, lines=30):
    """বটের লগ ফাইল পড়ুন"""
    try:
        bot = get_bot(bot_id)
        if not bot:
            return "❌ Bot not found in database"
        
        log_path = os.path.join(bot['folder'], "bot.log")
        if not os.path.exists(log_path):
            return "📭 No logs available yet. Bot may not have started."
        
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            all_lines = f.readlines()
            if not all_lines:
                return "📭 Log file is empty."
            recent_lines = all_lines[-lines:]
            return ''.join(recent_lines)
            
    except PermissionError:
        return "❌ Permission denied: Cannot read log file."
    except Exception as e:
        logger.error(f"Get logs error: {e}")
        return f"❌ Error reading logs: {str(e)}"


def delete_bot_files(bot_id):
    """বটের সব ফাইল ডিলিট করুন"""
    try:
        logger.info(f"Deleting bot files: {bot_id}")
        
        # আগে বট বন্ধ করুন
        stop_bot(bot_id)
        
        bot = get_bot(bot_id)
        if not bot:
            logger.error(f"Bot not found: {bot_id}")
            return False
        
        bot_folder = bot['folder']
        if os.path.exists(bot_folder):
            logger.info(f"Removing folder: {bot_folder}")
            shutil.rmtree(bot_folder, ignore_errors=True)
            logger.info(f"Folder removed successfully")
            return True
        else:
            logger.warning(f"Folder does not exist: {bot_folder}")
            return True
            
    except PermissionError:
        logger.error(f"Permission denied deleting {bot_folder}")
        return False
    except Exception as e:
        logger.error(f"Delete bot files error: {e}")
        return False


def server_stats():
    """সার্ভার স্ট্যাটাস"""
    try:
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            'cpu': cpu,
            'ram_used': round(ram.used / (1024**3), 1),
            'ram_total': round(ram.total / (1024**3), 1),
            'ram_percent': ram.percent,
            'disk_used': round(disk.used / (1024**3), 1),
            'disk_total': round(disk.total / (1024**3), 1),
            'disk_percent': disk.percent
        }
    except Exception as e:
        logger.error(f"Server stats error: {e}")
        return {
            'cpu': 0,
            'ram_used': 0,
            'ram_total': 0,
            'ram_percent': 0,
            'disk_used': 0,
            'disk_total': 0,
            'disk_percent': 0
        }


def get_bot_type(bot_id):
    """বটের টাইপ চেক করুন (Python/Node.js)"""
    try:
        bot = get_bot(bot_id)
        if not bot:
            return "❓ Unknown"
        
        bot_folder = bot['folder']
        if not os.path.exists(bot_folder):
            return "📁 Folder not found"
            
        runner, _ = find_main_file(bot_folder)
        
        if runner == 'python3':
            return "🐍 Python"
        elif runner == 'node':
            return "🟢 Node.js"
        return "❓ Unknown"
        
    except Exception as e:
        logger.error(f"Get bot type error: {e}")
        return "❓ Error"


def get_running_bots_count():
    """চলমান বটের সংখ্যা"""
    count = 0
    for bot_id in list(running_processes.keys()):
        if is_running(bot_id):
            count += 1
        else:
            # ডেড প্রসেস ক্লিনআপ
            if bot_id in running_processes:
                del running_processes[bot_id]
    return count


def cleanup_dead_processes():
    """মৃত প্রসেসগুলো ক্লিনআপ করুন"""
    dead_bots = []
    for bot_id, process in running_processes.items():
        if process.poll() is not None:
            dead_bots.append(bot_id)
    
    for bot_id in dead_bots:
        logger.info(f"Cleaning up dead process: {bot_id}")
        del running_processes[bot_id]
        update_bot_status(bot_id, 'stopped')
    
    return len(dead_bots)


def get_process_info(bot_id):
    """বট প্রসেসের বিস্তারিত তথ্য"""
    if bot_id not in running_processes:
        return None
    
    process = running_processes[bot_id]
    if process.poll() is not None:
        del running_processes[bot_id]
        return None
    
    try:
        proc = psutil.Process(process.pid)
        return {
            'pid': process.pid,
            'cpu_percent': proc.cpu_percent(interval=0.1),
            'memory_mb': round(proc.memory_info().rss / (1024 * 1024), 1),
            'running_time': proc.create_time()
        }
    except:
        return {
            'pid': process.pid,
            'cpu_percent': 0,
            'memory_mb': 0,
            'running_time': None
        }