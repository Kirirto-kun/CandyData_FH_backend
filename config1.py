from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import os

# Load environment variables from the .env file
load_dotenv()

# Database connection details
server = 'candydata.database.windows.net'
database = 'CandyDataDB'
username = 'Jafar'
password = 'cancancandada123!!!Kerey'

# Create the connection string
connection_string = f'mssql+pyodbc://{username}:{password}@{server}/{database}?driver=ODBC+Driver+17+for+SQL+Server'

# Create the SQLAlchemy engine
engine = create_engine(connection_string)

# Create a session factory for SQLAlchemy
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Define the base class for creating models
Base = declarative_base()

# Function to get a new session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Function to create all tables
def init_db():
    from models import UserInDB, CandidateInDB, VacancyInDB  # Import all models here
    Base.metadata.create_all(bind=engine)  # Create all tables based on imported models
