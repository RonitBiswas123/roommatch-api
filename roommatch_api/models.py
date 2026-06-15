from pydantic import BaseModel
from typing import Optional, List

class UserRegister(BaseModel):
    name:     str
    email:    str
    password: str
    branch:   str
    year:     int
    gender:   str

class UserLogin(BaseModel):
    email:    str
    password: str

class ProfileCreate(BaseModel):
    sleep_time:   str
    wake_time:    str
    study_hours:  str
    cleanliness:  str
    noise:        str
    guests:       str
    about:        Optional[str] = ""
    about_text:   Optional[str] = ""
    ai_traits:    Optional[List[str]] = []

class Token(BaseModel):
    access_token: str
    token_type:   str

class TokenData(BaseModel):
    user_id: Optional[int] = None
    email:   Optional[str] = None

class ExtractTraitsRequest(BaseModel):
    text: str