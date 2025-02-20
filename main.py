from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from typing import List
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from passlib.context import CryptContext

# Database Setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./petsitting.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Models
class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    phone = Column(String)
    pets = relationship("Pet", back_populates="owner")

class Pet(Base):
    __tablename__ = "pets"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    species = Column(String)
    breed = Column(String, nullable=True)
    owner_id = Column(Integer, ForeignKey("clients.id"))
    owner = relationship("Client", back_populates="pets")

class Booking(Base):
    __tablename__ = "bookings"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"))
    pet_id = Column(Integer, ForeignKey("pets.id"))
    service = Column(String)
    date = Column(String)
    status = Column(String, default="Pending")
    client = relationship("Client")
    pet = relationship("Pet")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)

# Create Tables
Base.metadata.create_all(bind=engine)

# FastAPI App
app = FastAPI()

# Pydantic Models
class ClientCreate(BaseModel):
    name: str
    email: str
    phone: str

class PetCreate(BaseModel):
    name: str
    species: str
    breed: str | None
    owner_id: int

class BookingCreate(BaseModel):
    client_id: int
    pet_id: int
    service: str
    date: str

class UserCreate(BaseModel):
    username: str
    password: str

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/register/")
def register_user(user: UserCreate, db: SessionLocal = Depends(get_db)):
    existing_user = db.query(User).filter(User.username == user.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already taken")
    
    hashed_password = pwd_context.hash(user.password)
    db_user = User(username=user.username, hashed_password=hashed_password)
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return {"message": "User registered successfully", "username": db_user.username}

# Endpoints
@app.post("/clients/", response_model=ClientCreate)
def create_client(client: ClientCreate, db: SessionLocal = Depends(get_db)):
    db_client = Client(name=client.name, email=client.email, phone=client.phone)
    db.add(db_client)
    db.commit()
    db.refresh(db_client)
    return db_client

@app.post("/pets/", response_model=PetCreate)
def create_pet(pet: PetCreate, db: SessionLocal = Depends(get_db)):
    db_pet = Pet(name=pet.name, species=pet.species, breed=pet.breed, owner_id=pet.owner_id)
    db.add(db_pet)
    db.commit()
    db.refresh(db_pet)
    return db_pet

@app.post("/bookings/", response_model=BookingCreate)
def create_booking(booking: BookingCreate, db: SessionLocal = Depends(get_db)):
    db_booking = Booking(client_id=booking.client_id, pet_id=booking.pet_id, service=booking.service, date=booking.date)
    db.add(db_booking)
    db.commit()
    db.refresh(db_booking)
    return db_booking
