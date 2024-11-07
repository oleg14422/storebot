from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, UniqueConstraint, select, exists, Date, DateTime, CheckConstraint

# URL бази даних (наприклад, SQLite). Для інших баз, змініть URL відповідно.
DATABASE_URL = "sqlite+aiosqlite:///./test.db"

# Створення асинхронного двигуна
engine = create_async_engine(DATABASE_URL, echo=True)

# Налаштування сесії
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)

# Базовий клас для всіх моделей
Base = declarative_base()

# Приклад моделі Product
class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    flavor = Column(String, index=True)
    size = Column(Integer)
    price = Column(Integer, nullable=False)
    count = Column(Integer, nullable=False)
    __table_args__ = (UniqueConstraint('flavor', 'size'),)


    def __repr__(self):
        return f"<Product(id={self.id}, flavor={self.flavor}, size={self.size}, price={self.price}, count={self.count})>"


class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    flavor = Column(String, index=True, nullable=False)
    size = Column(Integer, nullable=False)
    price = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.today, nullable=False)
    telegram_user_id = Column(Integer,nullable=False)
    telegram_user_first_name = Column(String, )
    telegram_user_last_name = Column(String, nullable=True)
    telegram_user_username = Column(String,nullable=True)
    status = Column(String(15), nullable=False)
    __table_args__ = (
        CheckConstraint(status.in_(["complete", "pending", "canceled", "failed"]), name="valid_status"),
    )

    def __repr__(self):
        return f"<Transaction(id={self.id}, flavor={self.flavor}, size={self.size}, price={self.price}, created_at={self.created_at})>"

# Функція для створення таблиць у базі даних
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Приклад функції для отримання сесії
async def get_db():
    async with SessionLocal() as session:
        yield session
