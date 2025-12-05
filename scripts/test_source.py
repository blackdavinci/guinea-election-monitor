#!/usr/bin/env python3
"""
Script de test pour valider une source.

Usage:
    python scripts/test_source.py "Guinée News"
    python scripts/test_source.py "Guinée News" --verbose
"""

import argparse
import sys
from pathlib import Path

# Ajouter le chemin du projet au PYTHONPATH
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import yaml
from config.settings import CONFIG_DIR
from src.scraper.generic_scraper import GenericScraper
from src.main import load_keywords_config


def load_source_config(source_name: str) -> dict:
    """Charge la configuration d'une source."""
    sources_file = CONFIG_DIR / "sources.yaml"
    with open(sources_file, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    for source in config.get("sources", []):
        if source["name"].lower() == source_name.lower():
            return source

    return None


def test_source(source_name: str, verbose: bool = False, max_articles: int = 5):
    """Teste le scraping d'une source."""
    print("=" * 60)
    print(f"Test de la source: {source_name}")
    print("=" * 60)

    # Charger la configuration
    source_config = load_source_config(source_name)
    if not source_config:
        print(f"\n❌ Source '{source_name}' non trouvée!")
        print("\nSources disponibles:")

        sources_file = CONFIG_DIR / "sources.yaml"
        with open(sources_file, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        for source in config.get("sources", []):
            print(f"  - {source['name']}")
        return 1

    print(f"\n📰 URL de base: {source_config['base_url']}")
    print(f"📂 Catégories: {len(source_config.get('category_urls', []))}")

    # Charger les mots-clés
    keywords_dict = load_keywords_config()

    # Configurer le scraper
    selectors = source_config.get("selectors", {})
    scraper = GenericScraper(
        source_name=source_config["name"],
        base_url=source_config["base_url"],
        selectors=selectors,
        encoding=source_config.get("encoding", "utf-8"),
    )

    total_articles = 0
    all_articles = []

    # Tester chaque catégorie
    for category_url in source_config.get("category_urls", []):
        print(f"\n🔍 Test de: {category_url}")

        try:
            # Récupérer la liste des articles
            articles = scraper.scrape_category(
                category_url,
                keywords_dict=keywords_dict,
                max_articles=max_articles,
            )

            print(f"   ✅ {len(articles)} articles trouvés")
            total_articles += len(articles)
            all_articles.extend(articles)

        except Exception as e:
            print(f"   ❌ Erreur: {e}")
            if verbose:
                import traceback
                traceback.print_exc()

    scraper.close()

    # Afficher les résultats
    print("\n" + "=" * 60)
    print("RÉSULTATS")
    print("=" * 60)

    if not all_articles:
        print("\n⚠️  Aucun article trouvé!")
        print("\nConseils de débogage:")
        print("1. Vérifiez que l'URL est accessible")
        print("2. Vérifiez les sélecteurs CSS")
        print("3. Le site a peut-être changé de structure")
        return 1

    print(f"\n📊 Total articles trouvés: {len(all_articles)}")

    # Afficher les articles
    print("\n📰 Articles extraits:\n")

    for i, article in enumerate(all_articles[:10], 1):
        title = article.get("title", "Sans titre")
        url = article.get("url", "N/A")
        relevance = article.get("relevance_score", 0)
        keywords = article.get("keywords_matched", [])
        date = article.get("published_date")

        print(f"{i}. {title[:70]}...")
        print(f"   🔗 {url[:80]}...")
        print(f"   📊 Pertinence: {relevance:.0%}")
        if keywords:
            print(f"   🏷️  Mots-clés: {', '.join(keywords[:5])}")
        if date:
            print(f"   📅 Date: {date}")
        print()

    # Statistiques de pertinence
    relevance_scores = [a.get("relevance_score", 0) for a in all_articles]
    avg_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0
    high_relevance = sum(1 for s in relevance_scores if s >= 0.5)

    print("=" * 60)
    print("STATISTIQUES")
    print("=" * 60)
    print(f"📊 Pertinence moyenne: {avg_relevance:.0%}")
    print(f"⭐ Articles haute pertinence (≥50%): {high_relevance}")

    if verbose and all_articles:
        print("\n" + "=" * 60)
        print("CONTENU DU PREMIER ARTICLE")
        print("=" * 60)
        content = all_articles[0].get("content", "")[:500]
        print(f"\n{content}...")

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Tester le scraping d'une source",
    )
    parser.add_argument(
        "source_name",
        help="Nom de la source à tester",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Mode verbose avec plus de détails",
    )
    parser.add_argument(
        "--max-articles", "-n",
        type=int,
        default=5,
        help="Nombre maximum d'articles à récupérer (défaut: 5)",
    )

    args = parser.parse_args()

    return test_source(
        args.source_name,
        verbose=args.verbose,
        max_articles=args.max_articles,
    )


if __name__ == "__main__":
    sys.exit(main())
