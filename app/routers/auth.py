from datetime import datetime, timedelta
from bson.objectid import ObjectId
from fastapi import APIRouter, Response, status, Depends, HTTPException
import loguru

from app.utilities.error_handler import handle_errors
from app.utilities.email_services import send_email
from app.utilities.utils import get_next_registration_id

from app import oauth2
from app.database import  User
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
        # Check if user already exists
        existing_user = User.find_one({'email': payload.email.lower()})
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail='Account already exists'
            )

        # Compare password and password_confirm
        if payload.password != payload.password_confirm:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Passwords do not match'
            )

        # Hash the password
        hashed_password = utils.hash_password(payload.password)
        
        # Create user dictionary
        user_data = payload.dict(exclude_unset=True)  # This ensures that optional fields are included if provided
        user_data['password'] = hashed_password
        user_data['role'] = payload.role or 'CUSTOMER'
        user_data['verified'] = True
        user_data['email'] = payload.email.lower()
        user_data['created_at'] = datetime.utcnow()
        user_data['updated_at'] = user_data['created_at']
        user_data['registration_id'] = get_next_registration_id()

        # Insert the user into the database
        result = User.insert_one(user_data)
        if not result.inserted_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Failed to create user'
            )

        # Fetch the newly created user
        new_user_data = User.find_one({'_id': result.inserted_id})
        if not new_user_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='User not found after creation'
            )

        # Transform to response schema
        new_user = userResponseEntity(new_user_data)

        # Send welcome email for CUSTOMER role
        if user_data['role'] == 'CUSTOMER':
            try:
                await send_email(
                    sender_email="aioverflow.ml@gmail.com",
                    sender_password="tvnt qtww egyq ktes",  # Retrieve from config in production
                    to_email=user_data['email'],
                    cc_emails=None,
                    subject="Welcome to Our Gym App!",
                    message=f"Hi {user_data['name']},\n\n"
                            f"Thank you for registering with our gym app!\n\n"
                            f"Download the app and start your fitness journey.\n\n"
                            f"Best regards,\nThe Gym Team"
                )
            except Exception as e:
                loguru.logger.error(f"Error sending email: {e}")

        return {"status": "success", "user": new_user}



@router.post('/login')
async def login(payload: user.LoginUserSchema, response: Response, Authorize: AuthJWT = Depends()):
    with handle_errors():
        # Check if the user exists
        db_user =  User.find_one({'email': payload.email.lower()})
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

        # Send both access and refresh tokens
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
