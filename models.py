from sqlalchemy import Column, Integer, Unicode, ForeignKey, JSON, UnicodeText, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from config import Base  # Import Base from config to avoid circular import
from pydantic import BaseModel

# User table
class UserInDB(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    name = Column(Unicode(255), nullable=False)
    company_name = Column(Unicode(255), nullable=False)
    email = Column(Unicode(255), unique=True)  
    subscription_level = Column(Unicode(50), nullable=False)
    hashed_password = Column(Unicode(255), nullable=False)

    requests = relationship("RequestInDB", back_populates="user")


# Candidate table
class CandidateInDB(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    name = Column(UnicodeText, nullable=True)
    salary = Column(Integer, nullable=True)
    description = Column(UnicodeText, nullable=True)
    experience = Column(Integer, nullable=True)
    expObject = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=True)
    languages = Column(JSON, nullable=True)

    forms = relationship("FormsInDB", back_populates="candidate")

# Vacancy table
class VacancyInDB(Base):
    __tablename__ = "vacancies"
    
    id = Column(Integer, primary_key=True)
    title = Column(Unicode(255), nullable=False)
    experience = Column(Unicode(50), nullable=True)
    salary = Column(Unicode(50), nullable=True)
    company = Column(Unicode(255), nullable=False)
    description = Column(Unicode, nullable=True)
    link = Column(Unicode(255), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'))


# Request table
class RequestInDB(Base):
    __tablename__ = "requests"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    title = Column(Unicode(255), nullable=False)
    history = Column(UnicodeText, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    status = Column(Unicode(50), nullable=False, default="open")

    user = relationship("UserInDB", back_populates="requests")
    messages = relationship("MessageInDB", back_populates="request")


# Message table
class MessageInDB(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True)
    request_id = Column(Integer, ForeignKey('requests.id'), nullable=False)
    sender = Column(Unicode(50), nullable=False)  # 'user' or 'agent'
    content = Column(UnicodeText, nullable=False)
    timestamp = Column(DateTime, default=func.now(), nullable=False)

    request = relationship("RequestInDB", back_populates="messages")

class FormsInDB(Base):
    __tablename__ = "forms"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    candidate_id = Column(Unicode(255), ForeignKey('candidates.id'), nullable=False)
    status = Column(Unicode(50), nullable=False)
    questions = Column(JSON, nullable=False)
    answer = Column(UnicodeText, nullable=True)
    candidate = relationship("CandidateInDB", back_populates="forms")

class Description(BaseModel):
    description: str

class ChatbotRequest(BaseModel):
    user_message: str
    request_id: int

class UserCreate(BaseModel):
    name: str
    company_name: str
    email: str
    password: str


class UserLogin(BaseModel):
    email: str
    password: str


class Token(BaseModel):
    access_token: str


class ResumeCreate(BaseModel):
    text: str


class RequestCreate(BaseModel):
    title: str
    status: str
    history: str = None


class MessageCreate(BaseModel):
    request_id: int
    sender: str
    content: str

