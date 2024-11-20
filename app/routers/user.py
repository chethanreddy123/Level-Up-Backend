from fastapi import APIRouter, Depends, Query, HTTPException, status
from bson.objectid import ObjectId
from datetime import datetime, timedelta
from app.serializers.userSerializers import userResponseEntity, userRegistrationEntity, serialize_user, serialize_users
from app.utilities.error_handler import handle_errors
from app.database import Registrations
from app.utilities.email_services import send_email
from fastapi import APIRouter, Depends, HTTPException, status
from bson.objectid import ObjectId
from app.database import User
from app.schemas.user import UserResponse, UserResponseSchema
from app.utilities.error_handler import handle_errors
from typing import Optional

from app.database import User
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


@router.get('/users' , response_model=dict)
def get_users(
    filter_field: Optional[str] = Query(None, description="Field to filter users by"),
    filter_value: Optional[str] = Query(None, description="Value to filter users by"),
    page: int = Query(1, ge=1, description="Page number for pagination"),
    page_size: int = Query(10, ge=1, le=100, description="Number of users per page"),
    Authorize: str = Depends(oauth2.require_user)
):
    """
    Get all users based on filter criteria and pagination.
    This route is accessible by all users.
    """
    with handle_errors():
        # Construct the query filter
        query = {}
        if filter_field and filter_value:
            query[filter_field] = filter_value

        # Calculate pagination values
        skip = (page - 1) * page_size
        limit = page_size

        # Retrieve users with filtering and pagination
        users_cursor = User.find(query).skip(skip).limit(limit)
        users_list = list(users_cursor)

        # Check if no users were found
        if not users_list:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No users found")

        # Serialize users
        serialized_users = serialize_users(users_list)

        return {
            "status": "success",
            "page": page,
            "page_size": page_size,
            "total_users": User.count_documents(query),
            "users": serialized_users
        }
