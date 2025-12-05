"""
Modèles SQLAlchemy pour la base de données.
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    JSON,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship, Mapped, mapped_column


class Base(DeclarativeBase):
    """Classe de base pour tous les modèles."""
    pass


class Source(Base):
    """Modèle pour les sites web sources."""

    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    scraper_type: Mapped[str] = mapped_column(String(50), default="generic")
    site_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # Type de site pour le scraper WordPress

    # Sélecteurs CSS pour le scraping
    article_list_selector: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    title_selector: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    link_selector: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    content_selector: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    date_selector: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # URLs des catégories à scraper (stockées en JSON)
    category_urls: Mapped[Optional[List]] = mapped_column(JSON, nullable=True)

    # Métadonnées
    encoding: Mapped[str] = mapped_column(String(20), default="utf-8")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_scraped: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relations
    articles: Mapped[List["Article"]] = relationship(
        "Article", back_populates="source_rel", cascade="all, delete-orphan"
    )
    scraping_logs: Mapped[List["ScrapingLog"]] = relationship(
        "ScrapingLog", back_populates="source", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Source(id={self.id}, name='{self.name}')>"


class Article(Base):
    """Modèle pour les articles collectés."""

    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Champs principaux selon les spécifications
    titre: Mapped[str] = mapped_column(String(500), nullable=False)
    source: Mapped[str] = mapped_column(String(255), nullable=False)  # Nom de la source (ex: "Guineenews")
    lien: Mapped[str] = mapped_column(String(1000), nullable=False, unique=True)
    date_publication: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    resume: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[List]] = mapped_column(JSON, nullable=True)  # Liste des tags de l'article
    categorie: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # Catégorie de l'article
    compte_election: Mapped[int] = mapped_column(Integer, default=0)  # Nombre d'occurrences du mot "élection"
    date_import: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    guid: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)  # Identifiant unique (hash de l'URL)

    # Champ pour le contenu complet (utilisé pour l'analyse)
    contenu: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relation avec la table sources (optionnelle, pour compatibilité)
    source_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("sources.id"), nullable=True)
    source_rel: Mapped[Optional["Source"]] = relationship("Source", back_populates="articles")

    # Index
    __table_args__ = (
        Index("idx_article_lien", "lien"),
        Index("idx_article_date_publication", "date_publication"),
        Index("idx_article_categorie", "categorie"),
        Index("idx_article_compte_election", "compte_election"),
        Index("idx_article_guid", "guid"),
        Index("idx_article_date_import", "date_import"),
    )

    def __repr__(self) -> str:
        return f"<Article(id={self.id}, titre='{self.titre[:50]}...')>"


class Keyword(Base):
    """Modèle pour les mots-clés de filtrage."""

    __tablename__ = "keywords"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    keyword: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Index
    __table_args__ = (
        Index("idx_keyword_keyword", "keyword"),
        Index("idx_keyword_category", "category"),
        UniqueConstraint("keyword", "category", name="uq_keyword_category"),
    )

    def __repr__(self) -> str:
        return f"<Keyword(id={self.id}, keyword='{self.keyword}', category='{self.category}')>"


class ScrapingLog(Base):
    """Modèle pour les logs d'exécution du scraping."""

    __tablename__ = "scraping_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(Integer, ForeignKey("sources.id"), nullable=False)

    # Timing
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Résultats
    status: Mapped[str] = mapped_column(String(20), default="running")  # running, success, partial, failed
    articles_found: Mapped[int] = mapped_column(Integer, default=0)
    articles_saved: Mapped[int] = mapped_column(Integer, default=0)
    articles_skipped: Mapped[int] = mapped_column(Integer, default=0)

    # Erreurs
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relations
    source: Mapped["Source"] = relationship("Source", back_populates="scraping_logs")

    # Index
    __table_args__ = (
        Index("idx_scraping_log_source_id", "source_id"),
        Index("idx_scraping_log_started_at", "started_at"),
        Index("idx_scraping_log_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<ScrapingLog(id={self.id}, source_id={self.source_id}, status='{self.status}')>"
