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

# Create indexes for the forms collection
Forms = db.forms
# Create an index on form_name to make querying forms by name more efficient
Forms.create_index([("form_name", ASCENDING)], unique=True)

# Optionally, create a compound index on fields if needed
# Forms.create_index([("form_name", ASCENDING), ("fields.field_name", ASCENDING)])

Exercises = db.exercises

# Create indexes for the exercises collection   
# Exercises.create_index([("exercise_name", ASCENDING)], unique=True)

DietPlans = db.diet_plans

FoodItems = db.food_items