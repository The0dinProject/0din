import requests
import time
import logging
import colorlog

# Configure logging
handler = colorlog.StreamHandler()
handler.setFormatter(colorlog.ColoredFormatter(
    '%(log_color)s%(asctime)s - %(levelname)s - %(message)s',
    log_colors={
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'bold_red',
    }
))

logger = colorlog.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


def _check_internet_connection(test_url="http://www.google.com", timeout=5):
    """
    Check if there is an active internet connection by making a request to a reliable URL.
    
    Args:
        test_url (str): URL to test internet connectivity.
        timeout (int): Timeout for the request in seconds.
    
    Returns:
        bool: True if internet connection is available, False otherwise.
    """
    try:
        response = requests.get(test_url, timeout=timeout)
        logger.info(f"Internet connection check: {response.status_code == 200}")
        return response.status_code == 200
    except requests.RequestException as e:
        logger.error(f"Internet connection check failed: {e}")
        return False


def announce(announce_url, node_id, known_nodes, max_retries=3, timeout=5):
    """
    Announce the node to a known node and update the known nodes list with the received list.
    
    Args:
        announce_url (str): URL of the known node to announce to.
        node_id (str): The ID of the announcing node (e.g., 'ip:port').
        known_nodes (set): Set of known nodes to be updated.
        max_retries (int): Maximum number of retries for the announcement.
        timeout (int): Timeout for the request in seconds.
    
    Returns:
        set: The list of known nodes received from the other node.
    """
    payload = {"node_id": node_id}
    for attempt in range(max_retries):
        try:
            logger.debug(f"Announcing to {announce_url}, attempt {attempt + 1}")
            response = requests.post(announce_url, json=payload, timeout=timeout)
            response.raise_for_status()
            response_data = response.json()
            received_nodes = response_data.get("known_nodes", [])
            known_nodes.update(received_nodes)
            logger.info(f"Announcement successful, known nodes received: {received_nodes}")
            return set(received_nodes)
        except requests.RequestException as e:
            logger.warning(f"Attempt {attempt + 1} failed: {e}")
            time.sleep(2 ** attempt)
    
    logger.error(f"Failed to announce to {announce_url} after {max_retries} attempts")
    return set()


def handle_announcement(node_id, received_known_nodes, known_nodes, response_url):
    """
    Handle an incoming announcement from another node, update the known nodes list,
    and return the updated list of known nodes to the announcing node.
    
    Args:
        node_id (str): The ID of the node making the announcement.
        received_known_nodes (list): The list of known nodes received from the announcing node.
        known_nodes (set): Set of known nodes to be updated.
        announced_nodes (set): Set of announced nodes to avoid re-announcement.
        response_url (str): URL to send the response with the list of known nodes.
    
    Returns:
        set: Updated set of known nodes after processing the announcement.
    """
    logger.debug(f"Handling announcement from {node_id}")
    known_nodes.add(node_id)
    known_nodes.update(received_known_nodes)
    logger.info(f"Updated known nodes with {received_known_nodes}")

    payload = {"known_nodes": list(known_nodes)}
    try:
        response = requests.post(response_url, json=payload)
        response.raise_for_status()
        logger.info(f"Successfully sent response to {response_url}")
    except requests.RequestException as e:
        logger.error(f"Failed to send response to {response_url}: {e}")

    return known_nodes


def heartbeat_ping(node_url, timeout=5):
    """
    Send a heartbeat ping to a node to check if it is still alive.
    
    Args:
        node_url (str): URL of the node to ping.
        timeout (int): Timeout for the request in seconds.
    
    Returns:
        int: 0 if the heartbeat page is valid, 1 if it is invalid, 2 if there is no internet connection.
    """
    if not _check_internet_connection():
        logger.warning("No internet connection available.")
        return 2

    try:
        logger.debug(f"Pinging node at {node_url}")
        response = requests.get(f"{node_url}/heartbeat", timeout=timeout)
        if response.status_code == 200 and 'heartbeat' in response.text:
            logger.info(f"Heartbeat valid from {node_url}")
            return 0
        else:
            logger.warning(f"Invalid or unreachable node at {node_url}")
            return 1
    except requests.RequestException as e:
        logger.error(f"Node {node_url} unreachable: {e}")
        return 1

