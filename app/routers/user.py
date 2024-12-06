from fastapi import APIRouter, Depends, Query, HTTPException, status, UploadFile, File, Form
from bson.objectid import ObjectId
from datetime import datetime, timedelta

from fastapi.encoders import jsonable_encoder
import loguru
from app.serializers.userSerializers import userResponseEntity, userRegistrationEntity, serialize_user, serialize_users
from app.utilities.error_handler import handle_errors
from app.database import Registrations, WorkoutPlans, DietPlans, Exercises, FoodItems
from app.utilities.email_services import send_email
from fastapi import APIRouter, Depends, HTTPException, status
from bson.objectid import ObjectId
from app.database import User, WorkoutandDietTracking
from app.schemas.exercise import UploadWorkoutRequest, WorkoutEntry
from app.schemas.user import UserResponse, UserResponseSchema, UploadFoodRequest
from app.utilities.utils import convert_object_ids, get_current_ist_time
from app.utilities.google_cloud_upload import upload_image_to_gcs, upload_profile_image, upload_weight_image
from typing import Optional
import json
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


# Route to update user details
@router.put('/user/update_by_self', status_code=200)
async def update_user_details(
    user_id: str = Depends(oauth2.require_user),  # Get authenticated user ID
    name: Optional[str] = Form(None),  # Optional: New name
    email: Optional[str] = Form(None),  # Optional: New email
    phone_no: Optional[str] = Form(None),  # Optional: New phone number
    address: Optional[str] = Form(None),  # Optional: New address
    file: Optional[UploadFile] = File(None)  # Optional: New profile photo
):
    """
    Update the details of the currently authenticated user.
    Allows changing name, email, phone number, address, and uploading a new profile photo (optional).
    """
    with handle_errors():
        # Fetch the user from the database
        user = User.find_one({"_id": ObjectId(user_id)})
        
        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        # Prepare updated user data
        updated_data = {}

        # Update fields if provided
        if name:
            updated_data["name"] = name
        if email:
            updated_data["email"] = email.lower()  # Make email lowercase
        if phone_no:
            updated_data["phone_no"] = phone_no
        if address:
            updated_data["address"] = address

        # Handle photo upload if provided
        if file:
            try:
                # Create a unique file name for the photo based on user ID
                file_name = f"profile"
                photo_url = upload_profile_image(file, str(user["_id"]), file_name)  # Function to upload image
                updated_data["photo"] = photo_url  # Save the URL of the uploaded image
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail="Error uploading profile photo"
                )

        # Update user details in the database
        if updated_data:
            result = User.update_one(
                {"_id": ObjectId(user_id)},  # Find the user by ID
                {"$set": updated_data}  # Update the fields
            )

            if result.modified_count == 0:
                raise HTTPException(
                    status_code=400,
                    detail="No changes were made"
                )

        # Return success response
        return {
            "status": "success",
            "message": "User details updated successfully",
            "updated_data": updated_data
        }

# @router.post('/new_registration')
# async def new_registration(payload: user.UserRegistration , user_id: str = Depends(oauth2.require_user)):
#     with handle_errors():
#         payload.set_created_timestamp()
#         payload.set_updated_timestamp()

#         result = Registrations.insert_one(payload.dict())
#         new_user = Registrations.find_one({'_id': result.inserted_id})

#          send_email(
#             sender_email="aioverflow.ml@gmail.com",
#             sender_password="tvnt qtww egyq ktes", # Need to get it from config
#             to_email=new_user['email'],
#             cc_emails=None,
#             subject="Welcome to Our Gym App!",
#             message=f"Hi {new_user['name']},\n\nThank you for registering with our gym app!\n\nDownload the app and start your fitness journey.\n\nBest regards,\nThe Gym Team"
#         )

#         return {"status": "success", "user": userRegistrationEntity(new_user)}


# Search Users by their name
@router.get('/user/search_users', response_model=dict)
def search_users(
    query: str = Query(..., description="Search query to match in user names"),
    page: int = Query(1, ge=1, description="Page number for pagination"),
    items_per_page: int = Query(10, ge=1, le=100, description="Number of items per page"),
    user_id: str = Depends(oauth2.require_user)  # Ensure that the user is authenticated
):
    """
    Search for users by name, with pagination.
    """
    with handle_errors():
        skip = (page - 1) * items_per_page
        
        # Use MongoDB's regex feature to search for users whose name contains the query string (case-insensitive)
        users_cursor = User.find(
            {"name": {"$regex": query, "$options": "i"}}  # Case-insensitive search
        ).skip(skip).limit(items_per_page).sort("created_at", 1)  # Sort by creation date (ascending)

        # Prepare the response data
        users_data = []
        for user in users_cursor:  # Synchronous iteration
            user_info = {
                "user_id": str(user["_id"]),
                "name": user.get("name", ""),
                "email": user.get("email", ""),
                "photo": user.get("photo", ""),
                "role": user.get("role", ""),
                "phone_no": user.get("phone_no", ""),
                "registration_id": user.get("registration_id", ""),
                "verified": user.get("verified", False),
                "created_at": user.get("created_at")
            }
            users_data.append(user_info)

        if not users_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No users found matching the search query."
            )

        # Get the total number of users matching the search query
        total_users = User.count_documents({"name": {"$regex": query, "$options": "i"}})

        # Prepare the final response with pagination and users data
        return {
            "status": "success",
            "page": page,
            "entries_per_page": items_per_page,
            "total_users": total_users,
            "users": users_data
        }


