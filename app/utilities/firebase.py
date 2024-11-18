from firebase_admin import storage
from uuid import uuid4
import mimetypes
from datetime import datetime
from fastapi import HTTPException

ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/jpg"]

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

    # Initialize Firebase Storage bucket
    bucket = storage.bucket()
    blob = bucket.blob(file_path)

    # Upload the new file to Firebase Storage
    blob.upload_from_file(file.file, content_type=content_type)
    
    # Make the file publicly accessible
    blob.make_public()

    # Return the public URL of the uploaded image
    return blob.public_url
