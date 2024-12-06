import os
from pymongo import MongoClient
from config import settings
from google.cloud import storage
from google.oauth2 import service_account
import logging
from pymongo import ASCENDING


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


client = MongoClient(settings.DATABASE_URL, serverSelectionTimeoutMS=5000)

try:
    conn = client.server_info()
    logger.info(f"Connected to MongoDB {conn.get('version')}")
except Exception as e:
    logger.error(f"Unable to connect to MongoDB: {e}")

# Select the database
db = client[settings.MONGO_INITDB_DATABASE]

# Collections
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


## User INDEX    

# Create index for User database for faster accessing
User.create_index([('role', 1)])
# Create indexes for 'created_at' to speed up sorting 
User.create_index([('created_at', 1)])  # Sorting by created_at (ascending)


# Set the path to your service account key file directly here
SERVICE_ACCOUNT_KEY_PATH = "serviceAccountKey.json"  # Update this to your actual path
GCS_BUCKET_NAME = "staging.medigenai-94061.appspot.com"  # Update with your actual bucket name


# Initialize Google Cloud Storage Client
def initialize_google_cloud():
    try:
        # Load credentials from the service account key file
        credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_KEY_PATH)

        # Initialize the Google Cloud Storage client with the credentials
        client = storage.Client(credentials=credentials)
        
        # Get the bucket using the bucket name
        bucket = client.get_bucket(GCS_BUCKET_NAME)
        
        logger.info("Successfully connected to Google Cloud Storage.")
        return bucket
    except Exception as e:
        logger.error(f"Failed to connect to Google Cloud Storage: {e}")
        return None

# Function to initialize the database (synchronous)
def initialize_database():
    # Initialize Firebase (this is synchronous)
    initialize_google_cloud()
