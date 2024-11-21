from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from bson.objectid import ObjectId
from datetime import datetime
from typing import List, Optional
from loguru import logger
import logging
from app.schemas.exercise import UploadWorkoutRequest, WorkoutEntry
from app.utilities.utils import get_current_ist_time
from app.database import User, WorkoutandDietTracking, Exercises, WorkoutPlans
from app.schemas.exercise import  ExerciseCreateSchema, ExerciseUpdateSchema, ExerciseResponseSchema, GetExercises
from app.schemas.workout_plan import WorkoutPlanDetails, UpdateWorkoutPlanDetails, ModifyWorkoutsUserResponse
from app.utilities.error_handler import handle_errors
from motor.motor_asyncio import AsyncIOMotorClient
from .. import oauth2

# Initialize the router
router = APIRouter()

@router.post('/workout-plans', status_code=status.HTTP_201_CREATED)
async def add_workout_plan(
    payload: WorkoutPlanDetails = Body(...),
    user_id: str = Query(..., description="Customer ID whose workout plan will be added"),
    auth_user_id: str = Depends(oauth2.require_user)
):
    """
    Add a new workout plan for the customer (manual customer_id), including start date, end date and weight goals.
    """
    with handle_errors():
        logger.info(f"Adding workout plan for customer ID: {user_id} by trainer ID: {auth_user_id}")

        # Extract and validate customer_id
        try:
            customer_id = ObjectId(user_id)
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid customer ID format.")

        # Check if the customer exists in the database
        existing_customer =  User.find_one({"_id": customer_id})
        if not existing_customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found"
            )

        # Check if a workout plan is already assigned
        assigned_workout_plan = existing_customer.get("workout_plan")
        if assigned_workout_plan:
            assigned_workout_plan_id = assigned_workout_plan.get("workout_plan_id")

            # Compare the IDs properly
            if assigned_workout_plan_id == payload.workout_plan_id:
                # Fetch the workout plan name from the WorkoutPlans collection
                assigned_plan =  WorkoutPlans.find_one({"_id": ObjectId(assigned_workout_plan_id)})
                assigned_plan_name = assigned_plan.get("workout_plan_name", "Unknown") if assigned_plan else "Unknown"
                
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"The workout plan '{assigned_plan_name}' is already assigned to the user."
                )

        # Prepare the workout plan details
        workout_plan_data = payload.dict()
        workout_plan_data["start_date"] = workout_plan_data["start_date"].isoformat()
        workout_plan_data["end_date"] = workout_plan_data["end_date"].isoformat()

        # Add timestamps
        formatted_date, formatted_time = get_current_ist_time()
        datetime_str = f"{formatted_date} {formatted_time}"
        workout_plan_data["created_at"] = datetime_str
        workout_plan_data["updated_at"] = datetime_str

        # Assign the workout plan to the customer
        update_result =  User.update_one(
            {"_id": customer_id},
            {"$set": {"workout_plan": workout_plan_data}}
        )

        if update_result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add workout plan."
            )

        # Return the response with the workout plan details
        return ModifyWorkoutsUserResponse(
            user_id=user_id,
            message="Workout plan details added successfully",
            workout_plan_details=WorkoutPlanDetails(**payload.dict())
        )


@router.get('/workout-plans', status_code=status.HTTP_200_OK)
async def get_workout_plan(
    user_id: str = Query(..., description="Customer ID whose workout plan will be retrieved"),
    auth_user_id: str = Depends(oauth2.require_user)
):
    """
    Retrieve the workout plan for a specific customer by their user_id.
    """
    with handle_errors():
        logger.info(f"Retrieving workout plan for customer ID: {user_id} by trainer ID: {auth_user_id}")

        # Validate the customer ID provided in the query
        try:
            customer_id = ObjectId(user_id)
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid customer ID format.")

        # Check if the customer exists in the database
        existing_customer =  User.find_one({"_id": customer_id})
        if not existing_customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found"
            )

        # Retrieve the workout plan
        workout_plan = existing_customer.get("workout_plan")
        if not workout_plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No workout plan found for the user."
            )

        # Return the response with the workout plan details
        return ModifyWorkoutsUserResponse(
            user_id=user_id,
            message="Workout plan details retrieved successfully",
            workout_plan_details=WorkoutPlanDetails(**workout_plan)  # Unpack workout_plan into WorkoutPlanDetails
        )


