from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()


class Color(Base):
    __tablename__ = "colors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)

    status = Column(String, default="open")
    # open / threshold_reached / closed

# threshold_reached_at = Column(DateTime, nullable=True)

    orders = relationship("Order", back_populates="color")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False)
    weight = Column(Float, nullable=False)

    color_id = Column(Integer, ForeignKey("colors.id"))
    color = relationship("Color", back_populates="orders")