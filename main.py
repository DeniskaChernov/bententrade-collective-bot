import os
from datetime import datetime, timedelta

import requests
from fastapi import FastAPI, Depends, HTTPException, Form
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from database import engine, SessionLocal
from models import Base, Color, Order

# ---------------- CONFIG ----------------

BOT_TOKEN = None
ADMIN_CHAT_ID = None

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "1234"

SECRET_KEY = "supersecret"
ALGORITHM = "HS256"

# ---------------- INIT ----------------

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
from fastapi.responses import FileResponse

@app.get("/")
def root():
    return FileResponse("static/index.html")

security = HTTPBearer()

# ---------------- DATABASE DEP ----------------

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------- JWT ----------------

def create_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=8)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


# ---------------- TELEGRAM ----------------

def notify_telegram(text: str):
    if not BOT_TOKEN or not ADMIN_CHAT_ID:
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": ADMIN_CHAT_ID,
        "text": text
    })


# ---------------- AUTO LOGIC ----------------

def auto_close_parties(db: Session):
    colors = db.query(Color).all()

    for color in colors:

        # 100 кг достигнуто
        if color.total_weight >= color.min_weight and color.status == "open":
            color.status = "waiting_24h"
            color.threshold_reached_at = datetime.utcnow()

            if not color.is_notified_100:
                notify_telegram(
                    f"⚡ Достигнуто 100 кг\n"
                    f"{color.article} — {color.name}"
                )
                color.is_notified_100 = True

        # 24 часа истекли
        if (
            color.status == "waiting_24h"
            and color.threshold_reached_at
            and datetime.utcnow() >= color.threshold_reached_at + timedelta(hours=24)
        ):
            color.status = "closed"

            if not color.is_notified_closed:
                notify_telegram(
                    f"🚀 Производство запущено\n"
                    f"{color.article} — {color.name}"
                )
                color.is_notified_closed = True

    db.commit()

    # ---------------- PUBLIC API ----------------

@app.get("/api/colors")
def get_colors(user_id: str = None, db: Session = Depends(get_db)):

    auto_close_parties(db)

    colors = db.query(Color).all()

    response = []

    for color in colors:

        # вклад пользователя
        user_weight = 0
        if user_id:
            orders = db.query(Order).filter(
                Order.user_id == user_id,
                Order.color_id == color.id
            ).all()

            user_weight = sum(o.weight for o in orders)

        # countdown
        remaining_seconds = None
        if color.status == "waiting_24h" and color.threshold_reached_at:
            end_time = color.threshold_reached_at + timedelta(hours=24)
            remaining_seconds = int(
                (end_time - datetime.utcnow()).total_seconds()
            )

            if remaining_seconds < 0:
                remaining_seconds = 0

        response.append({
            "id": color.id,
            "article": color.article,
            "name": color.name,
            "format": color.format,
            "image_url": color.image_url,
            "total_weight": color.total_weight,
            "min_weight": color.min_weight,
            "status": color.status,
            "remaining_seconds": remaining_seconds,
            "user_weight": user_weight
        })

    return response

@app.post("/api/confirm")
def confirm_order(data: dict, db: Session = Depends(get_db)):

    required_fields = [
        "user_id",
        "items",
        "first_name",
        "last_name",
        "phone",
        "delivery_method"
    ]

    for field in required_fields:
        if field not in data:
            raise HTTPException(status_code=400, detail="Missing field")

    summary_lines = []

    for item in data["items"]:

        color = db.query(Color).filter(
            Color.id == item["color_id"]
        ).first()

        if not color:
            raise HTTPException(status_code=404, detail="Color not found")

        if color.status == "closed":
            raise HTTPException(status_code=400, detail="Party closed")

        weight = item["weight"]

        if weight < 5 or weight % 5 != 0:
            raise HTTPException(status_code=400, detail="Invalid weight")

        order = Order(
            user_id=data["user_id"],
            color_id=color.id,
            weight=weight,
            first_name=data["first_name"],
            last_name=data["last_name"],
            phone=data["phone"],
            address=data.get("address"),
            delivery_method=data["delivery_method"]
        )

        db.add(order)

        color.total_weight += weight

        summary_lines.append(
            f"{color.article} — {weight} кг"
        )

    db.commit()

    auto_close_parties(db)

    notify_telegram(
        f"🛒 Новый заказ\n"
        f"{data['first_name']} {data['last_name']}\n"
        f"{data['phone']}\n"
        f"Способ: {data['delivery_method']}\n\n"
        + "\n".join(summary_lines)
    )

    return {"status": "ok"}

# ---------------- ADMIN ----------------

@app.post("/admin/login")
def admin_login(username: str = Form(...), password: str = Form(...)):

    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        token = create_token({"sub": "admin"})
        return {"token": token}

    raise HTTPException(status_code=401, detail="Invalid credentials")


@app.get("/admin/colors")
def admin_colors(payload=Depends(verify_token), db: Session = Depends(get_db)):
    return db.query(Color).all()


@app.post("/admin/add")
def admin_add(
    article: str = Form(...),
    name: str = Form(...),
    format: str = Form(...),
    image_url: str = Form(...),
    payload=Depends(verify_token),
    db: Session = Depends(get_db)
):

    color = Color(
        article=article,
        name=name,
        format=format,
        image_url=image_url
    )

    db.add(color)
    db.commit()

    return {"status": "added"}


@app.post("/admin/close/{color_id}")
def admin_close(
    color_id: int,
    payload=Depends(verify_token),
    db: Session = Depends(get_db)
):

    color = db.query(Color).filter(Color.id == color_id).first()

    if not color:
        raise HTTPException(status_code=404, detail="Not found")

    color.status = "closed"
    db.commit()

    return {"status": "closed"}