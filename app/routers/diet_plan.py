# app/routers/diet_plan.py

from fastapi import APIRouter, Depends, HTTPException, status, Query
from bson.objectid import ObjectId
from typing import List
from datetime import datetime
from loguru import logger

from app.database import User, DietPlans
from app.schemas.diet_plan import DietPlanSchema, DietPlanResponseSchema
from app.utilities.error_handler import handle_errors
from .. import oauth2

router = APIRouter()

# Create a new diet plan
@router.post('/diet-plan', status_code=status.HTTP_201_CREATED, response_model=DietPlanResponseSchema)
async def create_diet_plan(
    payload: DietPlanSchema,
    user_id: str = Query(..., description="User ID to associate the diet plan with")  # Accept user_id as a query parameter
):
    """
    Create a new diet plan for a specific user.
    """
    with handle_errors():
        logger.info(f"Creating diet plan for user ID: {user_id}")

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

        # Convert start_date and end_date to strings if they are `datetime` objects
        diet_plan_data = payload.dict()
        diet_plan_data["created_at"] = datetime.utcnow().isoformat()
        diet_plan_data["updated_at"] = datetime.utcnow().isoformat()

        # Insert diet plan into DietPlans collection
        result = DietPlans.insert_one(diet_plan_data)
        new_diet_plan = DietPlans.find_one({"_id": result.inserted_id})

        return DietPlanResponseSchema(id=str(new_diet_plan["_id"]), **new_diet_plan)


# Retrieve all diet plans for a user
@router.get('/diet-plans', response_model=List[DietPlanResponseSchema])
async def get_all_diet_plans(
    user_id: str = Query(..., description="User ID to get diet plans for")
):
    """
    Retrieve all diet plans for a specific user.
    """
    with handle_errors():
        try:
            user_id = ObjectId(user_id)
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format.")

        diet_plans = list(DietPlans.find({"user_id": str(user_id)}))
        return [DietPlanResponseSchema(id=str(dp["_id"]), **dp) for dp in diet_plans]


# Update a diet plan
@router.put('/diet-plan/{diet_plan_id}', response_model=DietPlanResponseSchema)
async def update_diet_plan(
    diet_plan_id: str,
    payload: DietPlanSchema,
    user_id: str = Depends(oauth2.require_user)
):
    """
    Update an existing diet plan for a specific user.
    """
    with handle_errors():
        try:
            diet_plan_obj_id = ObjectId(diet_plan_id)
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid diet plan ID format.")

        # Remove None fields from the update payload
        update_data = {k: v for k, v in payload.dict().items() if v is not None}

        # Update diet plan in the collection
        update_result = DietPlans.find_one_and_update(
            {"_id": diet_plan_obj_id, "user_id": user_id},
            {"$set": update_data},
            return_document=True
        )

        if not update_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Diet plan not found."
            )

        return DietPlanResponseSchema(id=str(update_result["_id"]), **update_result)


# Delete a diet plan
@router.delete('/diet-plan/{diet_plan_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_diet_plan(
    diet_plan_id: str,
    user_id: str = Depends(oauth2.require_user)
):
    """
    Delete a diet plan by its ID.
    """
    with handle_errors():
        try:
            diet_plan_obj_id = ObjectId(diet_plan_id)
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid diet plan ID format.")

        delete_result = DietPlans.delete_one({"_id": diet_plan_obj_id, "user_id": user_id})
        if delete_result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Diet plan not found."
            )

        return {"message": "Diet plan deleted successfully!"}