@router.get('/user/{user_id}', response_model=dict)
async def get_user_details(
    user_id: str,
    auth_user_id: str = Depends(oauth2.require_user)
):
    """
    Get user details based on the user_id as a query parameter.
    This route is accessible by all users.
    """
    try:
        object_id = ObjectId(user_id)  
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format")

    # Fetch user details
    user =  User.find_one({'_id': object_id})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Fetch the workout plan and expand exercise details
    workout_plan = None
    if 'workout_plan' in user:
        workout_plan_id = user['workout_plan'].get('workout_plan_id')
        if workout_plan_id:
            workout_plan =  WorkoutPlans.find_one({'_id': ObjectId(workout_plan_id)})
            if workout_plan:
                # Fetch exercise details
                for day, exercises in workout_plan.get('schedule', {}).items():
                    workout_plan['schedule'][day] = [
                         Exercises.find_one({'_id': ObjectId(ex_id)}) for ex_id in exercises
                    ]
                workout_plan = convert_object_ids(workout_plan)

    # Fetch the diet plan and expand food item details
    diet_plan = None
    if 'diet_plan' in user:
        diet_plan_id = user['diet_plan'].get('diet_plan_id')
        if diet_plan_id:
            diet_plan =  DietPlans.find_one({'_id': ObjectId(diet_plan_id)})
            if diet_plan:
                # Expand menu items in menu_plan
                for time_slot, details in diet_plan.get('menu_plan', {}).get('timings', {}).items():
                    details["menu"] = [
                         FoodItems.find_one({'_id': ObjectId(item_id)}) for item_id in details["menu"]
                    ]

                # Expand menu items in one_day_detox_plan
                for time_slot, details in diet_plan.get('one_day_detox_plan', {}).items():
                    details["menu"] = [
                         FoodItems.find_one({'_id': ObjectId(item_id)}) for item_id in details["menu"]
                    ]
                diet_plan = convert_object_ids(diet_plan)

    # Prepare serialized user data
    serialized_user = {
        "name": user.get("name", ""),
        "email": user.get("email", ""),
        "photo": user.get("photo", ""),
        "role": user.get("role", ""),
        "phone_no": user.get("phone_no", ""),
        "created_at": user.get("created_at"),
        "updated_at": user.get("updated_at"),
        "registration_id": user.get("registration_id", ""),
        "verified": user.get("verified", False),
        "workout_plan": {
            "start_date": user.get("workout_plan", {}).get("start_date"),
            "end_date": user.get("workout_plan", {}).get("end_date"),
            "current_weight": user.get("workout_plan", {}).get("current_weight"),
            "end_weight": user.get("workout_plan", {}).get("end_weight"),
            "workout_plan_details": workout_plan if workout_plan else None
        },
        "diet_plan": diet_plan if diet_plan else None,
        'weight_tracking':user.get("weight_tracking", {}),
        "screening": user.get("screening", {}),
        "subscription_plan": user.get("subscription_plan", {}),
        "id": str(user["_id"])  # Convert ObjectId to string here
    }

    return jsonable_encoder({"status": "success", "user": serialized_user})


@router.get('/users', response_model=dict)
def get_users(
    page: int = Query(1, ge=1, description="Page number for pagination"),
    items_per_page: int = Query(10, ge=1, le=100, description="Number of items per page"),
    filters: Optional[str] = Query(None, description="Filters for ordering and role, e.g., {'order': 'asc', 'role': 'ADMIN'}"),
    user_id: str = Depends(oauth2.require_user)  # Ensure that the user is authenticated
):
    """
    Retrieve a paginated list of users, optionally filtered by order and role.
    """
    with handle_errors():
        query_filter = {}
        sort_order = 1  # Default ascending order
        
        # Parse the filters JSON string into a dictionary if it's provided
        if filters:
            try:
                filters_dict = json.loads(filters)
                
                # Apply role filter if provided
                if "role" in filters_dict:
                    query_filter["role"] = filters_dict["role"]
                
                # Apply order filter if provided
                if "order" in filters_dict:
                    if filters_dict["order"] == "desc":
                        sort_order = -1  # Descending order
                    elif filters_dict["order"] == "asc":
                        sort_order = 1  # Ascending order
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid filters format. Filters must be a valid JSON string."
                )

        # Query the users based on pagination, filter by role, and order by created_at
        skip = (page - 1) * items_per_page
        users_cursor = User.find(query_filter).skip(skip).limit(items_per_page).sort("created_at", sort_order)

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
                "created_at": user.get("created_at")
            }

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
    

@router.delete('/user/delete_user/{user_id}', status_code=200)
async def delete_user(
    user_id: str,  
    auth_user_id: str = Depends(oauth2.require_admin)  
):
    """
    Delete a user from the database. This is an admin-only operation.
    """
    with handle_errors():
        # Ensure the user exists before trying to delete
        user = User.find_one({"_id": ObjectId(user_id)})
        
        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        # Perform the deletion
        result = User.delete_one({"_id": ObjectId(user_id)})
        
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=500,
                detail="Failed to delete user"
            )

        # Return success message
        return {
            "status": "success",
            "message": f"User with ID {user_id} deleted successfully"
        }

    
@router.post('/user/upload_weight', status_code=status.HTTP_201_CREATED)
async def upload_weight(
    user_id: str = Depends(oauth2.require_user), 
    weight: float = Form(...), 
    image: Optional[UploadFile] = File(None) 
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
            # If image is provided, handle the file upload
            try:
                file_name = f"weight_{current_date}"  # You can use a different naming convention if needed
                photo_url = upload_weight_image(image, user_id, file_name)  # Upload the image
                new_entry["photo"] = photo_url  # Store the photo URL in the new entry
            except Exception as e:
                loguru.logger.error(f"Error uploading weight image for user '{user_id}': {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to upload weight image"
                )

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