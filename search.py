import psycopg2
import os
import requests
import logging
from colorlog import ColoredFormatter
from concurrent.futures import ThreadPoolExecutor, as_completed

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

def get_db_connection():
    """Establish a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            dbname=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432')
        )
        logger.info("Database connection established successfully.")
        return conn
    except psycopg2.Error as e:
        logger.error(f"Database connection failed: {e}")
        raise

def local_search(search_term, node_id, search_type='name', category=None):
    """
    Perform a local search in the PostgreSQL database for a specific search term.

    Args:
        search_term (str): Term to search for, either in file names (partial) or md5_hash (exact match).
        node_id (str): The ID of the current node performing the search.
        search_type (str): The type of search to perform ('name' for file name, 'md5' for md5_hash).
        category (str, optional): Category to filter the search results by.

    Returns:
        list: A list of dictionaries matching the search term and category (if specified), with 'node_id' included.
    """
    matches = []
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        logger.debug(f"Starting local search: search_term={search_term}, search_type={search_type}, category={category}")

        # Create the SQL query
        query = "SELECT file_name, path, md5_hash, file_size, category FROM files WHERE"
        conditions = []
        if category:
            conditions.append(" category = %s")
        if search_type == 'name':
            conditions.append(" LOWER(file_name) LIKE LOWER(%s)")
            search_term = f"%{search_term}%"
        elif search_type == 'md5':
            conditions.append(" md5_hash = %s")

        query += " AND".join(conditions)

        # Execute the query
        cursor.execute(query, tuple([category, search_term] if category else [search_term]))
        results = cursor.fetchall()

        for row in results:
            match = {
                'file_name': row[0],
                'path': row[1],
                'md5_hash': row[2],
                'file_size': row[3],
                'category': row[4],
                'node_id': node_id
            }
            matches.append(match)

        logger.info(f"Local search completed. Found {len(matches)} matches.")
    except Exception as e:
        logger.error(f"Error during local search: {e}")
    finally:
        cursor.close()
        conn.close()

    return matches

def global_search(search_term, known_nodes, current_node_id, search_type='name', category=None):
    """
    Perform a global search across all known nodes and the local index in the PostgreSQL database.

    Args:
        search_term (str): Term to search for in file names or md5_hash.
        known_nodes (list): List of known nodes to query for remote searches.
        current_node_id (str): The ID of the current node performing the search.
        search_type (str): The type of search to perform ('name' for file name, 'md5' for md5_hash).
        category (str, optional): Category to filter the search results by.

    Returns:
        list: A combined list of dictionaries from both local and remote searches.
    """
    global_matches = []

    logger.debug(f"Initiating global search for term '{search_term}' on node '{current_node_id}'")
    
    # Perform local search
    local_matches = local_search(search_term, current_node_id, search_type, category)
    global_matches.extend(local_matches)

    def remote_search(node_id):
        """Performs the remote search request."""
        if node_id == current_node_id:
            return []  # Skip the current node
        try:
            search_url = f"http://{node_id}/localsearch"
            logger.debug(f"Sending remote search request to {search_url}")
            response = requests.post(search_url, json={
                "search_term": search_term,
                "search_type": search_type,
                "category": category
            })
            response.raise_for_status()
            remote_matches = response.json()
            for match in remote_matches:
                match['node_id'] = node_id
            logger.info(f"Received {len(remote_matches)} matches from node {node_id}")
            return remote_matches
        except requests.RequestException as e:
            logger.error(f"Error during global search on node {node_id}: {e}")
            return []

    # Use ThreadPoolExecutor to perform remote searches concurrently
    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(remote_search, node_id): node_id for node_id in known_nodes if node_id != current_node_id}

        for future in as_completed(futures):
            remote_matches = future.result()
            global_matches.extend(remote_matches)

    logger.info(f"Global search completed. Total matches found: {len(global_matches)}")
    return global_matches