@router.put('/workout-plans', status_code=status.HTTP_200_OK)
async def update_workout_plan(
    payload: UpdateWorkoutPlanDetails = Body(...),
    user_id: str = Query(..., description="Customer ID whose workout plan will be updated"),
    auth_user_id: str = Depends(oauth2.require_user)
):
    """
    Update an existing workout plan for a customer. Only the specified fields in the payload will be updated.
    """
    with handle_errors():
        # Validate the customer ID provided in the payload
        try:
            customer_id = ObjectId(user_id)
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format.")

        # Check if the customer exists in the database
        existing_customer =  User.find_one({"_id": customer_id})
        if not existing_customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found"
            )

        # Check if the customer already has a workout plan
        if "workout_plan" not in existing_customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No workout plan found for the user."
            )

        # Prepare the workout plan details for update
        workout_plan_data = payload.dict(exclude_none=True)
        if "start_date" in workout_plan_data:
            workout_plan_data["start_date"] = workout_plan_data["start_date"].isoformat()
        if "end_date" in workout_plan_data:
            workout_plan_data["end_date"] = workout_plan_data["end_date"].isoformat()

        # Ensure there's something to update
        if not workout_plan_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields provided for update."
            )

        # Compare with existing details
        current_workout_plan = existing_customer.get("workout_plan", {})
        if all(current_workout_plan.get(key) == value for key, value in workout_plan_data.items()):
            return ModifyWorkoutsUserResponse(
                user_id=user_id,
                message="No changes detected. The workout plan is already up-to-date.",
                workout_plan_details=WorkoutPlanDetails(**current_workout_plan)
            )

        # Get the current IST date and time
        formatted_date, formatted_time = get_current_ist_time()
        datetime_str = f"{formatted_date} {formatted_time}"
        
        # Update the workout plan in the user's document
        update_result =  User.update_one(
            {"_id": customer_id},
            {
                "$set": {
                    **{f"workout_plan.{k}": v for k, v in workout_plan_data.items()},
                    "workout_plan.updated_at": datetime_str
                }
            }
        )

        if update_result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred while updating the workout plan."
            )

        # Fetch the updated workout plan
        updated_customer =  User.find_one({"_id": customer_id})
        updated_workout_plan = updated_customer.get("workout_plan", {})

        return ModifyWorkoutsUserResponse(
            user_id=user_id,
            message="Workout plan updated successfully!",
            workout_plan_details=WorkoutPlanDetails(**updated_workout_plan)
        )



@router.delete('/workout-plans', status_code=status.HTTP_200_OK)
async def delete_workout_plan(
    user_id: str = Query(..., description="Customer ID whose workout plan will be deleted"),
    auth_user_id: str = Depends(oauth2.require_user)  # Authenticated trainer's or admin's user ID
):
    """
    Delete the workout plan for a specific customer.
    """
    with handle_errors():
        # Validate the customer ID provided in the query
        try:
            customer_id = ObjectId(user_id)
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid customer ID format.")

        # Check if the customer exists in the database
        existing_customer =  User.find_one({"_id": customer_id})
        if not existing_customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found"
            )

        # Check if the workout plan exists for the customer
        if "workout_plan" not in existing_customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No workout plan found for the user."
            )

        # Delete the workout plan
        update_result =  User.update_one(
            {"_id": customer_id},
            {"$unset": {"workout_plan": ""}}
        )

        if update_result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete workout plan."
            )

        return {"user_id": user_id, "message": "Workout plan deleted successfully!"}




# Exercise CRUD operations

@router.post('/exercise', status_code=status.HTTP_201_CREATED, response_model=ExerciseResponseSchema)
async def create_exercise(
    payload: ExerciseCreateSchema,
    user_id: str = Depends(oauth2.require_user)  # Admin authentication can be enforced using an admin check.
):
    """
    Create a new exercise.
    """
    with handle_errors():  # Error handling context manager
        logger.info(f"Creating a new exercise by user ID: {user_id}")

        # Check if an exercise with the same name already exists
        existing_exercise =  Exercises.find_one({'name': payload.name})
        if existing_exercise:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,  # Conflict status code
                detail=f"Exercise with name '{payload.name}' already exists."
            )

        # Prepare exercise data
        exercise_data = payload.dict()

        # Insert new exercise into the Exercises collection
        try:
            result =  Exercises.insert_one(exercise_data)
        except Exception as e:
            logger.error(f"Failed to create exercise '{payload.name}': {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create an exercise for {payload.name}. Please try again later."
            )

        # Fetch the newly inserted exercise
        new_exercise =  Exercises.find_one({'_id': result.inserted_id})

        return ExerciseResponseSchema(
            id=str(new_exercise['_id']),
            message="Exercise created successfully!", 
            **new_exercise)

