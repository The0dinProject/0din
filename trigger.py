import indexer
import database
import sys

path = sys.argv[1]

conn = database.get_db_connection()

indexer.indexer(path, conn)
