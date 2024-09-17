import json
import requests

def local_search(index_path, search_term, node_id, search_type='name', category=None):
    """
    Perform a local search in the given index.json file for a specific search term, either by file name (partial match) 
    or md5_hash (exact match), and optionally filter by category.
    
    Args:
        index_path (str): Path to the index.json file.
        search_term (str): Term to search for, either in file names (partial) or md5_hash (exact match).
        node_id (str): The ID of the current node performing the search.
        search_type (str): The type of search to perform ('name' for file name, 'md5' for md5_hash).
        category (str, optional): Category to filter the search results by.
    
    Returns:
        list: A list of dictionaries matching the search term and category (if specified), with 'node_id' included.
    """
    matches = []
    
    try:
        with open(index_path, 'r') as f:
            index = json.load(f)
        
        for file_info in index:
            # Check if the category matches (if specified)
            if category and file_info.get('category') != category:
                continue

            # Perform a partial match for file name or an exact match for md5_hash based on search_type
            if search_type == 'name' and search_term.lower() in file_info['file_name'].lower():
                match = {
                    'file_name': file_info['file_name'],
                    'path': file_info['path'],
                    'md5_hash': file_info['md5_hash'],
                    'file_size': file_info['file_size'],
                    'category': file_info['category'],
                    'node_id': node_id
                }
                matches.append(match)
            elif search_type == 'md5' and search_term == file_info['md5_hash']:
                match = {
                    'file_name': file_info['file_name'],
                    'path': file_info['path'],
                    'md5_hash': file_info['md5_hash'],
                    'file_size': file_info['file_size'],
                    'category': file_info['category'],
                    'node_id': node_id
                }
                matches.append(match)
    
    except Exception as e:
        print(f"Error during local search: {e}")
    
    return matches

def global_search(index_path, search_term, known_nodes, current_node_id, search_type='name', category=None):
    """
    Perform a global search across all known nodes and the local index for a specific search term, based on search type.
    
    Args:
        index_path (str): Path to the local index.json file.
        search_term (str): Term to search for in file names or md5_hash.
        known_nodes (list): List of known nodes to query for remote searches.
        current_node_id (str): The ID of the current node performing the search.
        search_type (str): The type of search to perform ('name' for file name, 'md5' for md5_hash).
        category (str, optional): Category to filter the search results by.
    
    Returns:
        list: A combined list of dictionaries from both local and remote searches.
    """
    global_matches = []
    
    # Perform local search
    local_matches = local_search(index_path, search_term, current_node_id, search_type, category)
    global_matches.extend(local_matches)
    
    # Perform remote searches
    for node_id in known_nodes:
        if node_id == current_node_id:
            continue  # Skip searching on the current node itself

        try:
            search_url = f"http://{node_id}/localsearch"
            response = requests.post(search_url, json={
                "search_term": search_term,
                "search_type": search_type,
                "category": category
            })
            response.raise_for_status()
            remote_matches = response.json()
            for match in remote_matches:
                match['node_id'] = node_id
            global_matches.extend(remote_matches)
        except requests.RequestException as e:
            print(f"Error during global search on node {node_id}: {e}")
    
    return global_matches

