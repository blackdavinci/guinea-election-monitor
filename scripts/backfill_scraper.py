#!/usr/bin/env python3
"""
Script de rattrapage pour récupérer les articles des jours passés.

Usage:
    python scripts/backfill_scraper.py --start 2025-11-28 --end 2025-12-04

Ce script:
1. Parcourt chaque source active
2. Pour chaque catégorie, pagine jusqu'à trouver des articles plus anciens que la date de début
3. Filtre les articles dans la plage de dates spécifiée
4. Sauvegarde les articles en base de données
"""

import argparse
import sys
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Set

# Ajouter le chemin du projet au PYTHONPATH
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import logging
from src.database.connection import session_scope, init_db
from src.database.operations import SourceOperations, ArticleOperations
from src.scraper.site_scrapers.wordpress_scraper import WordPressScraper
from src.scraper.site_scrapers.guineenews_scraper import GuineenewsScraper

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


class BackfillScraper:
    """Scraper pour rattraper les articles des jours passés."""

    def __init__(self, start_date: date, end_date: date, max_pages: int = 10):
        """
        Args:
            start_date: Date de début (incluse)
            end_date: Date de fin (incluse)
            max_pages: Nombre maximum de pages à parcourir par catégorie
        """
        self.start_date = start_date
        self.end_date = end_date
        self.max_pages = max_pages
        self.urls_seen: Set[str] = set()

    def is_date_in_range(self, article_date: Optional[datetime]) -> bool:
        """Vérifie si la date est dans la plage spécifiée."""
        if not article_date:
            return False
        article_day = article_date.date()
        return self.start_date <= article_day <= self.end_date

    def is_date_before_range(self, article_date: Optional[datetime]) -> bool:
        """Vérifie si la date est avant la plage (pour arrêter la pagination)."""
        if not article_date:
            return False
        return article_date.date() < self.start_date

    def scrape_category_with_pagination(
        self,
        scraper,
        category_url: str,
        categorie_name: str,
        max_articles_per_page: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        Scrape une catégorie avec pagination.

        Continue à paginer jusqu'à trouver des articles plus anciens que start_date
        ou atteindre max_pages.
        """
        all_articles = []
        page = 1
        found_old_articles = False

        while page <= self.max_pages and not found_old_articles:
            # Construire l'URL de la page
            if page == 1:
                page_url = category_url
            else:
                # Format WordPress standard pour la pagination
                if category_url.endswith('/'):
                    page_url = f"{category_url}page/{page}/"
                else:
                    page_url = f"{category_url}/page/{page}/"

            logger.info(f"  Page {page}: {page_url}")

            # Récupérer le HTML de la page
            html = scraper.fetch_page(page_url, scraper.encoding)
            if not html:
                logger.warning(f"  Impossible de récupérer la page {page}")
                break

            # Parser la liste des articles
            if hasattr(scraper, 'parse_article_list'):
                article_list = scraper.parse_article_list(html)
            else:
                article_list = scraper.scrape_article_list(page_url, scraper.encoding)

            if not article_list:
                logger.info(f"  Aucun article trouvé sur la page {page}, arrêt")
                break

            logger.info(f"  {len(article_list)} articles trouvés sur la page {page}")

            # Traiter chaque article
            articles_in_range = 0
            articles_before_range = 0
            articles_unknown_date = 0

            for article_info in article_list:
                url = article_info.get("url")
                if not url or url in self.urls_seen:
                    continue

                # Extraire la date depuis l'URL ou l'info
                published_date = article_info.get("published_date")
                if not published_date:
                    published_date = scraper.extract_date_from_url(url)

                # Si on a une date, filtrer
                if published_date:
                    if self.is_date_before_range(published_date):
                        articles_before_range += 1
                        continue

                    if not self.is_date_in_range(published_date):
                        # Article après la plage (trop récent), on passe
                        continue

                # Article potentiellement dans la plage (ou date inconnue), on le scrape
                try:
                    article_data = scraper.scrape_full_article(url, categorie_name)
                    if article_data:
                        # Vérifier la date après scraping
                        final_date = article_data.get("date_publication") or published_date
                        if final_date:
                            if self.is_date_in_range(final_date):
                                self.urls_seen.add(url)
                                all_articles.append(article_data)
                                articles_in_range += 1
                            elif self.is_date_before_range(final_date):
                                articles_before_range += 1
                        else:
                            # Pas de date trouvée même après scraping, on garde quand même
                            articles_unknown_date += 1
                            self.urls_seen.add(url)
                            all_articles.append(article_data)

                except Exception as e:
                    logger.error(f"  Erreur scraping {url}: {e}")
                    continue

            logger.info(f"  Page {page}: {articles_in_range} dans la plage, {articles_before_range} trop anciens, {articles_unknown_date} sans date")

            # Si tous les articles de la page sont trop anciens (et aucun sans date), on arrête
            if articles_before_range > 0 and articles_in_range == 0 and articles_unknown_date == 0:
                logger.info(f"  Tous les articles sont trop anciens, arrêt de la pagination")
                found_old_articles = True

            # Si la page était vide ou avait peu d'articles, on arrête
            if len(article_list) < 5:
                break

            page += 1

        return all_articles

    def run(self, source_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Exécute le rattrapage pour toutes les sources.

        Args:
            source_names: Liste des noms de sources (None = toutes)
        """
        logger.info("=" * 60)
        logger.info("RATTRAPAGE DES ARTICLES")
        logger.info(f"Période: {self.start_date} au {self.end_date}")
        logger.info("=" * 60)

        stats = {
            "start_date": self.start_date,
            "end_date": self.end_date,
            "sources_processed": 0,
            "total_articles_found": 0,
            "total_articles_saved": 0,
            "by_source": {},
        }

        init_db()

        with session_scope() as session:
            sources = SourceOperations.get_all_active(session)

            if source_names:
                sources = [s for s in sources if s.name in source_names]

            logger.info(f"Sources à traiter: {len(sources)}")

            for source in sources:
                logger.info(f"\n{'='*40}")
                logger.info(f"Source: {source.name}")
                logger.info(f"{'='*40}")

                source_articles = []
                self.urls_seen.clear()

                try:
                    # Créer le scraper approprié
                    selectors = {
                        "article_list": source.article_list_selector,
                        "title": source.title_selector,
                        "link": source.link_selector,
                        "date": source.date_selector,
                        "content": source.content_selector,
                    }

                    if source.scraper_type == "guineenews":
                        scraper = GuineenewsScraper(
                            source_name=source.name,
                            base_url=source.base_url,
                            selectors=selectors,
                            encoding=source.encoding or "utf-8",
                        )
                    else:
                        scraper = WordPressScraper(
                            source_name=source.name,
                            base_url=source.base_url,
                            site_type=source.site_type,
                            selectors=selectors,
                            encoding=source.encoding or "utf-8",
                            use_curl=True,
                        )

                    # Parcourir chaque catégorie
                    category_urls = source.category_urls or []
                    for cat_config in category_urls:
                        cat_url = cat_config.get("url")
                        cat_name = cat_config.get("categorie", "Non classé")

                        if not cat_url:
                            continue

                        logger.info(f"\nCatégorie: {cat_name}")

                        try:
                            articles = self.scrape_category_with_pagination(
                                scraper=scraper,
                                category_url=cat_url,
                                categorie_name=cat_name,
                            )
                            source_articles.extend(articles)
                        except Exception as e:
                            logger.warning(f"  Erreur sur catégorie {cat_name}: {e}")
                            continue

                    scraper.close()

                    # Dédupliquer par URL
                    unique_articles = []
                    seen_urls = set()
                    for article in source_articles:
                        url = article.get("lien")
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            unique_articles.append(article)

                    logger.info(f"\n{source.name}: {len(unique_articles)} articles uniques trouvés")

                    # Sauvegarder
                    if unique_articles:
                        created, skipped = ArticleOperations.bulk_create(session, unique_articles)
                        logger.info(f"{source.name}: {created} créés, {skipped} ignorés (déjà existants)")
                        stats["total_articles_saved"] += created

                    stats["total_articles_found"] += len(unique_articles)
                    stats["by_source"][source.name] = len(unique_articles)
                    stats["sources_processed"] += 1

                except Exception as e:
                    logger.error(f"Erreur pour {source.name}: {e}")
                    stats["by_source"][source.name] = f"ERREUR: {e}"

        # Résumé
        logger.info("\n" + "=" * 60)
        logger.info("RÉSUMÉ DU RATTRAPAGE")
        logger.info("=" * 60)
        logger.info(f"Période: {self.start_date} au {self.end_date}")
        logger.info(f"Sources traitées: {stats['sources_processed']}")
        logger.info(f"Articles trouvés: {stats['total_articles_found']}")
        logger.info(f"Articles sauvegardés: {stats['total_articles_saved']}")
        logger.info("\nPar source:")
        for source_name, count in stats["by_source"].items():
            logger.info(f"  - {source_name}: {count}")
        logger.info("=" * 60)

        return stats


def parse_date(date_str: str) -> date:
    """Parse une date au format YYYY-MM-DD."""
    return datetime.strptime(date_str, "%Y-%m-%d").date()


def main():
    parser = argparse.ArgumentParser(
        description="Rattrapage des articles pour une période donnée"
    )
    parser.add_argument(
        "--start",
        type=str,
        required=True,
        help="Date de début (format: YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end",
        type=str,
        required=True,
        help="Date de fin (format: YYYY-MM-DD)",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=10,
        help="Nombre maximum de pages à parcourir par catégorie (défaut: 10)",
    )
    parser.add_argument(
        "--sources",
        type=str,
        nargs="*",
        help="Noms des sources à traiter (défaut: toutes)",
    )

    args = parser.parse_args()

    start_date = parse_date(args.start)
    end_date = parse_date(args.end)

    if start_date > end_date:
        logger.error("La date de début doit être avant la date de fin")
        return 1

    backfill = BackfillScraper(
        start_date=start_date,
        end_date=end_date,
        max_pages=args.max_pages,
    )

    stats = backfill.run(source_names=args.sources)

    return 0 if stats["total_articles_found"] > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
