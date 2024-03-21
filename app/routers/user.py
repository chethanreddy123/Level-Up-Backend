from fastapi import APIRouter, Depends
from bson.objectid import ObjectId
from datetime import datetime, timedelta
from app.serializers.userSerializers import userResponseEntity, userRegistrationEntity
from app.utilities.error_handler import handle_errors
from app.database import Registrations
from app.utilities.email_services import send_email

from app.database import User
from .. import  oauth2
from app.schemas import user

router = APIRouter()


@router.get('/me', response_model= user.UserResponse)
def get_me(user_id: str = Depends(oauth2.require_user)):
    with handle_errors():
        user = userResponseEntity(User.find_one({'_id': ObjectId(str(user_id))}))
        return {"status": "success", "user": user}



@router.post('/new_registration')
async def new_registration(payload: user.UserRegistration , user_id: str = Depends(oauth2.require_user)):
    with handle_errors():
        payload.set_created_timestamp()
        payload.set_updated_timestamp()

        result = Registrations.insert_one(payload.dict())
        new_user = Registrations.find_one({'_id': result.inserted_id})

        await send_email(
            sender_email="aioverflow.ml@gmail.com",
            sender_password="iyfngcdhgfcbkufv", # Need to get it from config
            to_email=new_user['email'],
            cc_emails=None,
            subject="Welcome to Our Gym App!",
            message=f"Hi {new_user['name']},\n\nThank you for registering with our gym app!\n\nDownload the app and start your fitness journey.\n\nBest regards,\nThe Gym Team"
        )

        return {"status": "success", "user": userRegistrationEntity(new_user)}

