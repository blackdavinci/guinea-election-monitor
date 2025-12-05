#!/usr/bin/env python3
"""
Script d'exécution manuelle du scraper.

Usage:
    python scripts/run_scraper.py                    # Toutes les sources
    python scripts/run_scraper.py "Guinée News"     # Une source spécifique
    python scripts/run_scraper.py --list            # Lister les sources
"""

import argparse
import sys
from pathlib import Path

# Ajouter le chemin du projet au PYTHONPATH
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.main import main as run_main, setup_logging
from src.database.connection import session_scope
from src.database.operations import SourceOperations


def list_sources():
    """Affiche la liste des sources configurées."""
    print("\n📰 Sources configurées:\n")

    with session_scope() as session:
        sources = SourceOperations.get_all(session)

        if not sources:
            print("   Aucune source trouvée. Exécutez d'abord: python scripts/init_db.py")
            return

        for source in sources:
            status = "✅ Active" if source.is_active else "❌ Inactive"
            last_scraped = source.last_scraped.strftime("%Y-%m-%d %H:%M") if source.last_scraped else "Jamais"
            print(f"   {status} {source.name}")
            print(f"      URL: {source.base_url}")
            print(f"      Dernier scraping: {last_scraped}")
            print()


def run_for_sources(source_names: list):
    """Exécute le scraper pour des sources spécifiques."""
    from src.main import ElectionMonitor, setup_logging
    from src.database.connection import init_db

    logger = setup_logging()

    try:
        init_db()
        monitor = ElectionMonitor(logger)
        stats = monitor.run(source_names=source_names if source_names else None)
        return 0 if stats["sources_failed"] == 0 else 1
    except Exception as e:
        logger.critical(f"Erreur fatale: {e}", exc_info=True)
        return 1


def main():
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(
        description="Scraper de veille électorale Guinée",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  python scripts/run_scraper.py                     # Scraper toutes les sources
  python scripts/run_scraper.py "Guinée News"      # Scraper une source
  python scripts/run_scraper.py "Guinée News" "Africaguinee"  # Plusieurs sources
  python scripts/run_scraper.py --list              # Lister les sources
        """,
    )

    parser.add_argument(
        "sources",
        nargs="*",
        help="Noms des sources à scraper (toutes par défaut)",
    )

    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="Afficher la liste des sources configurées",
    )

    args = parser.parse_args()

    if args.list:
        list_sources()
        return 0

    print("=" * 60)
    print("🗞️  Veille Électorale Guinée - Scraper")
    print("=" * 60)

    if args.sources:
        print(f"\nSources sélectionnées: {', '.join(args.sources)}")

    return run_for_sources(args.sources if args.sources else None)


if __name__ == "__main__":
    sys.exit(main())
