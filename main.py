from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from database import engine, SessionLocal
from models import Base, Color, Order

# СОЗДАЁМ ТАБЛИЦЫ СРАЗУ ПРИ ЗАПУСКЕ
Base.metadata.create_all(bind=engine)

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
async def root():
    return FileResponse("static/index.html")


@app.post("/add_color")
def add_color(name: str, description: str, db: Session = Depends(get_db)):
    color = Color(name=name, description=description, status="open")
    db.add(color)
    db.commit()
    db.refresh(color)
    return {"status": "created", "color_id": color.id}


@app.post("/add_order")
def add_order(user_id: str, color_id: int, weight: float, db: Session = Depends(get_db)):
    order = Order(user_id=user_id, color_id=color_id, weight=weight)
    db.add(order)
    db.commit()

    total_weight = sum(
        o.weight for o in db.query(Order).filter(Order.color_id == color_id).all()
    )

    color = db.query(Color).filter(Color.id == color_id).first()

    if total_weight >= 100 and color.status == "open":
        color.status = "waiting_24h"
        db.commit()

    return {"status": "order_added", "total_weight": total_weight}


@app.get("/colors")
def get_colors(db: Session = Depends(get_db)):
    colors = db.query(Color).all()
    result = []

    for c in colors:
        total_weight = sum(o.weight for o in c.orders)
        result.append(
            {
                "id": c.id,
                "name": c.name,
                "description": c.description,
                "status": c.status,
                "total_weight": total_weight,
            }
        )

    return result