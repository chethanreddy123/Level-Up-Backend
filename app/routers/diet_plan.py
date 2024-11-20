# app/routers/diet_plan.py

from fastapi import APIRouter, Depends, HTTPException, status, Query, Form, File, UploadFile, Body
from bson.objectid import ObjectId
from typing import List, Optional
from datetime import datetime
from loguru import logger

from app.database import User, DietPlans, WorkoutandDietTracking, FoodItems, UserSlots
from app.schemas.diet_plan import DietPlan, DietPlanResponseSchema, UpdateDietPlanSchema
from app.utilities.error_handler import handle_errors
from .. import oauth2
from app.utilities.utils import get_current_ist_time
from app.utilities.firebase import upload_image_to_firebase
from pymongo.errors import PyMongoError

router = APIRouter()

@router.post('/diet-plan', status_code=status.HTTP_201_CREATED, response_model=DietPlanResponseSchema)
async def create_diet_plan(
    payload: DietPlan = Body(...),  # Explicitly specify that 'payload' is the request body
    user_id: str = Depends(oauth2.require_user)
):
    """
    Create a new diet plan for a specific user, using user_id as the diet_plan_id.
    """

    with handle_errors():
        logger.info(f"Creating diet plan for user ID: {payload.user_id}")

        # Convert user_id to ObjectId for MongoDB operations
        try:
            user_id = ObjectId(payload.user_id)
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format.")

        # Check if the user exists in the database
        existing_user = await User.find_one({"_id": user_id})
        if not existing_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found."
            )

        # Check if the diet plan already exists for the user
        existing_diet_plan = await DietPlans.find_one({"_id": user_id})
        if existing_diet_plan:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The Diet Plan for the user already exists."
            )

        # Prepare the diet plan data
        diet_plan_data = payload.dict()
        
        # Get the current time in IST from the helper function
        formatted_date, formatted_time = get_current_ist_time()

        # Combine the date and time into a single string
        datetime_str = f"{formatted_date} {formatted_time}"


        # Add timestamps for created_at and updated_at
        diet_plan_data["created_at"] = datetime_str
        diet_plan_data["updated_at"] = datetime_str

        # Set the user_id as the diet plan _id
        diet_plan_data["_id"] = user_id  # Use user_id as the diet plan _id

        # Insert the diet plan into DietPlans collection
        result = await DietPlans.insert_one(diet_plan_data)
        
        # Fetch the newly inserted diet plan from the collection using the user_id as _id
        new_diet_plan = await DietPlans.find_one({"_id": user_id})

        # Convert _id from ObjectId to string and return the response
        if new_diet_plan:
            new_diet_plan['_id'] = str(new_diet_plan['_id'])  # Convert ObjectId to string
            return DietPlanResponseSchema(diet_id=new_diet_plan['_id'], **new_diet_plan)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create diet plan."
        )


@router.get('/diet-plan', response_model=DietPlanResponseSchema)
async def get_diet_plan_for_user(
    user_id: str = Query(..., description="User ID to get the diet plan for"),
    auth_user_id: str = Depends(oauth2.require_user)
):
    """
    Retrieve the diet plan for a specific user by user_id.
    """
    try:
        # Convert user_id to ObjectId
        user_id = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format.")

    # Find the diet plan for the specific user
    diet_plan = await DietPlans.find_one({"_id": user_id})
    
    if not diet_plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Diet plan not found for this user."
        )

    # Helper function to populate food items
    async def populate_food_items(menu: List[str]) -> List[dict]:
        food_items = []
        for item_id in menu:
            food_item = await FoodItems.find_one({"_id": ObjectId(item_id)})
            if food_item:
                food_items.append({
                    "food_name": food_item["food_name"],
                    "energy_kcal": food_item.get("energy_kcal"),
                    "quantity": food_item.get("quantity"),
                    "carbohydrates": food_item.get("carbohydrates"),
                    "protein": food_item.get("protein"),
                })
        return food_items

    # Replace menu item IDs with FoodItem details
    if "menu_plan" in diet_plan:
        for time, details in diet_plan["menu_plan"]["timings"].items():
            details["menu"] = await populate_food_items(details["menu"])

    if "one_day_detox_plan" in diet_plan:
        for time, details in diet_plan["one_day_detox_plan"].items():
            details["menu"] = await populate_food_items(details["menu"])

    # Convert _id to string for the diet plan and format timestamps
    diet_plan["_id"] = str(diet_plan["_id"])
    diet_plan["created_at"] = diet_plan["created_at"]
    diet_plan["updated_at"] = diet_plan["updated_at"]

    # Return the response
    return DietPlanResponseSchema(
        diet_id=diet_plan["_id"],
        diet_name=diet_plan["diet_name"],
        bmi=diet_plan["bmi"],
        desired_weight=diet_plan["desired_weight"],
        desired_calories=diet_plan["desired_calories"],
        desired_proteins=diet_plan["desired_proteins"],
        menu_plan=diet_plan["menu_plan"],
        guidelines=diet_plan["guidelines"],
        one_day_detox_plan=diet_plan["one_day_detox_plan"],
        created_at=diet_plan["created_at"],
        updated_at=diet_plan["updated_at"]
    )

