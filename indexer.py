import os
import hashlib
import re
import logging
import colorlog
from database import init_db

# Configure logger with colorlog
logger = colorlog.getLogger(__name__)
handler = colorlog.StreamHandler()
handler.setFormatter(
    colorlog.ColoredFormatter(
        "%(log_color)s%(levelname)s:%(name)s:%(message)s",
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "bold_red",
        },
    )
)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

def _calculate_md5(file_path, connection):
    """Calculate or reuse the MD5 hash of a given file."""
    logger.debug(f"Checking MD5 for {file_path}")

    with connection.cursor() as cursor:
        cursor.execute("SELECT md5_hash FROM files WHERE path = %s;", (file_path,))
        result = cursor.fetchone()
        
    if result:
        logger.info(f"Reusing existing MD5 for {file_path}: {result[0]}")
        return result[0]
    
    logger.debug(f"Calculating MD5 for {file_path}")
    md5_hash = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5_hash.update(chunk)
        return md5_hash.hexdigest()
    except Exception as e:
        logger.error(f"Error calculating MD5 for {file_path}: {e}")
        return None

def _detect_category(file_path, file_extension):
    """Detect the file's category based on its path or file extension."""
    logger.debug(f"Detecting category for {file_path}")

    categories = {
        "movie": ["movie", "movies", "film", "cinema", "flick"],
        "tv show": ["tv", "show", "shows", "series", "episode", "season"],
        "book": ["book", "books", "novel", "textbook", "literature"],
        "audiobook": ["audiobook", "audiobooks", "audio book", "narration"],
        "podcast": ["podcast", "podcasts", "episode", "broadcast"],
        "music": ["music", "album", "track", "song"],
        "image": ["image", "picture", "photo", "snapshot", "gallery"],
        "ebook": ["ebook", "e-book", "electronic book", "kindle", "pdf"],
        "compressed": ["zip", "archive", "compressed", "rar", "tar"],
    }

    for category, keywords in categories.items():
        if any(keyword in file_path.lower() for keyword in keywords):
            logger.info(f"Category detected from path: {category}")
            return category

    extension_categories = {
        "audio": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"],
        "video": [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv"],
        "image": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".svg"],
        "plaintext": [".txt", ".md", ".log", ".csv", ".json"],
        "document": [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".odt"],
        "ebook": [".epub", ".mobi", ".azw"],
        "compressed": [".zip", ".rar", ".tar", ".gz", ".7z"],
    }

    for category, extensions in extension_categories.items():
        if file_extension.lower() in extensions:
            logger.info(f"Category detected from file extension: {category}")
            return category

    logger.warning(f"No category matched for {file_path}. Categorized as 'other'")
    return "other"

def _load_exclusion_patterns(directory):
    """Load the .exclude_patterns file if it exists in the directory."""
    if directory is None:
        raise ValueError("Directory cannot be None. Please check your settings.")
    logger.debug(f"Loading exclusion patterns from {directory}")
    exclude_file_path = os.path.join(directory, ".exclude_patterns")
    if os.path.exists(exclude_file_path):
        try:
            with open(exclude_file_path, "r") as f:
                logger.info(f"Exclusion patterns loaded from {exclude_file_path}")
                return [re.compile(line.strip()) for line in f.readlines() if line.strip()]
        except Exception as e:
            logger.error(f"Error loading exclusion patterns: {e}")
    return []

def _should_exclude(file_path, exclude_patterns):
    """Check if a file should be excluded based on the regex patterns."""
    for pattern in exclude_patterns:
        if pattern.search(file_path):
            logger.info(f"File {file_path} excluded by pattern {pattern.pattern}")
            return True
    return False
    
def _index_directory(directory, exclude_patterns, connection):
    """Index the files in the given directory and its subdirectories."""
    logger.debug(f"Indexing directory: {directory}")
    file_index = []

    for root, _, files in os.walk(directory):
        for file_name in files:
            if file_name == ".exclude_patterns":
                continue  # Skip the .exclude_patterns file itself

            file_path = os.path.join(root, file_name)

            # Skip files that match the exclusion patterns
            if _should_exclude(file_path, exclude_patterns):
                continue

            # Get file size and extension
            file_size = os.path.getsize(file_path)
            file_extension = os.path.splitext(file_name)[1]

            # Check if the file's MD5 hash already exists in the database
            file_hash = _calculate_md5(file_path, connection)
            if file_hash is None:
                logger.error(f"Skipping {file_path} due to MD5 error")
                continue

            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM files WHERE md5_hash = %s;", (file_hash,))
                existing_file = cursor.fetchone()

            if existing_file:
                logger.info(f"File already indexed: {file_name} (MD5: {file_hash})")
                continue  # Skip recalculation if the hash exists

            # Detect the file category
            file_category = _detect_category(file_path, file_extension)

            # Insert the new file entry into the database
            with connection.cursor() as cursor:
                cursor.execute("""
                INSERT INTO files (file_name, path, md5_hash, file_size, category)
                VALUES (%s, %s, %s, %s, %s);
                """, (file_name, file_path, file_hash, file_size, file_category))
                connection.commit()

            # Add to the index
            file_index.append({
                "file_name": file_name,
                "path": file_path,
                "md5_hash": file_hash,
                "file_size": file_size,
                "category": file_category,
            })
            logger.info(f"Indexed {file_name} with category {file_category}")

    return file_index

def indexer(directory, connection):
    """
    Index the files in the given directory, exclude files based on .exclude_patterns,
    and store the index in a PostgreSQL database.
    
    Args:
        directory (str): The directory to index.
    """
    logger.debug(f"Starting indexing for directory {directory}")
    


    # Create the database table if it doesn't exist
    init_db()

    # Load exclusion patterns from the parent directory
    exclude_patterns = _load_exclusion_patterns(directory)

    # Index the directory
    file_index = _index_directory(directory, exclude_patterns, connection)

    logger.info(f"Indexing complete. {len(file_index)} files indexed.")

    # Close the database connection
    connection.close()
    logger.debug("Database connection closed.")

# Example usage
# indexer("/path/to/directory")

