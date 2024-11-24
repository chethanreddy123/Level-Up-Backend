# app/routers/diet_plan.py

import mimetypes
from firebase_admin import storage
from fastapi import APIRouter, Depends, HTTPException, status, Query, Form, File, UploadFile, Body
from bson.objectid import ObjectId
from typing import List, Optional
from datetime import datetime, timedelta
from loguru import logger

from app.database import User, DietPlans, WorkoutandDietTracking, FoodItems, UserSlots
from app.schemas.diet_plan import DietPlan, DietPlanResponseSchema, UpdateDietPlanSchema
from app.utilities.error_handler import handle_errors
from .. import oauth2
from app.utilities.utils import get_current_ist_time
from app.utilities.firebase_upload import upload_image_to_firebase
from pymongo.errors import PyMongoError

router = APIRouter()



@router.post('/diet-plan', status_code=status.HTTP_201_CREATED, response_model=DietPlanResponseSchema)
async def create_diet_plan(
    payload: DietPlan = Body(...),  # Explicitly specify that 'payload' is the request body
    user_id: str = Depends(oauth2.require_user)
):
    """
    Create a new diet plan for a specific user, using user_id as the diet_plan_id.
    Also adds the diet plan details (name, id) to the User document under diet_plan.
    """

    with handle_errors():
        logger.info(f"Creating diet plan for user ID: {payload.user_id}")

        # Convert user_id to ObjectId for MongoDB operations
        try:
            user_id = ObjectId(payload.user_id)
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format.")

        # Check if the user exists in the database
        existing_user = User.find_one({"_id": user_id})
        if not existing_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found."
            )

        # Check if the diet plan already exists for the user
        existing_diet_plan = DietPlans.find_one({"_id": user_id})
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
        result = DietPlans.insert_one(diet_plan_data)

        # Fetch the newly inserted diet plan from the collection using the user_id as _id
        new_diet_plan = DietPlans.find_one({"_id": user_id})

        # Convert _id from ObjectId to string and return the response
        if new_diet_plan:
            new_diet_plan['_id'] = str(new_diet_plan['_id'])  # Convert ObjectId to string

            # Add the diet plan details to the User document
            user_update_result = User.update_one(
                {"_id": user_id},
                {
                    "$set": {
                        "diet_plan": {
                            "diet_plan_id": new_diet_plan["_id"],
                            "diet_plan_name": new_diet_plan.get("diet_name", "Unknown")
                        }
                    }
                }
            )

            if user_update_result.modified_count == 0:
                logger.error(f"Failed to update user with diet plan details")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update user with diet plan details."
                )

            return DietPlanResponseSchema(diet_id=new_diet_plan['_id'], **new_diet_plan)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create diet plan."
        )


