from fastapi import APIRouter, Depends, Query, HTTPException, status, UploadFile, File, Form
from bson.objectid import ObjectId
from datetime import datetime, timedelta
from app.serializers.userSerializers import userResponseEntity, userRegistrationEntity, serialize_user, serialize_users
from app.utilities.error_handler import handle_errors
from app.database import Registrations
from app.utilities.email_services import send_email
from fastapi import APIRouter, Depends, HTTPException, status
from bson.objectid import ObjectId
from app.database import User, WorkoutandDietTracking
from app.schemas.exercise import UploadWorkoutRequest, WorkoutEntry
from app.schemas.user import UserResponse, UserResponseSchema, UploadFoodRequest
from app.utilities.utils import get_current_ist_time
from app.utilities.firebase_upload import upload_image_to_firebase
# from app.utilities.error_handler import handle_errors
from typing import Optional
import pytz
from pymongo.errors import PyMongoError
# from app.database import User
from .. import  oauth2
from app.schemas import user

router = APIRouter()


@router.get('/me', response_model= user.UserResponse)
def get_me(user_id: str = Depends(oauth2.require_user)):
    with handle_errors():
        user = userResponseEntity(User.find_one({'_id': ObjectId(str(user_id))}))
        return {"status": "success", "user": user}



@router.post('/new_registration')
async def new_registration(payload: user.UserRegistration , user_id: str = Depends(oauth2.require_user)):
    with handle_errors():
        payload.set_created_timestamp()
        payload.set_updated_timestamp()

        result = Registrations.insert_one(payload.dict())
        new_user = Registrations.find_one({'_id': result.inserted_id})

        await send_email(
            sender_email="aioverflow.ml@gmail.com",
            sender_password="tvnt qtww egyq ktes", # Need to get it from config
            to_email=new_user['email'],
            cc_emails=None,
            subject="Welcome to Our Gym App!",
            message=f"Hi {new_user['name']},\n\nThank you for registering with our gym app!\n\nDownload the app and start your fitness journey.\n\nBest regards,\nThe Gym Team"
        )

        return {"status": "success", "user": userRegistrationEntity(new_user)}


@router.get('/user/{user_id}', response_model=dict)
def get_user_details(
    user_id: str,
    auth_user_id: str = Depends(oauth2.require_user)  # Ensure that the user is authenticated
):
    """
    Get user details based on the user_id as a query parameter.
    This route is accessible by all users.
    """
    with handle_errors():
        try:
            object_id = ObjectId(user_id)  # Convert to ObjectId for MongoDB query
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format")

        user = User.find_one({'_id': object_id})
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        # Serialize user and return the response
        serialized_user = serialize_user(user)
        return {"status": "success", "user": serialized_user}


