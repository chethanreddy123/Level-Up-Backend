# app/routers/workout_plan.py

from fastapi import APIRouter, Depends, HTTPException, status, Query
from bson.objectid import ObjectId
from datetime import datetime
from loguru import logger

from app.database import User
from app.schemas.workout_plan import WorkoutPlanSchema, WorkoutPlanUpdateSchema
from app.utilities.error_handler import handle_errors
from .. import oauth2

# Initialize the router
router = APIRouter()

@router.post('/workout-plan', status_code=status.HTTP_201_CREATED)
async def create_workout_plan(
    payload: WorkoutPlanSchema,
    user_id: str = Query(..., description="User ID to create workout plan for")  # Accept user_id as a query parameter
):
    """
    Create a new workout plan for the user. This endpoint is typically used by admins to create workout plans.
    """
    with handle_errors():
        logger.info(f"Creating workout plan for user ID: {user_id}")

        # Convert user_id to ObjectId for MongoDB operations
        try:
            user_id = ObjectId(user_id)
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format.")

        # Check if the user exists in the database
        existing_user = User.find_one({"_id": user_id})
        if not existing_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found."
            )

        # Convert `start_date` and `end_date` to strings if they are `datetime.date` objects
        workout_plan_data = payload.dict()
        if isinstance(workout_plan_data["start_date"], datetime):
            workout_plan_data["start_date"] = workout_plan_data["start_date"].isoformat()
        if isinstance(workout_plan_data["end_date"], datetime):
            workout_plan_data["end_date"] = workout_plan_data["end_date"].isoformat()

        # Set created_at and updated_at fields as datetime strings
        workout_plan_data["created_at"] = datetime.utcnow().isoformat()
        workout_plan_data["updated_at"] = datetime.utcnow().isoformat()

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

        return {"message": "Workout plan created successfully!"}


@router.get('/workout-plan', status_code=status.HTTP_200_OK)
async def get_workout_plan(
    user_id: str = Query(..., description="User ID to get workout plan for")
):
    """
    Retrieve the workout plan for a specific user.
    """
    with handle_errors():
        try:
            user_id = ObjectId(user_id)
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format.")

        existing_user = User.find_one({"_id": user_id}, {"workout_plan": 1})
        
        if not existing_user or "workout_plan" not in existing_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No workout plan found for the user."
            )

        return {"status": "success", "workout_plan": existing_user["workout_plan"]}


@router.put('/workout-plan', status_code=status.HTTP_200_OK)
async def update_workout_plan(
    payload: WorkoutPlanUpdateSchema,
    user_id: str = Query(..., description="User ID to update workout plan for")
):
    """
    Update an existing workout plan for a specific user.
    """
    with handle_errors():
        try:
            user_id = ObjectId(user_id)
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format.")

        existing_user = User.find_one({"_id": user_id})
        
        if not existing_user or "workout_plan" not in existing_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No workout plan found for the user."
            )

        # Remove None fields from the update payload
        update_data = {k: v for k, v in payload.dict().items() if v is not None}

        # Ensure `start_date` and `end_date` are strings
        if "start_date" in update_data and isinstance(update_data["start_date"], datetime):
            update_data["start_date"] = update_data["start_date"].isoformat()
        if "end_date" in update_data and isinstance(update_data["end_date"], datetime):
            update_data["end_date"] = update_data["end_date"].isoformat()

        # Update the workout plan in the user document
        update_result = User.update_one(
            {"_id": user_id},
            {"$set": {f"workout_plan.{k}": v for k, v in update_data.items()}}
        )

        if update_result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update workout plan."
            )

        return {"message": "Workout plan updated successfully!"}


@router.delete('/workout-plan', status_code=status.HTTP_204_NO_CONTENT)
async def delete_workout_plan(
    user_id: str = Query(..., description="User ID to delete workout plan for")
):
    """
    Delete the existing workout plan for a specific user.
    """
    with handle_errors():
        try:
            user_id = ObjectId(user_id)
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format.")

        existing_user = User.find_one({"_id": user_id})
        
        if not existing_user or "workout_plan" not in existing_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No workout plan found for the user."
            )

        # Remove the workout plan from the user document
        update_result = User.update_one(
            {"_id": user_id},
            {"$unset": {"workout_plan": ""}}
        )

        if update_result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete workout plan."
            )

        return {"message": "Workout plan deleted successfully!"}
