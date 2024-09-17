import os
import hashlib
import json
import re

def _calculate_md5(file_path):
    """Calculate the MD5 hash of a given file."""
    md5_hash = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()

def _detect_category(file_path, file_extension):
    """Detect the file's category based on its path or file extension."""
    categories = {
        "movie": ["movie", "movies"],
        "tv show": ["tv", "show", "shows", "series"],
        "book": ["book", "books"],
        "audiobook": ["audiobook", "audiobooks"],
    }
    
    # First, check the path for keywords
    for category, keywords in categories.items():
        if any(keyword in file_path.lower() for keyword in keywords):
            return category

    # If no match based on path, use file extension for categorization
    extension_categories = {
        "audio": [".mp3", ".wav", ".flac"],
        "video": [".mp4", ".avi", ".mkv", ".mov"],
        "picture": [".jpg", ".jpeg", ".png", ".gif", ".bmp"],
        "plaintext": [".txt", ".md", ".log"],
        "document": [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"],
    }

    for category, extensions in extension_categories.items():
        if file_extension.lower() in extensions:
            return category

    # If no other matches, categorize as "other"
    return "other"

def _load_exclusion_patterns(directory):
    """Load the .exclude_patterns file if it exists in the directory."""
    exclude_file_path = os.path.join(directory, ".exclude_patterns")
    if os.path.exists(exclude_file_path):
        with open(exclude_file_path, "r") as f:
            # Return the compiled regex patterns from the file
            return [re.compile(line.strip()) for line in f.readlines() if line.strip()]
    return []

def _should_exclude(file_path, exclude_patterns):
    """Check if a file should be excluded based on the regex patterns."""
    for pattern in exclude_patterns:
        if pattern.search(file_path):
            return True
    return False

def _index_directory(directory, exclude_patterns):
    """Index the files in the given directory and its subdirectories."""
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

            # Calculate the MD5 hash of the file
            file_hash = _calculate_md5(file_path)

            # Detect the file category
            file_category = _detect_category(file_path, file_extension)

            # Create the file entry
            file_entry = {
                "file_name": file_name,
                "path": file_path,
                "md5_hash": file_hash,
                "file_size": file_size,
                "category": file_category,
            }

            # Add to the index
            file_index.append(file_entry)

    return file_index

def indexer(directory, output_path):
    """
    Index the files in the given directory, exclude files based on .exclude_patterns, 
    and write the index to the specified output path.
    
    Args:
        directory (str): The directory to index.
        output_path (str): The path where the index.json will be written.
    """
    # Load exclusion patterns from the parent directory
    exclude_patterns = _load_exclusion_patterns(directory)

    # Index the directory
    file_index = _index_directory(directory, exclude_patterns)

    # Write the index to the output path
    with open(output_path, "w") as f:
        json.dump(file_index, f, indent=4)

    print(f"Indexing complete. Index written to {output_path}.")
