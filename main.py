import os
from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, Session, relationship

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")


# ------------------
# MODELS
# ------------------

class Color(Base):
    __tablename__ = "colors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    description = Column(String)
    status = Column(String, default="open")  # open / almost_full / closed

    orders = relationship("Order", back_populates="color")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String)
    weight = Column(Float)

    color_id = Column(Integer, ForeignKey("colors.id"))
    color = relationship("Color", back_populates="orders")


Base.metadata.create_all(bind=engine)


# ------------------
# DEPENDENCY
# ------------------

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ------------------
# ROUTES
# ------------------

@app.get("/")
async def root():
    return FileResponse("static/index.html")


@app.post("/add_color")
def add_color(name: str, description: str, db: Session = Depends(get_db)):
    color = Color(name=name, description=description)
    db.add(color)
    db.commit()
    db.refresh(color)
    return {"status": "created", "color_id": color.id}


@app.post("/add_order")
def add_order(user_id: str, color_id: int, weight: float, db: Session = Depends(get_db)):
    order = Order(user_id=user_id, color_id=color_id, weight=weight)
    db.add(order)
    db.commit()

    total_weight = sum(o.weight for o in db.query(Order).filter(Order.color_id == color_id).all())

    if total_weight >= 100:
        color = db.query(Color).filter(Color.id == color_id).first()
        color.status = "almost_full"
        db.commit()

    return {"status": "order_added", "total_weight": total_weight}


@app.get("/colors")
def get_colors(db: Session = Depends(get_db)):
    colors = db.query(Color).all()
    result = []

    for c in colors:
        total_weight = sum(o.weight for o in c.orders)
        result.append({
            "id": c.id,
            "name": c.name,
            "description": c.description,
            "status": c.status,
            "total_weight": total_weight
        })

    return result