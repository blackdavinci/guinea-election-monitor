#!/usr/bin/env python3
"""
Script d'initialisation de la base de données.

Ce script:
1. Crée toutes les tables
2. Insère les sources depuis sources.yaml
3. Insère les mots-clés depuis keywords.yaml
"""

import sys
from pathlib import Path

# Ajouter le chemin du projet au PYTHONPATH
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import yaml
from config.settings import CONFIG_DIR
from src.database.connection import init_db, session_scope, check_connection
from src.database.operations import SourceOperations, KeywordOperations


def load_sources() -> list:
    """Charge les sources depuis le fichier YAML."""
    sources_file = CONFIG_DIR / "sources.yaml"
    with open(sources_file, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config.get("sources", [])


def load_keywords() -> dict:
    """Charge les mots-clés depuis le fichier YAML."""
    keywords_file = CONFIG_DIR / "keywords.yaml"
    with open(keywords_file, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config.get("keywords", {})


def insert_sources(session) -> int:
    """Insère les sources en base de données."""
    sources = load_sources()
    count = 0

    for source_config in sources:
        # Vérifier si la source existe déjà
        existing = SourceOperations.get_by_name(session, source_config["name"])
        if existing:
            print(f"  ⏭️  Source déjà existante: {source_config['name']}")
            continue

        # Extraire les sélecteurs
        selectors = source_config.get("selectors", {})

        source = SourceOperations.create(
            session,
            name=source_config["name"],
            base_url=source_config["base_url"],
            scraper_type=source_config.get("scraper_type", "generic"),
            site_type=source_config.get("site_type"),
            article_list_selector=selectors.get("article_list"),
            title_selector=selectors.get("title"),
            link_selector=selectors.get("link"),
            content_selector=selectors.get("content"),
            date_selector=selectors.get("date"),
            category_urls=source_config.get("category_urls", []),
            encoding=source_config.get("encoding", "utf-8"),
            is_active=source_config.get("is_active", True),
        )
        print(f"  ✅ Source créée: {source.name}")
        count += 1

    return count


def insert_keywords(session) -> int:
    """Insère les mots-clés en base de données."""
    keywords_config = load_keywords()
    count = 0

    for category, data in keywords_config.items():
        weight = data.get("weight", 1.0)
        terms = data.get("terms", [])

        for term in terms:
            keyword = KeywordOperations.create(
                session,
                keyword=term,
                category=category,
                weight=weight,
                is_active=True,
            )
            if keyword:
                count += 1

    return count


def main():
    """Fonction principale d'initialisation."""
    print("=" * 60)
    print("Initialisation de la base de données")
    print("Veille Électorale Guinée")
    print("=" * 60)

    # Vérifier la connexion
    print("\n📡 Vérification de la connexion...")
    if not check_connection():
        print("❌ Impossible de se connecter à la base de données!")
        print("   Vérifiez que PostgreSQL est démarré et que les paramètres")
        print("   de connexion dans .env sont corrects.")
        return 1

    print("✅ Connexion réussie")

    # Créer les tables
    print("\n📦 Création des tables...")
    try:
        init_db()
        print("✅ Tables créées avec succès")
    except Exception as e:
        print(f"❌ Erreur lors de la création des tables: {e}")
        return 1

    # Insérer les données
    with session_scope() as session:
        # Sources
        print("\n📰 Insertion des sources...")
        sources_count = insert_sources(session)
        print(f"   {sources_count} nouvelles sources ajoutées")

        # Mots-clés
        print("\n🔑 Insertion des mots-clés...")
        keywords_count = insert_keywords(session)
        print(f"   {keywords_count} nouveaux mots-clés ajoutés")

    print("\n" + "=" * 60)
    print("✅ Initialisation terminée avec succès!")
    print("=" * 60)

    print("\nProchaines étapes:")
    print("1. Lancez le scraper: python scripts/run_scraper.py")
    print("2. Accédez à Metabase: http://localhost:3000")
    print("3. Configurez le cron: bash scripts/setup_cron.sh")

    return 0


if __name__ == "__main__":
    sys.exit(main())
