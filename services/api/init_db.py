from database import get_connection
from models import CREATE_JOBS_TABLE

connection = get_connection()

cursor = connection.cursor()

cursor.execute(CREATE_JOBS_TABLE)

connection.commit()

cursor.close()
connection.close()

print(
    "Database initialized successfully",
    flush=True
)