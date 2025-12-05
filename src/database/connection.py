"""
Gestion de la connexion à la base de données PostgreSQL.
"""

import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

import sys
from pathlib import Path

# Ajouter le chemin du projet au PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from config.settings import DATABASE_URL
from src.database.models import Base

logger = logging.getLogger(__name__)

# Créer le moteur SQLAlchemy
_engine = None
_SessionLocal = None


def get_engine():
    """Retourne l'instance du moteur SQLAlchemy (singleton)."""
    global _engine
    if _engine is None:
        _engine = create_engine(
            DATABASE_URL,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            echo=False,
        )
        logger.info("Moteur de base de données créé avec succès")
    return _engine


def get_session_factory():
    """Retourne la factory de sessions."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=get_engine(),
            autocommit=False,
            autoflush=False,
        )
    return _SessionLocal


def get_session() -> Session:
    """Crée et retourne une nouvelle session."""
    SessionLocal = get_session_factory()
    return SessionLocal()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """
    Context manager pour gérer les sessions de base de données.
    Gère automatiquement le commit et le rollback.
    """
    session = get_session()
    try:
        yield session
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Erreur de base de données: {e}")
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Erreur inattendue: {e}")
        raise
    finally:
        session.close()


def init_db() -> None:
    """
    Initialise la base de données en créant toutes les tables.
    """
    engine = get_engine()
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Tables de base de données créées avec succès")
    except SQLAlchemyError as e:
        logger.error(f"Erreur lors de la création des tables: {e}")
        raise


def drop_all_tables() -> None:
    """
    Supprime toutes les tables de la base de données.
    ATTENTION: À utiliser avec précaution!
    """
    engine = get_engine()
    try:
        Base.metadata.drop_all(bind=engine)
        logger.warning("Toutes les tables ont été supprimées")
    except SQLAlchemyError as e:
        logger.error(f"Erreur lors de la suppression des tables: {e}")
        raise


def check_connection() -> bool:
    """
    Vérifie que la connexion à la base de données fonctionne.
    """
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Connexion à la base de données réussie")
        return True
    except SQLAlchemyError as e:
        logger.error(f"Impossible de se connecter à la base de données: {e}")
        return False
