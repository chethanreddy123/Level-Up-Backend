# app/routers/workout_plan.py

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from fastapi.encoders import jsonable_encoder
from bson.objectid import ObjectId
from datetime import datetime
from loguru import logger
from app.utilities.utils import get_current_ist_time
from app.database import User, WorkoutPlans, Exercises
from app.schemas.workout_plan import WorkoutPlan, WorkoutPlanUpdateSchema, ExerciseOut
from app.utilities.error_handler import handle_errors
from .. import oauth2
from typing import List
import pytz

# Initialize the router
router = APIRouter()

@router.post('/workout-plan', status_code=status.HTTP_201_CREATED)
async def create_workout_plan(
    payload: WorkoutPlan,
    user_id: str = Depends(oauth2.require_user)
):
    """
    Create a new workout plan. This endpoint uploads a workout plan directly to the WorkoutPlans collection.
    """
    with handle_errors():
        logger.info("Creating new workout plan.")

        # Convert the payload into a dictionary
        workout_plan_data = payload.dict()

        # Get the current time in IST from the helper function
        formatted_date, formatted_time = get_current_ist_time()

        # Combine the date and time into a single string
        datetime_str = f"{formatted_date} {formatted_time}"

        # Directly use the datetime string for created_at and updated_at
        workout_plan_data["created_at"] = datetime_str
        workout_plan_data["updated_at"] = datetime_str

        # Check if a workout plan with the same name already exists
        existing_plan = await WorkoutPlans.find_one({"workout_plan_name": workout_plan_data["workout_plan_name"]})

        if existing_plan:
            # If a plan with the same name exists, raise a conflict exception
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,  # Conflict status code
                detail=f"Workout plan with the name '{workout_plan_data['workout_plan_name']}' already exists."
            )

        # Insert the new workout plan into the WorkoutPlans collection
        try:
            result = await WorkoutPlans.insert_one(workout_plan_data)
        except Exception as e:
            logger.error(f"Error creating workout plan: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create workout plan."
            )

        # Return a success message with the ID of the created workout plan
        return {"message": "Workout plan created successfully!", "workout_plan_id": str(result.inserted_id)}


@router.get('/workout-plan/{workout_plan_id}', status_code=status.HTTP_200_OK)
async def get_workout_plan(
    workout_plan_id: str,  # The workout plan ID to retrieve the plan
    user_id: str = Depends(oauth2.require_user)
):
    """
    Retrieve a workout plan by its ID, including exercise details.
    """
    with handle_errors():
        # Try to convert workout_plan_id to ObjectId for MongoDB operations
        try:
            workout_plan_id = ObjectId(workout_plan_id)
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid workout plan ID format.")

        # Look up the workout plan in the WorkoutPlans collection
        workout_plan = await WorkoutPlans.find_one({"_id": workout_plan_id})

        if not workout_plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No workout plan found with the given ID."
            )

        # Extract all unique exercise IDs from the workout plan schedule
        exercise_ids = set(
            exercise_id for day_exercises in workout_plan["schedule"].values() for exercise_id in day_exercises
        )

        # Convert exercise IDs to ObjectIds
        try:
            exercise_object_ids = [ObjectId(exercise_id) for exercise_id in exercise_ids]
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid exercise ID format: {str(e)}"
            )

        # Fetch all exercises by their ObjectIds
        exercises = await Exercises.find({"_id": {"$in": exercise_object_ids}}).to_list(length=None)

        # Create a dictionary mapping exercise ObjectId to exercise data
        exercise_dict = {str(exercise["_id"]): exercise for exercise in exercises}

        # Replace exercise IDs with exercise data in the workout plan schedule
        for day, exercise_ids_in_day in workout_plan["schedule"].items():
            # Replace each ID with its corresponding exercise data
            workout_plan["schedule"][day] = [
                exercise_dict.get(str(exercise_id), {"error": f"Exercise ID {exercise_id} not found"})
                for exercise_id in exercise_ids_in_day
            ]

        # Use jsonable_encoder to convert the ObjectIds to strings and return the full workout plan
        workout_plan = jsonable_encoder(workout_plan, custom_encoder={ObjectId: str})

        return {"status": "success", "workout_plan": workout_plan}



@router.put('/workout-plan/{workout_plan_id}', status_code=status.HTTP_200_OK)
async def update_workout_plan(
    workout_plan_id: str,
    payload: WorkoutPlanUpdateSchema = Body(...),
    user_id: str = Depends(oauth2.require_user)
):
    """
    Update an existing workout plan. 
    If the workout_plan_name is provided, update it. 
    If no changes are made, return a success message.
    """
    with handle_errors():
        # Validate workout_plan_id
        try:
            workout_plan_id = ObjectId(workout_plan_id)
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid workout plan ID format.")

        # Check if the workout plan exists
        existing_plan = await WorkoutPlans.find_one({"_id": workout_plan_id})

        if not existing_plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workout plan not found."
            )

        # Prepare update data and ensure we don't include None values
        update_data = {}

        # Only add workout_plan_name if it's not None and if it has changed
        if payload.workout_plan_name is not None and payload.workout_plan_name != existing_plan.get("workout_plan_name"):
            update_data["workout_plan_name"] = payload.workout_plan_name
        
        # Only add schedule if it's not None and if it has changed
        if payload.schedule is not None and payload.schedule != existing_plan.get("schedule"):
            update_data["schedule"] = payload.schedule
        
        # If there are changes, add the updated_at field
        if update_data:
            formatted_date, formatted_time = get_current_ist_time()
            datetime_str = f"{formatted_date} {formatted_time}"
            update_data["updated_at"] = datetime_str

        # If there's no data to update (i.e., all fields are None or unchanged), return a success message
        if not update_data:
            return {"message": "Workout plan is up to date. No changes applied."}

        # Update the workout plan in the database
        update_result = await WorkoutPlans.update_one(
            {"_id": workout_plan_id},
            {"$set": update_data}
        )

        if update_result.modified_count == 0:
            # If no modification happened (i.e., the data is the same), return a success message
            return {"message": "Workout plan is up to date. No changes applied."}

        # If update was successful
        return {"message": "Workout plan updated successfully!"}


@router.delete('/workout-plan/{workout_plan_id}', status_code=status.HTTP_200_OK)
async def delete_workout_plan(
    workout_plan_id: str,  # Take the workout plan ID directly in the URL path
    user_id: str = Depends(oauth2.require_user)
):
    """
    Delete the existing workout plan by its ID.
    """
    with handle_errors():
        try:
            workout_plan_id = ObjectId(workout_plan_id)  # Convert the ID to ObjectId
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid workout plan ID format.")

        # Check if the workout plan exists
        existing_plan = await WorkoutPlans.find_one({"_id": workout_plan_id})

        if not existing_plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workout plan not found."
            )

        # Remove the workout plan from the WorkoutPlans collection
        delete_result = await WorkoutPlans.delete_one({"_id": workout_plan_id})

        if delete_result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete workout plan."
            )

        return {"message": "Workout plan deleted successfully!"}
    

@router.get('/workout-plans/get_all_exercises', response_model=List[ExerciseOut], status_code=status.HTTP_200_OK)
async def get_all_exercises(user_id: str = Depends(oauth2.require_user)):
    """
    Retrieve all exercises with only ID and name.
    """
    try:
        # Fetch all exercises from the database (assumes MongoDB)
        exercises = await Exercises.find().to_list(length=None)

        if not exercises:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No exercises found."
            )

        # Convert exercises to the response format
        return [ExerciseOut.from_mongo(exercise) for exercise in exercises]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching exercises: {str(e)}"
        )
