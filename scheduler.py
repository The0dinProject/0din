import schedule
import time
import threading
import logging
import requests
from datetime import datetime, timedelta
from settings import get_setting, return_all, set_setting
from database import get_db_connection
import peer_discovery
import indexer
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

def run_indexer():
    """Runs the indexer task."""
    logger.info("Running indexer...")
    conn = get_db_connection()
    
    # Run your actual indexing logic here
    indexer.indexer(get_setting('DIRECTORY'), conn)

    logger.info("Indexer completed successfully.")

    # Schedule the next run after 24 hours
    schedule.every(24).hours.do(run_indexer)
    logger.info("Scheduled indexer for the next run in 24 hours")

def run_announcer():
    """Runs the announcer task."""
    logger.info("Running announcer...")
    known_nodes = get_setting("known_nodes")
    announced_nodes = set()
    new_nodes_discovered = False

    for node in known_nodes:
        if node not in announced_nodes:
            logger.info(f"Announcing to {node}...")
            new_nodes = peer_discovery.announce(f"http://{node}/announce", get_setting('NODE_ID'), known_nodes)
            announced_nodes.add(node)
            if new_nodes:
                new_nodes_discovered = True
                known_nodes.update(new_nodes)

    logger.info(f"Known nodes: {known_nodes}")
    logger.info(f"Announced nodes: {announced_nodes}")

    if not new_nodes_discovered:
        logger.info("No new nodes discovered, stopping announcer.")

    # Schedule the next run based on the interval set in settings
    interval = get_setting('PEER_DISCOVER_INTERVAL')
    schedule.every(interval).hours.do(run_announcer)
    logger.info(f"Scheduled announcer for the next run in {interval} hours")

def run_heartbeat_checker():
    """Runs the heartbeat checker."""
    logger.info("Running heartbeat checker...")
    known_nodes = return_all()['known_nodes']
    nodes_to_remove = set()

    for node in known_nodes:
        result = peer_discovery.heartbeat_ping(f"http://{node}/heartbeat")
        if result == 1:
            logger.info(f"Node {node} is unreachable or invalid, removing from known_nodes.")
            nodes_to_remove.add(node)
        elif result == 2:
            logger.error("No internet connection, cannot perform heartbeat check.")
            break

    # Update known nodes
    known_nodes.difference_update(nodes_to_remove)
    logger.info(f"Updated known nodes: {known_nodes}")

    # Schedule the next run based on the interval set in settings
    interval = get_setting('HEARTBEAT_INTERVAL')
    schedule.every(interval).minutes.do(run_heartbeat_checker)
    logger.info(f"Scheduled heartbeat checker for the next run in {interval} minutes")

def schedule_tasks():
    """Schedules all tasks."""
    # Schedule the indexer for the first time
    index_time = get_setting('INDEX_FILES_TIME')
    next_index_run = datetime.now().replace(hour=index_time, minute=0, second=0, microsecond=0)
    if datetime.now() > next_index_run:
        next_index_run += timedelta(days=1)

    delay_index = (next_index_run - datetime.now()).total_seconds()
    logger.info(f"Scheduled indexer for {next_index_run} (in {delay_index // 3600} hours and {(delay_index % 3600) // 60} minutes)")

    # Run the indexer immediately
    run_indexer()

    # Fetch known nodes from the URL and update settings
    response = requests.get(get_setting('URL'))
    if response.status_code == 200:
        data = response.json()
        current_known_nodes = return_all()['known_nodes']
        current_known_nodes.update(data)
        logger.info(f"Updated known nodes from the URL: {current_known_nodes}")
    else:
        logger.error(f"Failed to download node list, status code {response.status_code}")

    # Run announcer and heartbeat checker immediately
    run_announcer()
    run_heartbeat_checker()

def _run_scheduler():
    """Internal function to run the scheduler."""
    while True:
        schedule.run_pending()
        time.sleep(1)

def start_scheduler():
    """Start the task scheduler in a background thread."""
    scheduler_thread = threading.Thread(target=_run_scheduler, daemon=True)
    scheduler_thread.start()

