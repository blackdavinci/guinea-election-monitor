#!/usr/bin/env python3
"""
=============================================================================
DÉMONSTRATION DE LA MÉTHODOLOGIE DE VEILLE ÉLECTORALE GUINÉE
=============================================================================

Ce script explique et démontre le fonctionnement du système de veille
médiatique pour le suivi de l'actualité électorale en Guinée.

Usage:
    python scripts/demo_methodology.py

Auteur: Équipe Veille Électorale
Date: Décembre 2025
=============================================================================
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import time

# Ajouter le chemin du projet
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Couleurs pour l'affichage
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}{Colors.ENDC}\n")

def print_section(text):
    print(f"\n{Colors.CYAN}{Colors.BOLD}▶ {text}{Colors.ENDC}")
    print(f"{Colors.CYAN}{'─'*60}{Colors.ENDC}")

def print_step(num, text):
    print(f"{Colors.GREEN}  [{num}] {text}{Colors.ENDC}")

def print_info(text):
    print(f"{Colors.BLUE}      ℹ {text}{Colors.ENDC}")

def print_example(text):
    print(f"{Colors.YELLOW}      → {text}{Colors.ENDC}")

def print_stat(label, value):
    print(f"      {Colors.BOLD}{label}:{Colors.ENDC} {value}")

def pause():
    input(f"\n{Colors.CYAN}  Appuyez sur Entrée pour continuer...{Colors.ENDC}")


def demo_part1_introduction():
    """Partie 1: Introduction au système"""
    print_header("PARTIE 1: QU'EST-CE QUE LA VEILLE ÉLECTORALE ?")

    print("""
  La veille électorale est un système automatisé qui collecte et analyse
  les articles de presse guinéens pour suivre l'actualité électorale.

  🎯 OBJECTIF PRINCIPAL:
  ─────────────────────
  Permettre aux analystes, chercheurs et observateurs de suivre en temps
  réel ce que disent les médias guinéens sur les élections, sans avoir
  à consulter manuellement chaque site d'information.

  📊 CE QUE LE SYSTÈME FAIT:
  ──────────────────────────
  ✓ Collecte automatiquement les articles de 9 sites d'information
  ✓ Extrait le contenu intégral de chaque article
  ✓ Identifie les articles liés aux élections
  ✓ Stocke tout dans une base de données consultable
  ✓ Permet des analyses et visualisations via Metabase
    """)
    pause()


def demo_part2_sources():
    """Partie 2: Les sources d'information"""
    print_header("PARTIE 2: LES SOURCES D'INFORMATION COUVERTES")

    try:
        from src.database.connection import session_scope, init_db
        from src.database.operations import SourceOperations

        init_db()

        with session_scope() as session:
            sources = SourceOperations.get_all_active(session)

            print(f"""
  Le système surveille {Colors.BOLD}{len(sources)} sites d'information guinéens{Colors.ENDC}:

  ┌────────────────────┬──────────────┬───────────────────────────────────┐
  │ Source             │ Catégories   │ URL                               │
  ├────────────────────┼──────────────┼───────────────────────────────────┤""")

            for source in sources:
                cats = len(source.category_urls) if source.category_urls else 0
                name = source.name[:18].ljust(18)
                cats_str = str(cats).center(12)
                url = source.base_url[:33].ljust(33)
                print(f"  │ {name} │ {cats_str} │ {url} │")

            print("""  └────────────────────┴──────────────┴───────────────────────────────────┘

  📌 POURQUOI CES SOURCES ?
  ─────────────────────────
  Ces sites représentent les principaux médias en ligne guinéens couvrant
  l'actualité politique. Ils publient quotidiennement des articles sur
  la vie politique, les élections, et les activités des partis.
            """)

    except Exception as e:
        print(f"  (Erreur de connexion à la base: {e})")
        print("""
  Le système surveille 9 sites d'information guinéens:
  - Guineenews.org
  - Guinéematin.com
  - Guinée7.com
  - Vision Guinée
  - Guinée114.com
  - Média Guinée
  - Mosaique Guinée
  - Guinée360.com
  - Ledjely.com
        """)

    pause()


