# Méthodologie de Veille Électorale Guinée

## 1. Objectif du Système

La veille électorale est un système automatisé qui collecte et analyse les articles de presse guinéens pour suivre l'actualité électorale.

**Objectif principal :** Permettre aux analystes, chercheurs et observateurs de suivre en temps réel ce que disent les médias guinéens sur les élections, sans avoir à consulter manuellement chaque site d'information.

### Ce que le système fait

- Collecte automatiquement les articles de 9 sites d'information
- Extrait le contenu intégral de chaque article
- Identifie les articles liés aux élections
- Stocke tout dans une base de données consultable
- Permet des analyses et visualisations via Metabase

---

## 2. Sources d'Information Couvertes

Le système surveille **9 sites d'information guinéens** :

| Source | URL | Catégories surveillées |
|--------|-----|------------------------|
| Guineenews | guineenews.org | 10 catégories |
| Guinéematin | guineematin.com | 10 catégories |
| Guinée7 | guinee7.com | 10 catégories |
| Vision Guinée | visionguinee.info | 6 catégories |
| Guinée114 | guinee114.com | 11 catégories |
| Média Guinée | mediaguinee.com | 5 catégories |
| Mosaique Guinée | mosaiqueguinee.com | 14 catégories |
| Guinée360 | guinee360.com | 5 catégories |
| Ledjely | ledjely.com | 8 catégories |

### Pourquoi ces sources ?

Ces sites représentent les principaux médias en ligne guinéens couvrant l'actualité politique. Ils publient quotidiennement des articles sur la vie politique, les élections, et les activités des partis.

---

## 3. Méthodologie de Collecte

Le système utilise une approche en **4 étapes** pour collecter les articles :

### Étape 1 : Navigation dans les catégories

Pour chaque source, le système parcourt différentes catégories :

```
Exemple pour Guineenews :
├── Politique      → guineenews.org/category/politique/
├── Société        → guineenews.org/category/societe/
├── Économie       → guineenews.org/category/economie/
└── International  → guineenews.org/category/international/
```

Cela permet de couvrir l'ensemble de l'actualité, pas seulement la page d'accueil qui ne montre que les derniers articles.

### Étape 2 : Extraction de la liste d'articles

Sur chaque page de catégorie, le système identifie les articles :

```
┌─────────────────────────────────────────────────────────────┐
│  Page catégorie "Politique"                                 │
│  ─────────────────────────────────────────────────────────  │
│  📰 Article 1: "Le président annonce..."     [5 déc 2025]  │
│  📰 Article 2: "Les partis d'opposition..." [5 déc 2025]   │
│  📰 Article 3: "Débat sur la CENI..."        [4 déc 2025]  │
│  📰 Article 4: "Manifestation à Conakry..." [4 déc 2025]   │
└─────────────────────────────────────────────────────────────┘
```

Le système extrait : **titre**, **lien**, **date de publication**

### Étape 3 : Filtrage par date

Le système ne garde que les articles de la **VEILLE** :

```
Aujourd'hui: 5 décembre 2025
Articles recherchés: 4 décembre 2025

✓ Article du 4 déc → COLLECTÉ
✓ Article du 4 déc → COLLECTÉ
✗ Article du 3 déc → IGNORÉ (trop ancien)
✗ Article du 5 déc → IGNORÉ (jour en cours)
```

**Pourquoi la veille ?**

On collecte à 1h du matin, donc tous les articles de la veille ont eu le temps d'être publiés. Cela garantit une couverture complète de chaque journée.

### Étape 4 : Extraction du contenu complet

Pour chaque article retenu, le système :

1. Accède à la page de l'article
2. Extrait le contenu intégral du texte
3. Compte les mentions électorales
4. Génère un résumé automatique
5. Stocke en base de données

**Données extraites pour chaque article :**

| Champ | Description |
|-------|-------------|
| Titre | Titre complet de l'article |
| Contenu | Texte intégral |
| Date de publication | Date de mise en ligne |
| Source | Nom du média |
| Catégorie | Politique, Société, Économie, etc. |
| Lien | URL vers l'article original |
| Tags | Mots-clés associés |
| Compteur élection | Score de pertinence électorale |
| Résumé | Résumé automatique (300 caractères) |

---

## 4. Indicateur de Pertinence Électorale

Le système utilise un **"compteur élection"** pour évaluer la pertinence de chaque article par rapport au sujet électoral.

### Comment ça marche ?

Le système compte les occurrences de termes électoraux dans le titre et le contenu de chaque article.

**Termes recherchés :**

- élection, élections, électoral, électorale, électoraux
- vote, voter, votant, votants
- scrutin, scrutins
- urne, urnes
- candidat, candidate, candidats, candidates, candidature
- CENI (Commission Électorale Nationale Indépendante)
- suffrage, suffrages
- bulletin, bulletins
- bureau de vote, bureaux de vote
- campagne électorale

### Exemple concret

**Article exemple :**

> **Titre :** "Le président de la CENI annonce les dates des élections locales"
>
> **Contenu :** "La Commission Électorale Nationale Indépendante (CENI) a tenu une conférence de presse ce mardi pour annoncer le calendrier électoral. Le scrutin aura lieu en mars 2026. Les candidats pourront déposer leur candidature à partir de janvier. Les bureaux de vote seront installés dans toutes les communes. Le vote se déroulera sur une journée."

**Comptage :**

| Terme | Occurrences |
|-------|-------------|
| CENI | 2 |
| élections | 1 |
| électoral | 1 |
| scrutin | 1 |
| candidats | 1 |
| candidature | 1 |
| bureaux de vote | 1 |
| vote | 1 |
| **TOTAL** | **9** |

