# app/routers/diet_plan.py

from fastapi import APIRouter, Depends, HTTPException, status, Query, Form, File, UploadFile 
from bson.objectid import ObjectId
from typing import List, Optional
from datetime import datetime
from loguru import logger

from app.database import User, DietPlans, WorkoutandDietTracking
from app.schemas.diet_plan import DietPlanSchema, DietPlanResponseSchema
from app.utilities.error_handler import handle_errors
from .. import oauth2
from app.utilities.utils import get_current_ist_time
from app.utilities.firebase import upload_image_to_firebase
from pymongo.errors import PyMongoError

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


# # Retrieve all diet plans for a user
# @router.get('/diet-plans', response_model=List[DietPlanResponseSchema])
# async def get_all_diet_plans(
#     user_id: str = Query(..., description="User ID to get diet plans for")
# ):
#     """
#     Retrieve all diet plans for a specific user.
#     """
#     with handle_errors():
#         try:
#             user_id = ObjectId(user_id)
#         except Exception:
#             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format.")

#         diet_plans = list(DietPlans.find({"user_id": str(user_id)}))
#         return [DietPlanResponseSchema(id=str(dp["_id"]), **dp) for dp in diet_plans]


# # Update a diet plan
# @router.put('/diet-plan/{diet_plan_id}', response_model=DietPlanResponseSchema)
# async def update_diet_plan(
#     diet_plan_id: str,
#     payload: DietPlanSchema,
#     user_id: str = Depends(oauth2.require_user)
# ):
#     """
#     Update an existing diet plan for a specific user.
#     """
#     with handle_errors():
#         try:
#             diet_plan_obj_id = ObjectId(diet_plan_id)
#         except Exception:
#             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid diet plan ID format.")

#         # Remove None fields from the update payload
#         update_data = {k: v for k, v in payload.dict().items() if v is not None}

#         # Update diet plan in the collection
#         update_result = DietPlans.find_one_and_update(
#             {"_id": diet_plan_obj_id, "user_id": user_id},
#             {"$set": update_data},
#             return_document=True
#         )

#         if not update_result:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="Diet plan not found."
#             )

#         return DietPlanResponseSchema(id=str(update_result["_id"]), **update_result)


# # Delete a diet plan
# @router.delete('/diet-plan/{diet_plan_id}', status_code=status.HTTP_204_NO_CONTENT)
# async def delete_diet_plan(
#     diet_plan_id: str,
#     user_id: str = Depends(oauth2.require_user)
# ):
#     """
#     Delete a diet plan by its ID.
#     """
#     with handle_errors():
#         try:
#             diet_plan_obj_id = ObjectId(diet_plan_id)
#         except Exception:
#             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid diet plan ID format.")

#         delete_result = DietPlans.delete_one({"_id": diet_plan_obj_id, "user_id": user_id})
#         if delete_result.deleted_count == 0:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="Diet plan not found."
#             )

#         return {"message": "Diet plan deleted successfully!"}



# Route to upload the diet by the user from the mobile app 
@router.post('/diet-plan/upload_diet_logs')
async def upload_diet_logs(
    food_name: str = Form(...),  # food_name is a required form field
    quantity: float = Form(...),  # quantity is a required form field (as a float)
    units: Optional[str] = Form(None),  # units is an optional form field
    image: Optional[UploadFile] = File(None),  # image is an optional file upload
    user_id: str = Depends(oauth2.require_user)  # assuming authentication dependency
):
    """
    Uploads a diet log (food intake) for a user, storing the food information along with the uploaded image.
    If the same food has already been uploaded for the given date, returns an error.
    """
    with handle_errors():
        user_id = str(user_id)

        # Get the formatted date and time in IST
        formatted_date, formatted_time = get_current_ist_time()


        # Check if the food_name already exists for the given date in MongoDB
        existing_record = WorkoutandDietTracking.find_one(
            {"_id": user_id, f"{formatted_date}.diet_logs.food_name": food_name}
        )

        if existing_record:
            # If the food_name already exists for the date, raise an error
            raise HTTPException(
                status_code=400,
                detail=f"The Info about {food_name.title()} has already been uploaded for {formatted_date}."
            )

        # Initialize image_url variable to None
        image_url = None
        
        if image:
            # Upload image to Firebase and get the URL
            image_url = upload_image_to_firebase(file=image, user_id=user_id, food_name=food_name)

        # If no existing record for the food_name, proceed to create a new record
        new_diet_log = {
            "food_name": food_name,
            "quantity": quantity,
            "units": units,
            "image_url": image_url,  # Can be None or a placeholder
            "uploaded_time": formatted_time
        }

        # Check if a record for this date already exists
        existing_record = WorkoutandDietTracking.find_one({"_id": user_id, formatted_date: {"$exists": True}})

        if not existing_record:
            # If no record exists for this date, create a new record for the user
            new_record = {
                "_id": user_id,
                formatted_date: {
                    "workout_logs": [],  # Initially empty workout logs
                    "diet_logs": [new_diet_log]  # New diet log for today
                }
            }

            try:
                # Insert the new diet data into MongoDB
                WorkoutandDietTracking.insert_one(new_record)
            except PyMongoError as e:
                raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

            return {
                "status": "success",
                "message": f"Diet log for {food_name.title()} uploaded successfully on {formatted_date}!"
            }

        else:
            # If the record for the date already exists, we need to add the new diet log
            existing_diet_logs = existing_record.get(formatted_date, {}).get("diet_logs", [])

            # Check if `diet_logs` is a list (add validation)
            if not isinstance(existing_diet_logs, list):
                existing_diet_logs = []  # Default to an empty list if not



            # Append the new diet log
            existing_diet_logs.append(new_diet_log)

            # Update the existing record with the new diet log
            result = WorkoutandDietTracking.update_one(
                {"_id": user_id},
                {
                    "$set": {  # Use $set to add or update the date field
                        f"{formatted_date}.diet_logs": existing_diet_logs
                    }
                },
                upsert=True  # Ensure the date field gets created if it doesn't exist
            )


            return {
                "status": "success",
                "message": f"Diet log for {food_name.title()} uploaded successfully on {formatted_date}!"
            }
        

# Route to display the diet details uploaded by the user to the admin (trainer)
@router.get('/diet-plan/{date}')
async def get_diet_logs(
    date: str,  # Path parameter for date
    user_id: str = Depends(oauth2.require_user)  # This will get the authenticated user ID
):
    """
    Fetches the diet logs for a specific user and date from MongoDB.
    """
    with handle_errors():
        # Get the user_id from the authenticated user
        user_id = str(user_id)

        # Parse the formatted date (assuming it's in the format "dd-mm-yyyy")
        formatted_date = date  # You can apply any necessary formatting here if required

        # Find the record for the given user and date in the MongoDB collection
        existing_record = WorkoutandDietTracking.find_one(
            {"_id": user_id, formatted_date: {"$exists": True}}
        )

        if not existing_record:
            raise HTTPException(
                status_code=404,
                detail=f"No diet logs found for user {user_id} on {formatted_date}."
            )

        # Extract the diet logs for the given date
        diet_logs = existing_record.get(formatted_date, {}).get("diet_logs", [])

        # Return the diet logs for the specific date
        return {
            "status": "success",
            "diet_logs": diet_logs
        }