def demo_part3_methodology():
    """Partie 3: La méthodologie de collecte"""
    print_header("PARTIE 3: MÉTHODOLOGIE DE COLLECTE")

    print("""
  Le système utilise une approche en 4 étapes pour collecter les articles:
    """)

    print_section("ÉTAPE 1: Navigation dans les catégories")
    print("""
      Pour chaque source, le système parcourt différentes catégories:

      Exemple pour Guineenews:
      ├── Politique      → guineenews.org/category/politique/
      ├── Société        → guineenews.org/category/societe/
      ├── Économie       → guineenews.org/category/economie/
      └── International  → guineenews.org/category/international/

      Cela permet de couvrir l'ensemble de l'actualité, pas seulement
      la page d'accueil qui ne montre que les derniers articles.
    """)

    print_section("ÉTAPE 2: Extraction de la liste d'articles")
    print("""
      Sur chaque page de catégorie, le système identifie les articles:

      ┌─────────────────────────────────────────────────────────────┐
      │  Page catégorie "Politique"                                 │
      │  ─────────────────────────────────────────────────────────  │
      │  📰 Article 1: "Le président annonce..."     [5 déc 2025]  │
      │  📰 Article 2: "Les partis d'opposition..." [5 déc 2025]   │
      │  📰 Article 3: "Débat sur la CENI..."        [4 déc 2025]  │
      │  📰 Article 4: "Manifestation à Conakry..." [4 déc 2025]   │
      └─────────────────────────────────────────────────────────────┘

      Le système extrait: titre, lien, date de publication
    """)

    print_section("ÉTAPE 3: Filtrage par date")
    print("""
      Le système ne garde que les articles de la VEILLE:

      Aujourd'hui: 5 décembre 2025
      Articles recherchés: 4 décembre 2025

      ✓ Article du 4 déc → COLLECTÉ
      ✓ Article du 4 déc → COLLECTÉ
      ✗ Article du 3 déc → IGNORÉ (trop ancien)
      ✗ Article du 5 déc → IGNORÉ (jour en cours)

      💡 Pourquoi la veille ?
      On collecte à 1h du matin, donc tous les articles de la veille
      ont eu le temps d'être publiés. Cela garantit une couverture
      complète de chaque journée.
    """)

    print_section("ÉTAPE 4: Extraction du contenu complet")
    print("""
      Pour chaque article retenu, le système:

      1. Accède à la page de l'article
      2. Extrait le contenu intégral du texte
      3. Compte les mentions électorales
      4. Génère un résumé automatique
      5. Stocke en base de données

      ┌─────────────────────────────────────────────────────────────┐
      │  Données extraites pour chaque article:                     │
      │  ───────────────────────────────────────────────────────    │
      │  • Titre complet                                            │
      │  • Contenu intégral (texte)                                 │
      │  • Date de publication                                      │
      │  • Source (nom du média)                                    │
      │  • Catégorie (Politique, Société, etc.)                     │
      │  • Lien vers l'article original                             │
      │  • Tags/mots-clés                                           │
      │  • Compteur élection (pertinence)                           │
      │  • Résumé automatique (300 caractères)                      │
      └─────────────────────────────────────────────────────────────┘
    """)

    pause()


def demo_part4_election_counter():
    """Partie 4: Le compteur élection"""
    print_header("PARTIE 4: L'INDICATEUR DE PERTINENCE ÉLECTORALE")

    print("""
  Le système utilise un "compteur élection" pour évaluer la pertinence
  de chaque article par rapport au sujet électoral.
    """)

    print_section("Comment ça marche ?")
    print("""
      Le système compte les occurrences de termes électoraux dans
      le titre et le contenu de chaque article:

      TERMES RECHERCHÉS:
      ─────────────────
      • élection, élections, électoral, électorale, électoraux
      • vote, voter, votant, votants
      • scrutin, scrutins
      • urne, urnes
      • candidat, candidate, candidats, candidates, candidature
      • CENI (Commission Électorale Nationale Indépendante)
      • suffrage, suffrages
      • bulletin, bulletins
      • bureau de vote, bureaux de vote
      • campagne électorale
    """)

    print_section("Exemple concret")

    exemple_titre = "Le président de la CENI annonce les dates des élections locales"
    exemple_contenu = """La Commission Électorale Nationale Indépendante (CENI) a tenu
    une conférence de presse ce mardi pour annoncer le calendrier électoral.
    Le scrutin aura lieu en mars 2026. Les candidats pourront déposer leur
    candidature à partir de janvier. Les bureaux de vote seront installés
    dans toutes les communes. Le vote se déroulera sur une journée."""

    print(f"""
      ARTICLE EXEMPLE:
      ────────────────
      Titre: "{exemple_titre}"

      Contenu: "{exemple_contenu[:100]}..."

      COMPTAGE:
      ─────────
      • "CENI" → 2 occurrences
      • "élections" → 1 occurrence
      • "électoral" → 1 occurrence
      • "scrutin" → 1 occurrence
      • "candidats" → 1 occurrence
      • "candidature" → 1 occurrence
      • "bureaux de vote" → 1 occurrence
      • "vote" → 1 occurrence
      ────────────────────────────
      TOTAL: compte_election = 9
    """)

    print_section("Interprétation du score")
    print("""
      ┌────────────────────┬─────────────────────────────────────────┐
      │ compte_election    │ Interprétation                          │
      ├────────────────────┼─────────────────────────────────────────┤
      │ 0                  │ Article sans rapport aux élections      │
      │ 1-2                │ Mention occasionnelle des élections     │
      │ 3-5                │ Article lié aux élections               │
      │ 6+                 │ Article fortement électoral (PRIORITÉ)  │
      └────────────────────┴─────────────────────────────────────────┘

      💡 Utilisation pratique:

      Dans Metabase, vous pouvez filtrer:
      • compte_election >= 3 → Voir uniquement les articles électoraux
      • compte_election >= 6 → Voir les articles les plus pertinents
    """)

    pause()


