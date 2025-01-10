from models import User
from sqlalchemy.orm import Session


def validate_user(data : dict, db : Session):
    """ Validate the user on register """
    response = {
        "status": True,
        "response": "User is valid"
    }
    try:
        username = data.get("username").lower()
        password = data.get("password")
        user = db.query(User).filter(User.username == username).first()
        if user:
            response["status"] = False
            response["message"] = "User already exists. Please try different username."
        elif len(username)<3:
            response["status"] = False
            response["message"] = "Username should not smaller than 3 characters!"
        elif len(password)<8:
            response["status"] = False
            response["message"] = "Password should not smaller than 8 characters"
    except:
        response["status"] = False
        response["message"] = "An unexpected error occured. Please try again later !"
    return response