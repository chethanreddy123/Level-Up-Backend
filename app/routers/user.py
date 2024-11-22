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
from app.utilities.firebase import upload_image_to_firebase
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


@router.get('/user', response_model=dict)
def get_user_details(user_id: str, Authorize: str = Depends(oauth2.require_user)):
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
            # Initialize the user info
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
            
            # Only include workout_plan if it exists
            if "workout_plan" in user:
                user_info["workout_plan"] = {
                    "workout_plan_id": str(user["workout_plan"].get("workout_plan_id", "")),
                    "workout_plan_name": user["workout_plan"].get("workout_plan_name", "Unknown")
                }

            # Only include diet_plan if it exists
            if "diet_plan" in user:
                user_info["diet_plan"] = {
                    "diet_plan_id": str(user["diet_plan"].get("diet_plan_id", "")),
                    "diet_plan_name": user["diet_plan"].get("diet_plan_name", "Unknown")
                }

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