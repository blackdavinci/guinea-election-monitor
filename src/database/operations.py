"""
Opérations CRUD pour la base de données.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy import select, update, func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from .models import Source, Article, Keyword, ScrapingLog

logger = logging.getLogger(__name__)


class SourceOperations:
    """Opérations CRUD pour les sources."""

    @staticmethod
    def create(session: Session, **kwargs) -> Source:
        """Crée une nouvelle source."""
        source = Source(**kwargs)
        session.add(source)
        session.flush()
        logger.info(f"Source créée: {source.name}")
        return source

    @staticmethod
    def get_by_id(session: Session, source_id: int) -> Optional[Source]:
        """Récupère une source par son ID."""
        return session.get(Source, source_id)

    @staticmethod
    def get_by_name(session: Session, name: str) -> Optional[Source]:
        """Récupère une source par son nom."""
        stmt = select(Source).where(Source.name == name)
        return session.execute(stmt).scalar_one_or_none()

    @staticmethod
    def get_all_active(session: Session) -> List[Source]:
        """Récupère toutes les sources actives."""
        stmt = select(Source).where(Source.is_active == True).order_by(Source.name)
        return list(session.execute(stmt).scalars().all())

    @staticmethod
    def get_all(session: Session) -> List[Source]:
        """Récupère toutes les sources."""
        stmt = select(Source).order_by(Source.name)
        return list(session.execute(stmt).scalars().all())

    @staticmethod
    def update_last_scraped(session: Session, source_id: int) -> None:
        """Met à jour la date du dernier scraping."""
        stmt = (
            update(Source)
            .where(Source.id == source_id)
            .values(last_scraped=datetime.utcnow())
        )
        session.execute(stmt)

    @staticmethod
    def update(session: Session, source_id: int, **kwargs) -> Optional[Source]:
        """Met à jour une source."""
        source = session.get(Source, source_id)
        if source:
            for key, value in kwargs.items():
                if hasattr(source, key):
                    setattr(source, key, value)
            session.flush()
            logger.info(f"Source mise à jour: {source.name}")
        return source

    @staticmethod
    def delete(session: Session, source_id: int) -> bool:
        """Supprime une source."""
        source = session.get(Source, source_id)
        if source:
            session.delete(source)
            logger.info(f"Source supprimée: {source.name}")
            return True
        return False


class ArticleOperations:
    """Opérations CRUD pour les articles."""

    @staticmethod
    def create(session: Session, **kwargs) -> Optional[Article]:
        """Crée un nouvel article."""
        try:
            article = Article(**kwargs)
            session.add(article)
            session.flush()
            logger.debug(f"Article créé: {article.titre[:50]}...")
            return article
        except IntegrityError:
            session.rollback()
            logger.warning(f"Article déjà existant (lien dupliqué): {kwargs.get('lien', 'N/A')}")
            return None

    @staticmethod
    def get_by_id(session: Session, article_id: int) -> Optional[Article]:
        """Récupère un article par son ID."""
        return session.get(Article, article_id)

    @staticmethod
    def get_by_lien(session: Session, lien: str) -> Optional[Article]:
        """Récupère un article par son lien."""
        stmt = select(Article).where(Article.lien == lien)
        return session.execute(stmt).scalar_one_or_none()

    @staticmethod
    def get_by_guid(session: Session, guid: str) -> Optional[Article]:
        """Récupère un article par son GUID."""
        stmt = select(Article).where(Article.guid == guid)
        return session.execute(stmt).scalar_one_or_none()

    @staticmethod
    def exists_by_lien(session: Session, lien: str) -> bool:
        """Vérifie si un article existe par son lien."""
        stmt = select(func.count()).select_from(Article).where(Article.lien == lien)
        count = session.execute(stmt).scalar()
        return count > 0

    @staticmethod
    def exists_by_guid(session: Session, guid: str) -> bool:
        """Vérifie si un article existe par son GUID."""
        stmt = select(func.count()).select_from(Article).where(Article.guid == guid)
        count = session.execute(stmt).scalar()
        return count > 0

    @staticmethod
    def get_recent(
        session: Session,
        limit: int = 50,
        source_name: Optional[str] = None,
        categorie: Optional[str] = None,
    ) -> List[Article]:
        """Récupère les articles récents."""
        stmt = select(Article).order_by(Article.date_import.desc()).limit(limit)
        if source_name:
            stmt = stmt.where(Article.source == source_name)
        if categorie:
            stmt = stmt.where(Article.categorie == categorie)
        return list(session.execute(stmt).scalars().all())

    @staticmethod
    def get_by_date_range(
        session: Session,
        start_date: datetime,
        end_date: datetime,
    ) -> List[Article]:
        """Récupère les articles dans une plage de dates."""
        stmt = (
            select(Article)
            .where(
                Article.date_publication >= start_date,
                Article.date_publication <= end_date,
            )
            .order_by(Article.date_publication.desc())
        )
        return list(session.execute(stmt).scalars().all())

    @staticmethod
    def get_today_articles(session: Session) -> List[Article]:
        """Récupère les articles du jour."""
        from datetime import date
        today = date.today()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())
        return ArticleOperations.get_by_date_range(session, today_start, today_end)

    @staticmethod
    def count_by_source(session: Session) -> Dict[str, int]:
        """Compte les articles par source."""
        stmt = (
            select(Article.source, func.count(Article.id))
            .group_by(Article.source)
        )
        results = session.execute(stmt).all()
        return {name: count for name, count in results}

    @staticmethod
    def count_by_categorie(session: Session) -> Dict[str, int]:
        """Compte les articles par catégorie."""
        stmt = (
            select(Article.categorie, func.count(Article.id))
            .group_by(Article.categorie)
        )
        results = session.execute(stmt).all()
        return {cat or "Non classé": count for cat, count in results}

    @staticmethod
    def get_top_tags(session: Session, limit: int = 20) -> List[Dict[str, Any]]:
        """Récupère les tags les plus fréquents dans les articles."""
        # Note: Cette requête utilise jsonb_array_elements_text pour PostgreSQL
        stmt = """
            SELECT tag, COUNT(*) as frequency
            FROM articles, jsonb_array_elements_text(tags) as tag
            GROUP BY tag
            ORDER BY frequency DESC
            LIMIT :limit
        """
        from sqlalchemy import text
        results = session.execute(text(stmt), {"limit": limit}).all()
        return [{"tag": tag, "frequency": freq} for tag, freq in results]

    @staticmethod
    def get_election_stats(session: Session) -> Dict[str, Any]:
        """Récupère les statistiques sur le mot 'élection'."""
        # Total des occurrences
        total_stmt = select(func.sum(Article.compte_election))
        total = session.execute(total_stmt).scalar() or 0

        # Articles mentionnant élection
        articles_with_election_stmt = (
            select(func.count())
            .select_from(Article)
            .where(Article.compte_election > 0)
        )
        articles_with_election = session.execute(articles_with_election_stmt).scalar() or 0

        # Moyenne par article
        avg_stmt = select(func.avg(Article.compte_election))
        avg = session.execute(avg_stmt).scalar() or 0

        return {
            "total_occurrences": total,
            "articles_with_election": articles_with_election,
            "average_per_article": round(float(avg), 2),
        }

    @staticmethod
    def delete_old_articles(session: Session, days: int = 90) -> int:
        """Supprime les articles plus anciens que X jours."""
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        stmt = select(Article).where(Article.date_import < cutoff_date)
        articles = session.execute(stmt).scalars().all()
        count = len(articles)
        for article in articles:
            session.delete(article)
        logger.info(f"{count} articles anciens supprimés")
        return count

    @staticmethod
    def bulk_create(session: Session, articles_data: List[Dict[str, Any]]) -> tuple[int, int]:
        """
        Crée plusieurs articles en bulk.

        Returns:
            Tuple (articles créés, articles ignorés)
        """
        created = 0
        skipped = 0

        for article_data in articles_data:
            # Vérifier si l'article existe déjà
            if ArticleOperations.exists_by_guid(session, article_data.get("guid", "")):
                skipped += 1
                logger.debug(f"Article ignoré (déjà existant): {article_data.get('lien', 'N/A')}")
                continue

            try:
                article = Article(**article_data)
                session.add(article)
                created += 1
            except Exception as e:
                logger.error(f"Erreur lors de la création de l'article: {e}")
                skipped += 1

        session.flush()
        logger.info(f"{created} articles créés, {skipped} articles ignorés")
        return created, skipped


class KeywordOperations:
    """Opérations CRUD pour les mots-clés."""

    @staticmethod
    def create(session: Session, **kwargs) -> Optional[Keyword]:
        """Crée un nouveau mot-clé."""
        try:
            keyword = Keyword(**kwargs)
            session.add(keyword)
            session.flush()
            return keyword
        except IntegrityError:
            session.rollback()
            logger.debug(f"Mot-clé déjà existant: {kwargs.get('keyword', 'N/A')}")
            return None

    @staticmethod
    def get_all_active(session: Session) -> List[Keyword]:
        """Récupère tous les mots-clés actifs."""
        stmt = select(Keyword).where(Keyword.is_active == True)
        return list(session.execute(stmt).scalars().all())

    @staticmethod
    def get_by_category(session: Session, category: str) -> List[Keyword]:
        """Récupère les mots-clés par catégorie."""
        stmt = (
            select(Keyword)
            .where(Keyword.category == category, Keyword.is_active == True)
        )
        return list(session.execute(stmt).scalars().all())

    @staticmethod
    def bulk_create(session: Session, keywords: List[Dict[str, Any]]) -> int:
        """Crée plusieurs mots-clés en bulk."""
        count = 0
        for kw_data in keywords:
            try:
                keyword = Keyword(**kw_data)
                session.add(keyword)
                count += 1
            except IntegrityError:
                session.rollback()
                continue
        session.flush()
        logger.info(f"{count} mots-clés créés")
        return count

    @staticmethod
    def get_keywords_dict(session: Session) -> Dict[str, List[Dict[str, Any]]]:
        """Récupère tous les mots-clés groupés par catégorie."""
        keywords = KeywordOperations.get_all_active(session)
        result: Dict[str, List[Dict[str, Any]]] = {}
        for kw in keywords:
            if kw.category not in result:
                result[kw.category] = []
            result[kw.category].append({
                "keyword": kw.keyword,
                "weight": kw.weight,
            })
        return result


class LogOperations:
    """Opérations pour les logs de scraping."""

    @staticmethod
    def create(session: Session, source_id: int) -> ScrapingLog:
        """Crée un nouveau log de scraping."""
        log = ScrapingLog(source_id=source_id)
        session.add(log)
        session.flush()
        return log

    @staticmethod
    def update(
        session: Session,
        log_id: int,
        status: str,
        articles_found: int = 0,
        articles_saved: int = 0,
        articles_skipped: int = 0,
        error_message: Optional[str] = None,
    ) -> Optional[ScrapingLog]:
        """Met à jour un log de scraping."""
        log = session.get(ScrapingLog, log_id)
        if log:
            log.status = status
            log.ended_at = datetime.utcnow()
            log.articles_found = articles_found
            log.articles_saved = articles_saved
            log.articles_skipped = articles_skipped
            log.error_message = error_message
            session.flush()
        return log

    @staticmethod
    def get_recent_logs(
        session: Session,
        limit: int = 50,
        source_id: Optional[int] = None,
    ) -> List[ScrapingLog]:
        """Récupère les logs récents."""
        stmt = select(ScrapingLog).order_by(ScrapingLog.started_at.desc()).limit(limit)
        if source_id:
            stmt = stmt.where(ScrapingLog.source_id == source_id)
        return list(session.execute(stmt).scalars().all())

    @staticmethod
    def get_last_log_for_source(session: Session, source_id: int) -> Optional[ScrapingLog]:
        """Récupère le dernier log pour une source."""
        stmt = (
            select(ScrapingLog)
            .where(ScrapingLog.source_id == source_id)
            .order_by(ScrapingLog.started_at.desc())
            .limit(1)
        )
        return session.execute(stmt).scalar_one_or_none()

    @staticmethod
    def get_stats(session: Session, days: int = 7) -> Dict[str, Any]:
        """Récupère les statistiques des logs sur X jours."""
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Total des logs
        total_stmt = (
            select(func.count())
            .select_from(ScrapingLog)
            .where(ScrapingLog.started_at >= cutoff_date)
        )
        total = session.execute(total_stmt).scalar()

        # Succès
        success_stmt = (
            select(func.count())
            .select_from(ScrapingLog)
            .where(
                ScrapingLog.started_at >= cutoff_date,
                ScrapingLog.status == "success",
            )
        )
        success = session.execute(success_stmt).scalar()

        # Total articles
        articles_stmt = (
            select(func.sum(ScrapingLog.articles_saved))
            .where(ScrapingLog.started_at >= cutoff_date)
        )
        articles = session.execute(articles_stmt).scalar() or 0

        return {
            "total_runs": total,
            "successful_runs": success,
            "success_rate": (success / total * 100) if total > 0 else 0,
            "total_articles_saved": articles,
        }
