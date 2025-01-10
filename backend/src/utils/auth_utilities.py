import os
import jwt
from fastapi import HTTPException, status, Request
from datetime import datetime, timedelta, timezone


API_KEY = os.environ["API_KEY"]
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 1


def decode_jwt_token(token: str):
    """
    Decodes a JWT token and verifies its validity and expiration.

    Args:
        token (str): The JWT token to decode.

    Returns:
        dict: The decoded token payload.

    Raises:
        HTTPException: If the token is expired or invalid.
    """
    try:
        payload = jwt.decode(token, API_KEY, algorithms=[ALGORITHM])
        if payload["exp"] < datetime.now(timezone.utc).timestamp():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


def create_access_token(data: dict, expires_delta: timedelta = timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)):
    """
    Creates a JWT access token with a specified expiration time.

    Args:
        data (dict): The data to include in the token payload.
        expires_delta (timedelta): The expiration time of the token.

    Returns:
        str: The encoded JWT token.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, API_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def current_user(request: Request):
    """
    Extracts and validates the current user's JWT token from the Authorization header.

    Args:
        request (Request): The FastAPI request object containing headers.

    Returns:
        dict: The decoded token payload of the current user.

    Raises:
        HTTPException: If the Authorization header is missing, invalid, or the token is invalid.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is missing"
        )
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header's value is invalid"
        )
    token = auth_header.split("Bearer ")[1]
    return decode_jwt_token(token)


async def api_key_required(request: Request):
    """
    Validates the API-KEY header in the request.

    Args:
        request (Request): The FastAPI request object containing headers.

    Returns:
        dict: A success message and API_KEY if the API-KEY header is valid.

    Raises:
        HTTPException: If the API-KEY header is missing or invalid.
    """
    auth_header = request.headers.get("API-KEY")
    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API-KEY header is missing"
        )
    if auth_header != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API-KEY header's value is invalid"
        )
    return {
        "status": True,
        "message": "SUCCESS",
        "api_key": API_KEY
    }