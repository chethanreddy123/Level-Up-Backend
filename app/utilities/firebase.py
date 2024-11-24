# from firebase_admin import storage
# from uuid import uuid4
# import mimetypes
# from datetime import datetime
# from fastapi import HTTPException
# import logging

# ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/jpg"]

# def upload_image_to_firebase(file, user_id, food_name) -> str:
#     """
#     Uploads an image file to Firebase Storage and returns the URL.
#     """
#     content_type = file.content_type
#     if content_type not in ALLOWED_IMAGE_TYPES:
#         raise ValueError(f"Invalid file type: {content_type}. Only image files are allowed.")
    
#     extension = mimetypes.guess_extension(content_type)
#     if not extension:
#         raise ValueError("Unsupported file type")
    
#     current_date = datetime.now().strftime("%d-%m-%y")
#     file_path = f"level_up_images/rough/{current_date}/{food_name}{extension}"

#     # Initialize Firebase Storage bucket
#     bucket = storage.bucket()
#     blob = bucket.blob(file_path)

#     try:
#         blob.upload_from_file(file.file, content_type=content_type)
#         blob.make_public()  # Make the file publicly accessible
#         logging.debug(f"File uploaded successfully. Public URL: {blob.public_url}")
#         return blob.public_url
#     except Exception as e:
#         logging.error(f"Error uploading file to Firebase: {str(e)}")
#         raise HTTPException(status_code=500, detail=f"Error uploading file to Firebase: {str(e)}")