@router.get('/exercises', response_model=dict)
async def get_exercises(
    type: str = Query(None, description="Type of exercise (optional)"),
    level: str = Query(None, description="Level of exercise (optional)"),
    page: int = Query(1, ge=1, description="Page number for pagination"),
    items_per_page: int = Query(10, le=100, description="Number of items per page"),
    user_id: str = Depends(oauth2.require_user)  # Authenticated user
):
    """
    Retrieve all exercises, filtered by type and level, with pagination.
    """
    with handle_errors():
        # Debug: Log the incoming payload
        logger.info(f"Received payload: type:{type}, level:{level}")

        # Construct query filter
        query = {}
        if type:
            query['type'] = type  # Match the 'type' field
        else:
            logger.info("No 'type' filter provided.")
        
        if level:
            query['level'] = level  # Match the 'level' field
        else:
            logger.info("No 'level' filter provided.")

        # Debug: Log the constructed query
        logger.info(f"Constructed query: {query}")

        # Pagination
        skip = (page - 1) * items_per_page

        # Fetch exercises matching the query (synchronously)
        exercises = list(Exercises.find(query).skip(skip).limit(items_per_page))


        # Debug: Log the fetched exercises
        logger.info(f"Fetched exercises: {exercises}")

        # Convert ObjectId fields to strings for JSON serialization
        for exercise in exercises:
            exercise["_id"] = str(exercise["_id"])

        # Count total matching exercises
        total_items =  Exercises.count_documents(query)
        total_pages = (total_items + items_per_page - 1) // items_per_page

        # Return the formatted response
        return {
            "total_items": total_items,
            "total_pages": total_pages,
            "current_page": page,
            "items_per_page": items_per_page,
            "exercises": exercises
        }



@router.get('/exercise/{exercise_id}', response_model=ExerciseResponseSchema)
async def get_single_exercise(
    exercise_id: str,
    user_id: str = Depends(oauth2.require_user)
):
    """
    Retrieve a single exercise by its unique ID.
    """
    with handle_errors():
        # Convert exercise_id to ObjectId for MongoDB operations
        try:
            exercise_obj_id = ObjectId(exercise_id)
        except Exception as e:
            logger.error(f"Invalid ObjectId: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid exercise ID format."
            )

        # Find the exercise by ID
        exercise =  Exercises.find_one({"_id": exercise_obj_id})
        if not exercise:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exercise not found."
            )

        return ExerciseResponseSchema(id=str(exercise['_id']), **exercise)


@router.put('/exercise/{exercise_id}', response_model=ExerciseResponseSchema)
async def update_exercise(
    exercise_id: str,
    payload: ExerciseUpdateSchema,
    user_id: str = Depends(oauth2.require_user)
):
    """
    Update an existing exercise.
    """
    with handle_errors():
        logger.info(f"Updating exercise ID: {exercise_id} by user ID: {user_id}")

        # Convert exercise_id to ObjectId for MongoDB operations
        try:
            exercise_obj_id = ObjectId(exercise_id)
        except Exception as e:
            logger.error(f"Invalid ObjectId: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid exercise ID format."
            )

        # Remove None fields from the update payload
        update_data = {k: v for k, v in payload.dict().items() if v is not None}

        # Update exercise in the collection
        update_result =  Exercises.find_one_and_update(
            {"_id": exercise_obj_id},
            {"$set": update_data},
            return_document=True
        )

        if not update_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exercise not found."
            )

        return ExerciseResponseSchema(
            id=str(update_result['_id']), 
            message="Exercise updated successfully!",
            **update_result)


@router.delete('/exercise/{exercise_id}', status_code=status.HTTP_200_OK)
async def delete_exercise(
    exercise_id: str,
    user_id: str = Depends(oauth2.require_user)
):
    """
    Delete an exercise by its ID.
    """
    with handle_errors():
        logger.info(f"Deleting exercise ID: {exercise_id} by user ID: {user_id}")

        # Convert exercise_id to ObjectId for MongoDB operations
        try:
            exercise_obj_id = ObjectId(exercise_id)
        except Exception as e:
            logger.error(f"Invalid ObjectId: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid exercise ID format."
            )

        # Delete the exercise from the collection
        delete_result =  Exercises.delete_one({"_id": exercise_obj_id})
        if delete_result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exercise not found."
            )

        # Return a success message
        return {"message": "Exercise deleted successfully!"}




# Routes for the user in the gym app

