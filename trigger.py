import indexer
import database
import sys

path = sys.argv[1]

conn = database.create_sqlite_connection()

indexer.indexer(path, conn)
