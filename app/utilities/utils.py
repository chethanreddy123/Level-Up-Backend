from passlib.context import CryptContext
from datetime import datetime
from app.database import User
import pytz

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Synchronous functions for hashing and verifying passwords (no change needed)
def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(password: str, hashed_password: str):
    return pwd_context.verify(password, hashed_password)

# Make the function async because User.find_one is asynchronous
def get_next_registration_id():
    current_year = datetime.now().year
    year_suffix = str(current_year)[-2:]

    # Retrieve the most recent registration ID asynchronously
    recent_user = User.find_one(
        {"registration_id": {"$exists": True}},
        sort=[("_id", -1)],
        projection={"registration_id": True}
    )

    if recent_user and 'registration_id' in recent_user:
        # Extract the year and sequence number from the most recent registration ID
        last_id = recent_user['registration_id']
        last_year = last_id[:2]
        last_seq_num = int(last_id[-4:])

        if last_year == year_suffix:
            # Increment the sequence number if the year matches
            next_seq_num = last_seq_num + 1
        else:
            # Reset the sequence number if the year doesn't match
            next_seq_num = 1
    else:
        # If no users exist, start from 1
        next_seq_num = 1

    # Format the next ID
    next_id = f"{year_suffix}LEVELUP{next_seq_num:04d}"
    return next_id

# Helper function to get the Indian Standard Time (no change needed)
def get_current_ist_time() -> str:
    utc_now = datetime.utcnow().replace(tzinfo=pytz.utc)
    ist_timezone = pytz.timezone('Asia/Kolkata')
    local_time = utc_now.astimezone(ist_timezone)
    formatted_date = local_time.strftime("%d-%m-%Y")  # Day-Month-Year format
    formatted_time = local_time.strftime("%I:%M %p")  # 12-hour clock format with AM/PM
    return formatted_date, formatted_time
