from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException
from pydantic import BaseModel
from typing import List
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import JWTError, jwt

# Database Setup
DATABASE_URL = "sqlite:///./petsitting.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Secret Key for JWT
SECRET_KEY = "your_secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password Hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Authentication Dependency
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

# Models
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)

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

# Create Tables
Base.metadata.create_all(bind=engine)

# FastAPI App
app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Allow React frontend
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, PUT, DELETE)
    allow_headers=["*"],  # Allow all headers
)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Password Hashing Functions
def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# JWT Token Creation
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Pydantic Models
class UserCreate(BaseModel):
    username: str
    password: str

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

# Authentication Endpoints
@app.post("/register/")
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    hashed_password = get_password_hash(user.password)
    db_user = User(username=user.username, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return {"message": "User registered successfully"}

@app.post("/login/")
def login_user(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    if not form_data.username or not form_data.password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username and password are required")
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    access_token = create_access_token({"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

# Endpoints with Authentication Logging

@app.get("/clients/", dependencies=[Depends(oauth2_scheme)])
def get_clients(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    print(f"🔍 Received Token: {token}")  # Debugging Token
    return db.query(Client).all()

@app.get("/bookings/", dependencies=[Depends(oauth2_scheme)])
def get_bookings(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    print(f"🔍 Received Token: {token}")  # Debugging Token
    return db.query(Booking).all()

@app.post("/clients/", response_model=ClientCreate, dependencies=[Depends(oauth2_scheme)])
def create_client(client: ClientCreate, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    print(f"🔍 Received Token (POST /clients/): {token}")  # Debugging Token
    db_client = Client(name=client.name, email=client.email, phone=client.phone)
    db.add(db_client)
    db.commit()
    db.refresh(db_client)
    return db_client

@app.post("/pets/", response_model=PetCreate, dependencies=[Depends(oauth2_scheme)])
def create_pet(pet: PetCreate, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    print(f"🔍 Received Token (POST /pets/): {token}")  # Debugging Token
    db_pet = Pet(name=pet.name, species=pet.species, breed=pet.breed, owner_id=pet.owner_id)
    db.add(db_pet)
    db.commit()
    db.refresh(db_pet)
    return db_pet

@app.post("/bookings/", response_model=BookingCreate, dependencies=[Depends(oauth2_scheme)])
def create_booking(booking: BookingCreate, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    print(f"🔍 Received Token (POST /bookings/): {token}")  # Debugging Token
    db_booking = Booking(client_id=booking.client_id, pet_id=booking.pet_id, service=booking.service, date=booking.date)
    db.add(db_booking)
    db.commit()
    db.refresh(db_booking)
    return db_booking

@app.delete("/clients/{client_id}", dependencies=[Depends(oauth2_scheme)])
def delete_client(client_id: int, db: Session = Depends(get_db)):
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    db.delete(client)
    db.commit()
    return {"message": "Client deleted successfully"}

@app.post("/bookings/", dependencies=[Depends(oauth2_scheme)])
def create_booking(booking: BookingCreate, db: Session = Depends(get_db)):
    db_booking = Booking(
        client_id=booking.client_id,
        pet_id=booking.pet_id,
        service=booking.service,
        date=booking.date
    )
    db.add(db_booking)
    db.commit()
    db.refresh(db_booking)
    return db_booking

@app.delete("/bookings/{booking_id}", dependencies=[Depends(oauth2_scheme)])
def delete_booking(booking_id: int, db: Session = Depends(get_db)):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    db.delete(booking)
    db.commit()
    return {"message": "Booking deleted successfully"}

@app.post("/register/")
def register_user(username: str, password: str, db: Session = Depends(get_db)):
    hashed_password = pwd_context.hash(password)
    db_user = User(username=username, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    return {"message": "User registered successfully"}
