from pydantic import BaseModel
from datetime import datetime

class SystemInfoRequest(BaseModel):
    operating_system: str
    unique_system_id: str

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    first_name : str
    last_name : str
    username : str
    email : str
    password : str
    is_active : bool = True
    last_login : datetime = datetime.now()
    joined_at : datetime = datetime.now()