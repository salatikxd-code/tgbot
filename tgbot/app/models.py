from sqlalchemy import Column, Integer, String, Enum, DateTime
from sqlalchemy.orm import declarative_base
from datetime import datetime
import enum
import pytz

Base = declarative_base()

moscow = pytz.timezone("Europe/Moscow")

def now_moscow():
    return datetime.now(moscow)


class RoleEnum(enum.Enum):
    admin = "admin"
    notifier = "notifier"
    user = "user"
    guest = "guest"


class SiteStatus(Base):
    __tablename__ = "site_status"

    id = Column(Integer, primary_key=True)
    status = Column(String, default="off")
    updated_by = Column(String, nullable=True)
    updated_at = Column(DateTime, default=now_moscow, onupdate=now_moscow)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(String, unique=True)  # храним ВСЕГДА строкой
    name = Column(String)
    role = Column(Enum(RoleEnum))


class ActionLog(Base):
    __tablename__ = "action_log"

    id = Column(Integer, primary_key=True)
    actor = Column(String)
    action = Column(String)
    details = Column(String)
    timestamp = Column(DateTime, default=now_moscow)
