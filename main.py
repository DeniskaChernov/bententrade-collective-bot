from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

from database import engine, SessionLocal
from models import Base, Color, Order

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

Base.metadata.create_all(bind=engine)


# ----------------------
# Dependency
# ----------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ----------------------
# Root
# ----------------------
@app.get("/")
async def root():
    return FileResponse("static/index.html")


# ----------------------
# Add Color
# ----------------------
@app.post("/add_color")
def add_color(name: str, description: str, db: Session = Depends(get_db)):
    color = Color(name=name, description=description)
    db.add(color)
    db.commit()
    db.refresh(color)
    return {"status": "created", "color_id": color.id}


# ----------------------
# Add Order
# ----------------------
@app.post("/add_order")
def add_order(user_id: str, color_id: int, weight: float, db: Session = Depends(get_db)):

    color = db.query(Color).filter(Color.id == color_id).first()

    if not color:
        return {"error": "Color not found"}

    if color.status == "closed":
        return {"error": "Orders are closed for this color"}

    order = Order(user_id=user_id, color_id=color_id, weight=weight)
    db.add(order)
    db.commit()

    total_weight = db.query(func.sum(Order.weight)).filter(
        Order.color_id == color_id
    ).scalar() or 0

    # Если достигли 100 кг впервые
    if total_weight >= 100 and color.status == "open":
        color.status = "threshold_reached"
        color.threshold_reached_at = datetime.utcnow()
        db.commit()

    return {"status": "order_added", "total_weight": total_weight}


# ----------------------
# Get Colors
# ----------------------
@app.get("/colors")
def get_colors(db: Session = Depends(get_db)):

    colors = db.query(Color).all()
    result = []

    for c in colors:

        total_weight = db.query(func.sum(Order.weight)).filter(
            Order.color_id == c.id
        ).scalar() or 0

        # Проверка 24 часов
        if c.status == "threshold_reached" and c.threshold_reached_at:
            if datetime.utcnow() >= c.threshold_reached_at + timedelta(hours=24):
                c.status = "closed"
                db.commit()

        progress_percent = min((total_weight / 100) * 100, 100)

        result.append(
            {
                "id": c.id,
                "name": c.name,
                "description": c.description,
                "status": c.status,
                "total_weight": total_weight,
                "progress_percent": progress_percent,
                "threshold_reached_at": c.threshold_reached_at,
            }
        )

    return result