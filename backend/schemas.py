from pydantic import BaseModel, EmailStr
from typing import Optional, List

# 1. Base Schema (Common fields across model and API)
class UserBase(BaseModel):
    email: EmailStr

# 2. Signup Schema (What we expect when someone signs up)
class UserCreate(UserBase):
    password: str

# 3. User Response Schema (What we send back to the frontend)
class User(UserBase):
    id: int

    class Config:
        from_attributes = True

# 4. Token Schema (For successful login)
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class TokenRefresh(BaseModel):
    refresh_token: str

class TokenData(BaseModel):
    email: Optional[str] = None

# 5. Document Schema (For file library)
class DocumentBase(BaseModel):
    filename: str

class DocumentCreate(DocumentBase):
    vector_path: str

class Document(DocumentBase):
    id: int
    user_id: int

    class Config:
        from_attributes = True

# 6. Query Schema (For asking questions with selections)
class QueryBase(BaseModel):
    question: str

class QuestionMulti(BaseModel):
    question: str
    pdf_ids: List[int]