@router.get('/users', response_model=dict)
def get_users(
    page: int = Query(1, ge=1, description="Page number for pagination"),
    items_per_page: int = Query(10, ge=1, le=100, description="Number of items per page"),
    workout_plan_name: Optional[str] = Query(None, description="Filter by workout plan name"),
    user_id: str = Depends(oauth2.require_user)  # Ensure that the user is authenticated
):
    """
    Retrieve a paginated list of users, optionally filtered by workout plan name.
    """
    with handle_errors():
        # Define the filter for the query
        query_filter = {}
        
        if workout_plan_name:
            query_filter["workout_plan.workout_plan_name"] = {"$regex": workout_plan_name, "$options": "i"}  # Case-insensitive match
        
        # Query the users based on pagination and optional filter
        skip = (page - 1) * items_per_page
        users_cursor = User.find(query_filter).skip(skip).limit(items_per_page)

        # Prepare the response data
        users_data = []
        for user in users_cursor:  # Synchronous iteration
            # Initialize the user info with basic fields
            user_info = {
                "user_id": str(user["_id"]),
                "name": user.get("name", ""),
                "email": user.get("email", ""),
                "photo": user.get("photo", ""),
                "role": user.get("role", ""),
                "phone_no": user.get("phone_no", ""),
                "registration_id": user.get("registration_id", ""),
                "verified": user.get("verified", False),
            }

            # Include workout_plan if it exists
            if "workout_plan" in user:
                user_info["workout_plan"] = {
                    "workout_plan_id": str(user["workout_plan"].get("workout_plan_id", "")),
                    "workout_plan_name": user["workout_plan"].get("workout_plan_name", "Unknown")
                }

            # Include diet_plan if it exists
            if "diet_plan" in user:
                user_info["diet_plan"] = {
                    "diet_plan_id": str(user["diet_plan"].get("diet_plan_id", "")),
                    "diet_plan_name": user["diet_plan"].get("diet_plan_name", "Unknown")
                }

            # Include additional fields if they exist
            if "address" in user:
                user_info["address"] = user.get("address", "")
            if "slot_preference" in user:
                user_info["slot_preference"] = user.get("slot_preference", "")
            if "previous_gym" in user:
                user_info["previous_gym"] = user.get("previous_gym", "")

            # Add the constructed user_info to the list
            users_data.append(user_info)

        if not users_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No users found matching the criteria."
            )

        # Get the total number of users that match the query filter
        total_users = User.count_documents(query_filter)

        # Prepare the final response with pagination and users data
        return {
            "status": "success",
            "page": page,
            "entries_per_page": items_per_page,
            "total_users": total_users,
            "users": users_data
        }
    
@router.post('/user/upload_weight', status_code=status.HTTP_201_CREATED)
async def upload_weight(
    user_id: str = Depends(oauth2.require_user),  # Ensure the user is authenticated
    weight: float = Form(...),  # Required: User's weight (float)
    image: Optional[UploadFile] = File(None)  # Optional: Image file for weight tracking (nullable)
):
    """
    Upload user's weight and optional image for the current week.
    Ensures that only one weight entry can be made per week.
    """
    with handle_errors():
        # Get the current date in DD-MM-YYYY format
        current_date = datetime.utcnow().strftime("%d-%m-%Y")
        
        # Fetch the user from the database
        user = User.find_one({"_id": ObjectId(user_id)})
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )
        
        # Check if the user already has a weight entry for the current week
        current_week = datetime.utcnow().isocalendar()[1]  # Week number of the year
        for entry in user.get('weight_tracking', []):
            # If there's already an entry for the current week, raise a warning
            entry_date = datetime.strptime(entry['date'], "%d-%m-%Y")
            if entry_date.isocalendar()[1] == current_week:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User has already uploaded weight for this week"
                )

        # Prepare the new weight entry
        new_entry = {
            "date": current_date,
            "weight": weight,
            "photo": None  # Temporarily keep photo as None since Firebase is not working
        }

        if image:
            # If image is provided, handle the file upload (firebase code will go here)
            # Since firebase is not working, we are not saving the image for now
            pass

        # Add the new entry to the user's weight_tracking field
        result = User.update_one(
            {"_id": ObjectId(user_id)},
            {"$push": {"weight_tracking": new_entry}}  # Push new weight entry into the weight_tracking array
        )

        if result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload weight"
            )

        # Return success message
        return {
            "status": "success",
            "message": "Weight uploaded successfully."
        }
    
@router.get('/user/track_weight/{user_id}', status_code=status.HTTP_200_OK)
async def get_weight_details(
    user_id: str,  # User ID as a path parameter
    auth_user_id: str = Depends(oauth2.require_user)  # Ensure the user is authenticated
):
    """
    Fetch the weight tracking details for a specific user by user_id.
    """
    with handle_errors():
        # Fetch the user from the database
        user = User.find_one({"_id": ObjectId(user_id)})
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )
        
        # Fetch weight tracking details
        weight_tracking = user.get("weight_tracking", [])

        if not weight_tracking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No weight tracking details found for this user"
            )
        
        # Return the weight tracking details
        return {
            "status": "success",
            "user_id": user_id,
            "weight_tracking": weight_tracking
        }