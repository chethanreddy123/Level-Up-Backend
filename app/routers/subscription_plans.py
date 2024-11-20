from fastapi import APIRouter, Depends, HTTPException, status
from app.database import GymPlans  # Assuming GymPlans is the MongoDB collection
from app.schemas.subscription_plans import GymPlanSchema, GymPlanUpdateSchema
from app.utilities.error_handler import handle_errors
from app import oauth2
from bson import ObjectId
from app.utilities.utils import get_current_ist_time
from loguru import logger

router = APIRouter()

# Create a new gym plan
@router.post('/gym-plan', status_code=status.HTTP_201_CREATED)
async def create_gym_plan(
    payload: GymPlanSchema,
    user_id: str = Depends(oauth2.require_user)  # Optional, depending on your authentication
):
    """
    Create a new gym subscription plan.
    Ensures the plan name is unique (case-insensitive).
    """
    with handle_errors():
        # Log the action of creating a new plan
        logger.info(f"Creating a new gym plan: {payload.plan_name} by user ID: {user_id}")

        # Check if the gym plan already exists (case-insensitive)
        existing_plan = GymPlans.find_one(
            {"plan_name": {"$regex": f"^{payload.plan_name}$", "$options": "i"}}
        )
        
        if existing_plan:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"The gym plan '{payload.plan_name.title()}' already exists."
            )

        # Prepare the gym plan data
        gym_plan_data = payload.dict()

        # Convert the duration to string format (e.g., "3 months")
        if gym_plan_data['duration'] == 1:
            gym_plan_data['duration'] = "1 month"
        else:
            gym_plan_data['duration'] = f"{gym_plan_data['duration']} months"

        # Insert the new gym plan into the GymPlans collection
        result = GymPlans.insert_one(gym_plan_data)

        # Fetch the newly inserted gym plan, including the inserted _id
        new_gym_plan = GymPlans.find_one({'_id': result.inserted_id})

        # Convert _id from ObjectId to string
        if new_gym_plan:
            new_gym_plan['_id'] = str(new_gym_plan['_id'])

        return {
            "id": new_gym_plan['_id'],  # Return the new gym plan with its inserted data
            "message": "Gym plan added successfully!"
        }


# Get a gym plan by ID
@router.get('/gym-plan/{plan_id}')
async def get_gym_plan(plan_id: str, auth_user_id: str = Depends(oauth2.require_user)):
    """
    Retrieve a gym subscription plan by its ID.
    """
    with handle_errors():
        # Ensure the plan_id is a valid ObjectId
        if not ObjectId.is_valid(plan_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid plan ID format."
            )

        # Retrieve the gym plan from the database
        gym_plan = GymPlans.find_one({"_id": ObjectId(plan_id)})

        if not gym_plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Gym plan not found."
            )

        # Convert _id from ObjectId to string
        gym_plan['_id'] = str(gym_plan['_id'])

        return gym_plan
    
# Update an existing gym plan
@router.put('/gym-plan/{plan_id}', status_code=status.HTTP_200_OK)
async def update_gym_plan(
    plan_id: str, 
    payload: GymPlanUpdateSchema, 
    auth_user_id: str = Depends(oauth2.require_user)):
    """
    Update a gym subscription plan by its ID.
    Allows updating one or more fields (plan_name, duration, price).
    """
    with handle_errors():
        # Ensure the plan_id is a valid ObjectId
        if not ObjectId.is_valid(plan_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid plan ID format."
            )

        # Retrieve the existing gym plan
        gym_plan = GymPlans.find_one({"_id": ObjectId(plan_id)})

        if not gym_plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Gym plan not found."
            )

        # Prepare the update data, updating only the fields that are provided
        update_data = payload.dict(exclude_unset=True)  # Only include fields provided in the request

        # If the duration field is updated, convert it to the string format
        if update_data.get('duration') is not None:
            if update_data['duration'] == 1:
                update_data['duration'] = "1 month"
            else:
                update_data['duration'] = f"{update_data['duration']} months"
        
        # Update the gym plan in the database
        updated_gym_plan = GymPlans.find_one_and_update(
            {"_id": ObjectId(plan_id)}, 
            {"$set": update_data}, 
            return_document=True  # Return the updated document
        )

        # If update was successful, return the updated plan
        if updated_gym_plan:
            updated_gym_plan['_id'] = str(updated_gym_plan['_id'])
            return updated_gym_plan

        # If somehow the update failed
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update the gym plan."
        )
    
# Delete a gym plan by ID
@router.delete('/gym-plan/{plan_id}', status_code=status.HTTP_200_OK)
async def delete_gym_plan(
    plan_id: str, 
    auth_user_id: str = Depends(oauth2.require_user)):
    """
    Delete a gym subscription plan by its ID.
    Ensures the user is authenticated and the plan exists.
    """
    with handle_errors():
        # Ensure the plan_id is a valid ObjectId
        if not ObjectId.is_valid(plan_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid plan ID format."
            )

        # Retrieve the gym plan from the database
        gym_plan = GymPlans.find_one({"_id": ObjectId(plan_id)})

        if not gym_plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Gym plan not found."
            )

        # Delete the gym plan
        result = GymPlans.delete_one({"_id": ObjectId(plan_id)})

        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete the gym plan."
            )

        return {"message": "Gym plan deleted successfully."}
    

    # Get all gym plans
@router.get('/gym-plans', status_code=status.HTTP_200_OK)
async def get_all_gym_plans(auth_user_id: str = Depends(oauth2.require_user)):
    """
    Retrieve all gym subscription plans.
    """
    with handle_errors():
        # Fetch all gym plans from the database
        gym_plans = list(GymPlans.find())  # Convert cursor to list
        
        # Check if there are any plans
        if not gym_plans:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No gym plans found."
            )
        
        # Convert _id from ObjectId to string for each gym plan
        for plan in gym_plans:
            plan['_id'] = str(plan['_id'])
        
        return gym_plans