from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

from ucalc_api.ucalc_config import DB_URL

engine = create_engine(DB_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


class UcalcUnit(Base):
    __tablename__ = "ucalc_units"

    id = Column(Integer, primary_key=True)
    category = Column(String(32), nullable=False, index=True)  # length/mass/volume/temperature
    code = Column(String(16), nullable=False, unique=True)     # m, kg, c, f, k ...
    name = Column(String(64), nullable=False)                  # "метр", "килограмм" ...
    factor = Column(Float, nullable=False, default=1.0)        # к базовой единице
    offset = Column(Float, nullable=False, default=0.0)        # для температуры


class UcalcHistory(Base):
    __tablename__ = "ucalc_history"

    id = Column(Integer, primary_key=True)
    category = Column(String(32), nullable=False)
    from_code = Column(String(16), nullable=False)
    to_code = Column(String(16), nullable=False)
    input_value = Column(Float, nullable=False)
    result_value = Column(Float, nullable=False)
    precision = Column(Integer, nullable=False, default=2)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


SEED_UNITS = [
    # length, base = meter
    ("length", "mm", "миллиметр", 0.001, 0.0),
    ("length", "cm", "сантиметр", 0.01, 0.0),
    ("length", "m",  "метр", 1.0, 0.0),
    ("length", "km", "километр", 1000.0, 0.0),
    ("length", "in", "дюйм", 0.0254, 0.0),
    ("length", "ft", "фут", 0.3048, 0.0),
    ("length", "mi", "миля", 1609.344, 0.0),

    # mass, base = kilogram
    ("mass", "mg", "миллиграмм", 0.000001, 0.0),
    ("mass", "g",  "грамм", 0.001, 0.0),
    ("mass", "kg", "килограмм", 1.0, 0.0),
    ("mass", "t",  "тонна", 1000.0, 0.0),
    ("mass", "oz", "унция", 0.028349523125, 0.0),
    ("mass", "lb", "фунт", 0.45359237, 0.0),

    # volume, base = liter
    ("volume", "ml", "миллилитр", 0.001, 0.0),
    ("volume", "l",  "литр", 1.0, 0.0),
    ("volume", "m3", "кубометр", 1000.0, 0.0),
    ("volume", "gal", "галлон (US)", 3.785411784, 0.0),
    ("volume", "pt", "пинта (US)", 0.473176473, 0.0),

    # temperature, base = kelvin, value_base = value * factor + offset
    ("temperature", "c", "Цельсий", 1.0, 273.15),
    ("temperature", "f", "Фаренгейт", 5.0 / 9.0, 255.3722222222),
    ("temperature", "k", "Кельвин", 1.0, 0.0),
]


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if db.query(UcalcUnit).count() == 0:
            db.add_all(
                UcalcUnit(category=c, code=code, name=name, factor=f, offset=o)
                for c, code, name, f, o in SEED_UNITS
            )
            db.commit()