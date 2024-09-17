import os
import socket
from colorlog import ColoredFormatter
from datetime import datetime, timedelta
from flask import Flask, render_template, redirect, request, jsonify, send_file, abort
import indexer
import json
import logging
import peer_discovery
import requests
import sched
import search
import threading
import time

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
logger.setLevel(logging.DEBUG)  # Set to the desired level
logger.addHandler(console_handler)

INDEX = '/path/to/index.json'
NODE_ID = "127.0.0.1:5000"
LAST_EXECUTION_FILE = 'last_execution.txt'
INDEX_FILES_TIME = 1  # Hour to run the indexer task (24-hour format)
PEER_DISCOVER_INTERVAL = 1  # Interval in hours for the announcer task
DIRECTORY = "/the/directory/to/be/shared"
URL = "https://raw.githubusercontent.com/username/repository/branch/path/to/file.json"
HEARTBEAT_INTERVAL = 10  # Heartbeat check interval in minutes

known_nodes = set()
announced_nodes = set()

app = Flask(__name__)
scheduler = sched.scheduler(time.time, time.sleep)


def run_indexer():
    global known_nodes
    logger.info("Running indexer...")
    indexer.indexer(DIRECTORY, INDEX)
    
    # Schedule the next run
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
    
    # Schedule the next run
    delay = PEER_DISCOVER_INTERVAL * 3600  # Convert hours to seconds
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
            break  # Stop checking if there's no internet connection
    
    known_nodes.difference_update(nodes_to_remove)
    logger.info(f"Updated known nodes: {known_nodes}")
    
    # Schedule the next heartbeat check
    delay = HEARTBEAT_INTERVAL * 60  # Convert minutes to seconds
    logger.info(f"Scheduling heartbeat checker for the next run in {HEARTBEAT_INTERVAL} minutes")
    scheduler.enter(delay, 1, run_heartbeat_checker)


def schedule_tasks():
    global known_nodes
    # Calculate delay until the next occurrence of INDEX_FILES_TIME
    now = datetime.now()
    next_index_run = datetime.combine(now.date(), datetime.min.time()) + timedelta(hours=INDEX_FILES_TIME)
    
    if now > next_index_run:
        next_index_run += timedelta(days=1)
    
    delay_index = (next_index_run - now).total_seconds()
    logger.info(f"Scheduling indexer for {next_index_run} (in {delay_index // 3600} hours and {(delay_index % 3600) // 60} minutes)")
    scheduler.enter(delay_index, 1, run_indexer)
    
    # Run announcer once at startup and then periodically
    response = requests.get(URL)
    if response.status_code == 200:
        data = json.loads(response.text)
        known_nodes.update(data)
    else:
        logger.error(f"Failed to download node list, status code {response.status_code}")
        return None

    run_announcer()  # Run at startup
    scheduler.enter(0, 1, run_announcer)
    run_heartbeat_checker()  # Run heartbeat checker at startup
    scheduler.enter(0, 1, run_heartbeat_checker)

def run_scheduler():
    while True:
        scheduler.run(blocking=False)
        time.sleep(1)

# Route for the homepage with the search bar
@app.route('/')
def home():
    return render_template('index.html')

# Route to handle global search and redirect to results page
@app.route('/global_search', methods=['POST'])
def global_search_route():
    query = request.form.get('query')
    category = request.form.get('category', None)
    if category == 'all':
        category = None
    
    # Perform global search
    results = search.global_search(INDEX, query, known_nodes, NODE_ID, "name", category)
    
    # Render search results
    return render_template('results.html', query=query, category=category, results=results)

@app.route('/md5_search/<md5_hash>')
def md5_search(md5_hash):
    # Perform global search by MD5
    results = search.global_search(INDEX, md5_hash, known_nodes, NODE_ID, "md5")
    
    # Render the results page for the MD5 search
    return render_template('md5_results.html', md5_hash=md5_hash, results=results)

# Route to redirect the user to the appropriate node's download URL
@app.route('/download/<md5_hash>')
def download_file(md5_hash):
    # Construct the download URL
    download_url = f"/file/{md5_hash}"
    
    # Redirect the user to the download URL on the same server
    return redirect(download_url)

# Route to serve the file based on MD5 hash
@app.route('/file/<md5_hash>')
def serve_file(md5_hash):
    # Perform local search for the MD5 hash
    matches = search.local_search(INDEX, md5_hash, NODE_ID, 'md5')
    
    if not matches:
        abort(404)  # File not found
    
    # Assume the first match is the correct file (if there are multiple matches, handle accordingly)
    match = matches[0]
    file_path = match['path']
    
    # Ensure the file is within the allowed directory
    if not os.path.commonprefix([os.path.abspath(file_path), os.path.abspath(DIRECTORY)]) == os.path.abspath(DIRECTORY):
        abort(403)  # Forbidden

    return send_file(file_path, as_attachment=True)

@app.route('/announce', methods=['POST'])
def announce():
    # Extract data from the POST request
    data = request.get_json()
    
    node_id = data.get('node_id')
    received_known_nodes = data.get('received_known_nodes', [])
    response_url = data.get('response_url')
    
    # Ensure all required fields are present
    if not all([node_id, response_url]):
        return jsonify({"error": "Missing node_id or response_url"}), 400

    # Call the handle_announcement function
    updated_known_nodes = peer_discovery.handle_announcement(
        node_id,
        received_known_nodes,
        known_nodes,
        announced_nodes,
        response_url
    )
    
    # Return the updated list of known nodes
    return jsonify({"known_nodes": list(updated_known_nodes)}), 200

@app.route('/heartbeat', methods=['GET'])
def heartbeat():
    """
    Endpoint to confirm that the node is alive.
    
    Returns:
        str: A simple text response to confirm the node is alive.
    """
    return "Heartbeat OK", 200

if __name__ == '__main__':
    # Start the scheduler
    schedule_tasks()

    # Run the background scheduler in a separate thread
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()

    # Start the Flask server
    app.run(debug=True)

