# from fastapi import APIRouter, HTTPException, Form, UploadFile, File, Depends
from fastapi import HTTPException
from firebase_admin import storage
from datetime import datetime
import mimetypes
import logging
# from typing import Optional
from uuid import uuid4
# from app.utilities.error_handler import handle_errors
# from app.database import WorkoutandDietTracking  # Assuming your MongoDB model is in models
# from app.utilities.utils import get_current_ist_time  # Assuming you have a utility function for IST time
# from .auth import oauth2  # Assuming you have an oauth2 dependency for user authentication

# router = APIRouter()

ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/jpg"]

# Setup logging for better error tracking
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def upload_image_to_firebase(file, user_id, food_name) -> str:
    """
    Uploads an image file to Firebase Storage under the folder structure:
    'level_up_images/{user_id}/{date}/{food_name}{extension}'.
    Returns the public URL if the image is uploaded successfully.
    If the same food image has been uploaded before, it raises an exception
    with the previous upload timestamp.
    """
    # Extract the content type (MIME type) of the uploaded file
    content_type = file.content_type

    # Validate that the file is one of the allowed image types
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise ValueError(f"Invalid file type: {content_type}. Only image files are allowed.")

    # Extract the file extension based on the content type
    extension = mimetypes.guess_extension(content_type)
    if not extension:
        raise ValueError("Unsupported file type")

    # Get the current date in the format 'MM-DD-YY'
    current_date = datetime.now().strftime("%d-%m-%y")

    # Define the file path with the folder structure: 'level_up_images/{user_id}/{date}/{food_name}{extension}'
    file_path = f"level_up_images/{user_id}/{current_date}/{food_name}{extension}"

    try:
        # Initialize Firebase Storage bucket
        bucket = storage.bucket()
        blob = bucket.blob(file_path)

        # Upload the new file to Firebase Storage
        logger.debug(f"Uploading file: {file.filename}")
        blob.upload_from_file(file.file, content_type=content_type)
        blob.make_public()

        # Return the public URL of the uploaded image
        logger.info(f"Image uploaded successfully. Public URL: {blob.public_url}")
        return blob.public_url
    
    except Exception as e:
        logger.error(f"Error during file upload: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error uploading file to Firebase: {str(e)}")



# @router.post('/diet-plan/upload_diet_log')
# async def upload_diet_logs(
#     food_name: str = Form(...),  # Required form field
#     quantity: float = Form(...),  # Required quantity field
#     units: Optional[str] = Form(None),  # Optional units field
#     image: Optional[UploadFile] = File(None),  # Optional image file
#     user_id: str = Depends(oauth2.require_user)  # Authenticated user ID
# ):
#     """
#     Uploads a diet log entry for a user, including food details and an optional image.
#     Checks if the food has already been uploaded for the given date and user.
#     If no entry exists for the date, it creates a new entry; otherwise, it appends the new diet log.
#     """
    
#     with handle_errors():
#         user_id = str(user_id)

#         # Get the formatted date and time in IST
#         formatted_date, formatted_time = get_current_ist_time()

#         # Check if the food_name already exists for the given date and user in MongoDB
#         existing_record = WorkoutandDietTracking.find_one(
#             {"_id": user_id, f"{formatted_date}.diet_logs": {"$elemMatch": {"food_name": food_name}}}
#         )
#         if existing_record:
#             raise HTTPException(
#                 status_code=400,
#                 detail=f"The info about {food_name.title()} has already been uploaded for {formatted_date}."
#             )

#         # Initialize image_url variable to None
#         image_url = None
#         if image:
#             try:
#                 # Debugging: Log file attributes to ensure it's received correctly
#                 logger.debug(f"Received image: {image.filename}, Content type: {image.content_type}")

#                 # Upload image to Firebase and get the URL
#                 image_url = upload_image_to_firebase(file=image, user_id=user_id, food_name=food_name)
#                 logger.debug(f"Image uploaded successfully, URL: {image_url}")

#             except Exception as e:
#                 logger.error(f"Failed to upload image to Firebase: {str(e)}")
#                 raise HTTPException(status_code=500, detail="Image upload failed")

#         # Create the new diet log entry
#         new_diet_log = {
#             "food_name": food_name,
#             "quantity": quantity,
#             "units": units,
#             "image_url": image_url,  # Can be None or a placeholder
#             "uploaded_time": formatted_time
#         }

#         # Find the existing user record
#         existing_record = WorkoutandDietTracking.find_one({"_id": user_id})

#         if existing_record:
#             # Check if the specific date field (e.g., '21-11-2024') exists
#             if formatted_date in existing_record:
#                 # If the date exists, append the new diet log to that date's diet_logs array
#                 try:
#                     WorkoutandDietTracking.update_one(
#                         {"_id": user_id},
#                         {
#                             "$push": {f"{formatted_date}.diet_logs": new_diet_log}
#                         }
#                     )
#                     return {
#                         "status": "success",
#                         "message": f"Diet log for {food_name.title()} uploaded successfully on {formatted_date}!",
#                         "image_url": image_url  # Return the image URL here
#                     }
#                 except Exception as e:
#                     logger.error(f"Failed to update diet logs for {formatted_date}: {str(e)}")
#                     raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
#             else:
#                 # If the date does not exist, create the new date field and initialize diet_logs
#                 try:
#                     WorkoutandDietTracking.update_one(
#                         {"_id": user_id},
#                         {
#                             "$set": {  # Use $set to create a new date field if it doesn't exist
#                                 f"{formatted_date}": {
#                                     "workout_logs": [],  # Empty workout_logs for the new date
#                                     "diet_logs": [new_diet_log]  # Add the new diet log for today
#                                 }
#                             }
#                         }
#                     )
#                     return {
#                         "status": "success",
#                         "message": f"Diet log for {food_name.title()} uploaded successfully on {formatted_date}!",
#                         "image_url": image_url  # Return the image URL here
#                     }
#                 except Exception as e:
#                     logger.error(f"Failed to set diet logs for {formatted_date}: {str(e)}")
#                     raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

#         else:
#             # If the user record doesn't exist, handle this case (optional)
#             raise HTTPException(status_code=404, detail="User not found")
