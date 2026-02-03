from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

# 1. Define the User Model
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    refresh_token = Column(String, nullable=True)

    # Relationship: A user can have many documents
    documents = relationship("Document", back_populates="owner")

# 2. Define the Document Model
class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    vector_path = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))

    # Relationship: A document belongs to one user
    owner = relationship("User", back_populates="documents")
