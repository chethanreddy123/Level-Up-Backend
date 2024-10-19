from datetime import datetime, timedelta
from bson.objectid import ObjectId
from fastapi import APIRouter, Response, status, Depends, HTTPException
import loguru

from app.utilities.error_handler import handle_errors
from app.utilities.email_services import send_email
from app.utilities.utils import get_next_registration_id

from app import oauth2
from app.database import User
from app.serializers.userSerializers import userEntity, userResponseEntity
from app.utilities import utils
from app.schemas import user
from app.oauth2 import AuthJWT
from config import settings


router = APIRouter()
ACCESS_TOKEN_EXPIRES_IN = settings.ACCESS_TOKEN_EXPIRES_IN
REFRESH_TOKEN_EXPIRES_IN = settings.REFRESH_TOKEN_EXPIRES_IN


@router.post('/register', status_code=status.HTTP_201_CREATED, response_model=user.UserResponse)
async def create_user(payload: user.CreateUserSchema):
    with handle_errors():
        # Check if user already exist
        user = User.find_one({'email': payload.email.lower()})
        if user:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail='Account already exist')
        # Compare password and password_confirm
        if payload.password != payload.password_confirm:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail='Passwords do not match')
        #  Hash the password
        payload.password = utils.hash_password(payload.password)
        del payload.password_confirm
        payload.role = payload.role or 'CUSTOMER'
        payload.verified = True
        payload.email = payload.email.lower()
        payload.created_at = datetime.utcnow()
        payload.updated_at = payload.created_at

        # creating the Registration ID
        payload.registration_id = get_next_registration_id()

        # For CUSTOMER role, we need to create a new registration id and send an email
        if payload.role == 'CUSTOMER':
            try:
                await send_email(
                    sender_email="aioverflow.ml@gmail.com",
                    sender_password="tvnt qtww egyq ktes", # Need to get it from config
                    to_email=payload.email,
                    cc_emails=None,
                    subject="Welcome to Our Gym App!",
                    message=f"Hi {payload.name},\n\nThank you for registering with our gym app!\n\nDownload the app and start your fitness journey.\n\nBest regards,\nThe Gym Team"
                )
            except Exception as e:
                loguru.logger.error(f"Error sending email or reg id creation: {e}")

        result = User.insert_one(payload.dict())
        new_user = userResponseEntity(
            User.find_one({'_id': result.inserted_id}))
        return {"status": "success", "user": new_user}



@router.post('/login')
def login(payload: user.LoginUserSchema, response: Response, Authorize: AuthJWT = Depends()):
    with handle_errors():
        # Check if the user exist
        db_user = User.find_one({'email': payload.email.lower()})
        if not db_user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail='Incorrect Email or Password')
        user = userEntity(db_user)

        # Check if the password is valid
        if not utils.verify_password(payload.password, user['password']):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail='Incorrect Email or Password')

        # Create access token
        access_token = Authorize.create_access_token(
            subject=str(user["id"]), expires_time=timedelta(minutes=ACCESS_TOKEN_EXPIRES_IN))

        # Create refresh token
        refresh_token = Authorize.create_refresh_token(
            subject=str(user["id"]), expires_time=timedelta(minutes=REFRESH_TOKEN_EXPIRES_IN))

        # Store refresh and access tokens in cookie
        response.set_cookie('access_token', access_token, ACCESS_TOKEN_EXPIRES_IN * 60,
                            ACCESS_TOKEN_EXPIRES_IN * 60, '/', None, False, True, 'lax')
        response.set_cookie('refresh_token', refresh_token,
                            REFRESH_TOKEN_EXPIRES_IN * 60, REFRESH_TOKEN_EXPIRES_IN * 60, '/', None, False, True, 'lax')
        response.set_cookie('logged_in', 'True', ACCESS_TOKEN_EXPIRES_IN * 60,
                            ACCESS_TOKEN_EXPIRES_IN * 60, '/', None, False, False, 'lax')

        # Send both access
        return {'status': 'success', 'access_token': access_token}


@router.get('/refresh')
def refresh_token(response: Response, Authorize: AuthJWT = Depends()):
    with handle_errors():
        try:
            Authorize.jwt_refresh_token_required()

            user_id = Authorize.get_jwt_subject()
            if not user_id:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                    detail='Could not refresh access token')
            user = userEntity(User.find_one({'_id': ObjectId(str(user_id))}))
            if not user:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                    detail='The user belonging to this token no logger exist')
            access_token = Authorize.create_access_token(
                subject=str(user["id"]), expires_time=timedelta(minutes=ACCESS_TOKEN_EXPIRES_IN))
        except Exception as e:
            error = e.__class__.__name__
            if error == 'MissingTokenError':
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail='Please provide refresh token')
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=error)

        response.set_cookie('access_token', access_token, ACCESS_TOKEN_EXPIRES_IN * 60,
                            ACCESS_TOKEN_EXPIRES_IN * 60, '/', None, False, True, 'lax')
        response.set_cookie('logged_in', 'True', ACCESS_TOKEN_EXPIRES_IN * 60,
                            ACCESS_TOKEN_EXPIRES_IN * 60, '/', None, False, False, 'lax')
        return {'access_token': access_token}


@router.get('/logout', status_code=status.HTTP_200_OK)
def logout(response: Response, Authorize: AuthJWT = Depends(), user_id: str = Depends(oauth2.require_user)):
    with handle_errors():
        Authorize.unset_jwt_cookies()
        response.set_cookie('logged_in', '', -1)

        return {'status': 'success'}
