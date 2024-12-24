from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime, timedelta
from app.database import UserAttendance, User  # MongoDB collection for attendance
from app import oauth2
from bson import ObjectId
from app.utilities.utils import get_current_ist_time
from loguru import logger
from app.utilities.error_handler import handle_errors
from pymongo import ASCENDING, DESCENDING

router = APIRouter()

# Create a compound index on user_id and date fields in the UserAttendance collection (for fast quering of the db)
UserAttendance.create_index([("user_id", ASCENDING), ("date", ASCENDING)], unique=True)

@router.post('/mark-attendance', status_code=status.HTTP_201_CREATED)
def mark_attendance(
    user_id: str = Depends(oauth2.require_user)  # Getting authenticated user
):
    """
    Mark the user's attendance for the current day.
    The attendance is automatically marked as 'present' (status = True).
    """
    with handle_errors():  # Custom error handling context
        # Log the action of marking attendance
        logger.info(f"Marking attendance for user ID: {user_id}.")

        try:
            # Get the current date and time (as datetime object)
            current_date = datetime.utcnow()  # Get current UTC date and time
            current_date_str = current_date.strftime('%Y-%m-%d')  # Format for logging, optional

            # Check if the attendance for today already exists for this user
            existing_attendance = UserAttendance.find_one({
                "user_id": user_id, 
                "date": {"$gte": current_date.replace(hour=0,minute=0,second=0,microsecond=0), 
                         "$lte": current_date.replace(hour=23,minute=59,second=59,microsecond=999999)}  # date range for today
            })
            
            if existing_attendance:
                # Log the condition where attendance already exists
                logger.info(f"Attendance already exists for user ID: {user_id} on {current_date_str}.")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Attendance already recorded for user ID: {user_id} on {current_date_str}."
                )

            # Create the attendance record with current datetime
            attendance_record = {
                "user_id": user_id,  # The authenticated user's ID
                "date": current_date,  # Store the full datetime
                "status": True  # Status set to True (present)
            }

            # Insert the attendance record into the UserAttendance collection
            result = UserAttendance.insert_one(attendance_record)

            if result.acknowledged:
                # Log successful attendance marking
                logger.info(f"Attendance marked for user ID: {user_id} on {current_date_str}.")
                return {"message": "Attendance recorded successfully!"}
            else:
                # Log failure to insert attendance
                logger.error(f"Failed to record attendance for user ID: {user_id}.")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to record attendance."
                )

        except HTTPException as http_exc:
            # Log and raise the HTTPException with its original message
            logger.warning(f"HTTPException: {http_exc.detail}")
            raise http_exc

        except Exception as e:
            # Log the full exception with stack trace
            logger.error(f"Exception occurred: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred while processing your request."
            )
        

@router.post('/mark-absent', status_code=status.HTTP_201_CREATED)
def mark_absent(
):
    """
    Mark all users as absent if they haven't been marked present for the current day.
    Will be handled by cron-job at 11:30 PM everyday.
    """
    with handle_errors():  # Custom error handling context
        try:
            # Get the current date in 'yyyy-mm-dd' format
            current_date = datetime.utcnow().date()
            current_date_str = current_date.isoformat()  # Convert to string format (yyyy-mm-dd)

            # Fetch all user IDs from the User collection
            all_users = list(User.find({}, {"_id": 1}))  # Retrieve only user IDs
            all_user_ids = {str(user["_id"]) for user in all_users}

            # Fetch all user IDs that have already marked attendance for the current date
            present_users = list(UserAttendance.find({"date": current_date_str}, {"user_id": 1}))
            present_user_ids = {attendance["user_id"] for attendance in present_users}

            # Determine the user IDs that are not marked present (absent users)
            absent_user_ids = all_user_ids - present_user_ids

            if not absent_user_ids:
                return {"message": "All users have been marked for today. No absent users to mark."}

            # Insert attendance records for absent users
            absent_attendance_records = [
                {
                    "user_id": user_id,
                    "date": current_date_str,
                    "status": False  # Mark status as False for absent
                }
                for user_id in absent_user_ids
            ]

            # Insert absent records into UserAttendance collection
            if absent_attendance_records:
                result = UserAttendance.insert_many(absent_attendance_records)

                if result.acknowledged:
                    logger.info(f"Marked absent for users: {absent_user_ids}")
                    return {"message": "Absent users have been marked successfully."}
                else:
                    logger.error("Failed to insert absent attendance records.")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to mark absent users."
                    )

        except HTTPException as http_exc:
            # Log and raise the HTTPException with its original message
            logger.warning(f"HTTPException: {http_exc.detail}")
            raise http_exc

        except Exception as e:
            # Log the full exception with stack trace
            logger.error(f"Exception occurred: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred while processing your request."
            )
        

@router.get('/get-attendance/{user_id}', status_code=status.HTTP_200_OK)
def get_attendance(
    user_id: str,
    auth_user_id: str = Depends(oauth2.require_user)  # Getting authenticated user
):
    """
    Get attendance details for the user from their join date to today (or from the start of the month if it's after the first month).
    Returns the number of present days, total days they were eligible to attend, and attendance percentage.
    """
    try:
        # Check if the user exists in the User collection
        user = User.find_one({"_id": ObjectId(user_id)})
        if not user:
            logger.warning(f"User with ID: {user_id} not found.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID: {user_id} not found."
            )

        # Get the user's join date (assuming it's stored in 'created_at')
        join_date = user.get("created_at")
        if not join_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User does not have a join date."
            )

        # Normalize join date to the start of the day (midnight)
        join_date = join_date.replace(hour=0, minute=0, second=0, microsecond=0)

        # Get today's date
        today = datetime.utcnow()

        # Get the start of the current month
        start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # If it's the first month, calculate attendance from the join date.
        # Otherwise, calculate from the start of the month.
        if join_date.month == today.month and join_date.year == today.year:
            # First month: calculate total days from join date to today
            eligible_start_date = join_date
            total_days_in_month = (today - eligible_start_date).days + 1
        else:
            # Subsequent months: calculate from the 1st of the current month
            eligible_start_date = start_of_month
            total_days_in_month = today.day  # Count the days from the 1st to today

        # Adjust end date to include the current day completely
        end_date = today.replace(hour=23, minute=59, second=59, microsecond=999999)

        # Query attendance records for the user from their eligible start date to today
        attendance_records = list(UserAttendance.find({
            "user_id": user_id,
            "date": {"$gte": eligible_start_date, "$lte": end_date}
        }).sort("date", DESCENDING))  # Sort by date in descending order

        # Calculate present days (where status is True)
        present_days = sum(1 for record in attendance_records if record.get("status") is True)

        # Calculate attendance percentage
        attendance_percentage = (present_days / total_days_in_month) * 100 if total_days_in_month > 0 else 0

        # Return the attendance details
        return {
            "user_id": user_id,
            "total_days": total_days_in_month,
            "present_days": present_days,
            "attendance_percentage": round(attendance_percentage, 2)
        }

    except HTTPException as http_exc:
        # Log and raise the HTTPException with its original message
        logger.warning(f"HTTPException: {http_exc.detail}")
        raise http_exc

    except Exception as e:
        # Log the full exception with stack trace
        logger.error(f"Exception occurred: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing your request."
        )