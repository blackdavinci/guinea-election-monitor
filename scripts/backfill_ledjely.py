#!/usr/bin/env python3
"""
Script de rattrapage spécifique pour Ledjely.

Usage:
    python scripts/backfill_ledjely.py --start 2025-11-28 --end 2025-12-05

Ce script récupère les articles de Ledjely pour une période donnée.
"""

import argparse
import sys
from datetime import datetime, date
from pathlib import Path

# Ajouter le chemin du projet au PYTHONPATH
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import logging
from src.database.connection import session_scope, init_db
from src.database.operations import SourceOperations, ArticleOperations
from src.scraper.site_scrapers.wordpress_scraper import WordPressScraper

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


def backfill_ledjely(start_date: date, end_date: date, max_pages: int = 15):
    """
    Récupère les articles de Ledjely pour une période donnée.
    """
    logger.info("=" * 60)
    logger.info("RATTRAPAGE LEDJELY")
    logger.info(f"Période: {start_date} au {end_date}")
    logger.info("=" * 60)

    init_db()

    stats = {
        "articles_found": 0,
        "articles_saved": 0,
        "by_category": {},
    }

    with session_scope() as session:
        # Récupérer la source Ledjely
        source = SourceOperations.get_by_name(session, "Ledjely")

        if not source:
            logger.error("Source 'Ledjely' non trouvée en base. Exécutez d'abord init_db.py")
            return stats

        logger.info(f"Source trouvée: {source.name} - {source.base_url}")

        # Configurer le scraper
        selectors = {
            "article_list": source.article_list_selector,
            "title": source.title_selector,
            "link": source.link_selector,
            "date": source.date_selector,
            "content": source.content_selector,
        }

        scraper = WordPressScraper(
            source_name=source.name,
            base_url=source.base_url,
            site_type=source.site_type,
            selectors=selectors,
            encoding=source.encoding or "utf-8",
            use_curl=True,
        )

        category_urls = source.category_urls or []
        all_articles = []
        urls_seen = set()

        for cat_config in category_urls:
            cat_url = cat_config.get("url")
            cat_name = cat_config.get("categorie", "Non classé")

            if not cat_url:
                continue

            logger.info(f"\nCatégorie: {cat_name}")
            category_articles = []

            # Paginer pour trouver les articles dans la plage de dates
            page = 1
            found_old_articles = False

            while page <= max_pages and not found_old_articles:
                if page == 1:
                    page_url = cat_url
                else:
                    if cat_url.endswith('/'):
                        page_url = f"{cat_url}page/{page}/"
                    else:
                        page_url = f"{cat_url}/page/{page}/"

                logger.info(f"  Page {page}: {page_url}")

                html = scraper.fetch_page(page_url, scraper.encoding)
                if not html:
                    logger.warning(f"  Impossible de récupérer la page {page}")
                    break

                article_list = scraper.parse_article_list(html)
                if not article_list:
                    logger.info(f"  Aucun article trouvé sur la page {page}")
                    break

                logger.info(f"  {len(article_list)} articles trouvés")

                articles_in_range = 0
                articles_before_range = 0

                for article_info in article_list:
                    url = article_info.get("url")
                    if not url or url in urls_seen:
                        continue

                    # Extraire la date depuis l'URL
                    published_date = scraper.extract_date_from_url(url)

                    if published_date:
                        article_date = published_date.date()

                        if article_date < start_date:
                            articles_before_range += 1
                            continue

                        if article_date > end_date:
                            continue

                        # Article dans la plage - le scraper
                        try:
                            article_data = scraper.scrape_full_article(url, cat_name)
                            if article_data:
                                urls_seen.add(url)
                                category_articles.append(article_data)
                                articles_in_range += 1
                        except Exception as e:
                            logger.error(f"  Erreur scraping {url}: {e}")
                    else:
                        # Pas de date dans l'URL, on scrape quand même
                        try:
                            article_data = scraper.scrape_full_article(url, cat_name)
                            if article_data and article_data.get("date_publication"):
                                article_date = article_data["date_publication"].date()
                                if start_date <= article_date <= end_date:
                                    urls_seen.add(url)
                                    category_articles.append(article_data)
                                    articles_in_range += 1
                                elif article_date < start_date:
                                    articles_before_range += 1
                        except Exception as e:
                            logger.error(f"  Erreur scraping {url}: {e}")

                logger.info(f"  Page {page}: {articles_in_range} dans la plage, {articles_before_range} trop anciens")

                # Si tous les articles sont trop anciens, on arrête
                if articles_before_range > 0 and articles_in_range == 0:
                    logger.info(f"  Tous les articles sont trop anciens, arrêt")
                    found_old_articles = True

                if len(article_list) < 5:
                    break

                page += 1

            logger.info(f"  {cat_name}: {len(category_articles)} articles trouvés")
            stats["by_category"][cat_name] = len(category_articles)
            all_articles.extend(category_articles)

        scraper.close()

        # Sauvegarder les articles
        logger.info(f"\nTotal: {len(all_articles)} articles uniques trouvés")
        stats["articles_found"] = len(all_articles)

        if all_articles:
            created, skipped = ArticleOperations.bulk_create(session, all_articles)
            logger.info(f"Sauvegardés: {created} créés, {skipped} ignorés (déjà existants)")
            stats["articles_saved"] = created

    # Résumé
    logger.info("\n" + "=" * 60)
    logger.info("RÉSUMÉ RATTRAPAGE LEDJELY")
    logger.info("=" * 60)
    logger.info(f"Période: {start_date} au {end_date}")
    logger.info(f"Articles trouvés: {stats['articles_found']}")
    logger.info(f"Articles sauvegardés: {stats['articles_saved']}")
    logger.info("\nPar catégorie:")
    for cat_name, count in stats["by_category"].items():
        logger.info(f"  - {cat_name}: {count}")
    logger.info("=" * 60)

    return stats


def parse_date(date_str: str) -> date:
    """Parse une date au format YYYY-MM-DD."""
    return datetime.strptime(date_str, "%Y-%m-%d").date()


def main():
    parser = argparse.ArgumentParser(
        description="Rattrapage des articles Ledjely pour une période donnée"
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
        default=15,
        help="Nombre maximum de pages à parcourir par catégorie (défaut: 15)",
    )

    args = parser.parse_args()

    start_date = parse_date(args.start)
    end_date = parse_date(args.end)

    if start_date > end_date:
        logger.error("La date de début doit être avant la date de fin")
        return 1

    stats = backfill_ledjely(
        start_date=start_date,
        end_date=end_date,
        max_pages=args.max_pages,
    )

    return 0 if stats["articles_found"] > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