### Interprétation du score

| compte_election | Interprétation |
|-----------------|----------------|
| 0 | Article sans rapport aux élections |
| 1-2 | Mention occasionnelle des élections |
| 3-5 | Article lié aux élections |
| 6+ | Article fortement électoral (**PRIORITÉ**) |

**Utilisation pratique dans Metabase :**

- `compte_election >= 3` → Voir uniquement les articles électoraux
- `compte_election >= 6` → Voir les articles les plus pertinents

---

## 5. Gestion des Doublons

Le système utilise plusieurs mécanismes pour éviter les doublons :

### Mécanisme 1 : GUID unique par URL

Chaque article reçoit un identifiant unique (GUID) basé sur son URL :

```
URL: https://guineenews.org/article-123
         ↓
GUID: 7f8a9b2c-4d5e-6f7a-8b9c-0d1e2f3a4b5c
```

Si le même article est trouvé une seconde fois, le GUID sera identique et l'article ne sera pas réimporté.

### Mécanisme 2 : Vérification avant insertion

Avant d'insérer un article en base, le système vérifie :

1. L'URL existe-t-elle déjà ? → Si oui, on ignore
2. Le GUID existe-t-il déjà ? → Si oui, on ignore

### Résultat : Base de données propre

- Chaque article n'apparaît qu'**UNE SEULE fois**
- Les relances de scraping sont sûres (pas de doublons)
- Les statistiques restent fiables
- Pas de nettoyage manuel nécessaire

---

## 6. Automatisation Quotidienne

Le système est configuré pour fonctionner automatiquement chaque jour.

### Planification CRON

```bash
# Configuration sur le serveur OVH
0 1 * * * /opt/guinea-election-monitor/venv/bin/python \
          /opt/guinea-election-monitor/scripts/run_scraper.py
```

**Traduction :** Tous les jours à 1h00 du matin

### Pourquoi 1h du matin ?

1. Les journalistes publient généralement jusqu'à 22h-23h
2. À 1h du matin, tous les articles de la veille sont publiés
3. La nuit = moins de charge serveur = scraping plus rapide
4. Les données sont prêtes pour consultation le matin

### Chronologie type

```
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
```

### Cycle de vie des données

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  Sites   │ ──► │ Scraper  │ ──► │  Base    │ ──► │ Metabase │
│  web     │     │ Python   │     │ Postgres │     │ Analyses │
└──────────┘     └──────────┘     └──────────┘     └──────────┘

Publication      Collecte         Stockage         Consultation
des articles     automatique      permanent        par analystes
(journalistes)   (1h du matin)    (PostgreSQL)     (via web)
```

---

## 7. Exploitation des Données

Une fois les données collectées, plusieurs options d'exploitation :

### Option 1 : Metabase (Recommandé)

**URL :** `https://metabase.ablogui.org`

Metabase permet de :
- Créer des tableaux de bord visuels
- Filtrer les articles par source, date, pertinence
- Générer des graphiques d'évolution
- Exporter les données en CSV/Excel

**Exemples de requêtes :**
- "Articles du jour avec compte_election >= 3"
- "Évolution du nombre d'articles par semaine"
- "Répartition des sources pour les articles électoraux"

### Option 2 : N8N (Rapports automatiques)

**URL :** `https://n8n.ablogui.org`

N8N permet de :
- Envoyer un rapport quotidien par email
- Créer des alertes pour les articles importants
- Intégrer avec Slack, Telegram, etc.

**Workflow type :**
```
[Cron 8h] → [Requête SQL] → [Formatage] → [Email]
```

"Chaque matin à 8h, envoyer par email la liste des articles collectés la nuit avec un compte_election >= 3"

### Option 3 : Accès SQL direct

Pour les utilisateurs techniques :

```bash
psql -h localhost -U guinea_user -d guinea_elections_monitoring
```

**Exemples de requêtes :**

```sql
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
```

---

## 8. Scripts Disponibles

| Script | Usage | Commande |
|--------|-------|----------|
| `run_scraper.py` | Collecte quotidienne | `./venv/bin/python scripts/run_scraper.py` |
| `backfill_scraper.py` | Rattraper des jours passés | `./venv/bin/python scripts/backfill_scraper.py --start 2025-11-28 --end 2025-12-05` |
| `backfill_ledjely.py` | Rattraper Ledjely spécifiquement | `./venv/bin/python scripts/backfill_ledjely.py --start 2025-11-28 --end 2025-12-05` |
| `init_db.py` | Initialiser la base | `./venv/bin/python scripts/init_db.py` |
| `demo_methodology.py` | Démonstration interactive | `./venv/bin/python scripts/demo_methodology.py` |

---

## 9. Résumé

| Aspect | Détail |
|--------|--------|
| **Sources** | 9 médias guinéens |
| **Fréquence** | Quotidienne (1h du matin) |
| **Période collectée** | Articles de la veille |
| **Données extraites** | Titre, contenu, date, source, catégorie, pertinence |
| **Indicateur clé** | `compte_election` (score de pertinence) |
| **Stockage** | PostgreSQL |
| **Visualisation** | Metabase |
| **Alertes** | N8N (email) |

### Bénéfices pour les utilisateurs

- **Gain de temps** : Plus besoin de consulter 9 sites manuellement
- **Exhaustivité** : Aucun article important n'est manqué
- **Pertinence** : Focus sur les articles électoraux
- **Traçabilité** : Historique complet des publications
- **Analyse** : Données structurées pour statistiques et tendances

---

*Document généré le 6 décembre 2025*
