# actions/actions.py
# CRITICAL RELOAD TIMESTAMP: 2025-11-10 21:00:00 UTC - PERFORMANCE OPTIMIZATION
# THIS FILE MUST BE RELOADED - CHECK THIS TIMESTAMP IN LOGS!

from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
import os
import re
import math
import glob
import openai
import numpy as np
from pathlib import Path
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from rasa_sdk.events import SlotSet, FollowupAction

# Smart category matching shared with actions_expobeton (used by the
# registration category shortcut in ActionAnswerExpoBeton).
try:
    from actions_expobeton import match_category as _match_category_shared
except ImportError:  # loaded as a package by the Rasa action server
    from .actions_expobeton import match_category as _match_category_shared

# CRITICAL: Log file load timestamp
print("="*80)
print("🔥 ACTIONS.PY LOADED - TIMESTAMP: 2025-11-10 21:00:00 UTC")
print("🔥 OPTIMIZED: Reduced docs from 170 to 50 - 4min to <5s loading")
print("="*80)

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not available, environment variables must be set manually
    pass

# Initialize OpenAI client
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')

# ── Délais OpenAI ─────────────────────────────────────────────────────────────
# Le client openai>=1.0 utilise par défaut timeout=600 s et max_retries=2. Un
# appel sans argument `timeout` peut donc immobiliser un worker jusqu'à
# 30 minutes si l'egress du conteneur est filtré ou lent — et ce déploiement a
# déjà un egress filtré (le port 587 sortant tombe sur Errno 101).
# Ces appels sont DANS le chemin de réponse : find_relevant_docs() est invoqué
# pour toute question d'au moins 15 caractères. Sans plafond explicite, le bot
# se serait mis à geler dès que OPENAI_API_KEY serait renseigné — c'est-à-dire
# au moment précis où l'on demande à l'exploitation de l'ajouter.
# max_retries=0 : en cas d'échec on préfère répondre tout de suite par le repli
# lexical plutôt que de faire patienter l'utilisateur pendant des relances.
OPENAI_TIMEOUT = float(os.getenv('OPENAI_TIMEOUT', '6'))
# L'indexation de démarrage envoie ~48 documents en UN seul lot : 6 s seraient
# insuffisants et feraient échouer la construction de l'index — donc retomber
# définitivement sur le repli lexical, au moment précis où la clé vient d'être
# ajoutée. Ce lot n'a lieu qu'une fois au démarrage et son résultat est mis en
# cache, il peut donc se permettre un délai bien plus long.
OPENAI_BULK_TIMEOUT = float(os.getenv('OPENAI_BULK_TIMEOUT', '90'))
OPENAI_MAX_RETRIES = 0

# Budget total (recherche documentaire + génération) pour le chemin LLM, en
# secondes. Au-delà, l'utilisateur reçoit la réponse déterministe au lieu
# d'attendre.
LLM_TOTAL_TIMEOUT = float(os.getenv('LLM_TOTAL_TIMEOUT', '8'))

# File d'exécution PARTAGÉE, et non un ThreadPoolExecutor créé par requête.
# Deux raisons :
#  1. `with ThreadPoolExecutor(...)` appelle shutdown(wait=True) à la sortie du
#     bloc, donc le `future.result(timeout=LLM_TOTAL_TIMEOUT)` devenait
#     décoratif : on attendait quand même la fin de l'appel qui venait
#     d'expirer. Sans bloc `with`, plus rien n'attend.
#  2. Créer un exécuteur par message aurait fait croître le nombre de threads
#     sans limite si plusieurs appels ralentissaient en même temps.
# Deux workers suffisent : au-delà, les tâches excédentaires expirent à
# LLM_TOTAL_TIMEOUT et retombent sur la réponse déterministe, ce qui est la
# dégradation voulue.
_LLM_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix='llm')

_OPENAI_CLIENT = None


def _openai_client():
    """Client OpenAI à délais courts, construit à la demande.

    Paresseux volontairement : construire le client à l'import ferait échouer le
    chargement du module d'actions — donc tomber tout le serveur d'actions — si
    la clé est absente ou invalide. Ici l'échec reste confiné à la requête en
    cours, qui retombe sur le repli par mots-clés.
    """
    global _OPENAI_CLIENT
    if _OPENAI_CLIENT is None:
        if not OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY absent")
        _OPENAI_CLIENT = openai.OpenAI(
            api_key=OPENAI_API_KEY,
            timeout=OPENAI_TIMEOUT,
            max_retries=OPENAI_MAX_RETRIES,
        )
    return _OPENAI_CLIENT


if OPENAI_API_KEY:
    # Conservé pour compatibilité : d'autres modules lisent openai.api_key.
    openai.api_key = OPENAI_API_KEY
else:
    print("⚠️ WARNING: OPENAI_API_KEY not set! Using default from environment.")

# Email configuration
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')  # Default to Gmail
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USERNAME = os.getenv('SMTP_USERNAME', '')  # Set this in environment
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')  # Set this in environment
NOTIFICATION_EMAIL = 'bot@expobetonrdc.com'

# Envoi des transcripts : JAMAIS bloquant.
#
# Sur Railway, le port sortant 587 vers smtp.gmail.com est filtré. Sans timeout,
# smtplib.SMTP() restait en attente jusqu'au délai TCP du système (~130 s). Or
# send_conversation_email() était appelé SYNCHRONEMENT dans le chemin du
# fallback : l'utilisateur posait une question non reconnue, le webhook Rasa
# n'aboutissait jamais et le widget n'affichait aucune réponse. C'est l'origine
# des 35 sessions « no_bot_reply » des journaux (latence mesurée : 136 s).
#
# Trois garde-fous :
#   1. SMTP_TIMEOUT borne chaque tentative de connexion ;
#   2. l'envoi part dans un thread démon, comme send_analytics_event() ci-dessus ;
#   3. un disjoncteur cesse toute tentative après SMTP_MAX_FAILURES échecs
#      consécutifs — inutile de repayer le timeout à chaque fallback une fois
#      qu'on sait le SMTP injoignable depuis cet environnement.
SMTP_TIMEOUT = float(os.getenv('SMTP_TIMEOUT', '8'))
SMTP_MAX_FAILURES = int(os.getenv('SMTP_MAX_FAILURES', '3'))
_smtp_failures = 0
_smtp_disabled = False

# Placeholders laissés tels quels dans l'environnement de production : les
# journaux montraient « SMTP_USERNAME: your-email@gmail.com ». Comme la valeur
# n'est pas vide, le test « if SMTP_USERNAME and SMTP_PASSWORD » passait et le
# code partait dans la branche réseau — donc dans le blocage — au lieu du repli
# fichier. Une valeur manifestement non renseignée doit compter comme absente.
SMTP_PLACEHOLDERS = (
    "your-email", "your_email", "youremail", "your-email@gmail.com",
    "your-password", "your_password", "yourpassword",
    "example@gmail.com", "example@example.com", "changeme", "todo",
    "none", "null", "xxx", "password", "motdepasse",
    "smtp_username", "smtp_password", "dummy", "sample", "placeholder",
)


def _smtp_configured() -> bool:
    """Le SMTP est-il réellement configuré (valeurs présentes ET non factices) ?"""
    user = (SMTP_USERNAME or "").strip().lower()
    pwd = (SMTP_PASSWORD or "").strip().lower()
    if not user or not pwd:
        return False
    if user in SMTP_PLACEHOLDERS or pwd in SMTP_PLACEHOLDERS:
        return False
    for marker in SMTP_PLACEHOLDERS:
        if marker in user or marker in pwd:
            return False
    return True


# Cache for document embeddings
DOCS_CACHE = None
EMBEDDINGS_CACHE = None

# Conversation tracking
CONVERSATION_LOGS = {}
SESSION_LANGUAGES = {}  # Track detected language per session for consistency
ANALYTICS_SESSIONS_STARTED = set()  # Track which sessions already sent session_start

# Analytics API configuration
ANALYTICS_API_URL = os.getenv("ANALYTICS_API_URL", "https://admincb.expobetonrdc.com/api_chatbot_analytics.php")
ANALYTICS_API_KEY = os.getenv("ANALYTICS_API_KEY", "")  # Fixed: was EXPOBETON_API_KEY (wrong)

def send_analytics_event(action: str, data: dict):
    """Fire-and-forget POST to analytics API. Never blocks the chatbot."""
    try:
        import threading
        import requests as req_lib
        url = f"{ANALYTICS_API_URL}?action={action}&api_key={ANALYTICS_API_KEY}"
        print(f"[ANALYTICS] Sending {action} to {ANALYTICS_API_URL} (key={'SET' if ANALYTICS_API_KEY else 'EMPTY'})")
        def _post():
            try:
                resp = req_lib.post(
                    url,
                    json=data,
                    headers={"Authorization": f"Bearer {ANALYTICS_API_KEY}"},
                    timeout=10
                )
                print(f"[ANALYTICS] {action} response: status={resp.status_code}, body={resp.text[:200]}")
            except Exception as e:
                print(f"[ANALYTICS] Failed to send {action}: {e}")
        threading.Thread(target=_post, daemon=True).start()
    except Exception as e:
        print(f"[ANALYTICS] Thread error: {e}")

def _build_transcript_body(session_id: str, user_info: dict, messages: list) -> str:
    """Construit le corps texte du transcript (aucun appel réseau)."""
    transcript = ""
    for msg_data in messages:
        sender = "Utilisateur" if msg_data.get('sender') == 'user' else "Bot"

        # Handle timestamp - peut être datetime ou string ISO
        timestamp = msg_data.get('timestamp')
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except:
                timestamp = datetime.now()
        elif not isinstance(timestamp, datetime):
            timestamp = datetime.now()

        time_str = timestamp.strftime("%H:%M:%S")
        transcript += f"[{time_str}] {sender}: {msg_data.get('text', '')}\n\n"

    return f"""
Bonjour,

Voici le transcript d'une conversation avec le chatbot ExpoBeton RDC.

=== INFORMATIONS UTILISATEUR ===
Nom: {user_info.get('name', 'Non fourni')}
Téléphone: {user_info.get('phone', 'Non fourni')}
Email: {user_info.get('email', 'Non fourni')}
Session ID: {session_id}

=== CONVERSATION ===
{transcript}
=== FIN DE CONVERSATION ===

Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Nombre de messages: {len(messages)}

Cordialement,
Bot ExpoBeton RDC
"""


def _append_conversation_log(body: str):
    """Repli quand le SMTP est indisponible : on ne perd pas la trace."""
    try:
        log_file = Path(__file__).parent.parent / 'conversations.log'
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*50}\n")
            f.write(body)
            f.write(f"\n{'='*50}\n")
    except Exception as e:
        print(f"❌ [EMAIL] Écriture du journal de repli impossible : {e}")


def _deliver_email(label: str, msg):
    """Connexion SMTP réelle. Toujours exécutée dans un thread démon.

    Un timeout explicite est indispensable : sans lui, la connexion vers le port
    587 (filtré sur Railway) bloquait jusqu'au délai TCP du système. Partagée par
    les transcripts de conversation et les questions sans réponse.
    """
    global _smtp_failures, _smtp_disabled
    server = None
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=SMTP_TIMEOUT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)
        _smtp_failures = 0
        print(f"✅ [EMAIL] Envoyé : {label}")
    except Exception as e:
        _smtp_failures += 1
        if _smtp_failures >= SMTP_MAX_FAILURES:
            _smtp_disabled = True
            print(f"⛔ [EMAIL] {_smtp_failures} échecs consécutifs ({e}) — "
                  f"envoi désactivé jusqu'au redémarrage, repli fichier activé.")
        else:
            print(f"❌ [EMAIL] Échec d'envoi pour {label} "
                  f"({_smtp_failures}/{SMTP_MAX_FAILURES}) : {e}")
    finally:
        if server is not None:
            try:
                server.quit()
            except Exception:
                pass


def _queue_message_async(label: str, msg) -> bool:
    """Confie un message MIME déjà construit à un thread démon.

    Renvoie True si un envoi a été programmé, False si le SMTP est indisponible
    (non configuré ou disjoncté) — l'appelant sait alors qu'il doit se reposer
    uniquement sur son repli fichier.
    """
    if not _smtp_configured():
        return False
    if _smtp_disabled:
        # Disjoncteur ouvert : plus aucune tentative de connexion.
        return False
    try:
        import threading
        threading.Thread(
            target=_deliver_email,
            args=(label, msg),
            daemon=True,
        ).start()
        return True
    except Exception as e:
        print(f"❌ [EMAIL] Mise en file impossible pour {label} : {e}")
        return False


def _dispatch_email_async(label: str, subject: str, body: str) -> bool:
    """Construit un message texte simple puis le confie à _queue_message_async."""
    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_USERNAME or 'noreply@expobetonrdc.com'
        msg['To'] = NOTIFICATION_EMAIL
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
    except Exception as e:
        print(f"❌ [EMAIL] Préparation impossible pour {label} : {e}")
        return False
    return _queue_message_async(label, msg)


def send_conversation_email(session_id: str, user_info: dict, messages: list):
    """Enregistre le transcript d'une conversation SANS bloquer l'action.

    Le corps est construit ici (données déjà en mémoire, aucun I/O réseau), puis
    l'envoi SMTP part dans un thread démon — même principe que
    ``send_analytics_event``. Les quatre points d'appel restent inchangés.
    """
    try:
        body = _build_transcript_body(session_id, user_info, messages)
        subject = (
            f'[Bot] Conversation - {user_info.get("name", "Utilisateur")} - '
            f'{datetime.now().strftime("%Y-%m-%d %H:%M")}'
        )
        queued = _dispatch_email_async(f"transcript {session_id}", subject, body)
        if not queued:
            print(f"⚠️ [EMAIL] SMTP indisponible, transcript journalisé : {session_id}")
            _append_conversation_log(body)
    except Exception as e:
        print(f"❌ [EMAIL] Préparation du transcript impossible : {e}")



def log_conversation_message(session_id: str, sender: str, text: str, user_info: dict = None):
    """Log a message in the conversation"""
    if session_id not in CONVERSATION_LOGS:
        CONVERSATION_LOGS[session_id] = {
            'messages': [],
            'user_info': user_info or {},
            'started_at': datetime.now(),
            'last_activity': datetime.now()
        }
    
    CONVERSATION_LOGS[session_id]['messages'].append({
        'sender': sender,
        'text': text,
        'timestamp': datetime.now()
    })
    CONVERSATION_LOGS[session_id]['last_activity'] = datetime.now()
    CONVERSATION_LOGS[session_id]['user_info'] = user_info or CONVERSATION_LOGS[session_id]['user_info']
    
    # --- Analytics ---
    # Bot messages are NOT logged here: the chat widget already logs every
    # bubble displayed to the user, and double-logging produced duplicated
    # and fragmented transcripts in the admin panel. User messages are
    # logged with their NLU intent in ActionAnswerExpoBeton.
    
    # --- Analytics: update session with user info if email provided ---
    if user_info and (user_info.get('email') or user_info.get('name')):
        send_analytics_event('update_session', {
            'session_id': session_id,
            'user_email': user_info.get('email', ''),
            'user_name': user_info.get('name', '')
        })

