# Documentation Technique - Chatbot ExpoBeton RDC

## Table des Matières

1. [Vue d'ensemble](#vue-densemble)
2. [Architecture générale](#architecture-générale)
3. [Services utilisés](#services-utilisés)
4. [Fonctionnalités principales](#fonctionnalités-principales)
5. [Structure des fichiers](#structure-des-fichiers)
6. [Réponses statiques vs dynamiques](#réponses-statiques-vs-dynamiques)
7. [Configuration et personnalisation](#configuration-et-personnalisation)
8. [Déploiement](#déploiement)
9. [Meilleures pratiques](#meilleures-pratiques)
10. [Optimisations de performance](#optimisations-de-performance)
11. [Guide de reproduction pour un autre projet](#guide-de-reproduction-pour-un-autre-projet)

---

## Vue d'ensemble

Ce chatbot est un assistant conversationnel intelligent construit avec **Rasa Open Source**, enrichi par des intégrations **OpenAI GPT-4o** pour les réponses dynamiques et une recherche sémantique basée sur des embeddings vectoriels.

### Caractéristiques clés

| Caractéristique | Description |
|-----------------|-------------|
| **Framework** | Rasa Open Source 3.6 |
| **Langue** | Français (multilingue supporté) |
| **IA Générative** | OpenAI GPT-4o |
| **Embeddings** | OpenAI text-embedding-3-small |
| **Temps de réponse** | < 5 secondes (optimisé) |
| **Déploiement** | Railway / Docker / Heroku |

---

## Architecture générale

```
┌─────────────────────────────────────────────────────────────────┐
│                        INTERFACE WEB                             │
│                    (chat-widget.js + HTML)                       │
└───────────────────────────────┬─────────────────────────────────┘
                                │ HTTP/REST
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      SERVEUR RASA (Port 5005)                    │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────┐  │
│  │   NLU Pipeline  │  │  Dialogue Manager │  │   Responses    │  │
│  │  (DIETClassifier│  │   (TEDPolicy +    │  │   (domain.yml) │  │
│  │   + Fallback)   │  │   MemoPolicy)     │  │                │  │
│  └─────────────────┘  └──────────────────┘  └────────────────┘  │
└───────────────────────────────┬─────────────────────────────────┘
                                │ HTTP/Webhook
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                  SERVEUR ACTIONS (Port 5055)                     │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                     actions.py                               ││
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       ││
│  │  │   Keyword    │  │   OpenAI     │  │   Email      │       ││
│  │  │   Matching   │  │   RAG Search │  │   Notifier   │       ││
│  │  └──────────────┘  └──────────────┘  └──────────────┘       ││
│  └─────────────────────────────────────────────────────────────┘│
└───────────────────────────────┬─────────────────────────────────┘
                                │
                ┌───────────────┴───────────────┐
                ▼                               ▼
┌──────────────────────────┐    ┌──────────────────────────────────┐
│      DOCUMENTS (docs/)    │    │          OPENAI API              │
│  - Brochures (.txt)       │    │  - Embeddings (text-embedding-3) │
│  - Rapports (.txt)        │    │  - Chat Completion (GPT-4o)      │
│  - Présentations (.txt)   │    │                                  │
└──────────────────────────┘    └──────────────────────────────────┘
```

### Composants principaux

1. **Rasa NLU** - Classification d'intents et extraction d'entités
2. **Rasa Dialogue Manager** - Gestion des conversations et routing
3. **Action Server** - Logique métier personnalisée (Python)
4. **OpenAI Integration** - Recherche sémantique + génération de réponses
5. **Documents** - Base de connaissances en fichiers .txt

---

## Services utilisés

### 1. OpenAI (Principal)

| Service | Modèle | Usage |
|---------|--------|-------|
| **Embeddings** | `text-embedding-3-small` | Vectorisation des documents et requêtes |
| **Chat Completion** | `gpt-4o` | Génération de réponses dynamiques |

**Configuration requise:**
```python
# Dans actions.py
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
openai.api_key = OPENAI_API_KEY
```

**Coût approximatif:**
- Embeddings: ~$0.02 / 1M tokens
- GPT-4o: ~$2.50 / 1M tokens input, $10 / 1M tokens output

### 2. Cohere (Optionnel/Backup)

| Service | Modèle | Usage |
|---------|--------|-------|
| **Embeddings** | `embed-multilingual-v3.0` | Alternative aux embeddings OpenAI |
| **Chat** | `command-r-plus` | Alternative à GPT-4o |

**Note:** Cohere a été remplacé par OpenAI pour de meilleures performances.

### 3. SMTP (Email)

Utilisé pour envoyer des notifications quand:
- Une question reste sans réponse
- Une conversation se termine

**Configuration:**
```bash
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

---

## Fonctionnalités principales

### 1. Classification d'intents (NLU)

Le pipeline NLU analyse les messages utilisateur:

```yaml
# config.yml
pipeline:
  - name: WhitespaceTokenizer
  - name: RegexFeaturizer
  - name: LexicalSyntacticFeaturizer
  - name: CountVectorsFeaturizer
  - name: CountVectorsFeaturizer
    analyzer: char_wb
    min_ngram: 1
    max_ngram: 4
  - name: DIETClassifier
    epochs: 100
  - name: FallbackClassifier
    threshold: 0.1
```

### 2. Réponses statiques

Réponses prédéfinies pour les questions fréquentes:

| Intent | Réponse |
|--------|---------|
| `ask_event_dates` | `utter_event_dates` |
| `ask_event_location` | `utter_event_location` |
| `ask_city_population` | `utter_city_population` |
| `ask_urban_development` | `utter_urban_development` |

### 3. Réponses dynamiques (RAG)

Pour les questions complexes non couvertes par les intents statiques:

1. **Recherche sémantique** - Trouve les documents pertinents
2. **Génération GPT-4o** - Produit une réponse basée sur le contexte

### 4. Support multilingue

Détection automatique de la langue et réponses dans:
- Français (par défaut)
- Anglais
- Espagnol
- Russe
- Chinois
- Arabe

### 5. Gestion de conversation

- Suivi des sessions utilisateur
- Envoi d'email en fin de conversation
- Logging des questions sans réponse

---

## Structure des fichiers

```
project/
├── actions/
│   ├── actions.py          # Actions personnalisées (IA, emails)
│   └── action_human_handoff.py
├── data/
│   ├── nlu.yml             # Exemples d'entraînement NLU
│   ├── stories.yml         # Scénarios de conversation
│   └── rules.yml           # Règles de dialogue
├── docs/
│   ├── brochure_*.txt      # Documents de base de connaissances
│   └── *.txt               # Autres documents
├── domain/
│   └── *.yml               # Définitions partielles du domaine
├── web/
│   ├── chat-widget.js      # Widget de chat frontend
│   └── index.html          # Interface web
├── config.yml              # Configuration pipeline NLU
├── domain.yml              # Définition du domaine (intents, responses)
├── endpoints.yml           # Configuration des endpoints
├── credentials.yml         # Credentials des canaux
└── requirements-heroku.txt # Dépendances Python
```

### Fichiers clés à modifier

| Fichier | Quand modifier |
|---------|----------------|
| `data/nlu.yml` | Ajouter de nouveaux intents ou exemples |
| `data/stories.yml` | Définir de nouveaux flux de conversation |
| `domain.yml` | Ajouter intents, réponses statiques, actions |
| `actions/actions.py` | Logique métier, intégrations API |
| `docs/*.txt` | Contenu de la base de connaissances |
| `config.yml` | Ajuster le pipeline NLU |

---

## Réponses statiques vs dynamiques

### Comparaison

| Critère | Réponses Statiques | Réponses Dynamiques (OpenAI) |
|---------|-------------------|------------------------------|
| **Vitesse** | < 100ms | 2-5 secondes |
| **Coût** | Gratuit | ~$0.01 par réponse |
| **Fiabilité** | 100% | 99% (dépend API) |
| **Flexibilité** | Fixe | Adaptative |
| **Maintenance** | Manuelle | Auto-apprenante |

### Quand utiliser chaque type

**Réponses statiques (`utter_*`):**
- Questions fréquentes avec réponse fixe
- Informations critiques (dates, lieux)
- Performance maximale requise

**Réponses dynamiques (OpenAI):**
- Questions complexes/variées
- Informations changeantes
- Questions hors documentation

### Implémentation

**Réponse statique:**
```yaml
# domain.yml
responses:
  utter_event_dates:
    - text: "L'événement aura lieu du 15 au 18 avril 2026 à Kalemie."

# stories.yml
- story: ask dates
  steps:
  - intent: ask_event_dates
  - action: utter_event_dates
```

**Réponse dynamique:**
```python
# actions.py
def find_relevant_docs(query: str, top_k: int = 3):
    """Recherche sémantique avec OpenAI embeddings"""
    # ... vectorisation et similarité cosinus ...

# Dans la classe Action:
response = openai.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": "Tu es un assistant..."},
        {"role": "user", "content": f"Question: {query}\n\nContexte: {context}"}
    ],
    temperature=0.3,
    max_tokens=500
)
```

---

## Configuration et personnalisation

### Variables d'environnement requises

```bash
# .env
OPENAI_API_KEY=sk-xxx...           # Obligatoire pour RAG
COHERE_API_KEY=xxx...              # Optionnel (backup)
SMTP_SERVER=smtp.gmail.com         # Pour notifications email
SMTP_PORT=587
SMTP_USERNAME=email@example.com
SMTP_PASSWORD=app-password
```

### Modifier les intents

1. **Ajouter des exemples NLU** (`data/nlu.yml`):
```yaml
- intent: ask_new_topic
  examples: |
    - parle-moi du nouveau sujet
    - c'est quoi le nouveau sujet
    - qu'est-ce que le nouveau sujet
```

2. **Créer une réponse** (`domain.yml`):
```yaml
intents:
  - ask_new_topic

responses:
  utter_new_topic:
    - text: "Voici les informations sur le nouveau sujet..."

actions:
  - utter_new_topic
```

3. **Définir le routing** (`data/stories.yml`):
```yaml
- story: ask new topic story
  steps:
  - intent: ask_new_topic
  - action: utter_new_topic
```

### Ajouter des documents

Placez les fichiers `.txt` dans le dossier `docs/`:
```
docs/
├── nouveau_document.txt
├── brochure_2026.txt
└── rapport_annuel.txt
```

Le système les indexera automatiquement au démarrage.

---

## Déploiement

### Prérequis

- Python 3.10+
- Rasa 3.6.x
- Clé API OpenAI

### Déploiement local

```bash
# 1. Installer les dépendances
pip install -r requirements-heroku.txt

# 2. Entraîner le modèle
rasa train

# 3. Démarrer le serveur d'actions (terminal 1)
rasa run actions --port 5055

# 4. Démarrer Rasa (terminal 2)
rasa run --enable-api --cors "*" --port 5005
```

### Déploiement Railway

1. **Connecter le repo GitHub à Railway**

2. **Configurer les variables d'environnement:**
   - `OPENAI_API_KEY`
   - `PORT` (automatique)

3. **Le script `railway_start.sh` gère:**
   - Nettoyage du cache Python
   - Entraînement du modèle
   - Démarrage des serveurs

### Déploiement Docker

```bash
# Construire l'image
docker build -f Dockerfile.actions -t bot-actions .

# Lancer le conteneur
docker run -p 5055:5055 -e OPENAI_API_KEY=xxx bot-actions
```

### Architecture de déploiement

```
┌────────────────────────────────────────────┐
│           RAILWAY / HEROKU                  │
├────────────────────────────────────────────┤
│  ┌──────────────────────────────────────┐  │
│  │  Web Server (static_server.py:$PORT)  │  │
│  └──────────────────┬───────────────────┘  │
│                     │                       │
│  ┌──────────────────┴───────────────────┐  │
│  │     Rasa Server (localhost:5005)      │  │
│  └──────────────────┬───────────────────┘  │
│                     │                       │
│  ┌──────────────────┴───────────────────┐  │
│  │   Action Server (localhost:5055)      │  │
│  └──────────────────────────────────────┘  │
└────────────────────────────────────────────┘
```

---

## Meilleures pratiques

### 1. Conception des intents

| Bonne pratique | Mauvaise pratique |
|----------------|-------------------|
| Intents spécifiques (`ask_event_dates`) | Intents génériques (`ask_question`) |
| 10-20 exemples par intent | < 5 exemples |
| Exemples variés | Exemples répétitifs |
| Éviter le chevauchement | Intents ambigus |

### 2. Gestion des erreurs

```python
try:
    response = openai.chat.completions.create(...)
except Exception as e:
    print(f"❌ Erreur OpenAI: {e}")
    # Fallback vers réponse par défaut
    dispatcher.utter_message(text=FALLBACK_MESSAGE)
```

### 3. Timeout et performance

```python
# Utiliser ThreadPoolExecutor pour timeout
with ThreadPoolExecutor(max_workers=1) as executor:
    future = executor.submit(find_relevant_docs, query, 3)
    try:
        result = future.result(timeout=5)  # Max 5 secondes
    except TimeoutError:
        result = []  # Fallback
```

### 4. Logging

```python
print(f"🔍 Query: {query[:50]}...")
print(f"✅ Documents trouvés: {len(docs)}")
print(f"⏰ Temps de réponse: {elapsed_time:.2f}s")
```

### 5. Cache des embeddings

```python
# Cache global pour éviter de recalculer
DOCS_CACHE = None
EMBEDDINGS_CACHE = None

def load_and_embed_docs():
    global DOCS_CACHE, EMBEDDINGS_CACHE
    if DOCS_CACHE is not None:
        return DOCS_CACHE, EMBEDDINGS_CACHE
    # ... charger et créer embeddings ...
```

---

## Optimisations de performance

### Problèmes rencontrés et solutions

| Problème | Cause | Solution | Amélioration |
|----------|-------|----------|--------------|
| Réponse 10 min | Cohere timeout 30s | Timeout 5s + OpenAI | 120x plus rapide |
| Chargement 4 min | 170 documents | Limite à 50 docs | 48x plus rapide |
| Intent incorrect | Exemples trop génériques | Exemples spécifiques | Précision 95%+ |

### Optimisation du chargement des documents

```python
# AVANT (lent)
all_files = list(docs_path.glob('*.txt'))  # 170 fichiers
content = f.read()[:8000]  # 8000 caractères

# APRÈS (optimisé)
priority_keywords = ['brochure', 'rapport', '2024', '2025', '2026']
priority_files = [f for f in all_files if any(kw in f.name.lower() for kw in priority_keywords)]
selected_files = priority_files[:30] + other_files[:20]  # Max 50 fichiers
content = f.read()[:4000]  # 4000 caractères max
```

### Résumé des optimisations

1. **Timeout réduit:** 30s → 5s
2. **Documents limités:** 170 → 50 fichiers prioritaires
3. **Contenu tronqué:** 8000 → 4000 caractères/doc
4. **Cache des embeddings:** Calculés une seule fois au démarrage
5. **Réponses statiques:** Pour les questions fréquentes

---

## Guide de reproduction pour un autre projet

### Étape 1: Cloner la structure

```bash
mkdir mon-nouveau-bot
cd mon-nouveau-bot

# Créer la structure
mkdir -p actions data docs domain web
```

### Étape 2: Copier les fichiers essentiels

```bash
# Fichiers de configuration
cp original/config.yml .
cp original/domain.yml .
cp original/endpoints.yml .
cp original/credentials.yml .
cp original/requirements-heroku.txt .

# Actions (adapter le contenu)
cp original/actions/actions.py actions/

# Interface web
cp -r original/web/* web/
```

### Étape 3: Adapter le contenu

1. **`data/nlu.yml`** - Créer vos propres intents:
```yaml
version: "3.1"
nlu:
- intent: greet
  examples: |
    - bonjour
    - salut
    - hello

- intent: ask_your_topic
  examples: |
    - c'est quoi votre produit
    - parlez-moi de vos services
```

2. **`domain.yml`** - Définir vos réponses:
```yaml
version: "3.1"
intents:
  - greet
  - ask_your_topic

responses:
  utter_greet:
    - text: "Bonjour! Comment puis-je vous aider?"
  
  utter_your_topic:
    - text: "Voici des informations sur notre produit..."
```

3. **`data/stories.yml`** - Définir les flux:
```yaml
version: "3.1"
stories:
- story: greet
  steps:
  - intent: greet
  - action: utter_greet

- story: ask topic
  steps:
  - intent: ask_your_topic
  - action: utter_your_topic
```

4. **`docs/*.txt`** - Ajouter votre base de connaissances

5. **`actions/actions.py`** - Adapter:
   - Le nom du projet dans les réponses
   - Les mots-clés spécifiques
   - Les prompts système pour OpenAI

### Étape 4: Configurer l'environnement

```bash
# .env
OPENAI_API_KEY=votre-clé-openai
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=votre-email
SMTP_PASSWORD=votre-app-password
```

### Étape 5: Entraîner et tester

```bash
# Installer les dépendances
pip install -r requirements-heroku.txt

# Entraîner
rasa train

# Tester en local
rasa shell

# Ou démarrer les serveurs
rasa run actions --port 5055 &
rasa run --enable-api --cors "*" --port 5005
```

### Checklist de personnalisation

- [ ] Créer les intents spécifiques à votre domaine
- [ ] Ajouter 10-20 exemples par intent
- [ ] Définir les réponses statiques pour les FAQ
- [ ] Ajouter les documents de base de connaissances
- [ ] Configurer les variables d'environnement
- [ ] Adapter les prompts OpenAI au contexte
- [ ] Tester chaque intent manuellement
- [ ] Déployer sur Railway/Heroku

---

## Annexe: Dépendances

```txt
rasa==3.6.21
rasa-sdk==3.6.2
openai==1.68.2
cohere==5.20.0          # Optionnel
numpy                   # Pour calculs vectoriels
python-dotenv           # Chargement variables d'environnement
```

## Annexe: Commandes utiles

```bash
# Entraîner le modèle
rasa train

# Tester en conversation
rasa shell

# Valider les données
rasa data validate

# Visualiser les stories
rasa visualize

# Tester le NLU
rasa test nlu

# Démarrer les serveurs
rasa run actions --port 5055
rasa run --enable-api --cors "*" --port 5005
```

---

*Documentation générée le 2 janvier 2026*
*Version: 1.0*
