from fastapi import APIRouter, Depends, HTTPException, status
from bson.objectid import ObjectId
from datetime import datetime
from typing import List, Optional
from loguru import logger

from app.database import User, Exercises
from app.schemas.exercise import DayProgressSchema, ExerciseCreateSchema, ExerciseUpdateSchema, ExerciseResponseSchema
from app.schemas.workout_plan import WorkoutPlanSchema
from app.utilities.error_handler import handle_errors
from .. import oauth2

# Initialize the router
router = APIRouter()

@router.post('/workout-plan', status_code=status.HTTP_201_CREATED)
async def add_workout_plan(
    payload: WorkoutPlanSchema,
    user_id: str = Depends(oauth2.require_user)  # Get user_id from the authenticated user
):
    """
    Add a new workout plan for the user, including start date, end date, and empty progress.
    """
    with handle_errors():
        # Log user_id for debugging
        logger.info(f"Adding workout plan for user ID: {user_id}")
        
        # Convert user_id to ObjectId for MongoDB operations
        user_id = ObjectId(user_id)

        # Check if the user exists in the database
        existing_user = User.find_one({"_id": user_id})
        if not existing_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Prepare the workout plan data
        workout_plan_data = payload.dict()
        workout_plan_data["created_at"] = datetime.utcnow()
        workout_plan_data["updated_at"] = datetime.utcnow()

        # Update the user document with the new workout plan
        update_result = User.update_one(
            {"_id": user_id},
            {"$set": {"workout_plan": workout_plan_data}}
        )

        if update_result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add workout plan."
            )

        return {"message": "Workout plan added successfully!"}

@router.post('/workout-plan/progress', status_code=status.HTTP_201_CREATED)
async def add_workout_progress(
    payload: DayProgressSchema,
    user_id: str = Depends(oauth2.require_user)
):
    """
    Add a workout progress entry for a specific day in the user's workout plan.
    """
    with handle_errors():
        # Log user_id for debugging
        logger.info(f"Adding workout progress for user ID: {user_id}")

        # Convert user_id to ObjectId for MongoDB operations
        user_id = ObjectId(user_id)

        # Fetch the user's workout plan
        existing_user = User.find_one({"_id": user_id})
        if not existing_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check if the user has a workout plan
        if "workout_plan" not in existing_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No workout plan found for the user."
            )

        # Append the new day's progress to the existing workout plan's progress
        workout_plan = existing_user["workout_plan"]
        if "progress" not in workout_plan:
            workout_plan["progress"] = []

        # Check if the day already exists and update it
        day_exists = False
        for day_progress in workout_plan["progress"]:
            if day_progress["day"] == payload.day:
                day_progress["exercises"] = payload.exercises
                day_exists = True
                break

        # If day does not exist, append the new day progress
        if not day_exists:
            workout_plan["progress"].append(payload.dict())

        # Update the workout plan in the user document
        update_result = User.update_one(
            {"_id": user_id},
            {"$set": {"workout_plan": workout_plan}}
        )

        if update_result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add workout progress."
            )

        return {"message": "Workout progress added successfully!"}

@router.put('/workout-plan/progress', status_code=status.HTTP_200_OK)
async def edit_workout_progress(
    payload: DayProgressSchema,
    user_id: str = Depends(oauth2.require_user)
):
    """
    Edit an existing workout progress entry for a specific day in the user's workout plan.
    """
    with handle_errors():
        # Log user_id for debugging
        logger.info(f"Editing workout progress for user ID: {user_id}")

        # Convert user_id to ObjectId for MongoDB operations
        user_id = ObjectId(user_id)

        # Fetch the user's workout plan
        existing_user = User.find_one({"_id": user_id})
        if not existing_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check if the user has a workout plan
        if "workout_plan" not in existing_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No workout plan found for the user."
            )

        # Edit the day's progress in the workout plan
        workout_plan = existing_user["workout_plan"]
        if "progress" not in workout_plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No workout progress found in the workout plan."
            )

        # Update the day progress if it exists
        day_exists = False
        for day_progress in workout_plan["progress"]:
            if day_progress["day"] == payload.day:
                day_progress["exercises"] = payload.exercises
                day_exists = True
                break

        if not day_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No progress found for the day: {payload.day}"
            )

        # Update the workout plan in the user document
        update_result = User.update_one(
            {"_id": user_id},
            {"$set": {"workout_plan": workout_plan}}
        )

        if update_result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to edit workout progress."
            )

        return {"message": "Workout progress updated successfully!"}

@router.post('/exercise', status_code=status.HTTP_201_CREATED, response_model=ExerciseResponseSchema)
async def create_exercise(
    payload: ExerciseCreateSchema,
    user_id: str = Depends(oauth2.require_user)  # Admin authentication can be enforced using an admin check.
):
    """
    Create a new exercise.
    """
    with handle_errors():
        logger.info(f"Creating a new exercise by user ID: {user_id}")

        # Prepare exercise data
        exercise_data = payload.dict()

        # Insert new exercise into the Exercises collection
        result = Exercises.insert_one(exercise_data)
        new_exercise = Exercises.find_one({'_id': result.inserted_id})

        return ExerciseResponseSchema(id=str(new_exercise['_id']), **new_exercise)


@router.get('/exercises', response_model=List[ExerciseResponseSchema])
async def get_all_exercises(
    type: Optional[str] = None,
    category: Optional[str] = None,
    user_id: str = Depends(oauth2.require_user)
):
    """
    Retrieve all exercises, optionally filtered by type and category.
    """
    with handle_errors():
        logger.info(f"Retrieving exercises with filters: type={type}, category={category}")

        # Construct query filter
        query = {}
        if type:
            query['type'] = type
        if category:
            query['category'] = category

        # Fetch exercises from the collection
        exercises = list(Exercises.find(query))
        return [ExerciseResponseSchema(id=str(ex['_id']), **ex) for ex in exercises]


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
        exercise = Exercises.find_one({"_id": exercise_obj_id})
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
        update_result = Exercises.find_one_and_update(
            {"_id": exercise_obj_id},
            {"$set": update_data},
            return_document=True
        )

        if not update_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exercise not found."
            )

        return ExerciseResponseSchema(id=str(update_result['_id']), **update_result)


@router.delete('/exercise/{exercise_id}', status_code=status.HTTP_204_NO_CONTENT)
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
        delete_result = Exercises.delete_one({"_id": exercise_obj_id})
        if delete_result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exercise not found."
            )

        return {"message": "Exercise deleted successfully!"}
