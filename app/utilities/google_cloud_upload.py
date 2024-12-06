from fastapi import APIRouter, HTTPException, Form, UploadFile, File, Depends
from google.cloud import storage
from datetime import datetime
import mimetypes
import logging
from uuid import uuid4
from app import oauth2  
from app.database import initialize_google_cloud  


router = APIRouter()

ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/jpg"]

import logging

# Configure logging to display debug messages
logging.basicConfig(
    level=logging.DEBUG,  # Set the log level to DEBUG
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Custom log format
    handlers=[
        logging.StreamHandler()  # Output logs to the console (terminal)
    ]
)

# Example usage
logger = logging.getLogger(__name__)


def upload_image_to_gcs(file, folder_name, file_name) -> str:
    """
    Base function to upload an image file to Google Cloud Storage under a given folder structure.
    Returns the public URL of the uploaded image.
    """
    try:
        # Ensure file content type is valid
        content_type = file.content_type
        logger.debug(f"Received file: {file.filename}, Content type: {content_type}")

        # Validate that the file is one of the allowed image types
        if content_type not in ALLOWED_IMAGE_TYPES:
            raise ValueError(f"Invalid file type: {content_type}. Only image files are allowed.")

        # Extract the file extension based on content type
        extension = mimetypes.guess_extension(content_type) or ".jpg"  # Default to .jpg if extension is None
        if not extension:
            raise ValueError("Unsupported file type")

        # Construct the file path
        file_path = f"{folder_name}/{file_name}{extension}"

        # Initialize Google Cloud Storage bucket
        bucket = initialize_google_cloud()  # Initialize GCS
        if not bucket:
            raise ValueError("Google Cloud Storage bucket initialization failed.")
        
        # Upload the file to the bucket
        blob = bucket.blob(file_path)
        logger.debug(f"Uploading file: {file.filename} to GCS at path: {file_path}")
        
        # Reset the file pointer in case it's been read already
        file.file.seek(0)

        # Upload the file from the stream
        blob.upload_from_file(file.file, content_type=content_type)
        blob.make_public()  # Make the file public

        # Return the public URL of the uploaded image
        image_url = blob.public_url
        logger.info(f"Image uploaded successfully. Public URL: {image_url}")
        return image_url

    except Exception as e:
        logger.error(f"Error during file upload: {str(e)}")
        raise Exception(f"Error uploading file to Google Cloud Storage: {str(e)}")



def upload_diet_log_image(file, user_id, food_name) -> str:
    """
    Upload a diet log image by the User to Google Cloud Storage.
    The folder structure will be: 'level_up/diet_logs/{user_id}/{date}/{food_name}{extension}'.
    """
    # Format the current date for the folder structure
    current_date = datetime.now().strftime("%d-%m-%y")
    folder_name = f"level_up/user_images/{user_id}/diet_logs/{current_date}"  # Folder for diet logs, user-specific
    return upload_image_to_gcs(file, folder_name, food_name)


def upload_exercise_image(file, exercise_name) -> str:
    """
    Upload an exercise image to Google Cloud Storage.
    The folder structure will be: 'level_up/exercises/{exercise_name}{extension}'.
    """
    folder_name = "exercises"  # Folder for exercise images
    return upload_image_to_gcs(file, folder_name, exercise_name)


def upload_food_item_image(file, food_name) -> str:
    """
    Upload a food item image to Google Cloud Storage.
    The folder structure will be: 'level_up/food_items/{food_name}{extension}'.
    """
    folder_name = "level_up/food_items"  # Folder for food item images
    return upload_image_to_gcs(file, folder_name, food_name)


def upload_profile_image(file, user_id, file_name) -> str:
    """
    Upload the profile photo by the User and store it in the Google Cloud Storage.
    The folder structure will be: 'level_up/profile_photos/{user_id}/photo{extension}'.
    """
    folder_name = f"level_up/user_images/{user_id}/profile_photo"
    return upload_image_to_gcs(file, folder_name, file_name )


def upload_gym_plan_image(file, plan_name) -> str:
    """
    Upload the Gym Plan photo by the ADMIN/TRAINER and store it in the Google Cloud Storage.
    The folder structure will be: 'level_up/subscription_plan_images/{plan_name}{extension}'.
    """
    folder_name = "level_up/subscription_plan_images"
    return upload_image_to_gcs(file, folder_name, plan_name )


def upload_weight_image(file: UploadFile, user_id: str, file_name: str) -> str:
    """
    Upload the weight image to the Google Cloud Storage in the path:
    level_up/user_images/{user_id}/weight_track/{file_name}
    """
    folder_name = f"level_up/user_images/{user_id}/weight_track"
    return upload_image_to_gcs(file, folder_name, file_name)


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