@router.post('/exercise/upload_workout_task')
async def upload_workout_task(payload: UploadWorkoutRequest, user_id: str = Depends(oauth2.require_user)):
    """
    Uploads a workout task and diet log for a user. Both workout and diet logs are stored under the same date.
    """
    with handle_errors():
        user_id = str(user_id)

        # Get the formatted date and time in IST
        formatted_date, formatted_time = get_current_ist_time()

        # Extract workout details from the payload
        workout_name = payload.workout.workout_name

        # Get the user's existing record from the database asynchronously
        existing_record =  WorkoutandDietTracking.find_one({"_id": user_id})

        # If no record exists, create a new record for the user
        if not existing_record:
            new_record = {
                "_id": user_id,
                formatted_date: {
                    "workout_logs": [
                        {
                            "workout_name": workout_name,
                            "sets_assigned": payload.workout.sets_assigned,
                            "sets_done": payload.workout.sets_done,
                            "reps_assigned": payload.workout.reps_assigned,
                            "reps_done": payload.workout.reps_done,
                            "load_assigned": payload.workout.load_assigned,
                            "load_done": payload.workout.load_done,
                            "performance": payload.workout.performance,
                            "updated_at": formatted_time
                        }
                    ],
                    "diet_logs": []  # Initially empty diet logs
                }
            }

            # Insert the new workout and diet data into MongoDB
            WorkoutandDietTracking.insert_one(new_record)

            return {
                "status": "success",
                "message": f"Workout data for {workout_name} uploaded successfully for {formatted_date}!"
            }

        else:
            # Get existing workout logs for the given date
            existing_workouts = existing_record.get(formatted_date, {}).get("workout_logs", [])

            # Check if `existing_workouts` is a list (add validation)
            if not isinstance(existing_workouts, list):
                existing_workouts = []  # Default to empty list if it's not a list

            # Check if the workout already exists
            if any(workout["workout_name"] == workout_name for workout in existing_workouts):
                raise HTTPException(
                    status_code=400,
                    detail=f"The data for {workout_name} has already been uploaded today."
                )

            # Add the workout log to the existing record
            new_workout_log = {
                "workout_name": workout_name,
                "sets_assigned": payload.workout.sets_assigned,
                "sets_done": payload.workout.sets_done,
                "reps_assigned": payload.workout.reps_assigned,
                "reps_done": payload.workout.reps_done,
                "load_assigned": payload.workout.load_assigned,
                "load_done": payload.workout.load_done,
                "performance": payload.workout.performance,
                "updated_at": formatted_time
            }

            # Log the new workout log to be added (for debugging)
            logging.info(f"Appending new workout log: {new_workout_log}")

            # Update the workout logs by appending the new log
            WorkoutandDietTracking.update_one(
                {"_id": user_id},
                {
                    "$set": {  # Use $set to add or update the date field
                        f"{formatted_date}": {
                            "workout_logs": existing_workouts + [new_workout_log]
                        }
                    }
                },
                upsert=True  # Ensure that if the date field doesn't exist, it gets created
            )

            return {
                "status": "success",
                "message": f"Workout data for {workout_name} uploaded successfully for {formatted_date}!"
            }

@router.get('/exercise/workout_logs/{user_id}')
async def get_workout_logs(
    user_id: str,  # Path parameter for date (format: dd-mm-yyyy)
    auth_user_id: str = Depends(oauth2.require_user),  # Authenticated user ID
    date: str = Query(..., description="The date for which the workout logs are needed")
):
    """
    Fetches the workout logs for a specific user and date from MongoDB for the trainer and admin to track.
    """
    with handle_errors():
        # Log input data for debugging
        logger.info(f"Fetching workout logs for user {user_id} on date {date}")

        # Validate the date format (ensure it's in dd-mm-yyyy)
        try:
            day, month, year = map(int, date.split("-"))
            formatted_date = f"{day:02d}-{month:02d}-{year:04d}"  # Ensure leading zeros and consistent format
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use 'dd-mm-yyyy'."
            )

        # Fetch the record for the given user and date
        existing_record =  WorkoutandDietTracking.find_one(
            {"_id": user_id, formatted_date: {"$exists": True}}
        )

        if not existing_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No workout logs found for user {user_id} on {formatted_date}."
            )

        # Extract workout logs for the given date
        workout_logs = existing_record.get(formatted_date, {}).get("workout_logs", [])

        if not workout_logs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No workout logs found for user {user_id} on {formatted_date}."
            )

        # Return the workout logs for the specified date
        return {
            "status": "success",
            "workout_logs": workout_logs
        }