def send_unanswered_question_email(user_question: str):
    """Send email notification for unanswered questions"""
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = SMTP_USERNAME or 'noreply@expobetonrdc.com'
        msg['To'] = NOTIFICATION_EMAIL
        msg['Subject'] = f'[Bot] Question sans réponse - {datetime.now().strftime("%Y-%m-%d %H:%M")}'
        
        # Email body
        body = f"""
        Bonjour,
        
        Le chatbot ExpoBeton RDC a reçu une question à laquelle il n'a pas pu répondre.
        
        Question de l'utilisateur:
        "{user_question}"
        
        Date et heure: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        
        Veuillez envisager d'ajouter cette information à la base de connaissances du bot.
        
        Cordialement,
        Bot ExpoBeton RDC
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Journal local TOUJOURS écrit. C'est la matière première de l'audit des
        # lacunes du bot (questions non reconnues) : avant, il n'était alimenté
        # que lorsque le SMTP n'était pas configuré — donc perdu dès qu'un envoi
        # était tenté, c'est-à-dire précisément quand il partait en timeout.
        log_file = Path(__file__).parent.parent / 'unanswered_questions.log'
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {user_question}\n")

        # Envoi non bloquant. Cet appel se situe JUSTE AVANT la réponse de repli
        # envoyée à l'utilisateur : une connexion SMTP sans timeout y gelait donc
        # la réponse (~130 s sur Railway, où le port 587 sortant est filtré).
        # Thread démon + timeout + disjoncteur, partagés avec les transcripts.
        if not _queue_message_async(f"question sans réponse : {user_question[:60]}", msg):
            print(f"[UNANSWERED QUESTION] SMTP indisponible, question journalisée : {user_question}")
            
    except Exception as e:
        print(f"Error sending email: {e}")
        # Still log to file as backup
        try:
            log_file = Path(__file__).parent.parent / 'unanswered_questions.log'
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {user_question}\n")
        except:
            pass

# Canonical corpus files are pinned: they are the single source of truth for
# prices, dates, venue and procedures. They must never be crowded out by the
# ~190 legacy brochures, nor truncated by the generic character budget.
CANONICAL_PREFIX = '00_canonical_'
CANONICAL_CHAR_LIMIT = 16000
LEGACY_CHAR_LIMIT = 4000
# Per-document budget inside the LLM prompt. Canonical docs keep more text: their
# price/procedure tables sit past the 3000-char mark and used to be cut off.
CANONICAL_PROMPT_CHARS = 7000
LEGACY_PROMPT_CHARS = 3000

# Brochures d'éditions précédentes, exclues de l'index de recherche.
#
# Elles décrivent des dates, lieux, thèmes et tarifs révolus mais emploient le
# même vocabulaire que la 12ème édition. Pire : le filtre « priority_keywords »
# de load_and_embed_docs() les retenait EN PRIORITÉ — il contenait les années
# « 2024 » et « 2025 », et un nom comme
# FR_V1_Brochure_ExpoBetonRDC_Kalemie_2026.txt cumulait « brochure » et « 2026 ».
# Ces documents passaient donc devant le corpus canonique dans le prompt :
# origine directe des réponses « Kalemie », « avril 2026 », « Grand Katanga » et
# des anciens tarifs relevés dans les journaux de production.
#
# 24 fichiers du corpus portent une année passée, dont une fiche de sponsoring
# 2025 aux paliers périmés. L'historique reste interrogeable : le document
# canonique 00_canonical_evenement_ed12 rappelle explicitement le thème et le
# lieu de la 11ème édition.
SUPERSEDED_YEARS = ('2024', '2025')
SUPERSEDED_DOC_MARKERS = (
    'kalemie', 'lubumbashi', 'kolwezi',              # villes hôtes des éditions passées
    'edition_11', 'edition11', 'ed11', '11eme', '11ème',
)


def _is_superseded(path) -> bool:
    """True si le document décrit une édition passée et doit rester hors index.

    Les documents canoniques ne sont jamais exclus : ils sont la source de vérité,
    y compris lorsqu'ils mentionnent une édition précédente à titre historique.
    """
    name = path.name.lower()
    if name.startswith(CANONICAL_PREFIX):
        return False
    if any(year in name for year in SUPERSEDED_YEARS):
        return True
    return any(marker in name for marker in SUPERSEDED_DOC_MARKERS)



def _collect_doc_files(docs_path):
    """Deterministic .txt + .md inventory: canonical files first, deduped by stem.

    Sorting matters: the previous unsorted glob() made the 30+20 selection depend
    on filesystem enumeration order, so which brochures got indexed could vary
    between deploys.
    """
    found = sorted(docs_path.glob('*.txt')) + sorted(docs_path.glob('*.md'))
    by_stem = {}
    for f in found:
        # When both X.txt and X.md exist, keep the .txt twin (legacy convention).
        if f.stem in by_stem and by_stem[f.stem].suffix == '.txt':
            continue
        by_stem.setdefault(f.stem, f)
    files = [f for f in by_stem.values() if not _is_superseded(f)]
    canonical = [f for f in files if f.name.lower().startswith(CANONICAL_PREFIX)]
    rest = [f for f in files if not f.name.lower().startswith(CANONICAL_PREFIX)]
    return canonical, rest


def load_and_embed_docs():
    """Load all docs and create OpenAI embeddings"""
    global DOCS_CACHE, EMBEDDINGS_CACHE
    
    if DOCS_CACHE is not None:
        # EMBEDDINGS_CACHE stays None when OpenAI is unavailable: callers then use
        # the keyword fallback instead of re-reading the whole corpus each message.
        return DOCS_CACHE, (EMBEDDINGS_CACHE if EMBEDDINGS_CACHE is not None else [])
    
    docs_path = Path(__file__).parent.parent / 'docs'
    documents = []
    
    print(f"📚 Loading documents from {docs_path}...")
    
    # Inventory: .txt + .md, canonical docs pinned first (see _collect_doc_files)
    canonical_files, rest_files = _collect_doc_files(docs_path)
    all_files = canonical_files + rest_files
    
    # Prioritize important files (brochures, reports)
    # Les années passées (« 2024 », « 2025 ») ont été retirées de cette liste :
    # elles faisaient remonter en priorité des documents périmés, désormais exclus
    # par _is_superseded(). Ne reste que l'année de l'édition en cours.
    priority_keywords = ['brochure', 'rapport', 'final', '2026', 'invitation']
    priority_files = [f for f in rest_files if any(kw in f.name.lower() for kw in priority_keywords)]
    other_files = [f for f in rest_files if f not in priority_files]
    
    # Canonical docs are always indexed and always ranked first, on top of the
    # 30 priority + 20 legacy brochures.
    selected_files = canonical_files + priority_files[:30] + other_files[:20]
    
    print(f"📄 Selected {len(selected_files)} documents out of {len(all_files)} (prioritizing recent/important ones)")
    
    for file_path in selected_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Canonical docs keep their full text (source of truth for
                # prices/procedures); legacy brochures stay capped at 4000.
                limit = (CANONICAL_CHAR_LIMIT
                         if file_path.name.lower().startswith(CANONICAL_PREFIX)
                         else LEGACY_CHAR_LIMIT)
                content = content[:limit] if len(content) > limit else content
                documents.append({
                    'filename': file_path.name,
                    'content': content
                })
        except Exception as e:
            print(f"⚠️ Error reading {file_path.name}: {e}")
            continue
    
    if not documents:
        print("⚠️ No documents found!")
        return [], []
    
    print(f"✅ Loaded {len(documents)} documents, creating OpenAI embeddings...")
    
    # Create embeddings with OpenAI (batch processing)
    texts = [doc['content'] for doc in documents]
    try:
        response = _openai_client().embeddings.create(
            input=texts,
            model="text-embedding-3-small",  # Fast, multilingual, cost-effective
            timeout=OPENAI_BULK_TIMEOUT
        )
        embeddings = [item.embedding for item in response.data]
        
        DOCS_CACHE = documents
        EMBEDDINGS_CACHE = np.array(embeddings)
        
        print(f"✅ Successfully created {len(embeddings)} OpenAI embeddings")
        return documents, embeddings
    except Exception as e:
        print(f"❌ Error creating OpenAI embeddings: {e}")
        print("🔤 Retrieval falls back to keyword matching. "
              "Set OPENAI_API_KEY to restore semantic search.")
        # Cache the documents anyway: the keyword fallback answers from them, and
        # we avoid re-reading ~250 KB of corpus + retrying OpenAI on every message.
        DOCS_CACHE = documents
        EMBEDDINGS_CACHE = None
        return documents, []

def _normalize_text(text: str) -> str:
    """Lowercase and strip accents so 'édition' matches 'edition'."""
    import unicodedata
    nfkd = unicodedata.normalize('NFKD', text.lower())
    return ''.join(c for c in nfkd if not unicodedata.combining(c))


def _prefer_canonical(docs):
    """Canonical corpus prevails: when it matches, legacy brochures are dropped.

    The rule is "one canonical document per topic". Legacy files such as
    Fiche_Sponsoring_Stand_ExpoBeton_RDC_2025.txt or the Kalemie brochure carry
    superseded prices and dates, so mixing them into the prompt produces
    contradictory answers.
    """
    canonical = [d for d in docs if d['filename'].lower().startswith(CANONICAL_PREFIX)]
    return canonical if canonical else docs


def _keyword_fallback(query: str, documents, top_k: int = 3):
    """Lexical retrieval used when OpenAI embeddings are unavailable.

    Without this, a missing OPENAI_API_KEY made every open question answer with
    silence (observed in production logs: "No documents or embeddings available").
    """
    tokens = {t for t in re.findall(r"[a-z0-9]+", _normalize_text(query)) if len(t) > 2}
    if not tokens:
        return []

    scored = []
    for doc in documents:
        haystack = _normalize_text(doc['content'])
        filename = _normalize_text(doc['filename'])
        score = 0.0
        for tok in tokens:
            hits = haystack.count(tok)
            if hits:
                # Diminishing returns: a word repeated 200x is not 200x better.
                score += len(tok) * (1 + math.log(hits))
            if tok in filename:
                score += 25.0
        if score > 0:
            # Length normalisation: a focused document must not be outranked by a
            # long generalist one that merely repeats the query words more often.
            score /= 1.0 + math.log(1.0 + len(haystack) / 2000.0)
            if doc['filename'].lower().startswith(CANONICAL_PREFIX):
                score *= 1.35  # canonical corpus wins ties against old brochures
            scored.append((score, doc))

    scored.sort(key=lambda item: item[0], reverse=True)
    canonical_pairs = [p for p in scored
                       if p[1]['filename'].lower().startswith(CANONICAL_PREFIX)]
    top = (canonical_pairs or scored)[:top_k]
    if top:
        print(f"🔤 Keyword fallback: {len(top)} doc(s) for query '{query[:50]}'")
        for i, (score, doc) in enumerate(top):
            print(f"  {i+1}. {doc['filename']} (lexical score: {score:.1f})")
    else:
        print(f"🔤 Keyword fallback: no match for query '{query[:50]}'")
    return [doc for _score, doc in top]


def find_relevant_docs(query: str, top_k: int = 3):
    """Find most relevant documents using OpenAI embeddings"""
    documents, doc_embeddings = load_and_embed_docs()
    
    if not documents:
        print("⚠️ No documents available")
        return []
    
    if len(doc_embeddings) == 0:
        # No OPENAI_API_KEY (or the embedding call failed): answer from the corpus
        # lexically rather than returning nothing to the user.
        return _keyword_fallback(query, documents, top_k)
    
    try:
        # Create embedding for query with OpenAI
        # Délai court et sans relance : cet appel est dans le chemin de réponse
        # (une fois par question d'au moins 15 caractères). Le défaut du client
        # est 600 s × 3 tentatives, ce qui immobiliserait un worker du serveur
        # d'actions pendant plusieurs minutes.
        query_response = _openai_client().embeddings.create(
            input=[query],
            model="text-embedding-3-small",
            timeout=OPENAI_TIMEOUT
        )
        query_embedding = np.array(query_response.data[0].embedding)
        
        # Calculate cosine similarity
        doc_embeddings_array = np.array(doc_embeddings)
        similarities = np.dot(doc_embeddings_array, query_embedding) / (
            np.linalg.norm(doc_embeddings_array, axis=1) * np.linalg.norm(query_embedding)
        )
        
        # Rank a wider pool, then let the canonical corpus prevail over the
        # legacy brochures that carry superseded prices and dates.
        pool = min(len(documents), top_k * 4)
        top_indices = np.argsort(similarities)[-pool:][::-1]
        relevant_docs = _prefer_canonical([documents[i] for i in top_indices])[:top_k]
        sim_by_name = {documents[i]['filename']: float(similarities[i]) for i in top_indices}
        
        print(f"🔍 Found {len(relevant_docs)} relevant documents for query: {query[:50]}...")
        for i, doc in enumerate(relevant_docs):
            print(f"  {i+1}. {doc['filename']} (similarity: {sim_by_name.get(doc['filename'], 0.0):.3f})")
        
        return relevant_docs
    except Exception as e:
        print(f"❌ Error finding relevant docs with OpenAI: {e}")
        return _keyword_fallback(query, documents, top_k)

# Multilingual content dictionary
MULTILINGUAL_CONTENT = {
    'greeting': {
        'fr': "Bonjour! Je suis ravi de vous aider. Comment puis-je vous renseigner sur ExpoBeton RDC aujourd'hui?",
        'en': "Hello! I'm delighted to help you. How can I assist you with ExpoBeton RDC today?",
        'zh': "您好！我很高兴为您提供帮助。我能为您提供有关ExpoBeton RDC的哪些信息？",
        'ru': "Здравствуйте! Рад помочь вам. Как я могу помочь вам с ExpoBeton RDC сегодня?",
        'es': "¡Hola! Estoy encantado de ayudarle. ¿Cómo puedo ayudarle con ExpoBeton RDC hoy?",
        'ar': "مرحباً! يسعدني مساعدتك. كيف يمكنني مساعدتك بخصوص ExpoBeton RDC اليوم؟"
    },
    'how_are_you': {
        'fr': "Je vais très bien, merci de demander! 😊 Que souhaitez-vous savoir sur ExpoBeton RDC?",
        'en': "I'm doing great, thanks for asking! 😊 What would you like to know about ExpoBeton RDC?",
        'zh': "我很好，谢谢关心！😊 您想了解关于ExpoBeton RDC的什么信息？",
        'ru': "У меня все отлично, спасибо, что спросили! 😊 Что вы хотите узнать о ExpoBeton RDC?",
        'es': "¡Estoy muy bien, gracias por preguntar! 😊 ¿Qué le gustaría saber sobre ExpoBeton RDC?",
        'ar': "أنا بخير، شكراً لسؤالك! 😊 ماذا تريد أن تعرف عن ExpoBeton RDC؟"
    },
    'what_is_expobeton': {
        'fr': "ExpoBeton RDC est le salon international de la construction, des infrastructures et du développement urbain en République Démocratique du Congo. C'est un forum annuel qui crée un espace de réflexion et de partenariat pour rebâtir les villes congolaises et soutenir la croissance économique.",
        'en': "ExpoBeton RDC is the international construction, infrastructure and urban development fair in the Democratic Republic of Congo. It's an annual forum that creates a space for reflection and partnership to rebuild Congolese cities and support economic growth.",
        'zh': "ExpoBeton RDC是刚果民主共和国的国际建筑、基础设施和城市发展博览会。这是一个年度论坛,为重建刚果城市和支持经济增长创造了一个反思和伙伴关系的空间。",
        'ru': "ExpoBeton RDC - это международная выставка строительства, инфраструктуры и городского развития в Демократической Республике Конго. Это ежегодный форум, который создает пространство для размышлений и партнерства по восстановлению конголезских городов и поддержке экономического роста.",
        'es': "ExpoBeton RDC es la feria internacional de construcción, infraestructura y desarrollo urbano en la República Democrática del Congo. Es un foro anual que crea un espacio de reflexión y asociación para reconstruir las ciudades congoleñas y apoyar el crecimiento económico.",
        'ar': "ExpoBeton RDC هو المعرض الدولي للبناء والبنية التحتية والتنمية الحضرية في جمهورية الكونغو الديمقراطية. إنه منتدى سنوي يخلق مساحة للتفكير والشراكة لإعادة بناء المدن الكونغولية ودعم النمو الاقتصادي."
    },
    # Édition 12 : 07-10 octobre 2026, Kinshasa. Les variantes zh/ru/es/ar
    # décrivaient encore la 11e édition (Kalemie, 15-18 avril 2026).
    'dates': {
        'fr': "La prochaine édition (12ème) d'ExpoBeton RDC aura lieu du 07 au 10 octobre 2026 à Kinshasa, à La Grande Résidence — Galerie La Fontaine. Cette édition est consacrée au thème « Kinshasa, Locomotive de la Transformation des Villes de la RDC ». (La 11ème édition s'est tenue dans le Grand Katanga — Lubumbashi.)",
        'en': "The next edition (12th) of ExpoBeton RDC will take place from October 7 to 10, 2026 in Kinshasa, at La Grande Residence - Galerie La Fontaine. This edition focuses on the theme 'Kinshasa, Locomotive of the Transformation of DRC Cities'. (The 11th edition was held in the Grand Katanga - Lubumbashi.)",
        'zh': "ExpoBeton RDC下一届（第12届）将于2026年10月7日至10日在金沙萨举行，地点为 The Grand Residence — Galerie La Fontaine。本届主题为「金沙萨：刚果民主共和国城市转型的火车头」。（第11届在大加丹加地区——卢本巴希举行。）",
        'ru': "Следующее издание (12-е) ExpoBeton RDC состоится с 7 по 10 октября 2026 года в Киншасе, в The Grand Residence — Galerie La Fontaine. Тема этого издания: «Киншаса — локомотив трансформации городов ДРК». (11-е издание прошло в регионе Большой Катанга — Лубумбаши.)",
        'es': "La próxima edición (12ª) de ExpoBeton RDC tendrá lugar del 7 al 10 de octubre de 2026 en Kinshasa, en The Grand Residence — Galerie La Fontaine. El tema de esta edición es «Kinshasa, locomotora de la transformación de las ciudades de la RDC». (La 11ª edición se celebró en el Gran Katanga — Lubumbashi.)",
        'ar': "ستقام النسخة القادمة (الثانية عشرة) من ExpoBeton RDC من 7 إلى 10 أكتوبر 2026 في كينشاسا، في The Grand Residence — Galerie La Fontaine. موضوع هذه النسخة: «كينشاسا، قاطرة تحول المدن في جمهورية الكونغو الديمقراطية». (أقيمت النسخة الحادية عشرة في منطقة كاتانغا الكبرى — لوبومباشي.)"
    },
    # Deux adresses distinctes à ne jamais fusionner : le salon est à
    # La Grande Résidence (Gombe), le secrétariat de l'ASBL est à Ngaliema.
    'location': {
        'fr': "Le salon se tient à **The Grand Residence — Galerie La Fontaine**, croisement des avenues des Cliniques et Batetela, **Kinshasa / Gombe**. C'est là que se déroulent l'exposition, les conférences, les panels, les rendez-vous B2B/B2G et les cérémonies.\n\n🏢 Notre **secrétariat** (adresse administrative d'EXPO BÉTON ASBL) est au **07, avenue de l'OUA, Kinshasa / Ngaliema** — ce n'est pas le lieu du salon.",
        'en': "The show takes place at **The Grand Residence — Galerie La Fontaine**, intersection of avenues des Cliniques and Batetela, **Kinshasa / Gombe**. That is where the exhibition, conferences, panels, B2B/B2G meetings and ceremonies are held.\n\n🏢 Our **secretariat** (administrative address of EXPO BÉTON ASBL) is at **07, avenue de l'OUA, Kinshasa / Ngaliema** — this is not the show venue.",
        'zh': "展会地点：**The Grand Residence — Galerie La Fontaine**，Cliniques 大街与 Batetela 大街交汇处，**金沙萨 / 贡贝区（Gombe）**。展览、会议、专题讨论、B2B/B2G 洽谈和开闭幕式均在此举行。\n\n🏢 **秘书处**（EXPO BÉTON ASBL 行政地址）：**金沙萨 / 恩加利埃马区（Ngaliema），OUA 大街 07 号** —— 该地址不是展会场地。",
        'ru': "Место проведения выставки: **The Grand Residence — Galerie La Fontaine**, пересечение проспектов Cliniques и Batetela, **Киншаса / район Gombe**. Здесь проходят экспозиция, конференции, панели, деловые встречи B2B/B2G и церемонии.\n\n🏢 Наш **секретариат** (административный адрес EXPO BÉTON ASBL): **проспект де л'УА, 07, Киншаса / район Ngaliema** — это не место проведения выставки.",
        'es': "La feria se celebra en **The Grand Residence — Galerie La Fontaine**, cruce de las avenidas des Cliniques y Batetela, **Kinshasa / Gombe**. Allí tienen lugar la exposición, las conferencias, los paneles, las reuniones B2B/B2G y las ceremonias.\n\n🏢 Nuestra **secretaría** (dirección administrativa de EXPO BÉTON ASBL) está en **07, avenida de l'OUA, Kinshasa / Ngaliema** — no es el recinto de la feria.",
        'ar': "يُقام المعرض في **The Grand Residence — Galerie La Fontaine**، عند تقاطع شارعي Cliniques و Batetela، **كينشاسا / غومبي**. هناك تُقام المعارض والمؤتمرات وحلقات النقاش واجتماعات الأعمال ومراسم الافتتاح والاختتام.\n\n🏢 تقع **الأمانة العامة** (العنوان الإداري لجمعية EXPO BÉTON) في **07، شارع لْوا (OUA)، كينشاسا / نغاليما** — وهذا ليس موقع المعرض."
    },
    'thank_you': {
        'fr': "De rien! C'est avec plaisir! 😊\n\nSi vous avez d'autres questions sur ExpoBeton RDC, n'hésitez pas à me demander!",
        'en': "You're welcome! My pleasure! 😊\n\nIf you have any other questions about ExpoBeton RDC, don't hesitate to ask!",
        'zh': "不客气！很高兴为您服务！😊\n\n如果您对ExpoBeton RDC有任何其他问题，请随时提问！",
        'ru': "Пожалуйста! С удовольствием! 😊\n\nЕсли у вас есть другие вопросы о ExpoBeton RDC, не стесняйтесь спрашивать!",
        'es': "¡De nada! ¡Un plaisir! 😊\n\nSi tiene otras preguntas sobre ExpoBeton RDC, ¡no dude en preguntar!",
        'ar': "على الرحب والسعة! بكل سرور! 😊\n\nإذا كان لديك أي أسئلة أخرى حول ExpoBeton RDC، لا تتردد في السؤال!"
    },
    'goodbye': {
        'fr': "Au revoir! Merci d'avoir utilisé notre chatbot ExpoBeton RDC! 👋\n\nÀ très bientôt! N'hésitez pas à revenir si vous avez d'autres questions.",
        'en': "Goodbye! Thank you for using our ExpoBeton RDC chatbot! 👋\n\nSee you soon! Don't hesitate to come back if you have other questions.",
        'zh': "再见！感谢您使用我们的ExpoBeton RDC聊天机器人！👋\n\n很快见！如果您有其他问题，请随时回来。",
        'ru': "До свидания! Спасибо за использование нашего чат-бота ExpoBeton RDC! 👋\n\nДо скорой встречи! Не стесняйтесь вернуться, если у вас есть другие вопросы.",
        'es': "¡Adiós! ¡Gracias por usar nuestro chatbot ExpoBeton RDC! 👋\n\n¡Hasta pronto! No dude en volver si tiene otras preguntas.",
        'ar': "وداعاً! شكراً لاستخدامك روبوت الدردشة ExpoBeton RDC! 👋\n\nإلى اللقاء قريباً! لا تتردد في العودة إذا كان لديك أسئلة أخرى."
    },
    'fallback': {
        # Journal de conversations (sept. 2026) : l'ancienne formulation froide
        # « je ne peux pas vous fournir de réponse » terminait 30 sessions sans
        # relance. Le repli propose désormais des exemples concrets, dont le
        # pass VIP (question la plus fréquente sur les offres payantes).
        'fr': "Désolé, je n'ai pas encore de réponse à cette question. 🙏\n\n📧 Notre équipe se fera un plaisir de vous répondre : **info@expobetonrdc.com**\n\n💡 Voici ce que je peux vous renseigner :\n• 📅 **Dates & lieu** — du 07 au 10 octobre 2026, Kinshasa\n• 🎯 **Thème** de la 12ème édition\n• 📋 **Catégories d'inscription** — tapez « catégories » (Sponsor, Exposant, Participant Simple)\n• 🌟 **Pass Participant VIP** — 300 $ les 4 jours\n• 🏆 **Devenir ambassadeur**\n• 🎓 **Concours Jeunesse Horizon 2050**",
        'en': "Sorry, I don't have an answer to that question yet. 🙏\n\n📧 Our team will be happy to reply: **info@expobetonrdc.com**\n\n💡 Here's what I can help you with:\n• 📅 **Dates & venue** — October 7 to 10, 2026, Kinshasa\n• 🎯 **Theme** of the 12th edition\n• 📋 **Registration categories** — type 'categories' (Sponsor, Exhibitor, Simple Participant)\n• 🌟 **VIP Participant pass** — $300 for all 4 days\n• 🏆 **Becoming an ambassador**\n• 🎓 **Youth Contest Horizon 2050**",
        'zh': "抱歉，我暂时无法回答这个问题。🙏\n\n📧 我们的团队很乐意为您解答：**info@expobetonrdc.com**\n\n💡 我可以为您介绍：\n• 📅 **日期与地点** — 2026年10月7日至10日，金沙萨\n• 🎯 第12届**主题**\n• 📋 **注册类别** — 输入「类别」（赞助商、参展商、普通参与者）\n• 🌟 **VIP参与者通行证** — 300美元，涵盖4天\n• 🏆 **成为大使**\n• 🎓 **2050地平线青年竞赛**",
        'ru': "Извините, у меня пока нет ответа на этот вопрос. 🙏\n\n📧 Наша команда с радостью вам ответит: **info@expobetonrdc.com**\n\n💡 Вот с чем я могу помочь:\n• 📅 **Даты и место** — с 7 по 10 октября 2026 года, Киншаса\n• 🎯 **Тема** 12-го издания\n• 📋 **Категории регистрации** — введите «категории» (спонсор, экспонент, простой участник)\n• 🌟 **VIP-пасс участника** — 300 $ за все 4 дня\n• 🏆 **Стать послом**\n• 🎓 **Молодёжный конкурс Horizon 2050**",
        'es': "Lo siento, todavía no tengo respuesta para esa pregunta. 🙏\n\n📧 Nuestro equipo estará encantado de responderle: **info@expobetonrdc.com**\n\n💡 Esto es lo que puedo informarle:\n• 📅 **Fechas y lugar** — del 7 al 10 de octubre de 2026, Kinshasa\n• 🎯 **Tema** de la 12ª edición\n• 📋 **Categorías de inscripción** — escriba «categorías» (patrocinador, expositor, participante simple)\n• 🌟 **Pase VIP de participante** — 300 $ por los 4 días\n• 🏆 **Convertirse en embajador**\n• 🎓 **Concurso Juvenil Horizonte 2050**",
        'ar': "عذراً، ليس لدي إجابة على هذا السؤال بعد. 🙏\n\n📧 يسعد فريقنا الرد عليك: **info@expobetonrdc.com**\n\n💡 يمكنني مساعدتك في:\n• 📅 **التواريخ والموقع** — من 7 إلى 10 أكتوبر 2026، كينشاسا\n• 🎯 **موضوع** النسخة الثانية عشرة\n• 📋 **فئات التسجيل** — اكتب «الفئات» (راعي، عارض، مشارك عادي)\n• 🌟 **بطاقة VIP للمشارك** — 300 دولار للأيام الأربعة\n• 🏆 **أن تصبح سفيراً**\n• 🎓 **مسابقة الشباب أفق 2050**"
    },
    # Pass Participant VIP 12ème édition : forfait UNIQUE de 300 $ (USD hors
    # TVA) couvrant les 4 jours (07–10 octobre 2026, Kinshasa). Source de
    # vérité : sponsor/vip-participant.php. L'ancien tarif « 300 $ par jour,
    # journées au choix » (souscription-vip.php / vipDay) est abrogé.
    'registration': {
        'fr': "Pour participer à ExpoBeton RDC 2026 (07–10 octobre, Kinshasa), vous devez vous inscrire.\n\n📋 **4 offres disponibles :**\n1️⃣ 🏆 Sponsor (Platinum/Gold/Bronze/Silver — de 10.000 $ à 40.000 $)\n2️⃣ 🏗️ Exposant (stand 3×3m à 5.000 $ ou 2×3m à 3.500 $)\n3️⃣ 👤 Participant Simple (Gratuit)\n\n🌟 **Participant VIP** — pass unique **300 $ (USD hors TVA) couvrant les 4 jours** : accès privilégié, visite des stands + guide officiel, 1 RDV IBC B2G & B2B par jour, pass conférence, cocktail VIP et activités hors site.\n\n🔗 Souscription **en ligne uniquement** sur https://expobetonrdc.com/sponsor/vip-participant.php (Visa, Mastercard, Mobile Money).\n\n💬 Souhaitez-vous que je vous guide dans l'inscription ? Tapez « oui » ou « je veux m'inscrire » pour commencer.\n\n💡 Vous pourriez aussi demander :\n• Quelles sont les dates ?\n• Comment devenir ambassadeur ?\n• Quel est le thème ?",
        'en': "To participate in ExpoBeton RDC 2026 (October 7–10, Kinshasa), you need to register.\n\n📋 **4 offers available:**\n1️⃣ 🏆 Sponsor (Platinum/Gold/Bronze/Silver — from $10,000 to $40,000)\n2️⃣ 🏗️ Exhibitor (3×3m stand at $5,000 or 2×3m stand at $3,500)\n3️⃣ 👤 Simple Participant (Free)\n\n🌟 **VIP Participant** — a single pass of **$300 (USD excl. VAT) covering all 4 days**: privileged access, booth visits + official guide, 1 IBC B2G & B2B meeting per day, conference pass, VIP cocktail and off-site activities.\n\n🔗 Online subscription **only** at https://expobetonrdc.com/sponsor/vip-participant.php (Visa, Mastercard, Mobile Money).\n\n💬 Would you like me to guide you through the registration? Type 'yes' or 'I want to register' to begin.\n\n💡 You might also ask:\n• What are the dates?\n• How to become an ambassador?\n• What is the theme?",
        'zh': '要参加ExpoBeton RDC 2026（10月7日至10日，金沙萨），您需要注册。\n\n📋 **4种可选方案：**\n1️⃣ 🏆 赞助商（白金/金/铜/银 — 10,000至40,000美元）\n2️⃣ 🏗️ 参展商（3×3米展位5,000美元 或 2×3米展位3,500美元）\n3️⃣ 👤 普通参与者（免费）\n\n🌟 **VIP参与者** — 单一通行证 **300美元（不含增值税）涵盖全部4天**：优先入场、参观展位+官方指南、每天1场IBC B2G和B2B洽谈、会议通行证、VIP鸡尾酒会和场外活动。\n\n🔗 仅可通过 https://expobetonrdc.com/sponsor/vip-participant.php 在线订阅（Visa、Mastercard、移动支付）。\n\n💬 您想让我引导您完成注册吗？输入「是」开始。',
        'ru': "Чтобы принять участие в ExpoBeton RDC 2026 (7–10 октября, Киншаса), зарегистрируйтесь онлайн на https://expobetonrdc.com/#tg_register.\n\n📋 **4 категории:** спонсор (Platinum/Gold/Bronze/Silver — от 10 000 $ до 40 000 $), экспонент (стенд 3×3 м — 5 000 $ или 2×3 м — 3 500 $), VIP-участник (единый пасс 300 $ без НДС на все 4 дня: привилегированный доступ, посещение стендов + официальный гид, 1 встреча IBC B2G/B2B в день, пасс на конференции, VIP-коктейль и выездные мероприятия) и простой участник (бесплатно).\n\n🔗 VIP-участие оформляется только онлайн на https://expobetonrdc.com/sponsor/vip-participant.php (Visa, Mastercard, мобильные деньги).\n\n💡 Вы также можете спросить:\n• Какие даты?\n• Как стать послом?\n• Какая тема?",
        'es': "Para participar en ExpoBeton RDC 2026 (7 al 10 de octubre, Kinshasa), regístrese en línea en https://expobetonrdc.com/#tg_register.\n\n📋 **4 categorías:** patrocinador (Platinum/Gold/Bronze/Silver — de 10.000 $ a 40.000 $), expositor (stand 3×3m a 5.000 $ o 2×3m a 3.500 $), participante VIP (pase único de 300 $ sin IVA para los 4 días: acceso privilegiado, visita de stands + guía oficial, 1 reunión IBC B2G y B2B por día, pase de conferencias, cóctel VIP y actividades fuera del recinto) y participante simple (gratuito).\n\n🔗 La suscripción VIP se realiza solo en línea en https://expobetonrdc.com/sponsor/vip-participant.php (Visa, Mastercard, Mobile Money).\n\n💡 También podría preguntar:\n• ¿Cuáles son las fechas?\n• ¿Cómo convertirse en embajador?\n• ¿Cuál es el tema?",
        'ar': "للمشاركة في ExpoBeton RDC 2026 (من 7 إلى 10 أكتوبر، كينشاسا)، سجل عبر الإنترنت على https://expobetonrdc.com/#tg_register.\n\n📋 **4 فئات:** راعي (Platinum/Gold/Bronze/Silver — من 10,000 إلى 40,000 دولار)، عارض (جناح 3×3م بـ 5,000 دولار أو 2×3م بـ 3,500 دولار)، مشارك VIP (بطاقة موحدة بـ 300 دولار دون ضريبة تغطي الأيام الأربعة: وصول مميز، زيارة الأجنحة + الدليل الرسمي، لقاء IBC واحد B2G وB2B يومياً، بطاقة المؤتمرات، حفل استقبال VIP وأنشطة خارج الموقع) ومشارك عادي (مجاني).\n\n🔗 الاشتراك في VIP يتم حصرياً عبر الإنترنت على https://expobetonrdc.com/sponsor/vip-participant.php (Visa، Mastercard، الدفع عبر الهاتف).\n\n💡 قد تسأل أيضاً:\n• ما هي التواريخ؟\n• كيف تصبح سفيراً؟\n• ما هو الموضوع؟"
    }
}

def detect_language(text: str) -> str:
    """Detect language from user text. Returns language code."""
    text_lower = text.lower()
    # Split into words for whole-word matching
    words = set(text_lower.split())
    
    # French keywords (whole words only)
    french_keywords = ['bonjour', 'salut', 'merci', 'quoi', 'comment', 'pourquoi',
                       'quand', 'où', 'c\'est', 'quelles', 'quel', 'quelle',
                       'qui', 'sont', 'les', 'des', 'une', 'est', 'pour', 'dans',
                       'avec', 'sur', 'pas', 'nous', 'vous', 'votre', 'notre',
                       'cette', 'ces', 'aussi', 'mais', 'donc', 'oui', 'non',
                       'je', 'tu', 'il', 'elle', 'ils', 'elles', 'mon', 'ton',
                       'son', 'mes', 'tes', 'ses', 'leur', 'leurs']
    # English keywords (whole words only)
    english_keywords = ['hello', 'hi', 'thank', 'thanks', 'what', 'how', 'why',
                        'when', 'where', 'the', 'and', 'can', 'could', 'would',
                        'should', 'will', 'have', 'has', 'this', 'that', 'with',
                        'from', 'about', 'yes', 'no', 'please', 'want', 'need',
                        'like', 'know', 'tell', 'me', 'my', 'your', 'they']
    # Spanish keywords
    spanish_keywords = ['hola', 'gracias', 'qué', 'cómo', 'cuándo', 'dónde', 'por qué', 'buenos', 'días']
    # Russian keywords (Cyrillic)
    russian_keywords = ['привет', 'спасибо', 'что', 'как', 'когда', 'где', 'почему', 'здравствуй']
    # Chinese characters detection
    has_chinese = any('\u4e00' <= char <= '\u9fff' for char in text)
    # Arabic characters detection
    has_arabic = any('\u0600' <= char <= '\u06ff' for char in text)
    
    # Count matches using whole-word matching (set intersection)
    french_score = len(words & set(french_keywords))
    english_score = len(words & set(english_keywords))
    # Spanish still uses substring for multi-word phrases
    spanish_score = sum(1 for keyword in spanish_keywords if keyword in text_lower)
    russian_score = sum(1 for keyword in russian_keywords if keyword in text_lower)
    
    if has_chinese:
        return 'zh'
    if has_arabic:
        return 'ar'
    if russian_score > 0:
        return 'ru'
    if spanish_score > english_score and spanish_score > french_score:
        return 'es'
    if english_score > french_score:
        return 'en'
    if french_score > 0:
        return 'fr'
    
    # Default to French
    return 'fr'

def get_multilingual_response(key: str, lang: str = 'fr') -> str:
    """Get response in the specified language."""
    if key in MULTILINGUAL_CONTENT and lang in MULTILINGUAL_CONTENT[key]:
        return MULTILINGUAL_CONTENT[key][lang]
    # Fallback to French
    if key in MULTILINGUAL_CONTENT and 'fr' in MULTILINGUAL_CONTENT[key]:
        return MULTILINGUAL_CONTENT[key]['fr']
    return ""

class ActionGreetPersonalized(Action):
    """Custom action for personalized greeting with name extraction"""
    # FORCE RELOAD: 2025-11-08 14:25 - Fix Lubumbashi question detection - CRITICAL
    # VERSION: 2.1.8 - Enhanced NLU patterns for location questions
    
    def name(self) -> Text:
        return "action_greet_personalized"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Get the user's message FIRST to check if it's actually a question
        user_message = tracker.latest_message.get('text', '').lower()
        
        # CRITICAL DEBUG: Log that this action was called
        print(f"👋👋👋 [ACTION_GREET_PERSONALIZED] CALLED! user_message={tracker.latest_message.get('text', '')}, intent={tracker.latest_message.get('intent', {}).get('name', 'UNKNOWN')}")
        
        # =============================================================
        # CRITICAL: Check if this is actually a QUESTION, not a greeting!
        # =============================================================
        
        # ANY mention of Lubumbashi - ULTRA BROAD MATCH (no conditions!)
        # Match ANY variation of Lubumbashi, with or without question mark
        # Common typos: lubumabshi, lubumbachi, loubumbashi, etc.
        lubumbashi_variants = ['lubumbashi', 'lubumabshi', 'lubumbachi', 'loubumbashi', 'lubumbash', 'lumumbashi']
        
        # If ANY variant is mentioned, answer immediately!
        for variant in lubumbashi_variants:
            if variant in user_message:
                print(f"🔥🔥🔥 [GREET DEBUG] LUBUMBASHI DETECTED (variant={variant})! user_message={user_message}")
                answer = "ℹ️ La **12ème édition d'ExpoBeton RDC (07-10 octobre 2026)** se tiendra à **Kinshasa**, à La Grande Résidence — Galerie La Fontaine (Gombe).\n\n**Lubumbashi** a accueilli la **11ème édition** (avril 2026, volet Grand Katanga), avec des étapes satellites à Kalemie et Kolwezi : cette édition s'est concentrée sur le Grand Katanga comme carrefour stratégique des corridors africains du Sud, de l'Ouest et de l'Est, avec un potentiel énorme en infrastructures grâce aux réserves de cuivre, cobalt et lithium de la région."
                dispatcher.utter_message(text=answer)
                return []
        
        # History of ExpoBeton
        if any(word in user_message for word in ['histoire', 'history', 'historique']):
            print(f"🎯🎯🎯 [GREET DEBUG] HISTOIRE CHECK MATCHED IN GREET! user_message={user_message}")
            answer = "📜 **Histoire d'ExpoBeton RDC**\n\n🚀 **Création:** 2016 par Jean Bamanisa Saïdi\n\n🎯 **Mission:** Promouvoir les infrastructures, la construction et le développement urbain en RDC\n\n🏆 **Évolution:**\n• 2016-2022: Éditions à Kinshasa (focus capital)\n• 2023: Expansion vers Kolwezi (mines, Grand Katanga)\n• 2024: Double phase Kinshasa + Matadi (corridor ouest)\n• Avril 2026 (11e): Grand Katanga — Lubumbashi (+ étapes Kalemie et Kolwezi)\n• Octobre 2026 (12e): Kinshasa, du 07 au 10 octobre\n\n💡 **Impact:**\n• Création du Ministère de la Politique de la Ville (2024)\n• Recommandations adoptées par le gouvernement\n• Plateforme B2B, B2G majeure en RDC\n• Think tanks thématiques annuels\n\n👥 **Fondateurs:** Jean Bamanisa Saïdi (Président) + Momo Sungunza (Vice-Président)"
            dispatcher.utter_message(text=answer)
            return []
        
        # Which edition / how many editions (with typo support)
        if any(word in user_message for word in ['edition', 'édition', 'edtion', 'editon', 'ediiton', 'ediition']):
            if any(kw in user_message for kw in ['combien', 'how many', 'nombre']):
                answer = "**11 editions** d'ExpoBeton RDC ont deja ete organisees depuis 2016. La **12eme edition** aura lieu du **07 au 10 octobre 2026 a Kinshasa**."
                dispatcher.utter_message(text=answer)
                return []
            # Default: assume user is asking which edition (most common question)
            answer = "Nous sommes a la **12eme edition** d'ExpoBeton RDC ! Elle se tiendra du **07 au 10 octobre 2026** a **Kinshasa**, a La Grande Residence - Galerie La Fontaine.\n\nLe theme : **Kinshasa, Locomotive de la Transformation des Villes de la RDC.**\n\n(La 11eme edition s'est tenue dans le Grand Katanga - Lubumbashi, avec etapes satellites a Kalemie et Kolwezi.)"
            dispatcher.utter_message(text=answer)
            return []

        # Location questions in greeting message
        location_kw = ['lieu', 'lieux', 'location', 'address', 'adresse',
                       'se passe', 'se passera', 'se tiendra', 'se deroule',
                       'se deroulera', 'se tient', 'where', 'venue']
        has_loc_kw = any(kw in user_message for kw in location_kw)
        has_ou = any(w in user_message for w in [' ou ', ' ou', 'ou ', 'ou?', 'ou?'])
        has_loc_ctx = any(w in user_message for w in ['se passera', 'se passe', 'se tiendra', 'edition', 'edtion', 'editon', 'expobeton', 'salon', '2026'])
        if has_loc_kw or (has_ou and has_loc_ctx):
            # Lieu reel verifie sur index.php (ligne 275) : « The Grand Residence —
            # Galerie La Fontaine, croisement des avenues des Cliniques et Batetela,
            # Kinshasa Gombe ». Le 07, avenue de l'OUA (Ngaliema) est l'adresse du
            # secretariat de l'ASBL, pas le lieu du salon. Cette copie codee en dur
            # les confondait — le meme defaut que celui corrige dans domain.yml
            # (M7), mais dans l'action de salutation, donc sur un autre chemin.
            answer = (
                "📍 **Lieu précis — ExpoBeton RDC 2026 (12ème édition) :**\n\n"
                "Le salon se tient à **The Grand Residence — Galerie La Fontaine**, "
                "au **croisement des avenues des Cliniques et Batetela**, commune de "
                "la **Gombe**, à **Kinshasa**, capitale de la RDC.\n\n"
                "🏢 **Secrétariat / adresse administrative** d'EXPO BÉTON ASBL : "
                "**07, avenue de l'OUA, commune de Ngaliema**, Kinshasa.\n"
                "⚠️ Attention : le secrétariat n'est **pas** le lieu du salon.\n\n"
                "📅 Dates : du **07 au 10 octobre 2026** (4 jours)."
            )
            dispatcher.utter_message(text=answer)
            return []
        
        # =============================================================
        # ONLY proceed with greeting if it's NOT a question!
        # =============================================================
        
        # Get person entity
        person = next(tracker.get_latest_entity_values("person"), None)
        
        # Fallback: extract name from metadata (widget form) if entity not detected
        if not person:
            metadata = tracker.latest_message.get('metadata', {})
            person = metadata.get('name') or None
            if person:
                print(f"[GREET] Name from metadata: {person}")
        
        # Detect language
        user_message_original = tracker.latest_message.get('text', '')
        detected_lang = detect_language(user_message_original)
        
        if person:
            # Personalized greeting with name
            if detected_lang == 'fr':
                message = f"Bonjour {person}! 😊 Ravi de faire votre connaissance! Comment puis-je vous aider aujourd'hui avec ExpoBeton RDC?"
            elif detected_lang == 'en':
                message = f"Hello {person}! 😊 Nice to meet you! How can I assist you today with ExpoBeton RDC?"
            else:
                message = f"Bonjour {person}! 😊 Ravi de faire votre connaissance! Comment puis-je vous aider aujourd'hui avec ExpoBeton RDC?"
        else:
            # Generic greeting
            message = get_multilingual_response('greeting', detected_lang)
            if detected_lang == 'fr':
                message = message.replace("Bonjour!", "Bonjour! 😊")
            elif detected_lang == 'en':
                message = message.replace("Hello!", "Hello! 😊")

        # Drop-off fix (conversation logs): many users left right after the
        # open greeting question. Offer a guided menu immediately.
        if detected_lang == 'en':
            message += (
                "\n\n💡 I can help you with:\n"
                "• 📅 the **dates** and **location** of the event\n"
                "• 📋 the **program**\n"
                "• 🏷️ the **categories** and pricing\n"
                "• 📝 registration — type **« je veux m'inscrire »**"
            )
        else:
            message += (
                "\n\n💡 Je peux vous renseigner sur :\n"
                "• 📅 Les **dates** et le **lieu** de l'événement\n"
                "• 📋 Le **programme**\n"
                "• 🏷️ Les **catégories** et tarifs\n"
                "• 📝 L'**inscription** — tapez **« je veux m'inscrire »**"
            )
        
        dispatcher.utter_message(text=message)
        return []

class ActionAnswerExpoBeton(Action):
    def name(self) -> Text:
        return "action_answer_expobeton"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        user_question = tracker.latest_message.get('text', '').lower()
        user_message_original = tracker.latest_message.get('text', '')
        session_id = tracker.sender_id
        metadata = tracker.latest_message.get('metadata', {})
        
        # CRITICAL DEBUG: Log that this action was called
        print(f"🚨🚨🚨 [ACTION_ANSWER_EXPOBETON] CALLED! user_message={user_message_original}, intent={tracker.latest_message.get('intent', {}).get('name', 'UNKNOWN')}")
        
        # Detect user's language for EACH message (not session-based)
        detected_lang = detect_language(user_message_original)
        print(f"[MULTILINGUAL] Detected language: {detected_lang} for message: {user_message_original[:50]}")
        
        # Log user message
        log_conversation_message(session_id, 'user', user_message_original, metadata)
        
        # --- Analytics: session_start on first message ---
        if session_id not in ANALYTICS_SESSIONS_STARTED:
            ANALYTICS_SESSIONS_STARTED.add(session_id)
            send_analytics_event('session_start', {
                'session_id': session_id,
                'ip_address': metadata.get('client_ip', ''),
                'device_type': metadata.get('device_type', 'unknown'),
                'browser': metadata.get('browser', 'unknown'),
                'os': metadata.get('os', 'unknown'),
                'screen_width': metadata.get('screen_width'),
                'screen_height': metadata.get('screen_height'),
                'language': metadata.get('language', ''),
                'referrer': metadata.get('referrer', ''),
                'user_agent': metadata.get('user_agent', ''),
                'user_name': metadata.get('name', ''),
                'user_email': metadata.get('email', '')
            })
        
        # --- Analytics: log user message ---
        intent_info = tracker.latest_message.get('intent', {})
        send_analytics_event('log_message', {
            'session_id': session_id,
            'sender': 'user',
            'message_text': user_message_original,
            'intent': intent_info.get('name'),
            'confidence': intent_info.get('confidence')
        })
        
        bot_response = ""
        
        # How are you? responses (CHECK FIRST - more specific than greeting, more friendly)
        user_question_clean = user_question.replace('?', '').replace('!', '').strip()
        if any(phrase in user_question_clean for phrase in ['how are you', 'comment allez-vous', 'comment vas-tu', 'comment allez vous', 'comment vas tu', 'ça va', 'ca va', 'cómo estás', '如何', 'как дела', 'كيف حالك']):
            # Friendly response with emoji
            if detected_lang == 'fr':
                answer = "Je vais très bien, merci de demander! 😊 Et vous, comment allez-vous? Que souhaitez-vous savoir sur ExpoBeton RDC?"
            elif detected_lang == 'en':
                answer = "I'm doing great, thanks for asking! 😊 And you, how are you? What would you like to know about ExpoBeton RDC?"
            elif detected_lang == 'zh':
                answer = "我很好，谢谢关心！😊 您呢，您好吗？您想了解关于ExpoBeton RDC的什么信息？"
            elif detected_lang == 'ru':
                answer = "У меня все отлично, спасибо, что спросили! 😊 А у вас как дела? Что вы хотите узнать о ExpoBeton RDC?"
            elif detected_lang == 'es':
                answer = "¡Estoy muy bien, gracias por preguntar! 😊 ¿Y usted, cómo está? ¿Qué le gustaría saber sobre ExpoBeton RDC?"
            elif detected_lang == 'ar':
                answer = "أنا بخير، شكراً لسؤالك! 😊 وأنت، كيف حالك؟ ماذا تريد أن تعرف عن ExpoBeton RDC؟"
            else:
                answer = get_multilingual_response('how_are_you', detected_lang)
            
            dispatcher.utter_message(text=answer)
            bot_response = answer
            log_conversation_message(session_id, 'bot', bot_response, metadata)
            return []
        
        # ====================================================================
        # CRITICAL: CHECK SPECIFIC QUESTIONS FIRST (BEFORE GENERIC GREETINGS)
        # A greeting like 'bonjour' can be combined with a question in the same
        # message -- e.g. 'bonjour ou se passera l edition 2026'. Questions MUST
        # be answered, not dismissed as greetings.
        # ====================================================================
        
        # --- Registration category shortcut (conversation-log fix) ---
        # Users often answer the categories menu with "1"/"2"/"3" or a bare
        # category name that NLU classifies as nlu_fallback. When the bot
        # just displayed the categories or proposed registration, launch the
        # form with the matching category instead of apologizing.
        _last_bot_text = ""
        for _evt in reversed(tracker.applied_events()):
            if _evt.get("event") == "bot":
                _last_bot_text = str(_evt.get("text") or "").lower()
                break
        _cat_ctx = any(
            _m in _last_bot_text
            for _m in ("quelle catégorie", "catégorie vous intéresse",
                       "catégories disponibles", "« oui »", "souhaitez-vous")
        )
        if _cat_ctx and len(user_message_original.strip()) <= 40:
            _matched_cat = _match_category_shared(user_message_original)
            if _matched_cat:
                _cat_events = [
                    SlotSet("registration_pending", None),
                    SlotSet("_reg_category_phase", None),
                ]
                if _matched_cat == "_sponsor_":
                    dispatcher.utter_message(text="Excellent ! 🏆 Je démarre votre inscription **Sponsor** — je vous demanderai votre niveau (Platinum / Gold / Silver / Bronze) pendant le formulaire. 🚀")
                    _cat_events.append(SlotSet("_reg_category_phase", "sponsor"))
                elif _matched_cat == "_exposant_":
                    dispatcher.utter_message(text="Excellent ! 🏗️ Je démarre votre inscription **Exposant** — je vous demanderai votre type de stand pendant le formulaire. 🚀")
                    _cat_events.append(SlotSet("_reg_category_phase", "exposant"))
                else:
                    dispatcher.utter_message(text="Excellent choix ! 🚀 Je démarre votre inscription en catégorie **%s**." % _matched_cat)
                    _cat_events.append(SlotSet("reg_category", _matched_cat))
                    if _matched_cat == "Participant Simple":
                        _cat_events.append(SlotSet("reg_payment", "N/A"))
                _cat_events.append(FollowupAction("registration_form"))
                return _cat_events

        # --- Concours Jeunesse Horizon 2050 (CHECK BEFORE LOCATION/DATES) ---
        # The youth contest has its OWN dates (semaine du 14 septembre 2026 for
        # submission, 10 octobre 2026 for the final) different from the general
        # event dates, so it MUST be matched before the generic date/location
        # handlers below.
        concours_keywords = [
            'concours jeunesse', 'concours jeune', 'jeunesse horizon',
            'horizon 2050', 'youth contest', 'youth competition',
            'concours horizon', 'concour jeunesse', 'concour jeune',
            'concours des jeunes', 'competition jeunesse', 'compétition jeunesse'
        ]
        has_concours = any(kw in user_question for kw in concours_keywords)
        # Also accept the broader pattern: ('concours' OR 'competition') + youth context
        if not has_concours:
            has_concours_word = any(w in user_question for w in ['concours', 'compétition', 'competition'])
            has_youth_word = any(w in user_question for w in ['jeunesse', 'jeune', 'jeunes', 'youth', 'horizon 2050', 'horizon2050'])
            has_concours = has_concours_word and has_youth_word

        if has_concours:
            print(f"🏆 [CONCOURS JEUNESSE] DETECTED! user_question={user_question}")

            # Sub-topic routing
            asks_categories = any(w in user_question for w in ['catégorie', 'categorie', 'category', 'categories', 'thématique', 'thematique', 'thème', 'theme', 'domaine', 'domaines'])
            asks_eligibility = any(w in user_question for w in ['éligibilité', 'eligibilite', 'eligibility', 'qui peut', 'qui participe', 'qui participer', 'âge', 'age', 'ans', 'eligible', 'éligible', 'condition', 'conditions', 'requirement', 'requirements', 'critère', 'critere', 'criteres', 'critères'])
            asks_dates = any(w in user_question for w in ['date', 'quand', 'when', 'délai', 'delai', 'deadline', 'calendrier', 'planning'])
            asks_prizes = any(w in user_question for w in ['prix', 'prize', 'prizes', 'gagner', 'gagne', 'récompense', 'recompense', 'awards', 'award', 'avantage', 'avantages', 'lauréat', 'laureat', 'lauréats', 'laureats'])
            asks_submission = any(w in user_question for w in ['soumission', 'soumettre', 'submit', 'submission', 'postuler', 'candidature', 'candidater', 'inscription', 'inscrire', 'apply', 'application', 'dossier', 'comment participer', 'how to participate', 'how to apply', 'how to register'])
            asks_jury = any(w in user_question for w in ['jury', 'juge', 'juges', 'judge', 'judges', 'évaluateur', 'evaluateur', 'évaluation', 'evaluation'])

            if asks_categories:
                answer = (
                    "🏆 **Concours Jeunesse Horizon 2050 — 4 catégories thématiques :**\n\n"
                    "**1️⃣ BTP & Aménagement Durable**\n"
                    "Matériaux locaux / low-cost, construction modulaire / antisismique, urbanisme de Kalemie, sécurisation foncière.\n\n"
                    "**2️⃣ Transformation Minerais & Lithium**\n"
                    "Valorisation locale, traçabilité blockchain, solutions pour les Zones Économiques Spéciales (ZES).\n\n"
                    "**3️⃣ Infrastructures & Corridors**\n"
                    "Logistique multimodale, énergie hydro / solaire, transport durable, infrastructures résilientes.\n\n"
                    "**4️⃣ Agro-Logistique & Économie Verte**\n"
                    "Chaînes de valeur corridors + BTP (entrepôts, transformation, économie verte).\n\n"
                    "🔗 Plus d'infos : https://expobetonrdc.com/concours-jeunesse.html"
                )
            elif asks_eligibility:
                answer = (
                    "🏆 **Concours Jeunesse Horizon 2050 — Éligibilité :**\n\n"
                    "✅ **Équipes de 2 à 5 jeunes** âgés de **18 à 35 ans**.\n"
                    "✅ **Au moins 1 membre** doit être **résidant en RDC**.\n\n"
                    "👥 **Profils acceptés :**\n"
                    "• Étudiants\n"
                    "• Lycéens techniques\n"
                    "• Jeunes du Club BTP & CMA\n"
                    "• MVR (Mouvement des Volontaires de la Reconstruction)\n"
                    "• Artisans\n"
                    "• Entrepreneurs\n\n"
                    "Chaque équipe désigne un **chef d'équipe** comme personne référente.\n\n"
                    "🔗 S'inscrire : https://expobetonrdc.com/concours-jeunesse.html"
                )
            elif asks_dates:
                answer = (
                    "📅 **Concours Jeunesse Horizon 2050 — Dates clés :**\n\n"
                    "• **Soumission des dossiers :** semaine du **14 septembre 2026**\n"
                    "• **Sélection :** 10 projets retenus pour pré-incubation gratuite\n"
                    "• **Pré-incubation :** coaching, formation, appui technique (Club BTP & CMA + partenaires)\n"
                    "• **Finale :** **10 octobre 2026** (Jour 4 d'EXPOBETON RDC) — pitch 5 min + Q&R devant jury\n"
                    "• **Remise des prix :** cérémonie de clôture officielle, **10 octobre 2026**\n\n"
                    "📍 Le concours fait partie de la 12ème édition d'EXPOBETON RDC, du **07 au 10 octobre 2026 à Kinshasa**.\n\n"
                    "🔗 https://expobetonrdc.com/concours-jeunesse.html"
                )
            elif asks_prizes:
                answer = (
                    "🏆 **Concours Jeunesse Horizon 2050 — Prix et avantages :**\n\n"
                    "**🥇 1er prix par catégorie** (4 lauréats principaux)\n"
                    "Kit de démarrage complet : financement + accompagnement 6 mois + formation.\n\n"
                    "**⭐ Prix spéciaux**\n"
                    "• Meilleure innovation lithium / blockchain\n"
                    "• Meilleure solution femme / jeune rural\n"
                    "• Prix de l'impact social\n\n"
                    "**🌐 Visibilité & réseau**\n"
                    "• Stand gratuit à l'édition suivante d'EXPOBETON RDC\n"
                    "• Mise en relation B2B / B2G avec sponsors (PPC BARNET, Great Lakes Cement, LMC...)\n\n"
                    "**🤝 Accompagnement**\n"
                    "• Suivi personnalisé\n"
                    "• Accès aux centres polyvalents des jeunes\n"
                    "• Coaching en management\n\n"
                    "🔗 https://expobetonrdc.com/concours-jeunesse.html"
                )
            elif asks_submission:
                answer = (
                    "📝 **Concours Jeunesse Horizon 2050 — Comment participer :**\n\n"
                    "**1️⃣ Constituer une équipe**\n"
                    "2 à 5 jeunes (18-35 ans), avec au moins 1 membre résidant en RDC.\n\n"
                    "**2️⃣ Préparer le dossier (semaine du 14 septembre 2026)**\n"
                    "• Dossier projet : 5 à 10 pages (PDF)\n"
                    "• Vidéo de pitch : 2 minutes (YouTube, Vimeo, Google Drive...)\n"
                    "• Choisir 1 catégorie parmi 4 (BTP, Lithium, Corridors, Agro-Verte)\n\n"
                    "**3️⃣ Remplir le formulaire en ligne**\n"
                    "Titre, pitch (max 600 caractères), infos chef d'équipe, origine, équipe, engagements.\n\n"
                    "**4️⃣ Attendre la sélection**\n"
                    "10 projets seront retenus pour la pré-incubation, puis la finale du **10 octobre 2026** à Kinshasa.\n\n"
                    "🔗 **S'inscrire :** https://expobetonrdc.com/concours-jeunesse.html"
                )
            elif asks_jury:
                answer = (
                    "⚖️ **Concours Jeunesse Horizon 2050 — Composition du jury :**\n\n"
                    "• Le **Gouverneur** (Ville de Kinshasa)\n"
                    "• Les **Ministres** (Jeunesse, PME, Formation)\n"
                    "• Les représentants du **Club BTP & CMA**\n"
                    "• Les **sponsors BTP**\n"
                    "• Les **experts universitaires** (universités partenaires)\n"
                    "• Les **partenaires techniques**\n\n"
                    "Les finalistes présentent un pitch de 5 minutes + session Q&R le **10 octobre 2026**.\n\n"
                    "🔗 https://expobetonrdc.com/concours-jeunesse.html"
                )
            else:
                # General overview
                answer = (
                    "🏆 **Concours Jeunesse Horizon 2050 — EXPOBETON RDC Kinshasa 2026**\n\n"
                    "\"La jeunesse congolaise ne doit plus seulement rêver le futur, elle doit désormais le construire.\" 🚧\n\n"
                    "📍 **Lieu :** Kinshasa | 📅 **Dates :** 07-10 octobre 2026 (12ème édition)\n\n"
                    "**🎯 3 objectifs :**\n"
                    "1. Encourager l'innovation en architecture, urbanisme, BTP et mining\n"
                    "2. Valoriser les ressources locales de la RDC\n"
                    "3. Créer des emplois durables et stimuler l'entrepreneuriat jeune\n\n"
                    "**📚 4 catégories thématiques :**\n"
                    "1️⃣ BTP & Aménagement Durable\n"
                    "2️⃣ Transformation Minerais & Lithium\n"
                    "3️⃣ Infrastructures & Corridors\n"
                    "4️⃣ Agro-Logistique & Économie Verte\n\n"
                    "**👥 Éligibilité :** équipes de 2 à 5 jeunes (18-35 ans), dont au moins 1 résidant en RDC.\n\n"
                    "**📝 Soumission :** semaine du 14 septembre 2026 (dossier 5-10 pages + vidéo 2 min)\n"
                    "**🎤 Finale :** 10 octobre 2026, pitch 5 min devant jury\n\n"
                    "**🏆 Prix :** kit de démarrage (financement + coaching 6 mois), stand gratuit édition suivante, mise en relation B2B/B2G.\n\n"
                    "💡 Demandez-moi : *catégories*, *éligibilité*, *dates*, *prix*, *soumission* ou *jury*.\n\n"
                    "🔗 **S'inscrire :** https://expobetonrdc.com/concours-jeunesse.html"
                )

            dispatcher.utter_message(text=answer)
            bot_response = answer
            log_conversation_message(session_id, 'bot', bot_response, metadata)
            return []

        # --- Location questions (CHECK VERY EARLY -- often combined with greeting) ---
        location_keywords = [
            'lieu', 'lieux', 'location', 'address', 'adresse',
            'se passe', 'se passera', 'se tiendra', 'se deroule',
            'se deroulera', 'se tient', 'organise', 'organisee',
            'where', 'venue'
        ]
        # Also check for 'ou' or 'ou' (where) but only if combined with context
        has_where_word = any(kw in user_question for kw in location_keywords)
        has_ou = any(w in user_question for w in [' ou ', ' ou', 'ou ', 'ou?', 'ou?'])
        has_location_context = any(w in user_question for w in [
            'se passera', 'se passe', 'se tiendra', 'se tient', 'edition', 'edtion', 'editon',
            'expobeton', 'salon', 'evenement', '2026', 'prochain'
        ])
        if has_where_word or (has_ou and has_location_context):
            # Meme correction que dans l'action de salutation : cette seconde copie
            # codee en dur situait le salon au 07, avenue de l'OUA (Ngaliema), qui
            # est le secretariat de l'ASBL. Le lieu reel est a la Gombe (index.php,
            # ligne 275). Deux exemplaires de la meme reponse existaient donc, dont
            # un seul avait ete corrige : la verification en production ne suffit
            # pas, il faut balayer le contenu, pas seulement un chemin d'entree.
            answer = (
                "📍 **Lieu précis — ExpoBeton RDC 2026 (12ème édition) :**\n\n"
                "Le salon se tient à **The Grand Residence — Galerie La Fontaine**, "
                "au **croisement des avenues des Cliniques et Batetela**, commune de "
                "la **Gombe**, à **Kinshasa**, capitale de la RDC.\n\n"
                "🏛️ C'est là que se déroulent l'exposition, les conférences, les "
                "panels, les rendez-vous B2B/B2G et les cérémonies d'ouverture et "
                "de clôture.\n\n"
                "🏢 **Secrétariat / adresse administrative** d'EXPO BÉTON ASBL : "
                "**07, avenue de l'OUA, commune de Ngaliema**, Kinshasa.\n"
                "⚠️ Attention : le secrétariat n'est **pas** le lieu du salon.\n\n"
                "🕘 **Horaires sur le site :** 09h00 – 15h30.\n\n"
                "📅 Dates : du **07 au 10 octobre 2026** (4 jours)."
            )
            dispatcher.utter_message(text=answer)
            bot_response = answer
            log_conversation_message(session_id, 'bot', bot_response, metadata)
            return []
        
        # --- Date questions (often combined with greeting too) ---
        if any(kw in user_question for kw in ['date', 'quand', 'when', 'calendrier', 'duree', 'combien de jours', 'period']):
            if any(w in user_question for w in ['expobeton', 'salon', 'edition', 'edtion', 'editon', 'evenement', '2026']):
                answer = (
                    "La 12eme edition d'ExpoBeton RDC se tiendra du **07 au 10 octobre 2026** "
                    "(4 jours) a **Kinshasa**, a La Grande Residence - Galerie La Fontaine.\n\n"
                    "Programme resume :\n"
                    "• Mer 07 oct : Journee Portes Ouvertes, Touristique et Culturelle\n"
                    "• Jeu 08 oct : Ouverture officielle + Panels Habitat & Territoire\n"
                    "• Ven 09 oct : Corridors transfrontaliers, ZES, Energie\n"
                    "• Sam 10 oct : Jeunesse & Innovation + CLOTURE"
                )
                dispatcher.utter_message(text=answer)
                bot_response = answer
                log_conversation_message(session_id, 'bot', bot_response, metadata)
                return []
        
        # --- Theme questions ---
        if any(kw in user_question for kw in ['theme', 'sujet', 'topic', 'tema']):
            if any(w in user_question for w in ['edition', 'edtion', 'editon', '2026', 'expobeton', 'salon']):
                answer = (
                    "Le theme de la 12eme edition (2026) est : "
                    "**Kinshasa, Locomotive de la Transformation des Villes "
                    "de la RDC.**\n\n"
                    "Cette edition est consacree au role moteur de Kinshasa et met en lumiere "
                    "la transformation urbaine et les infrastructures."
                )
                dispatcher.utter_message(text=answer)
                bot_response = answer
                log_conversation_message(session_id, 'bot', bot_response, metadata)
                return []
        
        # History of ExpoBeton - CHECK BEFORE "HI" TO AVOID "HISTOIRE" COLLISION!
        if any(word in user_question for word in ['histoire', 'history', 'historique']):
            print(f"✅✅✅ [DEBUG] HISTOIRE CHECK MATCHED! user_question={user_question}")
            answer = "📜 **Histoire d'ExpoBeton RDC**\n\n🚀 **Création:** 2016 par Jean Bamanisa Saïdi\n\n🎯 **Mission:** Promouvoir les infrastructures, la construction et le développement urbain en RDC\n\n🏆 **Évolution:**\n• 2016-2022: Éditions à Kinshasa (focus capital)\n• 2023: Expansion vers Kolwezi (mines, Grand Katanga)\n• 2024: Double phase Kinshasa + Matadi (corridor ouest)\n• Avril 2026 (11e): Grand Katanga — Lubumbashi (+ étapes Kalemie et Kolwezi)\n• Octobre 2026 (12e): Kinshasa, du 07 au 10 octobre\n\n💡 **Impact:**\n• Création du Ministère de la Politique de la Ville (2024)\n• Recommandations adoptées par le gouvernement\n• Plateforme B2B, B2G majeure en RDC\n• Think tanks thématiques annuels\n\n👥 **Fondateurs:** Jean Bamanisa Saïdi (Président) + Momo Sungunza (Vice-Président)"
            dispatcher.utter_message(text=answer)
            bot_response = answer
            log_conversation_message(session_id, 'bot', bot_response, metadata)
            return []
        
        # Which edition are we on? - "quelle edition", "c'est quelle edtion", etc. (with typo support)
        if any(word in user_question for word in ['édition', 'edition', 'edtion', 'editon', 'ediiton', 'ediition']):
            # "how many editions" pattern - check first (more specific)
            if any(word in user_question for word in ['combien', 'how many', 'nombre']):
                answer = "**11 editions** d'ExpoBeton RDC ont deja ete organisees depuis 2016 :\n\n1. 2016 : 1ere edition - Kinshasa\n2. 2017 : 2eme edition - Kinshasa\n3. 2018 : 3eme edition - Kinshasa\n4. 2019 : 4eme edition - Kinshasa\n5. 2021 : 5eme edition - Kinshasa\n6. 2022 : 6eme edition - Kinshasa\n7. 2023 : 7eme edition - Kolwezi (Lualaba)\n8. 2024 : 8eme edition - Kinshasa + Matadi\n9. 2025 : 9eme edition - Kinshasa\n10. 2025 : 10eme edition - Kinshasa\n\n11. 2026 : 11eme edition - Grand Katanga (Lubumbashi, satellites Kalemie & Kolwezi)\n\nLa **12eme edition** aura lieu du **07 au 10 octobre 2026 a Kinshasa**."
                dispatcher.utter_message(text=answer)
                bot_response = answer
                log_conversation_message(session_id, 'bot', bot_response, metadata)
                return []
            # Default: assume user is asking which edition (most common question)
            answer = "Nous sommes a la **12eme edition** d'ExpoBeton RDC ! Elle se tiendra du **07 au 10 octobre 2026** a **Kinshasa**, a La Grande Residence - Galerie La Fontaine.\n\nLe theme : **Kinshasa, Locomotive de la Transformation des Villes de la RDC.**\n\n(La 11eme edition s'est tenue dans le Grand Katanga - Lubumbashi, avec etapes satellites a Kalemie et Kolwezi.)"
            dispatcher.utter_message(text=answer)
            bot_response = answer
            log_conversation_message(session_id, 'bot', bot_response, metadata)
            return []
        
        # Greetings and politeness responses (FRIENDLY with emojis)
        if any(word in user_question for word in ['bonjour', 'salut', 'hello', 'hi', 'bonsoir', 'hola', 'привет', '你好', 'مرحبا']):
            print(f"🔥🔥🔥 [ANSWER_EXPOBETON DEBUG] GREETING CHECK MATCHED! user_question={user_question}")
            # Extract user's name if provided
            user_name = None
            import re
            name_patterns = [
                r"je m['\u2019]appelle\s+([A-Za-zÀ-ÿ]+(?:\s+[A-Za-zÀ-ÿ]+)*)",  # French - capture name with spaces
                r"my name is\s+([A-Za-z]+(?:\s+[A-Za-z]+)*)",  # English - capture name with spaces
                r"i['\u2019]m\s+([A-Za-z]+(?:\s+[A-Za-z]+)*)",  # English - capture name with spaces
                r"me llamo\s+([A-Za-z]+(?:\s+[A-Za-z]+)*)",  # Spanish - capture name with spaces
            ]
            for pattern in name_patterns:
                match = re.search(pattern, user_message_original, re.IGNORECASE)
                if match:
                    user_name = match.group(1).strip().title()
                    break
            
            # Build personalized greeting with FRIENDLY tone and emoji
            if user_name and detected_lang == 'fr':
                answer = f"Bonjour {user_name}! 😊 Enchanté de faire votre connaissance! Comment allez-vous? Qu'aimeriez-vous savoir sur ExpoBeton RDC?"
            elif user_name and detected_lang == 'en':
                answer = f"Hello {user_name}! 😊 Nice to meet you! How are you doing? What would you like to know about ExpoBeton RDC?"
            else:
                # Add emoji to generic greeting
                base_answer = get_multilingual_response('greeting', detected_lang)
                if detected_lang == 'fr':
                    answer = base_answer.replace("Bonjour!", "Bonjour! 😊")
                elif detected_lang == 'en':
                    answer = base_answer.replace("Hello!", "Hello! 😊")
                else:
                    answer = base_answer
            
            dispatcher.utter_message(text=answer)
            bot_response = answer
            
            # Language-specific suggestions (only if no name given)
            if not user_name:
                if detected_lang == 'fr':
                    suggestion = "\n💡 Vous pourriez me demander:\n• C'est quoi ExpoBeton?\n• Quelles sont les dates?\n• Comment devenir ambassadeur?"
                elif detected_lang == 'en':
                    suggestion = "\n💡 You could ask me:\n• What is ExpoBeton?\n• What are the dates?\n• How to become an ambassador?"
                elif detected_lang == 'zh':
                    suggestion = "\n💡 您可以问我：\n• 什么是ExpoBeton？\n• 日期是什么时候？\n• 如何成为大使？"
                elif detected_lang == 'ru':
                    suggestion = "\n💡 Вы можете спросить меня:\n• Что такое ExpoBeton?\n• Какие даты?\n• Как стать послом?"
                elif detected_lang == 'es':
                    suggestion = "\n💡 Podría preguntarme:\n• ¿Qué es ExpoBeton?\n• ¿Cuáles son las fechas?\n• ¿Cómo convertirse en embajador?"
                elif detected_lang == 'ar':
                    suggestion = "\n💡 يمكنك أن تسألني:\n• ما هو ExpoBeton؟\n• ما هي التواريخ؟\n• كيف تصبح سفيرا؟"
                else:
                    suggestion = "\n💡 Vous pourriez me demander:\n• C'est quoi ExpoBeton?\n• Quelles sont les dates?\n• Comment devenir ambassadeur?"
                dispatcher.utter_message(text=suggestion)
                bot_response += suggestion
            
            log_conversation_message(session_id, 'bot', bot_response, metadata)
            return []
        
        # Thank you responses
        if any(word in user_question for word in ['merci', 'thanks', 'thank you', 'thank', 'danke', 'gracias', 'спасибо', 'شكرا']):
            answer = get_multilingual_response('thank_you', detected_lang)
            dispatcher.utter_message(text=answer)
            bot_response = answer
            log_conversation_message(session_id, 'bot', bot_response, metadata)
            return []
        
        # Registration / Participation (CHECK BEFORE GOODBYE!)
        if any(word in user_question for word in ['inscription', 'register', 'participer', 'participate', 'subscribe', 'join', 'enroll', 'comment participer']):
            answer = get_multilingual_response('registration', detected_lang)
            dispatcher.utter_message(text=answer)
            bot_response = answer
            log_conversation_message(session_id, 'bot', bot_response, metadata)
            return []
        
        # Goodbye responses (CHECK LAST - be more specific!)
        # Exclude messages with 'oui' or 'comment' that might be questions
        is_goodbye = any(word in user_question for word in ['au revoir', 'bye', 'goodbye', 'à bientôt', 'adieu', 'ciao', 'adiós', 'пока', '再见', 'مع السلامة'])
        is_question = any(word in user_question for word in ['oui', 'comment', 'qui', 'quoi', 'où', 'quand', 'pourquoi'])
        
        if is_goodbye and not is_question:
            answer = get_multilingual_response('goodbye', detected_lang)
            dispatcher.utter_message(text=answer)
            bot_response = answer
            log_conversation_message(session_id, 'bot', bot_response, metadata)
            # Send conversation email
            if session_id in CONVERSATION_LOGS:
                conversation = CONVERSATION_LOGS[session_id]
                if len(conversation['messages']) > 0:
                    send_conversation_email(
                        session_id,
                        conversation['user_info'],
                        conversation['messages']
                    )
            return []
        
        # ====================================================================
        # CRITICAL: CHECK SPECIFIC QUESTIONS FIRST (BEFORE GENERIC "WHAT IS")
        # ====================================================================
        
        # History of ExpoBeton - CHECK FIRST TO AVOID "WHAT IS" COLLISION
        if any(word in user_question for word in ['histoire', 'history', 'historique']):
            print(f"\u2705\u2705\u2705 [DEBUG] HISTOIRE CHECK MATCHED! user_question={user_question}")
            answer = "📜 **Histoire d'ExpoBeton RDC**\n\n🚀 **Création:** 2016 par Jean Bamanisa Saïdi\n\n🎯 **Mission:** Promouvoir les infrastructures, la construction et le développement urbain en RDC\n\n🏆 **Évolution:**\n• 2016-2022: Éditions à Kinshasa (focus capital)\n• 2023: Expansion vers Kolwezi (mines, Grand Katanga)\n• 2024: Double phase Kinshasa + Matadi (corridor ouest)\n• Avril 2026 (11e): Grand Katanga — Lubumbashi (+ étapes Kalemie et Kolwezi)\n• Octobre 2026 (12e): Kinshasa, du 07 au 10 octobre\n\n💡 **Impact:**\n• Création du Ministère de la Politique de la Ville (2024)\n• Recommandations adoptées par le gouvernement\n• Plateforme B2B, B2G majeure en RDC\n• Think tanks thématiques annuels\n\n👥 **Fondateurs:** Jean Bamanisa Saïdi (Président) + Momo Sungunza (Vice-Président)"
            dispatcher.utter_message(text=answer)
            bot_response = answer
            log_conversation_message(session_id, 'bot', bot_response, metadata)
            return []
        
        # (Edition check already handled earlier - removed duplicate)
        
        # ANY mention of Lubumbashi - ULTRA BROAD MATCH (no conditions!)
        # Match ANY variation of Lubumbashi, with or without question mark
        # Common typos: lubumabshi, lubumbachi, loubumbashi, etc.
        lubumbashi_variants = ['lubumbashi', 'lubumabshi', 'lubumbachi', 'loubumbashi', 'lubumbash', 'lumumbashi']
        
        # If ANY variant is mentioned, answer immediately!
        for variant in lubumbashi_variants:
            if variant in user_question:
                print(f"🔥🔥🔥 [DEBUG LUBUMBASHI] DETECTED (variant={variant})! user_question={user_question}")
                answer = "ℹ️ La **12ème édition d'ExpoBeton RDC (07-10 octobre 2026)** se tiendra à **Kinshasa**, à La Grande Résidence — Galerie La Fontaine (Gombe).\n\n**Lubumbashi** a accueilli la **11ème édition** (avril 2026, volet Grand Katanga), avec des étapes satellites à Kalemie et Kolwezi : cette édition s'est concentrée sur le Grand Katanga comme carrefour stratégique des corridors africains du Sud, de l'Ouest et de l'Est, avec un potentiel énorme en infrastructures grâce aux réserves de cuivre, cobalt et lithium de la région."
                dispatcher.utter_message(text=answer)
                bot_response = answer
                log_conversation_message(session_id, 'bot', bot_response, metadata)
                return []
        
        # ====================================================================
        # END CRITICAL CHECKS - NOW PROCEED TO OTHER CHECKS
        # ====================================================================
        
        # Ambassador questions - MULTILINGUAL SUPPORT
        if any(word in user_question for word in ['ambassadeur', 'ambassador', 'devenir', 'rejoindre', 'become']):
            # Check if we have multilingual content for ambassador
            if detected_lang == 'en':
                answer = "To become an ExpoBeton RDC Ambassador:\n\n✅ Membership is by selection\n✅ Apply online at https://expobetonrdc.com/\n\nProfiles sought:\n• Technical and scientific experts\n• Opinion leaders and influencers\n• Construction professionals\n• Innovative entrepreneurs\n• Academics and researchers\n\nAs an Ambassador, you participate in thematic Think Tanks, contribute to reconstruction policies, and benefit from a national and international network of influence."
                suggestion = "\n💡 You might also ask:\n• What is ExpoBeton?\n• What are the event dates?\n• Who are the founders?"
            else:  # French (default)
                answer = "Pour devenir Ambassadeur d'Expo Béton RDC :\n\n✅ L'adhésion se fait sur sélection\n✅ Postulez en ligne sur https://expobetonrdc.com/\n\nProfils recherchés :\n• Experts techniques et scientifiques\n• Leaders d'opinion et influenceurs\n• Professionnels du BTP\n• Entrepreneurs innovants\n• Universitaires et chercheurs\n\nEn tant qu'Ambassadeur, vous participez aux Think Tanks thématiques, contribuez aux politiques de reconstruction, et bénéficiez d'un réseau d'influence national et international."
                suggestion = "\n💡 Vous pourriez aussi me demander :\n• C'est quoi ExpoBeton ?\n• Quelles sont les dates de l'événement ?\n• Qui sont les fondateurs ?"
            
            dispatcher.utter_message(text=answer)
            bot_response = answer
            dispatcher.utter_message(text=suggestion)
            bot_response += suggestion
            log_conversation_message(session_id, 'bot', bot_response, metadata)
            return []
        
        # Skip LLM for very short/vague queries (< 15 chars) — respond instantly
        if len(user_question.strip()) < 15:
            print(f"⚡ Query too short/vague for LLM ({len(user_question.strip())} chars) - skipping to instant fallback")
        else:
            # Try to find relevant documents using OpenAI for substantive questions
            # TOTAL TIMEOUT: 8 seconds for the entire LLM pipeline (search + generation)
            def _llm_answer():
                docs = find_relevant_docs(tracker.latest_message.get('text', ''), 3)
                if not docs:
                    return None
                # Prepare context
                context_parts = []
                for i, doc in enumerate(docs):
                    budget = (CANONICAL_PROMPT_CHARS
                              if doc['filename'].lower().startswith(CANONICAL_PREFIX)
                              else LEGACY_PROMPT_CHARS)
                    content = doc['content'][:budget]
                    context_parts.append(f"Document {i+1} ({doc['filename']}):\n{content}")
                context = "\n\n".join(context_parts)
                # Call GPT-4o with timeout parameter
                resp = _openai_client().chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "Tu es un assistant intelligent pour ExpoBeton RDC. Réponds de manière précise et concise en français, en te basant UNIQUEMENT sur les documents fournis. Si l'information n'est pas dans les documents, dis-le clairement. Utilise des emojis et une mise en forme claire (bullet points, numéros) pour rendre la réponse facile à lire."},
                        {"role": "user", "content": f"Question: {user_message_original}\n\nDocuments de référence:\n{context}"}
                    ],
                    temperature=0.3,
                    max_tokens=500,
                    timeout=OPENAI_TIMEOUT
                )
                answer = resp.choices[0].message.content.strip()
                if len(answer) > 50 and 'ne sais pas' not in answer.lower() and 'ne peux pas' not in answer.lower():
                    return answer
                return None
            
            try:
                # _LLM_EXECUTOR est partagé au niveau du module (voir sa
                # définition). L'ancien code utilisait
                # `with ThreadPoolExecutor(max_workers=1) as executor:` :
                # la sortie du bloc appelait shutdown(wait=True), qui attend la
                # fin du thread, donc le future.result(timeout=8) était
                # purement décoratif. À l'expiration du délai on affichait
                # « returning fallback immediately », puis on bloquait quand
                # même sur l'appel qui venait d'expirer — jusqu'à son propre
                # délai réseau, qui était le défaut du client OpenAI (600 s).
                # Il n'y a plus de bloc `with`, donc plus rien n'attend : le
                # budget est réellement opposable, et la tâche abandonnée reste
                # bornée par OPENAI_TIMEOUT côté client.
                future = _LLM_EXECUTOR.submit(_llm_answer)
                try:
                    llm_answer = future.result(timeout=LLM_TOTAL_TIMEOUT)
                except FuturesTimeoutError:
                    print(f"⏰ LLM pipeline timed out after {LLM_TOTAL_TIMEOUT:.0f} seconds - returning fallback immediately")
                    future.cancel()
                    llm_answer = None
                
                if llm_answer:
                    print(f"✅ LLM generated answer: {llm_answer[:100]}...")
                    dispatcher.utter_message(text=llm_answer)
                    bot_response = llm_answer
                    log_conversation_message(session_id, 'bot', bot_response, metadata)
                    return []
            except Exception as e:
                print(f"❌ LLM pipeline error: {e}")
        
        # Default: show help and log unanswered question
        if any(word in user_question for word in ['fondateur', 'créateur', 'président', 'qui est', 'qui sont', 'responsable', 'organisateur', 'organise', 'dirige', 'tête', 'qui a créé', 'qui a fondé']):
            if 'jean' in user_question or 'bamanisa' in user_question or 'fondateur' in user_question or 'créateur' in user_question:
                answer = "Jean Bamanisa Saïdi est le président, promoteur, créateur et fondateur d'ExpoBeton RDC. C'est un homme d'affaires et personnalité politique congolaise, ancien gouverneur de la province de l'Ituri. Il porte la vision stratégique de l'événement et met en avant la reconstruction, l'urbanisation et le développement durable de la RDC."
                dispatcher.utter_message(text=answer)
                suggestion = "\n💡 Vous pourriez aussi demander :\n• Qui est le vice-président ?\n• Comment devenir ambassadeur ?\n• Quelles sont les dates de l'événement ?"
                dispatcher.utter_message(text=suggestion)
                log_conversation_message(session_id, 'bot', answer, metadata)
                return []
            if 'momo' in user_question or 'sungunza' in user_question or 'vice' in user_question:
                answer = "Momo Sungunza est le vice-président d'ExpoBeton RDC. Il assure la coordination opérationnelle et organisationnelle du forum, et travaille en tandem avec Jean Bamanisa pour mobiliser les partenaires publics et privés."
                dispatcher.utter_message(text=answer)
                suggestion = "\n💡 Vous pourriez aussi demander :\n• Qui est le fondateur ?\n• C'est quoi le thème de l'édition 2025 ?\n• Comment participer ?"
                dispatcher.utter_message(text=suggestion)
                log_conversation_message(session_id, 'bot', answer, metadata)
                return []
            # Generic: who runs / who is responsible / who organizes ExpoBeton
            if detected_lang == 'fr':
                answer = "ExpoBeton RDC est dirigé par :\n\n👤 **Jean Bamanisa Saïdi** — Président, promoteur, créateur et fondateur d'ExpoBeton RDC. Homme d'affaires et personnalité politique congolaise, ancien gouverneur de la province de l'Ituri.\n\n👤 **Momo Sungunza** — Vice-président d'ExpoBeton RDC. Il assure la coordination opérationnelle et organisationnelle du forum."
            else:
                answer = "ExpoBeton RDC is led by:\n\n👤 **Jean Bamanisa Saïdi** — President, promoter, creator and founder of ExpoBeton RDC. Congolese businessman and political figure, former governor of Ituri province.\n\n👤 **Momo Sungunza** — Vice-president of ExpoBeton RDC. He manages the operational and organizational coordination of the forum."
            dispatcher.utter_message(text=answer)
            suggestion = "\n💡 Vous pourriez aussi demander :\n• Comment devenir ambassadeur ?\n• Quelles sont les dates de l'événement ?\n• Comment participer ?"
            dispatcher.utter_message(text=suggestion)
            log_conversation_message(session_id, 'bot', answer, metadata)
            return []
        
        # What is ExpoBeton (handle typos like 'expbeton', 'expo beton')
        if any(word in user_question for word in ['quoi', 'what', 'est-ce', 'c\'est', 'qué', '什么', 'что', 'ما']):
            # Check for 'grand katanga' FIRST
            if 'grand katanga' in user_question or 'katanga' in user_question:
                if detected_lang == 'fr':
                    answer = "Le Grand Katanga est une région stratégique de la RDC comprenant trois provinces : Haut-Katanga (capitale Lubumbashi), Lualaba (capitale Kolwezi) et Tanganyika (capitale Kalemie). Cette région représente environ 70% des exportations nationales grâce à ses réserves de cobalt et de cuivre.\n\n📜 Le Grand Katanga était le thème de la **11ème édition** d'ExpoBeton RDC (Lubumbashi, avec étapes satellites à Kalemie et Kolwezi). La **12ème édition** se tient à **Kinshasa du 07 au 10 octobre 2026**, sous le thème « Kinshasa, Locomotive de la Transformation des Villes de la RDC »."
                else:
                    answer = "Grand Katanga is a strategic region of the DRC comprising three provinces: Haut-Katanga (capital Lubumbashi), Lualaba (capital Kolwezi) and Tanganyika (capital Kalemie). The region accounts for around 70% of national exports thanks to its cobalt and copper reserves.\n\n📜 Grand Katanga was the theme of the **11th edition** of ExpoBeton RDC (Lubumbashi, with satellite stops in Kalemie and Kolwezi). The **12th edition** takes place in **Kinshasa from October 7 to 10, 2026**, under the theme 'Kinshasa, Locomotive of the Transformation of DRC Cities'."
                dispatcher.utter_message(text=answer)
                bot_response = answer
                log_conversation_message(session_id, 'bot', bot_response, metadata)
                return []
            # Check for 'expobeton' or common typos like 'expbeton'
            if 'expobeton' in user_question or 'expbeton' in user_question or 'expo beton' in user_question or 'expo béton' in user_question:
                answer = get_multilingual_response('what_is_expobeton', detected_lang)
                dispatcher.utter_message(text=answer)
                bot_response = answer
                log_conversation_message(session_id, 'bot', bot_response, metadata)
                return []
        
        # Dates
        if any(word in user_question for word in ['date', 'when', 'quand', 'cuándo', 'когда', '什么时候', 'متى']):
            answer = get_multilingual_response('dates', detected_lang)
            dispatcher.utter_message(text=answer)
            bot_response = answer
            log_conversation_message(session_id, 'bot', bot_response, metadata)
            return []
        
        # Location
        if any(word in user_question for word in ['lieu', 'where', 'où', 'dónde', 'где', '哪里', 'أين']):
            answer = get_multilingual_response('location', detected_lang)
            dispatcher.utter_message(text=answer)
            bot_response = answer
            log_conversation_message(session_id, 'bot', bot_response, metadata)
            return []
        
        # Ambassador questions - MULTILINGUAL SUPPORT (moved earlier - see line 646)
        
        # Duration / Number of days
        if any(word in user_question for word in ['combien de jours', 'durée', 'how many days', 'duration']):
            answer = (
                "📅 La **12ème édition d'ExpoBeton RDC** durera **4 jours** : "
                "du **mercredi 07 au samedi 10 octobre 2026**, à Kinshasa "
                "(The Grand Residence — Galerie La Fontaine, Gombe).\n\n"
                "🕘 Horaires sur le site : **09h00 – 15h30**.\n"
                "🌆 Activités hors site : **16h00 – 19h15**, du **06 au 11 octobre 2026**.\n\n"
                "**Jour 1 (mer 07)** : Journée Portes Ouvertes, Touristique et Culturelle\n"
                "**Jour 2 (jeu 08)** : Cérémonie d'ouverture officielle + panels Habitat & Territoire\n"
                "**Jour 3 (ven 09)** : Corridors transfrontaliers, ZES, Énergie\n"
                "**Jour 4 (sam 10)** : Jeunesse & Innovation + cérémonie de clôture"
            )
            dispatcher.utter_message(text=answer)
            bot_response = answer
            log_conversation_message(session_id, 'bot', bot_response, metadata)
            return []
        
        # Why Lubumbashi in 2026? - DUPLICATE CHECK REMOVED (moved to line 644)
        
        # Cities of Grand Katanga
        if any(word in user_question for word in ['villes', 'quelles villes', 'cities', 'which cities']):
            if 'grand katanga' in user_question or 'katanga' in user_question:
                answer = "Les trois villes principales du Grand Katanga sont :\n\n1️⃣ **Lubumbashi** (capitale du Haut-Katanga) - centre économique et industriel\n2️⃣ **Kolwezi** (capitale du Lualaba) - capitale mondiale du cobalt\n3️⃣ **Kalemie** (capitale du Tanganyika) - port stratégique sur le lac Tanganyika\n\nCes trois villes sont les piliers du développement régional au cœur d'ExpoBeton 2026."
                dispatcher.utter_message(text=answer)
                bot_response = answer
                log_conversation_message(session_id, 'bot', bot_response, metadata)
                return []
        
        # Kolwezi
        if 'kolwezi' in user_question:
            answer = "Kolwezi est la capitale de la province du Lualaba et l'une des trois villes clés du Grand Katanga. Elle est connue comme la **capitale mondiale du cobalt** grâce à ses réserves immenses. Kolwezi joue un rôle stratégique dans l'industrie minière de la RDC et est un pilier majeur du développement économique de la région, au cœur du thème d'ExpoBeton 2026."
            dispatcher.utter_message(text=answer)
            bot_response = answer
            log_conversation_message(session_id, 'bot', bot_response, metadata)
            return []
        
        # Kalemie
        if 'kalemie' in user_question:
            answer = "Kalemie est la capitale de la province du Tanganyika et l'une des trois villes clés du Grand Katanga. C'est un **port stratégique** sur le lac Tanganyika, reliant la RDC aux corridors africains de l'Est. Kalemie est essentielle pour le transport et le commerce régional, faisant partie intégrante du thème d'ExpoBeton 2026 : 'Grand Katanga : Carrefour Stratégique'."
            dispatcher.utter_message(text=answer)
            bot_response = answer
            log_conversation_message(session_id, 'bot', bot_response, metadata)
            return []
        
        # KAMOA (mining project)
        if 'kamoa' in user_question:
            answer = "KAMOA-KAKULA est l'un des plus grands projets de cuivre au monde, situé dans la province du Lualaba (Grand Katanga). Développé par Ivanhoe Mines, ce projet a été présenté lors d'ExpoBeton comme un exemple majeur du potentiel minier de la région. KAMOA contribue significativement aux 70% des exportations nationales que représente le Grand Katanga."
            dispatcher.utter_message(text=answer)
            bot_response = answer
            log_conversation_message(session_id, 'bot', bot_response, metadata)
            return []
        
        # Presidential speech 2024
        if any(word in user_question for word in ['président', 'president', 'discours', 'speech']) and ('2024' in user_question or 'dit' in user_question or 'said' in user_question or 'ouverture' in user_question or 'opening' in user_question):
            answer = "Lors de l'ouverture d'ExpoBeton 2024 (8ème édition), le Président Félix Tshisekedi a souligné plusieurs points clés :\n\n🏆 **Thème 2024:** 'Révolution urbaine et solutions durables du corridor ouest pour Kinshasa et Kongo-Central'\n\n🛣️ **3 Engagements majeurs:**\n1️⃣ Création d'un **ministère dédié à la politique de la ville**\n2️⃣ **Désenclavement des territoires** comme priorité absolue (initiative présidentielle)\n3️⃣ **Partenariats publics-privés** pour les infrastructures\n\n🏛️ **Vision:** Faire du secteur de la construction un **levier majeur de transformation économique**, garantir l'égalité d'accès aux services de base pour tous les Congolais.\n\nLe Président a déclaré : 'La question du désenclavement de nos territoires est une priorité absolue pour moi, car elle touche directement à l'égalité des chances pour tous.'"
            dispatcher.utter_message(text=answer)
            bot_response = answer
            log_conversation_message(session_id, 'bot', bot_response, metadata)
            return []
        
        # Rapport final 2024
        if any(word in user_question for word in ['rapport', 'report']) and '2024' in user_question:
            answer = "📊 **Rapport Final ExpoBeton 2024 (8ème édition)** \n\n✅ **Deux phases:**\n• Phase 1: Kinshasa (10-12 sept 2024)\n• Phase 2: Matadi, Kongo-Central (18-19 sept 2024)\n\n🎯 **Thème:** 'Révolution urbaine : Des solutions durables du corridor ouest pour Kinshasa et Kongo-Central'\n\n📈 **Chiffres clés:**\n• 200+ participants (experts, décideurs, entreprises)\n• 5 sessions thématiques\n• Concours étudiants avec 5 universités\n• Expositions et stands d'entreprises\n\n💡 **Recommandations majeures:**\n• Modernisation des infrastructures routières et portuaires\n• Création de cités satellites le long de la rocade\n• PPP pour financement des projets\n• Gestion durable des déchets\n\nPour plus de détails, consultez le rapport complet sur https://expobetonrdc.com/"
            dispatcher.utter_message(text=answer)
            bot_response = answer
            log_conversation_message(session_id, 'bot', bot_response, metadata)
            return []
        
        # What happened in 2023
        if ('2023' in user_question or 'sept' in user_question) and any(word in user_question for word in ['passé', 'happened', 'edition', 'édition']):
            answer = "🏆 **ExpoBeton 2023 (7ème édition) - Kolwezi, Lualaba**\n\n📍 **Lieu:** Kolwezi\n🎯 **Thème:** 'Kolwezi-Lualaba, Eldorado du corridor sud de la RDC-SADC'\n\n👥 **Intervenants clés:**\n• TFM (Tenke Fungurume Mining) - Edouard Swana\n• FONER - Pierre Bundoki (DG)\n• CAMI - Popol Mabolia Yenga (DG)\n• KAMOA - Guy Muswil\n• Ministre de l'Industrie - Julien Paluku\n\n💎 **Focus minier:** Exploitation minière responsable, protection environnementale, développement communautaire, cobalt et cuivre\n\n📊 **Résultats:** Recommandations sur RSE, corridors de développement, zones économiques spéciales"
            dispatcher.utter_message(text=answer)
            bot_response = answer
            log_conversation_message(session_id, 'bot', bot_response, metadata)
            return []
        
        # Types of stands
        # Cette reponse inventait trois paliers (« Stand Premium 12m² minimum »,
        # « Stand Standard 6m²-9m² », « Stand Startup/PME 3m²-6m² ») qui n'existent
        # nulle part sur le site et ne donnaient AUCUN prix. Elle se declenchait sur
        # tout message contenant « stand » ou « types » — y compris « Stand 2×3m »,
        # qui devait pourtant resoudre la categorie directement. Remplacee par le
        # catalogue reel (actions_expobeton.py, show_categories) : deux formats
        # exposant seulement, le 2×4m etant retire, plus les stands inclus dans les
        # paliers de sponsoring.
        if any(word in user_question for word in ['stand', 'stands', 'types']) and not any(word in user_question for word in ['meilleur', 'best']):
            answer = (
                "🎪 **Stands ExpoBeton RDC 2026 — catalogue réel**\n\n"
                "🏗️ **Exposant (stands du site principal) :**\n"
                "   • Stand 3×3m — 9 m² — **5.000 $** (2 pass délégués, 30 places)\n"
                "   • Stand 2×3m — 6 m² — **3.500 $** (1 pass délégué, 5 places)\n"
                "ℹ️ Le **stand 2×4m n'est plus proposé** pour l'édition 2026.\n\n"
                "🏆 **Sponsor (stand inclus dans le palier) :**\n"
                "   • Platinum — 40.000 $ (stand 45 m², 5 pass)\n"
                "   • Gold — 20.000 $ (stand 20 m², 3 pass)\n"
                "   • Bronze — 15.000 $ (stand 15 m², 2 pass)\n"
                "   • Silver — 10.000 $ (stand 12 m², 2 pass)\n\n"
                "💼 **Inclus :** mobilier (table, chaises), éclairage, connexion "
                "internet et badges participants.\n"
                "💰 Montants en USD hors TVA (EXPO BÉTON ASBL, non assujettie à la TVA).\n\n"
                "📞 **Réservation :** info@expobetonrdc.com ou "
                "https://expobetonrdc.com/#tg_register"
            )
            dispatcher.utter_message(text=answer)
            bot_response = answer
            log_conversation_message(session_id, 'bot', bot_response, metadata)
            return []
        
        # How to register / subscribe
        if any(word in user_question for word in ['inscrire', 'inscription', 's\'inscrire', 'register', 'registration']):
            answer = "✍️ **Comment s'inscrire à ExpoBeton RDC?**\n\n👉 **Étape 1:** Visitez https://expobetonrdc.com/#tg_register\n\n👉 **Étape 2:** Remplissez le formulaire d'inscription avec:\n• Nom et coordonnées\n• Type de participation (visiteur, exposant, partenaire)\n• Secteur d'activité\n\n👉 **Étape 3:** Choisissez votre formule (si exposant)\n\n👉 **Étape 4:** Validez votre inscription\n\n📧 **Contact:** info@expobetonrdc.com\n📞 **Tél:** +243 826 158 411\n\n✅ **Inscription gratuite pour visiteurs!**\n💰 **Tarifs préférentiels pour exposants avant le 1er mars 2026**"
            dispatcher.utter_message(text=answer)
            bot_response = answer
            log_conversation_message(session_id, 'bot', bot_response, metadata)
            return []
        
        # African corridors
        if any(word in user_question for word in ['corridor', 'corridors']) and 'africain' in user_question:
            answer = "🌍 **Les corridors africains du Grand Katanga:**\n\n👇 **Corridor Sud (SADC):**\n• Lubumbashi → Zambie → Afrique du Sud\n• Axes miniers et commerciaux\n• Ports: Durban, Maputo\n\n➡️ **Corridor Est:**\n• Kalemie (Lac Tanganyika) → Tanzanie\n• Port de Dar es Salaam\n• Connexion Océan Indien\n\n⬅️ **Corridor Ouest:**\n• Lubumbashi → Kolwezi → Kinshasa → Matadi\n• Océan Atlantique\n• Ports: Matadi, Boma, Banana\n\n🎯 **Importance stratégique:**\n• Exportation cobalt et cuivre\n• Importation équipements et biens\n• Intégration régionale africaine\n• Développement économique\n\n💡 Thème ExpoBeton 2026: 'Grand Katanga : Carrefour Stratégique au cœur des corridors africains'"
            dispatcher.utter_message(text=answer)
            bot_response = answer
            log_conversation_message(session_id, 'bot', bot_response, metadata)
            return []
        
        # Special Economic Zones (ZES)
        if any(word in user_question for word in ['zes', 'zone', 'zones', 'zés']) and any(word in user_question for word in ['économique', 'economic', 'spéciale', 'special']):
            answer = "🏭 **Zones Économiques Spéciales (ZES) en RDC:**\n\n🎯 **Définition:** Zones avec régime fiscal et douanier avantageux pour attirer investissements\n\n📍 **ZES Grand Katanga:**\n1️⃣ **Lukala** (Kongo-Central) - Cimenterie\n2️⃣ **Kimpese** (Kongo-Central) - Industrie\n3️⃣ **Songololo** (Kongo-Central) - Cimenterie\n4️⃣ **Kolwezi** (Lualaba) - Transformation minière\n5️⃣ **Lubumbashi** (Haut-Katanga) - Industrielle\n\n✅ **Avantages:**\n• Exonérations fiscales (5-10 ans)\n• Facilités douanières\n• Infrastructures modernes\n• Procédures simplifiées\n\n🏛️ **Gestion:** AZES (Agence des Zones Économiques Spéciales)\n\n📞 **Info:** Intervenant ExpoBeton 2024"
            dispatcher.utter_message(text=answer)
            bot_response = answer
            log_conversation_message(session_id, 'bot', bot_response, metadata)
            return []
        
        # West corridor
        if any(word in user_question for word in ['corridor ouest', 'ouest', 'west corridor']):
            answer = "🌅 **Corridor Ouest de la RDC:**\n\n📍 **Trajet:** Lubumbashi → Kinshasa → Matadi → Océan Atlantique\n\n🏛️ **Provinces traversées:**\n• Haut-Katanga, Lualaba (Grand Katanga)\n• Kinshasa (capitale)\n• Kongo-Central (ports)\n\n🚢 **Ports majeurs:**\n1️⃣ **Matadi** - Principal port RDC\n2️⃣ **Boma** - Port secondaire\n3️⃣ **Banana** - Port en eau profonde (en construction)\n\n🛣️ **Infrastructures:**\n• Route Nationale N°1 (550 km)\n• Chemin de fer Matadi-Kinshasa (366 km)\n• Fleuve Congo (transport fluvial)\n\n🎯 **Thème ExpoBeton 2024:** 'Révolution urbaine : Des solutions durables du corridor ouest pour Kinshasa et Kongo-Central'\n\n💡 **Enjeux:** Développement urbain, infrastructures, mobilité, énergie"
            dispatcher.utter_message(text=answer)
            bot_response = answer
            log_conversation_message(session_id, 'bot', bot_response, metadata)
            return []
        
        # Role of Kinshasa
        if any(word in user_question for word in ['kinshasa', 'rôle', 'role']) and 'kinshasa' in user_question:
            answer = "🏛️ **Rôle de Kinshasa dans le développement RDC:**\n\n📊 **Capitale politique et économique:**\n• 15+ millions d'habitants\n• 40% du PIB national\n• Siège du gouvernement\n\n🏭 **Centre économique:**\n• Hub commercial et financier\n• Port fluvial majeur\n• Industries et services\n\n🛣️ **Défis infrastructurels:**\n• Congestion urbaine\n• Déficit logements (2M unités)\n• Mobilité et transport\n• Assainissement et déchets\n\n💡 **Projets prioritaires:**\n• Rocade sud-est (décongestion)\n• Cités satellites (Maluku, SOSAK)\n• Métro Kinshasa (METROKIN)\n• Ministère Politique de la Ville\n\n🎯 **Projection 2050:** 30M habitants - Nécessite transformation urgente\n\n📜 **Source:** ExpoBeton 2024, discours Président Félix Tshisekedi"
            dispatcher.utter_message(text=answer)
            bot_response = answer
            log_conversation_message(session_id, 'bot', bot_response, metadata)
            return []
        
        # Who spoke at ExpoBeton 2023
        if ('2023' in user_question or 'kolwezi' in user_question) and any(word in user_question for word in ['parlé', 'spoke', 'intervenant', 'speaker']):
            answer = "🎯 **Intervenants ExpoBeton 2023 (Kolwezi, Lualaba):**\n\n👥 **Autorités:**\n• SEM Julien Paluku - Ministre de l'Industrie\n• Jacques Kaumba - Sénateur\n\n🏭 **Entreprises minières:**\n• Prof Dr Edouard Swana (TFM) - RSE et environnement\n• Guy Muswil (KAMOA-KAKULA) - Projet cuivre\n\n🏛️ **Institutions publiques:**\n• Pierre Bundoki (FONER) - Entretien routier\n• Popol Mabolia Yenga (CAMI) - Cadastre minier\n• Christian Basunga - Expert BTP\n\n🎯 **Thématiques:**\n• Exploitation minière responsable\n• Protection environnementale\n• Développement communautaire\n• Corridors de développement\n• Zones économiques spéciales\n\n📜 **Rapport complet disponible sur expobetonrdc.com**"
            dispatcher.utter_message(text=answer)
            bot_response = answer
            log_conversation_message(session_id, 'bot', bot_response, metadata)
            return []
        
        # Minister of Industry
        if any(word in user_question for word in ['ministre', 'minister']) and any(word in user_question for word in ['industrie', 'industry']):
            answer = "🏭 **Ministre de l'Industrie - ExpoBeton:**\n\n👨‍💼 **SEM Julien Paluku Kahongya**\n\n💼 **Fonction:** Ministre de l'Industrie de la RDC\n\n🎯 **Intervention ExpoBeton 2023 (Kolwezi):**\n• Promotion de l'industrialisation locale\n• Transformation des matières premières\n• Développement des PME/PMI\n• Zones économiques spéciales\n\n💡 **Messages clés:**\n• Nécessité de transformer cobalt et cuivre localement\n• Création d'emplois par l'industrie\n• Partenariats public-privé\n• Financement innovant\n\n📜 **Documents:** Présentations disponibles dans archives ExpoBeton 2023"
            dispatcher.utter_message(text=answer)
            bot_response = answer
            log_conversation_message(session_id, 'bot', bot_response, metadata)
            return []
        
        # Governor of Kinshasa
        if any(word in user_question for word in ['gouverneur', 'governor']) and 'kinshasa' in user_question:
            answer = "🏛️ **Gouverneur de Kinshasa - ExpoBeton 2024:**\n\n👨‍💼 **SEM BUMBA LUBAKI Daniel**\n\n💼 **Fonction:** Gouverneur de la Ville-Province de Kinshasa\n\n🎯 **Intervention ExpoBeton 2024:**\n• Support à l'événement ExpoBeton\n• Défis urbains de Kinshasa\n• Prix d'encouragement universités\n\n💡 **Priorités gouvernorat:**\n• Amélioration voiries urbaines\n• Gestion des déchets\n• Mobilité et transport\n• Développement cités satellites\n• Assainissement et drainage\n\n🏆 **Action ExpoBeton:** Remise 1er prix concours étudiants INBTP\n\n📜 **Rapport ExpoBeton 2024** pour détails complets"
            dispatcher.utter_message(text=answer)
            bot_response = answer
            log_conversation_message(session_id, 'bot', bot_response, metadata)
            return []
        
        # TFM (Tenke Fungurume Mining)
        if 'tfm' in user_question or 'tenke' in user_question or 'fungurume' in user_question:
            answer = "🏭 **TFM (Tenke Fungurume Mining)**\n\n📍 **Localisation:** Province du Lualaba, Kolwezi\n⚙️ **Activité:** Exploitation minière (cuivre et cobalt)\n\n🌍 **RSE & Environnement:**\n✅ Certifications ISO 9001, 14001, 18001, 45001\n✅ Réduction des émissions CO2 et NO2\n✅ Énergie propre (turbine à gaz, hydro-électricité)\n✅ Promotion voitures électriques (cobalt)\n\n🏘️ **Développement communautaire:**\n• 31 millions USD investis (2021-2025)\n• Santé: HGR 200 lits, centres de santé\n• Éducation: écoles, bibliothèques, ISTA\n• Économie: centre agricole, coopératives\n• Infrastructures: routes, ponts, marchés\n\n👨‍💼 **Intervenant ExpoBeton 2023:** Prof Dr Edouard Swana (Manager Relations Communautaires)"
            dispatcher.utter_message(text=answer)
            bot_response = answer
            log_conversation_message(session_id, 'bot', bot_response, metadata)
            return []
        
        # FONER (Fonds National d'Entretien Routier)
        if 'foner' in user_question:
            answer = "🛣️ **FONER (Fonds National d'Entretien Routier)**\n\n📋 **Création:** 2008\n🎯 **Mission:** Financer l'entretien et la protection du patrimoine routier RDC\n\n💰 **Ressources:**\n• Redevances sur lubrifiants et carburants\n• Droits de péage\n• Allocations budgétaires État\n\n📊 **Réalisations 2019-2022:** 435 millions USD investis\n📈 **Projection 2023:** 170 millions USD mobilisés\n\n🚧 **Travaux financés:**\n• 60% réseau routier national\n• 40% réseau provincial et local\n• Entretien routes, ponts, voiries urbaines\n\n⚠️ **Défis:** Besoins annuels de 380 millions USD vs 170 millions disponibles\n\n👨‍💼 **DG:** Pierre Bundoki (intervenant ExpoBeton 2023)"
            dispatcher.utter_message(text=answer)
            bot_response = answer
            log_conversation_message(session_id, 'bot', bot_response, metadata)
            return []
        
        # CAMI (Cadastre Minier)
        if 'cami' in user_question or 'cadastre minier' in user_question:
            answer = "⛏️ **CAMI (Cadastre Minier)**\n\n📋 **Nature:** Établissement public\n🎯 **Mission:** Gestion du domaine minier et des titres miniers/carrières\n\n📜 **Types d'autorisations:**\n1️⃣ Recherches de produits de carrières\n2️⃣ Exploitation de carrière temporaire\n3️⃣ Exploitation de carrière permanente\n\n📊 **Lualaba (chiffres clés):**\n• 201 droits de carrières actifs\n• 122 ARPC (61%)\n• 73 AECP (36%)\n• 6 CUP (3%)\n\n🏗️ **Programme PDL 145:**\n• 38.936 Km routes à réhabiliter\n• 418 mini centrales solaires\n• 238 marchés modernes\n• 788 centres de santé\n\n👨‍💼 **DG:** Popol Mabolia Yenga (intervenant ExpoBeton 2023)"
            dispatcher.utter_message(text=answer)
            bot_response = answer
            log_conversation_message(session_id, 'bot', bot_response, metadata)
            return []
        
        # BCC (Banque Centrale du Congo)
        if 'bcc' in user_question or 'banque centrale' in user_question:
            answer = "🏦 **BCC (Banque Centrale du Congo)**\n\n🎯 **Rôle:** Financement du secteur productif RDC\n\n📊 **Chiffres:**\n• Crédit à l'économie: 2.010,7 milliards CDF (2017)\n• Part bancaire: 93,9%\n• Ratio crédit/PIB: 8,3% (très faible vs Afrique du Sud 63,4%)\n\n⚠️ **Défis:**\n• Faible niveau d'épargne domestique\n• Absence de marché financier organisé\n• Dollarisation de l'économie\n• Déficit en infrastructures\n\n💡 **Solutions proposées:**\n• Amélioration climat des affaires\n• Création institutions financières spécialisées\n• Guichet de refinancement long\n• Émission valeurs du Trésor\n• Fonds de garantie de dépôts\n\n👨‍💼 **Vice-Gouverneur** (intervenant ExpoBeton 2018)"
            dispatcher.utter_message(text=answer)
            bot_response = answer
            log_conversation_message(session_id, 'bot', bot_response, metadata)
            return []
        
        # Theme
        if any(word in user_question for word in ['thème', 'theme', 'sujet']):
            answer = (
                "🎯 Le thème de la **12ème édition (2026)** est :\n\n"
                "**« KINSHASA, LOCOMOTIVE DE LA TRANSFORMATION DES VILLES DE LA RDC »**\n\n"
                "Cette édition met Kinshasa au centre des enjeux d'infrastructures, "
                "d'habitat, de développement urbain et de partenariats public-privé.\n\n"
                "📜 Le thème **« Grand Katanga : Carrefour Stratégique au cœur des "
                "corridors africains du Sud, de l'Ouest et de l'Est »** était celui de la "
                "**11ème édition**, organisée à Lubumbashi avec des étapes satellites à "
                "Kalemie et Kolwezi."
            )
            dispatcher.utter_message(text=answer)
            suggestion = "\n💡 Vous pourriez aussi demander :\n• Qui sont les fondateurs ?\n• Comment devenir ambassadeur ?\n• Où se déroule l'événement ?"
            dispatcher.utter_message(text=suggestion)
            return []
        
        # Default: show help and log unanswered question
        user_message = tracker.latest_message.get('text', '')
        session_id = tracker.sender_id
        metadata = tracker.latest_message.get('metadata', {})
        
        # Send email notification for unanswered question
        send_unanswered_question_email(user_message)
        
        # Use multilingual fallback message
        fallback_message = get_multilingual_response('fallback', detected_lang)
        
        dispatcher.utter_message(text=fallback_message)
        
        # Log bot response
        log_conversation_message(session_id, 'bot', fallback_message, metadata)
        
        # Send conversation email after every 3 messages or fallback
        if session_id in CONVERSATION_LOGS:
            msg_count = len(CONVERSATION_LOGS[session_id]['messages'])
            if msg_count >= 4:  # Send after 4 messages (2 user + 2 bot minimum)
                send_conversation_email(
                    session_id,
                    CONVERSATION_LOGS[session_id]['user_info'],
                    CONVERSATION_LOGS[session_id]['messages']
                )
        
        return []

class ActionAnswerAndSuggest(Action):
    def name(self) -> Text:
        return "action_answer_and_suggest"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        user_question = tracker.latest_message.get('text', '')
        detected_lang = detect_language(user_question)

        # Use updated responses from MULTILINGUAL_CONTENT
        if "date" in user_question.lower() or "quand" in user_question.lower():
            answer = get_multilingual_response('dates', detected_lang)
            if detected_lang == 'fr':
                suggestion = "Souhaitez-vous connaître le thème de 2026 ?"
            else:
                suggestion = "Would you like to know the 2026 theme?"
        else:
            if detected_lang == 'fr':
                answer = "Je suis là pour vous aider sur ExpoBeton RDC."
                suggestion = "Souhaitez-vous découvrir les opportunités d'investissement ?"
            else:
                answer = "I'm here to help you with ExpoBeton RDC."
                suggestion = "Would you like to discover investment opportunities?"

        dispatcher.utter_message(text=answer)
        dispatcher.utter_message(text=suggestion)

        return []

class ActionEndConversation(Action):
    def name(self) -> Text:
        return "action_end_conversation"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        session_id = tracker.sender_id
        metadata = tracker.latest_message.get('metadata', {})
        
        print(f"\n{'='*60}")
        print(f"[ACTION END CONVERSATION] Called for session: {session_id}")
        print(f"[ACTION END CONVERSATION] Metadata received: {metadata}")
        print(f"[ACTION END CONVERSATION] Has 'messages' in metadata: {'messages' in metadata}")
        print(f"[ACTION END CONVERSATION] Has 'user_info' in metadata: {'user_info' in metadata}")
        print(f"{'='*60}\n")
        
        # Get conversation data from metadata if provided by frontend
        if 'messages' in metadata and 'user_info' in metadata:
            print(f"[ACTION END CONVERSATION] Using metadata from frontend")
            # Frontend sent complete conversation data
            messages = metadata.get('messages', [])
            user_info = metadata.get('user_info', {})
            
            print(f"[ACTION END CONVERSATION] Messages count: {len(messages)}")
            print(f"[ACTION END CONVERSATION] User info: {user_info}")
            
            # Convert frontend message format to backend format
            formatted_messages = []
            for msg in messages:
                # Handle timestamp - JavaScript toISOString() adds 'Z' which needs to be replaced
                timestamp = msg.get('timestamp')
                if isinstance(timestamp, str):
                    try:
                        # Replace 'Z' with '+00:00' for Python compatibility
                        timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    except Exception as e:
                        print(f"[ERROR] Failed to parse timestamp '{timestamp}': {e}")
                        timestamp = datetime.now()
                elif not isinstance(timestamp, datetime):
                    timestamp = datetime.now()
                
                formatted_messages.append({
                    'sender': msg.get('sender'),
                    'text': msg.get('text'),
                    'timestamp': timestamp
                })
            
            # Send email with conversation
            # Libellés de journal corrigés : l'envoi est désormais asynchrone et peut
            # être entièrement court-circuité (SMTP non configuré, identifiants
            # factices ou disjoncteur ouvert). Annoncer « email sent » ici était faux
            # dans la quasi-totalité des cas et a masqué le blocage décrit dans C1.
            print(f"[ACTION END CONVERSATION] Transmission du transcript (asynchrone)...")
            send_conversation_email(session_id, user_info, formatted_messages)
            print(f"✅ [ACTION END CONVERSATION] Conversation terminée et transcript journalisé pour la session : {session_id}")
            
        # Or check if we have messages in our local storage
        elif session_id in CONVERSATION_LOGS:
            print(f"[ACTION END CONVERSATION] Using conversation logs from memory")
            conversation = CONVERSATION_LOGS[session_id]
            if len(conversation['messages']) > 0:
                print(f"[ACTION END CONVERSATION] Messages in log: {len(conversation['messages'])}")
                send_conversation_email(
                    session_id,
                    conversation['user_info'],
                    conversation['messages']
                )
                # Clear conversation from memory
                del CONVERSATION_LOGS[session_id]
                print(f"✅ [ACTION END CONVERSATION] Conversation terminée et transcript journalisé pour la session : {session_id}")
            else:
                print(f"⚠️ [ACTION END CONVERSATION] No messages found in conversation log")
        else:
            print(f"❌ [ACTION END CONVERSATION] No conversation data found!")
            print(f"   - Not in metadata")
            print(f"   - Not in CONVERSATION_LOGS")
            print(f"   - Available CONVERSATION_LOGS keys: {list(CONVERSATION_LOGS.keys())}")
        
        dispatcher.utter_message(
            text="👋 Merci pour votre visite! La conversation a été enregistrée."
        )
        
        # --- Analytics: end session ---
        send_analytics_event('session_end', {'session_id': session_id})
        
        # Clean up analytics tracking
        ANALYTICS_SESSIONS_STARTED.discard(session_id)
        
        return []

class ActionAskFeedbackRating(Action):
    """Custom action to ask for feedback in the user's language"""
    
    def name(self) -> Text:
        return "action_ask_feedback_rating"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Detect language from the LAST user message
        events = tracker.events
        user_messages = [e for e in events if e.get('event') == 'user']
        
        if user_messages:
            last_user_message = user_messages[-1].get('text', '')
            detected_lang = detect_language(last_user_message)
        else:
            detected_lang = 'fr'  # Default to French
        
        # Multilingual feedback prompts
        feedback_prompts = {
            'fr': {
                'text': "Nous aimerions connaître votre avis! Comment trouvez-vous notre service?",
                'thumbs_up': "👍 Excellent",
                'thumbs_down': "👎 Peut être amélioré"
            },
            'en': {
                'text': "We'd love to hear your feedback! How would you rate our service?",
                'thumbs_up': "👍 Excellent",
                'thumbs_down': "👎 Could be better"
            },
            'zh': {
                'text': "我们很想听到您的反馈！您如何评价我们的服务？",
                'thumbs_up': "👍 非常好",
                'thumbs_down': "👎 可以更好"
            },
            'ru': {
                'text': "Мы бы хотели услышать ваше мнение! Как вы оцениваете наш сервис?",
                'thumbs_up': "👍 Отлично",
                'thumbs_down': "👎 Можно лучше"
            },
            'es': {
                'text': "¡Nos encantaría conocer tu opinión! ¿Cómo calificarías nuestro servicio?",
                'thumbs_up': "👍 Excelente",
                'thumbs_down': "👎 Podría mejorar"
            },
            'ar': {
                'text': "نود أن نسمع رأيك! كيف تقيّم خدمتنا؟",
                'thumbs_up': "👍 ممتاز",
                'thumbs_down': "👎 يمكن أن يكون أفضل"
            }
        }
        
        prompt = feedback_prompts.get(detected_lang, feedback_prompts['fr'])
        
        buttons = [
            {"title": prompt['thumbs_up'], "payload": "/SetSlots(feedback_rating=thumbs_up)"},
            {"title": prompt['thumbs_down'], "payload": "/SetSlots(feedback_rating=thumbs_down)"}
        ]
        
        dispatcher.utter_message(text=prompt['text'], buttons=buttons)
        return []

