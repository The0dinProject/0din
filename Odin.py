import os
import json
import time
import logging
import secrets
import requests
import threading
import sched
import search
import peer_discovery
import indexer
from datetime import datetime, timedelta
from flask import Flask, render_template, redirect, request, jsonify, send_file, abort, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from colorlog import ColoredFormatter

# Logging configuration
log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
formatter = ColoredFormatter(
    "%(asctime)s - %(name)s - %(log_color)s%(levelname)s%(reset)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    log_colors={
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'bold_red',
    }
)
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.addHandler(console_handler)

# Global variables
known_nodes = set()
announced_nodes = set()

# Flask application
app = Flask(__name__)
scheduler = sched.scheduler(time.time, time.sleep)
app.secret_key = secrets.token_hex(16)

# Default configuration
DEFAULT_CONFIG = {
    'INDEX': '/path/to/index.json',
    'NODE_ID': '127.0.0.1:5000',
    'LAST_EXECUTION_FILE': 'last_execution.txt',
    'INDEX_FILES_TIME': 1,
    'PEER_DISCOVER_INTERVAL': 1,
    'DIRECTORY': '/the/directory/to/be/shared',
    'URL': 'https://raw.githubusercontent.com/username/repository/branch/path/to/file.json',
    'HEARTBEAT_INTERVAL': 10
}

def setup_admin_credentials(username, password):
    hashed_password = generate_password_hash(password)
    with open('credentials.json', 'w') as f:
        json.dump({'username': username, 'password': hashed_password}, f)

def initialize_settings():
    if not os.path.exists('settings.json'):
        with open('settings.json', 'w') as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)
    with open('settings.json') as f:
        config = json.load(f)
    for key, value in DEFAULT_CONFIG.items():
        globals()[key] = config.get(key, value)

def load_constants():
    if os.path.exists('settings.json'):
        with open('settings.json') as f:
            return json.load(f)
    return DEFAULT_CONFIG.copy()

def save_constants(config):
    with open('settings.json', 'w') as f:
        json.dump(config, f, indent=4)

def load_credentials():
    if os.path.exists('credentials.json'):
        with open('credentials.json') as f:
            return json.load(f)
    return {'username': 'admin', 'password': generate_password_hash('admin')}

@app.before_request
def check_setup():
    if not os.path.exists('credentials.json'):
        if request.endpoint not in ['setup', 'login']:
            return redirect(url_for('setup'))

