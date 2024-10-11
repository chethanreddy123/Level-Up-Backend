from pymongo import MongoClient, ASCENDING
from config import settings

# Connect to MongoDB
client = MongoClient(
    settings.DATABASE_URL, serverSelectionTimeoutMS=5000
)

try:
    conn = client.server_info()
    print(f'Connected to MongoDB {conn.get("version")}')
except Exception as e:
    print(f"Unable to connect to the MongoDB server: {e}")

# Select the database
db = client[settings.MONGO_INITDB_DATABASE]

# Create indexes for the users collection
User = db.users
User.create_index([("email", ASCENDING)], unique=True)

# Create indexes for the registrations collection
Registrations = db.registrations
Registrations.create_index([("email", ASCENDING)], unique=True)

# Create indexes for the customers collection
Customers = db.customers
Customers.create_index([("name", ASCENDING), ("phone_no", ASCENDING), ("email", ASCENDING)], unique=True)
