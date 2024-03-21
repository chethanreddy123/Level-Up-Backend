def userEntity(user) -> dict:
    return {
        "id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
        "photo": user["photo"],
        "verified": user["verified"],
        "password": user["password"],
        "created_at": user["created_at"],
        "updated_at": user["updated_at"]
    }


def userResponseEntity(user) -> dict:
    return {
        "id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
        "photo": user["photo"],
        "created_at": user["created_at"],
        "updated_at": user["updated_at"]
    }


def embeddedUserResponse(user) -> dict:
    return {
        "id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"],
        "photo": user["photo"]
    }


def userListEntity(users) -> list:
    return [userEntity(user) for user in users]

def userRegistrationEntity(user) -> dict:
    return {
        "id": str(user["_id"]),
        "name": user["name"],
        "address": user["address"],
        "email": user["email"],
        "phone_no": user["phone_no"],
        "previous_gym": user["previous_gym"],
        "slot_preference": user["slot_preference"],
        "created_at": user["created_at"],
        "updated_at": user["updated_at"]
    }
