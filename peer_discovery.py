import requests
import time

def _check_internet_connection(test_url="http://www.google.com", timeout=5):
    """
    Check if there is an active internet connection by making a request to a reliable URL, INTERNAL FUNCTION
    
    Args:
        test_url (str): URL to test internet connectivity.
        timeout (int): Timeout for the request in seconds.
    
    Returns:
        bool: True if internet connection is available, False otherwise.
    """
    try:
        response = requests.get(test_url, timeout=timeout)
        return response.status_code == 200
    except requests.RequestException:
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
            response = requests.post(announce_url, json=payload, timeout=timeout)
            response.raise_for_status()
            response_data = response.json()
            received_nodes = response_data.get("known_nodes", [])
            known_nodes.update(received_nodes)
            return set(received_nodes)  # Return the list of known nodes received
        except requests.RequestException as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            time.sleep(2 ** attempt)
    print(f"Failed to announce to {announce_url} after {max_retries} attempts")
    return set()

def handle_announcement(node_id, received_known_nodes, known_nodes, announced_nodes, response_url):
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
    if node_id not in announced_nodes:
        announced_nodes.add(node_id)
        known_nodes.add(node_id)  # Add the node making the announcement
        known_nodes.update(received_known_nodes)
        
        # Send back the updated list of known nodes
        payload = {"known_nodes": list(known_nodes)}
        try:
            response = requests.post(response_url, json=payload)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"Failed to send response to {response_url}: {e}")

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
        return 2

    try:
        response = requests.get(node_url, timeout=timeout)
        if response.status_code == 200 and 'heartbeat' in response.text:
            return 0  # Valid heartbeat page
        else:
            return 1  # Invalid or unreachable
    except requests.RequestException:
        return 1  # Node is unreachable or invalid