@app.route('/setup', methods=['GET', 'POST'])
def setup():
    if os.path.exists('credentials.json'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        setup_admin_credentials(username, password)
        return redirect(url_for('login'))
    
    return render_template('setup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        credentials = load_credentials()
        if username == credentials['username'] and check_password_hash(credentials['password'], password):
            session['logged_in'] = True
            return redirect(url_for('admin'))
        else:
            return 'Invalid credentials', 401
    return render_template('login.html')

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    config = load_constants()

    if request.method == 'POST':
        for key in config:
            if key in request.form:
                try:
                    config[key] = json.loads(request.form[key])
                except ValueError:
                    config[key] = request.form[key]
        save_constants(config)

    return render_template('admin.html', config=config)

@app.route('/shutdown', methods=['POST'])
def shutdown():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()
    return 'Server shutting down...'

@app.route('/restart', methods=['POST'])
def restart():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()
    os.execv(__file__, ['python'] + [__file__])
    return 'Server restarting...'

def run_indexer():
    logger.info("Running indexer...")
    indexer.indexer(DIRECTORY, INDEX)
    
    next_run = datetime.now() + timedelta(hours=24)
    delay = (next_run - datetime.now()).total_seconds()
    logger.info(f"Scheduling indexer for the next run in 24 hours")
    scheduler.enter(delay, 1, run_indexer)

def run_announcer():
    global known_nodes, announced_nodes
    logger.info("Running announcer...")
    new_nodes_discovered = False
    for node in list(known_nodes):
        if node not in announced_nodes:
            logger.info(f"Announcing to {node}...")
            new_nodes = peer_discovery.announce(f"http://{node}/announce", NODE_ID, known_nodes)
            announced_nodes.add(node)
            if new_nodes:
                new_nodes_discovered = True
                known_nodes.update(new_nodes)
    
    logger.info(f"Known nodes: {known_nodes}")
    logger.info(f"Announced nodes: {announced_nodes}")
    
    if not new_nodes_discovered:
        logger.info("No new nodes discovered, stopping announcer.")
    
    delay = PEER_DISCOVER_INTERVAL * 3600
    logger.info(f"Scheduling announcer for the next run in {PEER_DISCOVER_INTERVAL} hours")
    scheduler.enter(delay, 1, run_announcer)

def run_heartbeat_checker():
    global known_nodes
    logger.info("Running heartbeat checker...")
    nodes_to_remove = set()
    for node in list(known_nodes):
        result = peer_discovery.heartbeat_ping(f"http://{node}/heartbeat")
        if result == 1:
            logger.info(f"Node {node} is unreachable or invalid, removing from known_nodes.")
            nodes_to_remove.add(node)
        elif result == 2:
            logger.error("No internet connection, cannot perform heartbeat check.")
            break
    
    known_nodes.difference_update(nodes_to_remove)
    logger.info(f"Updated known nodes: {known_nodes}")
    
    delay = HEARTBEAT_INTERVAL * 60
    logger.info(f"Scheduling heartbeat checker for the next run in {HEARTBEAT_INTERVAL} minutes")
    scheduler.enter(delay, 1, run_heartbeat_checker)

def schedule_tasks():
    now = datetime.now()
    next_index_run = datetime.combine(now.date(), datetime.min.time()) + timedelta(hours=INDEX_FILES_TIME)
    if now > next_index_run:
        next_index_run += timedelta(days=1)
    
    delay_index = (next_index_run - now).total_seconds()
    logger.info(f"Scheduling indexer for {next_index_run} (in {delay_index // 3600} hours and {(delay_index % 3600) // 60} minutes)")
    scheduler.enter(delay_index, 1, run_indexer)
    
    response = requests.get(URL)
    if response.status_code == 200:
        data = json.loads(response.text)
        known_nodes.update(data)
    else:
        logger.error(f"Failed to download node list, status code {response.status_code}")
        return None

    run_announcer()
    scheduler.enter(0, 1, run_announcer)
    run_heartbeat_checker()
    scheduler.enter(0, 1, run_heartbeat_checker)

def run_scheduler():
    while True:
        scheduler.run(blocking=False)
        time.sleep(1)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/global_search', methods=['POST'])
def global_search_route():
    query = request.form.get('query')
    category = request.form.get('category', None)
    if category == 'all':
        category = None
    
    results = search.global_search(INDEX, query, known_nodes, NODE_ID, "name", category)
    
    return render_template('results.html', query=query, category=category, results=results)

@app.route('/md5_search/<md5_hash>')
def md5_search(md5_hash):
    results = search.global_search(INDEX, md5_hash, known_nodes, NODE_ID, "md5")
    
    return render_template('md5_results.html', md5_hash=md5_hash, results=results)

@app.route('/download/<md5_hash>')
def download_file(md5_hash):
    download_url = f"/file/{md5_hash}"
    return redirect(download_url)

@app.route('/file/<md5_hash>')
def serve_file(md5_hash):
    matches = search.local_search(INDEX, md5_hash, NODE_ID, 'md5')
    if not matches:
        abort(404)
    
    file_path = matches[0].get('file_path')
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    
    abort(404)

@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return 'Heartbeat received', 200


@app.route('/json/nodes')
def nodes():
    global known_nodes
    
    return jsonify(list(known_nodes))

if __name__ == '__main__':
    initialize_settings()
    schedule_tasks()
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.start()
    app.run(host='0.0.0.0', port=5000, debug=True)

