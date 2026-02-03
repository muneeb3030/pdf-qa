from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm

import sys
import os

# Ensure the parent directory is in the path so we can import models, schemas, etc.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import models, schemas, auth, database
from database import get_db

router = APIRouter(
    tags=["Authentication"]
)

@router.post("/signup", response_model=schemas.User)
def signup(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # Check if user already exists
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Hash the password and save
    hashed_pwd = auth.get_password_hash(user.password)
    new_user = models.User(email=user.email, hashed_password=hashed_pwd)
    
    # Generate Refresh Token
    new_user.refresh_token = auth.create_refresh_token(data={"sub": user.email})
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post("/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # 1. Find the user
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    # 2. Verify password
    if not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    # 3. Create tokens
    access_token = auth.create_access_token(data={"sub": user.email})
    refresh_token = auth.create_refresh_token(data={"sub": user.email})
    
    # 4. Save refresh token to DB
    user.refresh_token = refresh_token
    db.commit()
    
    return {
        "access_token": access_token, 
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/refresh", response_model=schemas.Token)
def refresh_token(payload: schemas.TokenRefresh, db: Session = Depends(get_db)):
    try:
        from jose import jwt
        # 1. Decode refresh token
        decoded = jwt.decode(payload.refresh_token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        email: str = decoded.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        
        # 2. Verify against DB
        user = db.query(models.User).filter(models.User.email == email).first()
        if not user or user.refresh_token != payload.refresh_token:
            raise HTTPException(status_code=401, detail="Refresh token revoked or invalid")
        
        # 3. Issue new tokens
        new_access = auth.create_access_token(data={"sub": user.email})
        new_refresh = auth.create_refresh_token(data={"sub": user.email})
        
        # 4. Update DB
        user.refresh_token = new_refresh
        db.commit()
        
        return {
            "access_token": new_access,
            "refresh_token": new_refresh,
            "token_type": "bearer"
        }
    except Exception:
        raise HTTPException(status_code=401, detail="Could not refresh token")