def demo_part5_deduplication():
    """Partie 5: Gestion des doublons"""
    print_header("PARTIE 5: GESTION DES DOUBLONS")

    print("""
  Le système utilise plusieurs mécanismes pour éviter les doublons:
    """)

    print_section("Mécanisme 1: GUID unique par URL")
    print("""
      Chaque article reçoit un identifiant unique (GUID) basé sur son URL:

      URL: https://guineenews.org/article-123
           ↓
      GUID: 7f8a9b2c-4d5e-6f7a-8b9c-0d1e2f3a4b5c

      Si le même article est trouvé une seconde fois, le GUID sera
      identique et l'article ne sera pas réimporté.
    """)

    print_section("Mécanisme 2: Vérification avant insertion")
    print("""
      Avant d'insérer un article en base, le système vérifie:

      1. L'URL existe-t-elle déjà ? → Si oui, on ignore
      2. Le GUID existe-t-il déjà ? → Si oui, on ignore

      ┌─────────────────────────────────────────────────────────────┐
      │  Tentative d'insertion:                                     │
      │  ───────────────────────────────────────────────────────    │
      │  Article "Le président annonce..."                          │
      │  URL: guineenews.org/article-123                            │
      │                                                             │
      │  ✓ Vérification GUID... EXISTE DÉJÀ                         │
      │  → Article ignoré (doublon)                                 │
      └─────────────────────────────────────────────────────────────┘
    """)

    print_section("Résultat: Base de données propre")
    print("""
      Grâce à ces mécanismes:

      ✓ Chaque article n'apparaît qu'UNE SEULE fois
      ✓ Les relances de scraping sont sûres (pas de doublons)
      ✓ Les statistiques restent fiables
      ✓ Pas de nettoyage manuel nécessaire
    """)

    pause()


