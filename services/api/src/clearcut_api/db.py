from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from .models import Base


@dataclass(frozen=True)
class Database:
    engine: Engine
    session_factory: sessionmaker[Session]

    def init(self) -> None:
        Base.metadata.create_all(self.engine)


def create_database(database_url: str) -> Database:
    if database_url.startswith("sqlite:///./"):
        Path(database_url.removeprefix("sqlite:///./")).parent.mkdir(parents=True, exist_ok=True)

    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    poolclass = StaticPool if database_url in {"sqlite://", "sqlite:///:memory:"} else None
    engine_kwargs = {"future": True, "connect_args": connect_args}
    if poolclass is not None:
        engine_kwargs["poolclass"] = poolclass
    engine = create_engine(database_url, **engine_kwargs)
    return Database(
        engine=engine,
        session_factory=sessionmaker(bind=engine, autoflush=False, expire_on_commit=False),
    )
