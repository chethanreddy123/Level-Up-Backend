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


# @router.post('/upload_workout_task')
# async def upload_workout_task(payload: UploadWorkoutRequest, user_id: str = Depends(oauth2.require_user)):
#     """
#     Uploads a workout task and diet log for a user. Both workout and diet logs are stored under the same date.
#     """
#     with handle_errors():
#         user_id = str(user_id)

#         # Get the formatted date and time in IST
#         formatted_date, formatted_time = get_current_ist_time()

#         # Extract workout details from the payload
#         workout_name = payload.workout.workout_name

#         # Get today's workout and diet data for the user from the database
#         existing_record = WorkoutandDietTracking.find_one({"_id": user_id, formatted_date: {"$exists": True}})

#         # If no record exists for this date, create a new record for the user
#         if not existing_record:
#             new_record = {
#                 "_id": user_id,
#                 formatted_date: {
#                     "workout_logs": [
#                         {
#                             "workout_name": payload.workout.workout_name,
#                             "sets_assigned": payload.workout.sets_assigned,
#                             "sets_done": payload.workout.sets_done,
#                             "reps_assigned": payload.workout.reps_assigned,
#                             "reps_done": payload.workout.reps_done,
#                             "load_assigned": payload.workout.load_assigned,
#                             "load_done": payload.workout.load_done,
#                             "performance": payload.workout.performance,
#                             "updated_at": formatted_time  # Track the time of the workout log
#                         }
#                     ],
#                     "diet_logs": []  # Initially empty diet logs
#                 }
#             }

#             # Insert the new workout and diet data into MongoDB
#             WorkoutandDietTracking.insert_one(new_record)

#             return {
#                 "status": "success",
#                 "message": f"Workout data for {workout_name} uploaded successfully for {formatted_date}!"
#             }

#         else:
#             # If the record for the date already exists, check if the workout is already recorded
#             existing_workouts = existing_record.get(formatted_date, {}).get("workout_logs", [])
#             existing_diet_logs = existing_record.get(formatted_date, {}).get("diet_logs", [])

#             # Check if the workout already exists
#             if any(workout["workout_name"] == workout_name for workout in existing_workouts):
#                 return {
#                     "status_code": 409,
#                     "message": f"The data for {workout_name} has already been uploaded today."
#                 }

#             # Add the workout log to the existing record
#             new_workout_log = {
#                 "workout_name": workout_name,
#                 "sets_assigned": payload.workout.sets_assigned,
#                 "sets_done": payload.workout.sets_done,
#                 "reps_assigned": payload.workout.reps_assigned,
#                 "reps_done": payload.workout.reps_done,
#                 "load_assigned": payload.workout.load_assigned,
#                 "load_done": payload.workout.load_done,
#                 "performance": payload.workout.performance,
#                 "updated_at": formatted_time
#             }

#             # Update the workout logs
#             existing_record[formatted_date]["workout_logs"].append(new_workout_log)

#             # Update the existing record in MongoDB
#             WorkoutandDietTracking.update_one(
#                 {"_id": user_id},
#                 {"$set": existing_record},
#                 upsert=True
#             )

#             return {
#                 "status": "success",
#                 "message": f"Workout data for {workout_name} uploaded successfully for {formatted_date}!"
#             }

# @router.post('/upload_diet_logs')
# async def upload_diet_logs(
#     food_name: str = Form(...),  # food_name is a required form field
#     quantity: float = Form(...),  # quantity is a required form field (as a float)
#     units: Optional[str] = Form(None),  # units is an optional form field
#     image: Optional[UploadFile] = File(None),  # image is an optional file upload
#     user_id: str = Depends(oauth2.require_user)  # assuming authentication dependency
# ):
#     """
#     Uploads a diet log (food intake) for a user, storing the food information along with the uploaded image.
#     If the same food has already been uploaded for the given date, returns an error.
#     """
#     with handle_errors():
#         user_id = str(user_id)

#         # Get the formatted date and time in IST
#         formatted_date, formatted_time = get_current_ist_time()


#         # Check if the food_name already exists for the given date in MongoDB
#         existing_record = WorkoutandDietTracking.find_one(
#             {"_id": user_id, f"{formatted_date}.diet_logs.food_name": food_name}
#         )

#         if existing_record:
#             # If the food_name already exists for the date, raise an error
#             raise HTTPException(
#                 status_code=400,
#                 detail=f"The Info about {food_name.title()} has already been uploaded for {formatted_date}."
#             )

#                 # Initialize image_url variable to None
#         image_url = None
        
#         if image:
            
#             image_url = upload_image_to_firebase(file=image, user_id=user_id, food_name=food_name)

#         # If no existing record for the food_name, proceed to create a new record
#         new_diet_log = {
#             "food_name": food_name,
#             "quantity": quantity,
#             "units": units,
#             "image_url": image_url,  # Can be None or a placeholder
#             "uploaded_time": formatted_time
#         }

#         # Check if a record for this date already exists
#         existing_record = WorkoutandDietTracking.find_one({"_id": user_id, formatted_date: {"$exists": True}})

#         if not existing_record:
#             # If no record exists for this date, create a new record for the user
#             new_record = {
#                 "_id": user_id,
#                 formatted_date: {
#                     "workout_logs": [],  # Initially empty workout logs
#                     "diet_logs": [new_diet_log]
#                 }
#             }

#             try:
#                 # Insert the new diet data into MongoDB
#                 WorkoutandDietTracking.insert_one(new_record)
#             except PyMongoError as e:
#                 raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

#             return {
#                 "status": "success",
#                 "message": f"Diet log for {food_name.title()} uploaded successfully on {formatted_date}!"
#             }

#         else:
#             # If the record for the date already exists, add the new diet log
#             existing_record[formatted_date]["diet_logs"].append(new_diet_log)

#             try:
#                 # Update the existing record in MongoDB
#                 WorkoutandDietTracking.update_one(
#                     {"_id": user_id},
#                     {"$set": existing_record},
#                     upsert=True
#                 )
#             except PyMongoError as e:
#                 raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

#             return {
#                 "status": "success",
#                 "message": f"Diet log for {food_name.title()} uploaded successfully on {formatted_date}!"
#             }