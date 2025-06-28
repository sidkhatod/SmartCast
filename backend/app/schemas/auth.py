from pydantic import BaseModel, EmailStr

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    username: str

class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: str
    is_streamer: bool = False

class LoginRequest(BaseModel):
    username: str
    password: str