def demo_part6_stats():
    """Partie 6: Statistiques actuelles"""
    print_header("PARTIE 6: STATISTIQUES DE LA BASE DE DONNÉES")

    try:
        from src.database.connection import session_scope, init_db
        from sqlalchemy import text

        init_db()

        with session_scope() as session:
            # Nombre total d'articles
            result = session.execute(text("SELECT COUNT(*) FROM articles"))
            total = result.scalar()

            # Articles par source
            result = session.execute(text("""
                SELECT s.name, COUNT(a.id) as count
                FROM articles a
                JOIN sources s ON a.source_id = s.id
                GROUP BY s.name
                ORDER BY count DESC
            """))
            by_source = result.fetchall()

            # Articles avec forte pertinence électorale
            result = session.execute(text("""
                SELECT COUNT(*) FROM articles WHERE compte_election >= 3
            """))
            high_relevance = result.scalar()

            # Plage de dates
            result = session.execute(text("""
                SELECT MIN(date_publication), MAX(date_publication) FROM articles
            """))
            date_range = result.fetchone()

            print(f"""
  📊 ÉTAT ACTUEL DE LA BASE DE DONNÉES
  ════════════════════════════════════

  Total d'articles collectés: {Colors.BOLD}{total}{Colors.ENDC}
  Articles à forte pertinence électorale (≥3): {Colors.BOLD}{high_relevance}{Colors.ENDC}
  Période couverte: {date_range[0]} → {date_range[1]}

  RÉPARTITION PAR SOURCE:
  ───────────────────────""")

            for source_name, count in by_source:
                bar = "█" * (count // 10) + "░" * (15 - count // 10)
                print(f"  {source_name:20} {bar} {count:4} articles")

            # Top 5 articles les plus pertinents
            result = session.execute(text("""
                SELECT titre, source, compte_election
                FROM (
                    SELECT a.titre, s.name as source, a.compte_election
                    FROM articles a
                    JOIN sources s ON a.source_id = s.id
                    WHERE a.compte_election >= 3
                    ORDER BY a.compte_election DESC
                    LIMIT 5
                ) sub
            """))
            top_articles = result.fetchall()

            if top_articles:
                print(f"""
  TOP 5 ARTICLES LES PLUS PERTINENTS:
  ───────────────────────────────────""")
                for i, (titre, source, score) in enumerate(top_articles, 1):
                    titre_court = titre[:50] + "..." if len(titre) > 50 else titre
                    print(f"  {i}. [{score}] {titre_court}")
                    print(f"     Source: {source}")

    except Exception as e:
        print(f"""
  (Erreur de connexion à la base de données: {e})

  Les statistiques seront disponibles une fois la base de données
  configurée et les premiers articles collectés.
        """)

    pause()


def demo_part7_automation():
    """Partie 7: Automatisation"""
    print_header("PARTIE 7: AUTOMATISATION QUOTIDIENNE")

    print("""
  Le système est configuré pour fonctionner automatiquement chaque jour:
    """)

    print_section("Planification CRON")
    print("""
      ┌────────────────────────────────────────────────────────────────┐
      │  Configuration cron (sur le serveur OVH):                      │
      │  ──────────────────────────────────────────────────────────    │
      │  0 1 * * * /opt/guinea-election-monitor/venv/bin/python \\     │
      │            /opt/guinea-election-monitor/scripts/run_scraper.py │
      │                                                                │
      │  Traduction: Tous les jours à 1h00 du matin                    │
      └────────────────────────────────────────────────────────────────┘
    """)

    print_section("Pourquoi 1h du matin ?")
    print("""
      1. Les journalistes publient généralement jusqu'à 22h-23h
      2. À 1h du matin, tous les articles de la veille sont publiés
      3. La nuit = moins de charge serveur = scraping plus rapide
      4. Les données sont prêtes pour consultation le matin

      CHRONOLOGIE TYPE:
      ─────────────────

      J-1 (ex: 4 décembre)
      │
      ├── 08:00 - Les journalistes commencent à publier
      ├── 12:00 - Articles du matin en ligne
      ├── 18:00 - Articles de l'après-midi
      └── 22:00 - Derniers articles du soir

      J (ex: 5 décembre)
      │
      ├── 01:00 ← SCRAPING AUTOMATIQUE (articles du 4 déc)
      ├── 01:30 - Scraping terminé, données en base
      └── 08:00 - Analystes consultent les données sur Metabase
    """)

    print_section("Cycle de vie des données")
    print("""
      ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
      │  Sites   │ ──► │ Scraper  │ ──► │  Base    │ ──► │ Metabase │
      │  web     │     │ Python   │     │ Postgres │     │ Analyses │
      └──────────┘     └──────────┘     └──────────┘     └──────────┘

      Publication      Collecte         Stockage         Consultation
      des articles     automatique      permanent        par analystes
      (journalistes)   (1h du matin)    (PostgreSQL)     (via web)
    """)

    pause()


def demo_part8_usage():
    """Partie 8: Comment utiliser les données"""
    print_header("PARTIE 8: EXPLOITATION DES DONNÉES")

    print("""
  Une fois les données collectées, plusieurs options d'exploitation:
    """)

    print_section("Option 1: Metabase (Recommandé)")
    print("""
      URL: https://metabase.ablogui.org

      Metabase permet de:
      ✓ Créer des tableaux de bord visuels
      ✓ Filtrer les articles par source, date, pertinence
      ✓ Générer des graphiques d'évolution
      ✓ Exporter les données en CSV/Excel

      EXEMPLES DE REQUÊTES:
      ─────────────────────
      • "Articles du jour avec compte_election >= 3"
      • "Évolution du nombre d'articles par semaine"
      • "Répartition des sources pour les articles électoraux"
    """)

    print_section("Option 2: N8N (Rapports automatiques)")
    print("""
      URL: https://n8n.ablogui.org

      N8N permet de:
      ✓ Envoyer un rapport quotidien par email
      ✓ Créer des alertes pour les articles importants
      ✓ Intégrer avec Slack, Telegram, etc.

      WORKFLOW TYPE:
      ──────────────
      [Cron 8h] → [Requête SQL] → [Formatage] → [Email]

      "Chaque matin à 8h, envoyer par email la liste des articles
       collectés la nuit avec un compte_election >= 3"
    """)

    print_section("Option 3: Accès SQL direct")
    print("""
      Pour les utilisateurs techniques:

      psql -h localhost -U guinea_user -d guinea_elections_monitoring

      Exemples de requêtes:
      ─────────────────────
      -- Articles d'aujourd'hui à forte pertinence
      SELECT titre, source, compte_election, lien
      FROM articles a
      JOIN sources s ON a.source_id = s.id
      WHERE date_publication >= CURRENT_DATE
        AND compte_election >= 3
      ORDER BY compte_election DESC;

      -- Statistiques par source
      SELECT s.name, COUNT(*), AVG(compte_election)
      FROM articles a
      JOIN sources s ON a.source_id = s.id
      GROUP BY s.name;
    """)

    pause()


def demo_conclusion():
    """Conclusion de la démonstration"""
    print_header("RÉSUMÉ ET CONCLUSION")

    print(f"""
  {Colors.BOLD}RÉCAPITULATIF DE LA SOLUTION{Colors.ENDC}
  ════════════════════════════

  1. COLLECTE AUTOMATIQUE
     • 9 sources d'information guinéennes
     • Scraping quotidien à 1h du matin
     • Couverture complète des articles de la veille

  2. ANALYSE INTELLIGENTE
     • Compteur de pertinence électorale
     • Détection automatique des articles prioritaires
     • Dédoublonnage automatique

  3. STOCKAGE STRUCTURÉ
     • Base PostgreSQL robuste
     • Historique complet conservé
     • Données facilement interrogeables

  4. EXPLOITATION FLEXIBLE
     • Tableaux de bord Metabase
     • Rapports automatiques N8N
     • Accès SQL pour analyses avancées

  {Colors.BOLD}BÉNÉFICES POUR LES UTILISATEURS{Colors.ENDC}
  ════════════════════════════════

  ✓ Gain de temps: Plus besoin de consulter 9 sites manuellement
  ✓ Exhaustivité: Aucun article important n'est manqué
  ✓ Pertinence: Focus sur les articles électoraux
  ✓ Traçabilité: Historique complet des publications
  ✓ Analyse: Données structurées pour statistiques et tendances

  {Colors.GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.ENDC}
  {Colors.GREEN}  La veille électorale est opérationnelle et collecte les données  {Colors.ENDC}
  {Colors.GREEN}  quotidiennement. Consultez Metabase pour explorer les articles.  {Colors.ENDC}
  {Colors.GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.ENDC}
    """)


def main():
    """Point d'entrée principal"""
    print(f"""
{Colors.HEADER}{Colors.BOLD}
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║     🗳️  DÉMONSTRATION - VEILLE ÉLECTORALE GUINÉE  🗳️                ║
║                                                                      ║
║     Ce script interactif explique le fonctionnement du système       ║
║     de veille médiatique pour le suivi électoral en Guinée.          ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
{Colors.ENDC}
    """)

    print(f"""
  {Colors.BOLD}PLAN DE LA DÉMONSTRATION:{Colors.ENDC}

  1. Introduction - Qu'est-ce que la veille électorale ?
  2. Les sources - Quels médias sont surveillés ?
  3. Méthodologie - Comment les articles sont collectés ?
  4. Pertinence - Le compteur élection
  5. Doublons - Comment on évite les duplications ?
  6. Statistiques - État actuel de la base
  7. Automatisation - Fonctionnement quotidien
  8. Exploitation - Comment utiliser les données ?
    """)

    input(f"{Colors.CYAN}  Appuyez sur Entrée pour commencer la démonstration...{Colors.ENDC}")

    # Exécuter chaque partie
    demo_part1_introduction()
    demo_part2_sources()
    demo_part3_methodology()
    demo_part4_election_counter()
    demo_part5_deduplication()
    demo_part6_stats()
    demo_part7_automation()
    demo_part8_usage()
    demo_conclusion()

    print(f"\n{Colors.GREEN}  Fin de la démonstration. Merci !{Colors.ENDC}\n")


if __name__ == "__main__":
    main()
