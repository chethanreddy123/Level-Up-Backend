from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING
from firebase_admin import credentials, initialize_app, storage
from config import settings
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB Connection
client = AsyncIOMotorClient(settings.DATABASE_URL, serverSelectionTimeoutMS=5000)

try:
    conn = client.server_info()
    logger.info(f"Connected to MongoDB {conn.get('version')}")
except Exception as e:
    logger.error(f"Unable to connect to MongoDB: {e}")

# Select the database
db = client[settings.MONGO_INITDB_DATABASE]

# Define collections for external use
User = db.users
Registrations = db.registrations
Customers = db.customers
Forms = db.forms
Exercises = db.exercises
WorkoutPlans = db.workout_plans
DietPlans = db.diet_plans
FoodItems = db.food_items
WorkoutandDietTracking = db.workout_and_diet_tracking

# Asynchronous Index Creation
async def create_indexes():
    try:
        await User.create_index([("email", ASCENDING)], unique=True)
        logger.info("Index created for 'users.email'")

        await Registrations.create_index([("email", ASCENDING)], unique=True)
        logger.info("Index created for 'registrations.email'")

        await Customers.create_index(
            [("name", ASCENDING), ("phone_no", ASCENDING), ("email", ASCENDING)],
            unique=True
        )
        logger.info("Compound index created for 'customers.name', 'phone_no', and 'email'")

        await Forms.create_index([("form_name", ASCENDING)], unique=True)
        logger.info("Index created for 'forms.form_name'")

        await Exercises.create_index([("exercise_name", ASCENDING)], unique=True)
        logger.info("Index created for 'exercises.exercise_name'")
    except Exception as e:
        logger.error(f"Failed to create indexes: {e}")

# Firebase Initialization
def initialize_firebase():
    try:
        cred = credentials.Certificate(settings.FIREBASE_CONFIG_PATH)
        initialize_app(cred, {
            'storageBucket': 'medigenai-94061.appspot.com'
        })
        logger.info("Connected to Firebase Storage successfully.")
    except Exception as e:
        logger.error(f"Failed to connect to Firebase: {e}")

# Initialize Firebase immediately
initialize_firebase()

# Function to initialize the database (exported for external use)
async def initialize_database():
    await create_indexes()
