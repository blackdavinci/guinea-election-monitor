"""
Point d'entrée principal du système de veille électorale.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

import yaml

# Ajouter le chemin du projet au PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import (
    CONFIG_DIR,
    LOGS_DIR,
    LOG_LEVEL,
    LOG_FORMAT,
    LOG_FILE,
    SCRAPING_CONFIG,
)
from src.database.connection import session_scope, init_db
from src.database.operations import (
    SourceOperations,
    ArticleOperations,
    KeywordOperations,
    LogOperations,
)
from src.scraper.generic_scraper import GenericScraper
from src.scraper.site_scrapers.guineenews_scraper import GuineenewsScraper
from src.scraper.site_scrapers.wordpress_scraper import WordPressScraper
from src.utils.text_processor import TextProcessor
from src.utils.deduplication import Deduplicator
from src.utils.notifications import NotificationManager


def setup_logging() -> logging.Logger:
    """Configure le logging pour l'application."""
    # Créer le dossier logs s'il n'existe pas
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # Configuration du logger
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL),
        format=LOG_FORMAT,
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )

    return logging.getLogger(__name__)


def load_keywords_config() -> Dict[str, List[Dict[str, Any]]]:
    """Charge la configuration des mots-clés depuis le fichier YAML."""
    keywords_file = CONFIG_DIR / "keywords.yaml"

    with open(keywords_file, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # Transformer en format utilisable par le scraper
    keywords_dict = {}
    for category, data in config.get("keywords", {}).items():
        weight = data.get("weight", 1.0)
        keywords_dict[category] = [
            {"keyword": term, "weight": weight}
            for term in data.get("terms", [])
        ]

    return keywords_dict


def load_sources_config() -> List[Dict[str, Any]]:
    """Charge la configuration des sources depuis le fichier YAML."""
    sources_file = CONFIG_DIR / "sources.yaml"

    with open(sources_file, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    return config.get("sources", [])


class ElectionMonitor:
    """Classe principale pour orchestrer le scraping."""

    def __init__(self, logger: logging.Logger, days_back: int = 1):
        """
        Args:
            logger: Logger pour les messages
            days_back: Nombre de jours en arrière à scraper (1 = aujourd'hui + hier)
        """
        self.logger = logger
        self.keywords_dict = load_keywords_config()
        self.sources_config = load_sources_config()
        self.notification_manager = NotificationManager()
        self.relevance_threshold = SCRAPING_CONFIG["relevance_threshold"]
        self.days_back = days_back

    def run(self, source_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Exécute le scraping pour toutes les sources ou une sélection.

        Args:
            source_names: Liste des noms de sources à scraper (None = toutes)

        Returns:
            Dictionnaire avec les statistiques d'exécution
        """
        self.logger.info("=" * 60)
        self.logger.info("Démarrage du scraping - Veille Électorale Guinée")
        self.logger.info("=" * 60)

        stats = {
            "started_at": datetime.utcnow(),
            "sources_processed": 0,
            "sources_success": 0,
            "sources_failed": 0,
            "total_articles_found": 0,
            "total_articles_saved": 0,
            "total_articles_skipped": 0,
            "high_relevance_articles": [],
            "sources_status": {},
        }

        with session_scope() as session:
            # Récupérer les sources actives
            sources = SourceOperations.get_all_active(session)

            if source_names:
                sources = [s for s in sources if s.name in source_names]

            if not sources:
                self.logger.warning("Aucune source active trouvée")
                return stats

            self.logger.info(f"Sources à traiter: {len(sources)}")

            for source in sources:
                try:
                    source_stats = self._scrape_source(session, source)
                    stats["sources_processed"] += 1
                    stats["total_articles_found"] += source_stats["articles_found"]
                    stats["total_articles_saved"] += source_stats["articles_saved"]
                    stats["total_articles_skipped"] += source_stats["articles_skipped"]
                    stats["high_relevance_articles"].extend(
                        source_stats.get("high_relevance", [])
                    )

                    if source_stats["status"] == "success":
                        stats["sources_success"] += 1
                    stats["sources_status"][source.name] = source_stats["status"]

                except Exception as e:
                    self.logger.error(f"Erreur critique pour {source.name}: {e}")
                    stats["sources_failed"] += 1
                    stats["sources_status"][source.name] = "failed"

        stats["ended_at"] = datetime.utcnow()
        stats["duration"] = (stats["ended_at"] - stats["started_at"]).total_seconds()

        self._log_summary(stats)
        self._send_notifications(stats)

        return stats

    def _scrape_source(self, session, source) -> Dict[str, Any]:
        """
        Scrape une source spécifique.

        Args:
            session: Session SQLAlchemy
            source: Objet Source

        Returns:
            Statistiques du scraping pour cette source
        """
        self.logger.info(f"\n--- Traitement de: {source.name} ---")

        # Créer un log de scraping
        scraping_log = LogOperations.create(session, source.id)
        session.commit()

        stats = {
            "status": "running",
            "articles_found": 0,
            "articles_saved": 0,
            "articles_skipped": 0,
            "high_relevance": [],
            "error_message": None,
        }

        try:
            # Configurer les sélecteurs
            selectors = {
                "article_list": source.article_list_selector,
                "title": source.title_selector,
                "link": source.link_selector,
                "date": source.date_selector,
                "content": source.content_selector,
            }

            all_articles = []
            category_urls = source.category_urls or []

            # Utiliser le scraper approprié selon le type
            if source.scraper_type == "guineenews":
                # Utiliser le scraper spécialisé Guineenews
                selectors["tags"] = "a[rel='tag']"
                scraper = GuineenewsScraper(
                    source_name=source.name,
                    base_url=source.base_url,
                    selectors=selectors,
                    encoding=source.encoding or "utf-8",
                )

                # Scraper toutes les catégories (articles du jour + jours précédents selon days_back)
                all_articles = scraper.scrape_all_categories(
                    category_configs=category_urls,
                    max_articles_per_category=30,
                    only_today=True,
                    days_back=self.days_back,
                )
                scraper.close()

                stats["articles_found"] = len(all_articles)

                # Sauvegarder les articles avec le nouveau format
                created, skipped = ArticleOperations.bulk_create(session, all_articles)
                stats["articles_saved"] = created
                stats["articles_skipped"] = skipped

                # Identifier les articles avec beaucoup de mentions d'élection
                for article_data in all_articles:
                    if article_data.get("compte_election", 0) >= 3:
                        stats["high_relevance"].append({
                            "title": article_data.get("titre"),
                            "url": article_data.get("lien"),
                            "source": source.name,
                            "compte_election": article_data.get("compte_election", 0),
                        })

            elif source.scraper_type == "wordpress":
                # Utiliser le scraper WordPress générique
                scraper = WordPressScraper(
                    source_name=source.name,
                    base_url=source.base_url,
                    site_type=source.site_type if hasattr(source, 'site_type') else None,
                    selectors=selectors,
                    encoding=source.encoding or "utf-8",
                    use_curl=True,  # Utiliser curl pour contourner les problèmes de connexion
                )

                # Scraper toutes les catégories (articles du jour + jours précédents selon days_back)
                all_articles = scraper.scrape_all_categories(
                    category_configs=category_urls,
                    max_articles_per_category=30,
                    only_today=True,
                    days_back=self.days_back,
                )
                scraper.close()

                stats["articles_found"] = len(all_articles)

                # Sauvegarder les articles avec le nouveau format
                created, skipped = ArticleOperations.bulk_create(session, all_articles)
                stats["articles_saved"] = created
                stats["articles_skipped"] = skipped

                # Identifier les articles avec beaucoup de mentions d'élection
                for article_data in all_articles:
                    if article_data.get("compte_election", 0) >= 3:
                        stats["high_relevance"].append({
                            "title": article_data.get("titre"),
                            "url": article_data.get("lien"),
                            "source": source.name,
                            "compte_election": article_data.get("compte_election", 0),
                        })

            else:
                # Utiliser le scraper générique pour les autres sources
                scraper = GenericScraper(
                    source_name=source.name,
                    base_url=source.base_url,
                    selectors=selectors,
                    encoding=source.encoding or "utf-8",
                )

                for category_url in category_urls:
                    # Support ancien format (string) et nouveau format (dict)
                    if isinstance(category_url, dict):
                        url = category_url.get("url")
                    else:
                        url = category_url

                    try:
                        articles = scraper.scrape_category(
                            url,
                            keywords_dict=self.keywords_dict,
                            max_articles=30,
                        )
                        all_articles.extend(articles)
                    except Exception as e:
                        self.logger.warning(
                            f"Erreur lors du scraping de {url}: {e}"
                        )

                scraper.close()

                stats["articles_found"] = len(all_articles)

                # Dédupliquer
                all_articles = Deduplicator.deduplicate_list(all_articles)

                # Sauvegarder les articles (ancien format)
                for article_data in all_articles:
                    saved, is_high_relevance = self._save_article(
                        session, source, article_data
                    )
                    if saved:
                        stats["articles_saved"] += 1
                        if is_high_relevance:
                            stats["high_relevance"].append({
                                "title": article_data.get("title"),
                                "url": article_data.get("url"),
                                "source": source.name,
                                "relevance_score": article_data.get("relevance_score", 0),
                            })
                    else:
                        stats["articles_skipped"] += 1

            # Mettre à jour le timestamp de dernière mise à jour
            SourceOperations.update_last_scraped(session, source.id)

            stats["status"] = "success" if stats["articles_saved"] > 0 else "partial"

        except Exception as e:
            self.logger.error(f"Erreur lors du scraping de {source.name}: {e}")
            stats["status"] = "failed"
            stats["error_message"] = str(e)

        # Mettre à jour le log
        LogOperations.update(
            session,
            scraping_log.id,
            status=stats["status"],
            articles_found=stats["articles_found"],
            articles_saved=stats["articles_saved"],
            articles_skipped=stats["articles_skipped"],
            error_message=stats["error_message"],
        )
        session.commit()

        self.logger.info(
            f"[{source.name}] Terminé: {stats['articles_saved']}/{stats['articles_found']} "
            f"articles sauvegardés"
        )

        return stats

    def _save_article(self, session, source, article_data: dict) -> tuple:
        """
        Sauvegarde un article en base de données.

        Args:
            session: Session SQLAlchemy
            source: Source de l'article
            article_data: Données de l'article

        Returns:
            Tuple (sauvegardé: bool, haute_pertinence: bool)
        """
        url = article_data.get("url")
        if not url:
            return False, False

        # Vérifier si l'article existe déjà
        if ArticleOperations.exists_by_url(session, url):
            self.logger.debug(f"Article déjà existant: {url}")
            return False, False

        # Vérifier le score de pertinence
        relevance_score = article_data.get("relevance_score", 0)
        if relevance_score < self.relevance_threshold:
            self.logger.debug(
                f"Article ignoré (pertinence {relevance_score:.2f} < {self.relevance_threshold}): "
                f"{article_data.get('title', 'N/A')[:50]}"
            )
            return False, False

        # Calculer le hash du contenu
        content = article_data.get("content", "")
        content_hash = TextProcessor.compute_hash(content)

        # Vérifier si un article avec le même contenu existe
        if content_hash and ArticleOperations.exists_by_content_hash(session, content_hash):
            self.logger.debug(f"Article avec contenu identique trouvé: {url}")
            return False, False

        # Générer un résumé
        summary = TextProcessor.generate_summary(content, max_length=300)

        # Détecter la langue
        language = TextProcessor.detect_language(content)

        # Créer l'article
        article = ArticleOperations.create(
            session,
            source_id=source.id,
            title=article_data.get("title", ""),
            url=url,
            content=content,
            summary=summary,
            published_date=article_data.get("published_date"),
            keywords_matched=article_data.get("keywords_matched", []),
            relevance_score=relevance_score,
            language=language,
            content_hash=content_hash,
        )

        if article:
            is_high_relevance = relevance_score >= 0.7
            if is_high_relevance:
                self.logger.info(
                    f"✨ Article haute pertinence ({relevance_score:.0%}): "
                    f"{article_data.get('title', 'N/A')[:60]}"
                )
            return True, is_high_relevance

        return False, False

    def _log_summary(self, stats: Dict[str, Any]) -> None:
        """Affiche un résumé des statistiques."""
        self.logger.info("\n" + "=" * 60)
        self.logger.info("RÉSUMÉ DU SCRAPING")
        self.logger.info("=" * 60)
        self.logger.info(f"Durée: {stats['duration']:.1f} secondes")
        self.logger.info(f"Sources traitées: {stats['sources_processed']}")
        self.logger.info(f"  - Succès: {stats['sources_success']}")
        self.logger.info(f"  - Échecs: {stats['sources_failed']}")
        self.logger.info(f"Articles trouvés: {stats['total_articles_found']}")
        self.logger.info(f"Articles sauvegardés: {stats['total_articles_saved']}")
        self.logger.info(f"Articles ignorés: {stats['total_articles_skipped']}")
        self.logger.info(
            f"Articles haute pertinence: {len(stats['high_relevance_articles'])}"
        )
        self.logger.info("=" * 60 + "\n")

    def _send_notifications(self, stats: Dict[str, Any]) -> None:
        """Envoie les notifications si configurées."""
        # Notifier pour chaque article à haute pertinence
        for article in stats["high_relevance_articles"]:
            self.notification_manager.notify_new_article(
                title=article.get("title") or article.get("titre", ""),
                url=article.get("url") or article.get("lien", ""),
                source=article.get("source", ""),
                relevance_score=article.get("relevance_score") or article.get("compte_election", 0),
            )


def main():
    """Fonction principale."""
    logger = setup_logging()

    try:
        # Initialiser la base de données
        init_db()
        logger.info("Base de données initialisée")

        # Lancer le scraping
        monitor = ElectionMonitor(logger)
        stats = monitor.run()

        return 0 if stats["sources_failed"] == 0 else 1

    except Exception as e:
        logger.critical(f"Erreur fatale: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