class ActionThankYouPositive(Action):
    """Custom action for positive feedback thank you in user's language"""
    
    def name(self) -> Text:
        return "action_thankyou_positive"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Detect language from the LAST user message
        events = tracker.events
        user_messages = [e for e in events if e.get('event') == 'user']
        
        if user_messages:
            last_user_message = user_messages[-1].get('text', '')
            detected_lang = detect_language(last_user_message)
        else:
            detected_lang = 'fr'  # Default to French
        
        # Multilingual positive feedback responses
        positive_responses = {
            'fr': "C'est merveilleux à entendre! Merci d'avoir pris le temps de nous donner votre avis. 🌟",
            'en': "That's wonderful to hear! Thank you for taking the time to share your feedback. 🌟",
            'zh': "真好！感谢您花时间分享您的反馈。🌟",
            'ru': "Замечательно! Спасибо, что нашли время поделиться своим мнением. 🌟",
            'es': "¡Qué maravilloso escuchar eso! Gracias por tomarse el tiempo de compartir sus comentarios. 🌟",
            'ar': "هذا رائع! شكراً لك على أخذ الوقت لمشاركة رأيك. 🌟"
        }
        
        message = positive_responses.get(detected_lang, positive_responses['fr'])
        dispatcher.utter_message(text=message)
        return []