@router.get('/diet-plan/{user_id}', response_model=DietPlanResponseSchema)
async def get_diet_plan_for_user(
    user_id: str,
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
    diet_plan =  DietPlans.find_one({"_id": user_id})
    
    if not diet_plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Diet plan not found for this user."
        )

    # Helper function to populate food items
    def populate_food_items(menu: List[str]) -> List[dict]:
        food_items = []
        for item_id in menu:
            food_item =  FoodItems.find_one({"_id": ObjectId(item_id)})
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
            details["menu"] =  populate_food_items(details["menu"])

    if "one_day_detox_plan" in diet_plan:
        for time, details in diet_plan["one_day_detox_plan"].items():
            details["menu"] =  populate_food_items(details["menu"])

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
        update_result =  DietPlans.find_one_and_update(
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
        delete_result =  DietPlans.delete_one({"_id": diet_plan_obj_id, "user_id": user_id})
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


# ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/jpg"]

# def upload_image_to_firebase(file, user_id, food_name) -> str:
#     """
#     Uploads an image file to Firebase Storage under the folder structure:
#     'level_up_images/{user_id}/{date}/{food_name}{extension}'.
#     Returns the public URL if the image is uploaded successfully.
#     If the same food image has been uploaded before, it raises an exception
#     with the previous upload timestamp.
#     """
#     # Extract the content type (MIME type) of the uploaded file
#     content_type = file.content_type

#     # Validate that the file is one of the allowed image types
#     if content_type not in ALLOWED_IMAGE_TYPES:
#         raise ValueError(f"Invalid file type: {content_type}. Only image files are allowed.")

#     # Extract the file extension based on the content type
#     extension = mimetypes.guess_extension(content_type)
#     if not extension:
#         raise ValueError("Unsupported file type")

#     # Get the current date in the format 'MM-DD-YY'
#     current_date = datetime.now().strftime("%d-%m-%y")

#     # Define the file path with the folder structure: 'level_up_images/{user_id}/{date}/{food_name}{extension}'
#     file_path = f"level_up_images/{user_id}/{current_date}/{food_name}{extension}"

#     try:
#         # Initialize Firebase Storage bucket
#         bucket = storage.bucket()
#         blob = bucket.blob(file_path)

#         # Upload the new file to Firebase Storage
#         logger.debug(f"Uploading file: {file.filename}")
#         blob.upload_from_file(file.file, content_type=content_type)
#         blob.make_public()

#         # Return the public URL of the uploaded image
#         logger.info(f"Image uploaded successfully. Public URL: {blob.public_url}")
#         return blob.public_url
    
#     except Exception as e:
#         logger.error(f"Error during file upload: {str(e)}")
#         raise HTTPException(status_code=500, detail=f"Error uploading file to Firebase: {str(e)}")



@router.post('/diet-plan/upload_diet_logs')
async def upload_diet_logs(
    food_name: str = Form(...),  # Required form field
    quantity: float = Form(...),  # Required quantity field
    units: Optional[str] = Form(None),  # Optional units field
    image: Optional[UploadFile] = File(None),  # Optional image file
    user_id: str = Depends(oauth2.require_user)  # Authenticated user ID
):
    """
    Uploads a diet log entry for a user, including food details and an optional image.
    Checks if the food has already been uploaded for the given date and user.
    If no entry exists for the date, it creates a new entry; otherwise, it appends the new diet log.
    """
    
    with handle_errors():
        user_id = str(user_id)

        # Get the formatted date and time in IST
        formatted_date, formatted_time = get_current_ist_time()

        # Check if the food_name already exists for the given date and user in MongoDB
        existing_record = WorkoutandDietTracking.find_one(
            {"_id": user_id, f"{formatted_date}.diet_logs": {"$elemMatch": {"food_name": food_name}}}
        )
        if existing_record:
            raise HTTPException(
                status_code=400,
                detail=f"The info about {food_name.title()} has already been uploaded for {formatted_date}."
            )

        # Initialize image_url variable to None
        image_url = None
        if image:
            try:
                # Debugging: Log file attributes to ensure it's received correctly
                logger.debug(f"Received image: {image.filename}, Content type: {image.content_type}")

                # Upload image to Firebase and get the URL
                image_url = upload_image_to_firebase(file=image, user_id=user_id, food_name=food_name, folder_name='diet_log_images')
                logger.debug(f"Image uploaded successfully, URL: {image_url}")

            except Exception as e:
                logger.error(f"Failed to upload image to Firebase: {str(e)}")
                raise HTTPException(status_code=500, detail="Image upload failed")

        # Create the new diet log entry
        new_diet_log = {
            "food_name": food_name,
            "quantity": quantity,
            "units": units,
            "image_url": image_url,  # Can be None or a placeholder
            "uploaded_time": formatted_time
        }

        # Find the existing user record
        existing_record = WorkoutandDietTracking.find_one({"_id": user_id})

        if existing_record:
            # Check if the specific date field (e.g., '21-11-2024') exists
            if formatted_date in existing_record:
                # If the date exists, append the new diet log to that date's diet_logs array
                try:
                    WorkoutandDietTracking.update_one(
                        {"_id": user_id},
                        {
                            "$push": {f"{formatted_date}.diet_logs": new_diet_log}
                        }
                    )
                    return {
                        "status": "success",
                        "message": f"Diet log for {food_name.title()} uploaded successfully on {formatted_date}!",
                        "image_url": image_url  # Return the image URL here
                    }
                except Exception as e:
                    logger.error(f"Failed to update diet logs for {formatted_date}: {str(e)}")
                    raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
            else:
                # If the date does not exist, create the new date field and initialize diet_logs
                try:
                    WorkoutandDietTracking.update_one(
                        {"_id": user_id},
                        {
                            "$set": {  # Use $set to create a new date field if it doesn't exist
                                f"{formatted_date}": {
                                    "workout_logs": [],  # Empty workout_logs for the new date
                                    "diet_logs": [new_diet_log]  # Add the new diet log for today
                                }
                            }
                        }
                    )
                    return {
                        "status": "success",
                        "message": f"Diet log for {food_name.title()} uploaded successfully on {formatted_date}!",
                        "image_url": image_url  # Return the image URL here
                    }
                except Exception as e:
                    logger.error(f"Failed to set diet logs for {formatted_date}: {str(e)}")
                    raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

        else:
            # If the user record doesn't exist, handle this case (optional)
            raise HTTPException(status_code=404, detail="User not found")



# Route to display the diet details uploaded by the user to the admin (trainer)
@router.get('/diet-plan/get_diet_logs/{user_id}')
async def get_diet_logs(
    user_id: str,
    from_date: str = Query(..., description="Start date for diet logs (format: dd-mm-yyyy)"),
    to_date: str = Query(..., description="End date for diet logs (format: dd-mm-yyyy)"),
    auth_user_id: str = Depends(oauth2.require_user)  # This will get the authenticated user ID
):
    """
    Fetches the diet logs for a specific user within a date range from MongoDB.
    The food items for each date will be grouped into a list.
    If no logs are found for a specific day, or if the date doesn't exist, 
    the message 'No diet logs for this date' will be returned.
    """
    with handle_errors():
        # Ensure user_id is a string (in case it's not already)
        user_id = str(user_id)

        # Convert the string dates to datetime objects for comparison
        try:
            from_date = datetime.strptime(from_date, "%d-%m-%Y")
            to_date = datetime.strptime(to_date, "%d-%m-%Y")
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid date format. Please use 'dd-mm-yyyy'."
            )

        # Fetch the record for the specific user
        existing_record = WorkoutandDietTracking.find_one({"_id": user_id})

        if not existing_record:
            raise HTTPException(
                status_code=404,
                detail=f"No diet logs found for user {user_id}."
            )

        # Initialize a dictionary to group the diet logs by date
        grouped_diet_logs = {}

        # Iterate through all the dates in the range
        current_date = from_date
        while current_date <= to_date:
            date_key = current_date.strftime("%d-%m-%Y")  # Format the date to match MongoDB's date format

            # Check if the date exists in the database
            date_data = existing_record.get(date_key)

            if date_data:
                # If there are diet logs for this date, use them
                food_items = date_data.get("diet_logs", [])
                if food_items:
                    grouped_diet_logs[date_key] = food_items
                else:
                    # If no food items for this date, add the "No diet logs for this date" message
                    grouped_diet_logs[date_key] = "No diet logs for this date"
            else:
                # If the date doesn't exist, return the "No diet logs for this date" message
                grouped_diet_logs[date_key] = "No diet logs for this date"

            # Move to the next date
            current_date += timedelta(days=1)

        # Return the grouped diet logs for the specified date range
        return {
            "status": "success",
            "diet_logs": grouped_diet_logs
        }
    

ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/jpg"]

@router.post("/upload-image/")
async def upload_image(file: UploadFile = File(None)):
    """
    Upload an image to Firebase Storage.
    """
    content_type = file.content_type

    # Validate file type
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Invalid file type. Only image files are allowed.")

    # Extract the file extension
    extension = mimetypes.guess_extension(content_type)
    if not extension:
        raise HTTPException(status_code=400, detail="Unsupported file type.")

    # Define the file path (you can customize this based on your needs)
    file_name = f"level_up/images/{file.filename}"

    try:
        # Upload the image to Firebase Storage
        bucket = storage.bucket()
        blob = bucket.blob(file_name)

        # Upload the file
        blob.upload_from_file(file.file, content_type=content_type)
        blob.make_public()  # Make the file publicly accessible (optional)

        # Return the public URL of the uploaded image
        logger.info(f"Image uploaded successfully: {blob.public_url}")
        return {"url": blob.public_url}

    except Exception as e:
        logger.error(f"Error uploading image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error uploading image: {str(e)}")