from fastapi import FastAPI
from models import Car
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

app = FastAPI()

engine = create_engine("sqlite:///cars.db")
Session = sessionmaker(bind=engine)
session = Session()

@app.get("/recommendations/")
def get_recommendations(budget: float):
    cars = session.query(Car).filter(Car.price <= budget).all()
    return [{"make": car.make, "model": car.model, "price": car.price} for car in cars]