class ActionThankYouNegative(Action):
    """Custom action for negative feedback thank you in user's language"""
    
    def name(self) -> Text:
        return "action_thankyou_negative"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Detect language from the LAST user message
        events = tracker.events
        user_messages = [e for e in events if e.get('event') == 'user']
        
        if user_messages:
            last_user_message = user_messages[-1].get('text', '')
            detected_lang = detect_language(last_user_message)
        else:
            detected_lang = 'fr'  # Default to French
        
        # Multilingual negative feedback responses
        negative_responses = {
            'fr': "Nous apprécions que vous ayez pris le temps de nous donner votre avis. Nous travaillons toujours à améliorer notre service.",
            'en': "We appreciate you taking the time to share your feedback. We're always working to improve our service.",
            'zh': "感谢您花时间分享您的反馈。我们一直在努力改进我们的服务。",
            'ru': "Мы ценим, что вы нашли время поделиться своим мнением. Мы постоянно работаем над улучшением нашего сервиса.",
            'es': "Agradecemos que se haya tomado el tiempo de compartir sus comentarios. Siempre estamos trabajando para mejorar nuestro servicio.",
            'ar': "نحن نقدر أخذك الوقت لمشاركة رأيك. نحن نعمل دائماً على تحسين خدمتنا."
        }
        
        message = negative_responses.get(detected_lang, negative_responses['fr'])
        dispatcher.utter_message(text=message)
        return []
