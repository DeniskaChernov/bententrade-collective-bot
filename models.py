from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()


class Color(Base):
    __tablename__ = "colors"

    id = Column(Integer, primary_key=True)

    article = Column(String, nullable=False)
    name = Column(String, nullable=False)
    format = Column(String, nullable=False)
    image_url = Column(String, nullable=True)

    total_weight = Column(Float, default=0)
    min_weight = Column(Float, default=100)

    status = Column(String, default="open")
    # open
    # waiting_24h
    # closed

    threshold_reached_at = Column(DateTime, nullable=True)

    is_notified_100 = Column(Boolean, default=False)
    is_notified_closed = Column(Boolean, default=False)


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)

    user_id = Column(String, nullable=False)
    color_id = Column(Integer, nullable=False)

    weight = Column(Float, nullable=False)

    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    address = Column(String, nullable=True)

    delivery_method = Column(String, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)