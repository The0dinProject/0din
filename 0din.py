import os
import json
import logging
import secrets
import search
import indexer
import psycopg2
import settings
from flask import Flask, render_template, redirect, request, jsonify, flash, send_file, abort, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from colorlog import ColoredFormatter
from dotenv import load_dotenv
from database import get_db_connection, put_connection
from scheduler import start_scheduler, schedule_tasks

load_dotenv()

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

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

def setup_admin_credentials(username, password):
    hashed_password = generate_password_hash(password)
    with open('credentials.json', 'w') as f:
        json.dump({'username': username, 'password': hashed_password}, f)

def load_credentials():
    if os.path.exists('credentials.json'):
        with open('credentials.json') as f:
            return json.load(f)
    return {'username': 'admin', 'password': generate_password_hash('admin')}

@app.before_request
def check_setup():
    ssl_enabled = os.getenv("ENABLE_SSL") == "true"
    https_redirect_enabled = os.getenv("ENABLE_HTTPS_REDIRECT") == "true"

    if ssl_enabled:
        if not request.is_secure:
            url = request.url.replace("http://", "https://", 1)
            return redirect(url, code=301)
        return

    if https_redirect_enabled:
        if not request.is_secure and request.headers.get('X-Forwarded-Proto', 'http') != 'https':
            url = request.url.replace("http://", "https://", 1)
            return redirect(url, code=301)

    if request.path.startswith('/static') or request.endpoint in ['setup', 'login']:
        return

    if not os.path.exists('credentials.json'):
        return redirect(url_for('setup'))

@app.route('/setup', methods=['GET', 'POST'])
def setup():
    if os.path.exists('credentials.json'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        password_confirmation = request.form['password_confirmation']

        if (password_confirmation != password):
            flash("Passwords do not match", 'error')

            return redirect(url_for('setup'))

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

    config = settings.return_all()

    if request.method == 'POST':
        for key in config:
            if key in request.form:
                try:
                    config[key] = json.loads(request.form[key])
                except ValueError:
                    config[key] = request.form[key]

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

@app.route('/indexer', methods=['POST'])
def trigger_indexer():
    if not session.get('logged_in'):
        return "Unauthorized", 401  # Return an unauthorized response

    conn = get_db_connection()  # Call the function to get the connection

    # Assuming 'path' is passed in the POST request body
    path = request.json.get('path')  # Retrieve path from JSON payload
    if not path:
        return "Path is required", 400  # Return a bad request response if path is missing

    try:
        indexer.indexer(path, conn)  # Call the indexer function
        return "Indexer run successfully", 200  # Return success message with status code
    except Exception as e:
        return f"An error occurred: {str(e)}", 500  # Handle any exceptions

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/global_search', methods=['POST'])
def global_search_route():
    conn = get_db_connection()
    query = request.form.get('query')
    category = request.form.get('category', None)
    if category == 'all':
        category = None
    
    results = search.global_search(query, settings.get_setting("known_nodes"), settings.get_setting("NODE_ID"), conn, "name", category)
    
    return render_template('results.html', query=query, category=category, results=results)

@app.route('/json/global_search', methods=['POST'])
def global_search_json():
    conn = get_db_connection()
    query = request.form.get('query')
    category = request.form.get('category', None)
    if category == 'all':
        category = None
    
    results = search.global_search(query, settings.get_setting("known_nodes"), settings.get_setting("NODE_ID"), conn, "name", category)
    
    return jsonify(results)

@app.route('/localsearch', methods=['POST'])
def localsearch_endpoint():
    conn = get_db_connection()
    data = request.get_json()

    search_term = data.get('search_term')
    search_type = data.get('search_type', 'name')
    category = data.get('category', None)

    logger.debug(f"Received request for local search: search_term={search_term}, search_type={search_type}, category={category}")

    matches = search.local_search(search_term, settings.get_setting("NODE_ID"), conn, search_type, category)

    return jsonify(matches), 200

@app.route('/md5_search/<md5_hash>')
def md5_search(md5_hash):
    conn = None
    try:
        conn = get_db_connection()  # Retrieve a connection from the pool
        results = search.global_search(md5_hash, settings.get_setting("known_nodes"), settings.get_setting("NODE_ID"), conn, "md5")
        return render_template('md5_results.html', md5_hash=md5_hash, results=results)
    except Exception as e:
        logger.error(f"Error during MD5 search: {e}")
        return "An error occurred during the search."
    finally:
        if conn:
            put_connection(conn)

@app.route('/json/md5_search/<md5_hash>')
def md5_search_json(md5_hash):
    conn = get_db_connection()
    return search.global_search(md5_hash, settings.get_setting("known_nodes"), settings.get_setting("NODE_ID"), conn, "md5")
    
@app.route('/download/<md5_hash>')
def download_file(md5_hash):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Select the file path based on the provided md5_hash
        select_query = """
        SELECT path FROM files WHERE md5_hash = %s;
        """
        cursor.execute(select_query, (md5_hash,))
        result = cursor.fetchone()
        
        if result:
            path = result[0]
            
            # Increment the download_count for the specific file
            update_query = """
            UPDATE files SET download_count = download_count + 1 WHERE md5_hash = %s;
            """
            cursor.execute(update_query, (md5_hash,))
            conn.commit()  # Commit the update
            
            return send_file(path)
        else:
            abort(404, description="File not found")
    
    finally:
        cursor.close()
        conn.close()

@app.route('/json/nodes')
def nodes():
    return jsonify(list(settings.get_setting("known_nodes")))

@app.route('/total_file_size', methods=['GET'])
def total_file_size():
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT SUM(file_size) FROM files;")
            result = cursor.fetchone()
            total_size = result[0] if result[0] is not None else 0
            return jsonify({'total_file_size': total_size})
    except psycopg2.Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

@app.route('/preview/<path:filename>', methods=['GET'])
def serve_preview(filename):
    """
    Serve the image preview for the specified filename.

    Args:
        filename (str): The name of the file whose preview is requested.

    Returns:
        Response: The preview image file if found, otherwise a 404 error.
    """
    try:
        # Get the shared directory from environment variable
        shared_directory = os.getenv("SHARED_DIRECTORY")
        hidden_directory = os.path.join(shared_directory, '.previews')

        # Construct the full path to the preview file
        preview_file_path = os.path.join(hidden_directory, f"{filename}")

        # Check if the file exists
        if not os.path.exists(preview_file_path):
            logger.warning(f"Preview file not found: {preview_file_path}")
            abort(404)  # Return a 404 error if the file does not exist

        # Serve the file
        return send_file(preview_file_path, mimetype='image/webp')
    except Exception as e:
        logger.error(f"Error serving preview for {filename}: {e}")
        abort(500)

@app.route('/announce', methods=['POST'])
def announce_endpoint():
    """
    Endpoint to handle node announcements.
    """
    data = request.json
    node_id = data.get("node_id")
    response_url = data.get("response_url")
    received_known_nodes = data.get("known_nodes", [])
    logger.debug(f"Handling Announcement From {node_id}")
    known_nodes = settings.get_setting("known_nodes")
    known_nodes.add(node_id)
    known_nodes.add(received_known_nodes)
    settings.set_setting("known_nodes", known_nodes)

    return jsonify({"known_nodes": list(known_nodes)}), 200

@app.route('/heartbeat', methods=['GET'])
def heartbeat():
    """
    Endpoint to respond to a heartbeat ping.
    
    Returns a JSON response indicating the node is alive.
    """
    return jsonify({"status": "alive", "message": "Heartbeat response from the node"}), 200

start_scheduler()
schedule_tasks()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv("NODE_PORT", 5000)))
