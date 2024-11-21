from pymongo import MongoClient
from firebase_admin import credentials, initialize_app, storage
from config import settings
import logging
from pymongo import ASCENDING

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB Connection
client = MongoClient(settings.DATABASE_URL, serverSelectionTimeoutMS=5000)

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
UserSlots = db.user_slots
Forms = db.forms
Exercises = db.exercises
WorkoutPlans = db.workout_plans
DietPlans = db.diet_plans
FoodItems = db.food_items
GymPlans = db.gym_plans
UserAttendance = db.user_attendance
WorkoutandDietTracking = db.workout_and_diet_tracking



# Firebase Initialization (Synchronous)
def initialize_firebase():
    try:
        cred = credentials.Certificate(settings.FIREBASE_CONFIG_PATH)
        initialize_app(cred, {
            'storageBucket': 'medigenai-94061.appspot.com'
        })
        logger.info("Connected to Firebase Storage successfully.")
    except Exception as e:
        logger.error(f"Failed to connect to Firebase: {e}")

# Function to initialize the database (synchronous)
def initialize_database():
    # Initialize Firebase (this is synchronous)
    initialize_firebase()
