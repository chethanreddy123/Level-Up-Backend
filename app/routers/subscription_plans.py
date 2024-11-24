from fastapi import APIRouter, Depends, Form, HTTPException, status
import loguru
from app.database import GymPlans, User  # Assuming GymPlans is the MongoDB collection
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
    


@router.post('/gym-plan/add_user', status_code=status.HTTP_201_CREATED)
async def add_gym_plan(
    user_id: str = Form(..., description="User ID of the user"),
    subscription_plan_id: str = Form(..., description="ID of the gym subscription plan from GymPlans collection"),
    auth_user_id: str = Depends(oauth2.require_user)  # Ensure the user is authenticated
):
    """
    Add or update the gym subscription plan for a user.
    The plan is fetched from the GymPlans collection using subscription_plan_id.
    If the user already has a subscription plan, a warning is raised.
    """
    with handle_errors():
        # Check if user exists
        user = User.find_one({"_id": ObjectId(user_id)})
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )

        # Check if the user already has a subscription plan
        if "subscription_plan" in user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already has a subscription plan"
            )

        # Fetch the gym plan from the GymPlans collection
        gym_plan = GymPlans.find_one({"_id": ObjectId(subscription_plan_id)})

        if not gym_plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Subscription plan with ID {subscription_plan_id} not found in GymPlans"
            )

        # Prepare the subscription plan to add to the user
        subscription_plan = {
            "plan_name": gym_plan["plan_name"],
            "duration": gym_plan["duration"],
            "price": gym_plan["price"]
        }

        # Add subscription_plan to the user document
        result = User.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"subscription_plan": subscription_plan}}
        )

        if result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add subscription plan"
            )

        # Log the addition of the gym plan
        loguru.logger.info(f"User {user_id} subscribed to {gym_plan['plan_name']} for {gym_plan['duration']} at {gym_plan['price']}.")

        # Return a success message
        return {
            "status": "success",
            "message": f"Subscription plan '{gym_plan['plan_name']}' added for user {user_id}.",
            "user_id": user_id,
            "subscription_plan": subscription_plan
        }
    
@router.delete('/gym-plan/remove_user/{user_id}', status_code=status.HTTP_200_OK)
async def delete_gym_plan(
    user_id: str,  # The user_id from query parameters
    auth_user_id: str = Depends(oauth2.require_user)  # Ensure the user is authenticated
):
    """
    Delete the gym subscription plan for the given user_id.
    This removes the 'subscription_plan' field from the user's profile.
    """
    with handle_errors():
        # Check if user exists
        user = User.find_one({"_id": ObjectId(user_id)})
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )
        
        # Check if the user has a subscription plan
        if "subscription_plan" not in user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User does not have a subscription plan"
            )

        # Remove the subscription plan from the user document
        result = User.update_one(
            {"_id": ObjectId(user_id)},
            {"$unset": {"subscription_plan": ""}}  # Unset the subscription_plan field
        )

        if result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete subscription plan"
            )

        # Log the deletion
        loguru.logger.info(f"Subscription plan deleted for user {user_id}.")

        # Return success message
        return {
            "status": "success",
            "message": f"Subscription plan deleted for user {user_id}."
        }
    
@router.put('/update-gym-plan/{user_id}/{plan_id}', status_code=status.HTTP_200_OK)
async def update_gym_plan(
    user_id: str,  # User ID as a path parameter
    plan_id: str,  # Plan ID as a path parameter
    auth_user_id: str = Depends(oauth2.require_user)  # Ensure the user is authenticated
):
    """
    Update the gym subscription plan for the given user_id if the current plan is different from the new plan_id.
    Fetches the plan from GymPlans collection and updates the user's profile.
    """
    with handle_errors():
        # Fetch the new gym plan from the GymPlans collection
        gym_plan = GymPlans.find_one({"_id": ObjectId(plan_id)})
        
        if not gym_plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Gym plan with ID {plan_id} not found"
            )
        
        # Check if the user exists
        user = User.find_one({"_id": ObjectId(user_id)})
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )

        # Check if the user already has a subscription plan
        if "subscription_plan" in user:
            # Compare the existing plan with the new plan
            existing_plan = user["subscription_plan"]
            if existing_plan["plan_name"] == gym_plan["plan_name"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User already has this subscription plan"
                )
        
        # Prepare the new subscription plan data
        updated_plan = {
            "plan_name": gym_plan.get("plan_name"),
            "duration": gym_plan.get("duration"),
            "price": gym_plan.get("price"),
        }

        # Update the user's subscription_plan with the new plan
        result = User.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"subscription_plan": updated_plan}}  # Set the new subscription_plan field
        )

        if result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update subscription plan"
            )

        # Log the update
        loguru.logger.info(f"Subscription plan updated for user {user_id} to plan {plan_id}.")

        # Return success message
        return {
            "status": "success",
            "message": f"Subscription plan updated for user {user_id}."
        }