@router.put('/diet-plan/{user_id}', response_model=DietPlanResponseSchema)
async def update_diet_plan(
    user_id: str,
    payload: UpdateDietPlanSchema,
    auth_user_id: str = Depends(oauth2.require_user)
):
    """
    Update an existing diet plan for a specific user.
    """
    with handle_errors():
        # Validate diet_plan_id
        try:
            diet_plan_obj_id = ObjectId(user_id)
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid diet plan ID format.")

        # Prepare the update data by excluding None fields
        update_data = {k: v for k, v in payload.dict().items() if v is not None}

        if not update_data:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields provided for update.")

        # Get current time in IST form the helper function
        formatted_date, formatted_time = get_current_ist_time()

        # Combine them both into str
        datetime_str = f"{formatted_date} {formatted_time}"

        update_data["updated_at"] = datetime_str
        # Update the diet plan in the database
        update_result = await DietPlans.find_one_and_update(
            {"_id": diet_plan_obj_id, "user_id": user_id},
            {"$set": update_data},
            return_document=True
        )

        if not update_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Diet plan not found."
            )

        # Format the response
        update_result["_id"] = str(update_result["_id"])
        return DietPlanResponseSchema(diet_id=update_result["_id"],**update_result)


@router.delete('/diet-plan/{user_id}', status_code=status.HTTP_200_OK)
async def delete_diet_plan(
    user_id: str,
    auth_user_id: str = Depends(oauth2.require_user)
):
    """
    Delete a diet plan by its ID.
    """
    with handle_errors():
        # Validate diet_plan_id
        try:
            diet_plan_obj_id = ObjectId(user_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Invalid diet plan ID format."
            )

        # Attempt to delete the diet plan
        delete_result = await DietPlans.delete_one({"_id": diet_plan_obj_id, "user_id": user_id})
        if delete_result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Diet plan not found."
            )

        # Successful deletion does not return a body for HTTP 204
        return{
                "id": user_id,
                "message": "Diet plan deleted successfully"
        }


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



@router.post('/diet-plan/upload_diet_logs')
async def upload_diet_logs(
    food_name: str = Form(...),  # Required form field
    quantity: float = Form(...),  # Required quantity field
    units: Optional[str] = Form(None),  # Optional units field
    image: Optional[UploadFile] = File(None),  # Optional image file
    user_id: str = Depends(oauth2.require_user)  # Authenticated user ID
):
    """
    Uploads a diet log (food intake) for a user, storing the food information along with the uploaded image.
    If the same food has already been uploaded for the given date, returns an error.
    """
    with handle_errors():
        user_id = str(user_id)

        # Get the formatted date and time in IST
        formatted_date, formatted_time = get_current_ist_time()

        # Check if the food_name already exists for the given date and user in MongoDB
        existing_record = await WorkoutandDietTracking.find_one(
            {"_id": user_id, f"{formatted_date}.diet_logs": {"$elemMatch": {"food_name": food_name}}}
        )

        if existing_record:
            # If the food_name already exists for the date, raise an error
            raise HTTPException(
                status_code=400,
                detail=f"The info about {food_name.title()} has already been uploaded for {formatted_date}."
            )

        # Initialize image_url variable to None
        image_url = None

        if image:
            # Upload image to Firebase and get the URL
            image_url = upload_image_to_firebase(file=image, user_id=user_id, food_name=food_name)

        # Create the new diet log entry
        new_diet_log = {
            "food_name": food_name,
            "quantity": quantity,
            "units": units,
            "image_url": image_url,  # Can be None or a placeholder
            "uploaded_time": formatted_time
        }

        # Check if a record for this date already exists
        existing_record = await WorkoutandDietTracking.find_one({"_id": user_id, formatted_date: {"$exists": True}})

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
                await WorkoutandDietTracking.insert_one(new_record)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

            return {
                "status": "success",
                "message": f"Diet log for {food_name.title()} uploaded successfully on {formatted_date}!"
            }

        else:
            # If the record for the date already exists, we need to add the new diet log
            existing_diet_logs = existing_record.get(formatted_date, {}).get("diet_logs", [])

            # Ensure that the existing diet logs are a list
            if not isinstance(existing_diet_logs, list):
                existing_diet_logs = []  # Default to an empty list if not

            # Append the new diet log
            existing_diet_logs.append(new_diet_log)

            # Update the existing record with the new diet log
            try:
                await WorkoutandDietTracking.update_one(
                    {"_id": user_id},
                    {
                        "$set": {  # Use $set to add or update the date field
                            f"{formatted_date}.diet_logs": existing_diet_logs
                        }
                    }
                )
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

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


# @router.post('/dump-slots', status_code=status.HTTP_201_CREATED)
# async def dump_slot_info(payload: dict = Body(...)):
#     """
#     Dump the slot information into UserSlots collection. This is to be used only once.
#     """
#     # Log the slot info creation request
#     logger.info("Dumping slot information into UserSlots collection")
    
#     with handle_errors():
#         # Add ObjectId as the document's _id
#         payload["_id"] = ObjectId()
        
#         # Check if the slot information already exists in UserSlots by slot name
#         existing_slots = await UserSlots.find_one({"slot_name": payload["slot_name"]})
#         if existing_slots:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Slot information already exists."
#             )

#         # Insert the slot information into the UserSlots collection
#         result = await UserSlots.insert_one(payload)

#         if result.inserted_id:
#             return {"message": "Slot information successfully dumped."}
#         else:
#             raise HTTPException(
#                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#                 detail="Failed to dump slot information."
            # )