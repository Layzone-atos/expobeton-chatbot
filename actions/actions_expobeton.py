"""
ExpoBeton RDC — Rasa Custom Actions for Registration & Ambassador
=================================================================
This module provides custom actions for the Rasa chatbot to register users
directly into the ExpoBeton admin database via the REST API.

Installation:
    pip install requests

Place this file in your Rasa project's `actions/` directory.
Add `action_endpoint` to your Rasa `endpoints.yml`:

    action_endpoint:
      url: "http://localhost:5055/webhook"

Then run the action server:
    rasa run actions
"""

import logging
import re
import requests
from typing import Any, Dict, List, Text, Optional
from rasa_sdk import Action, Tracker, FormValidationAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet, AllSlotsReset, FollowupAction
from rasa_sdk.types import DomainDict

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════
# Configuration — Update these values for your deployment
# ═══════════════════════════════════════════════════════════════════════
import os
EXPOBETON_API_URL = os.getenv("EXPOBETON_API_URL", "https://expobetonrdc.com/api_chatbot_register.php")
EXPOBETON_API_KEY = os.getenv("EXPOBETON_API_KEY", "ebx-rasa-2026-kAlEmIe-be96bac9f905b106ed2b941dfe536b07")
ADMINCB_ANALYTICS_URL = os.getenv("ADMINCB_ANALYTICS_URL", "https://admincb.expobetonrdc.com/api_chatbot_analytics.php")


def api_headers() -> dict:
    """Return the standard headers for the ExpoBeton API."""
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {EXPOBETON_API_KEY}",
        "User-Agent": "RasaChatbot/1.0 ExpoBeton",
    }


# ═══════════════════════════════════════════════════════════════════════
# Helper: API Client
# ═══════════════════════════════════════════════════════════════════════

class ExpoBetonAPI:
    """Wrapper around the ExpoBeton chatbot registration API."""

    @staticmethod
    def health_check() -> dict:
        """Check if the API is reachable."""
        try:
            r = requests.get(
                f"{EXPOBETON_API_URL}?action=health",
                headers={"Accept": "application/json", "User-Agent": "RasaChatbot/1.0 ExpoBeton"},
                timeout=10,
            )
            return r.json()
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def get_categories() -> dict:
        """Fetch available registration categories and pricing."""
        try:
            r = requests.get(
                f"{EXPOBETON_API_URL}?action=categories",
                headers={"Accept": "application/json", "User-Agent": "RasaChatbot/1.0 ExpoBeton"},
                timeout=10,
            )
            return r.json()
        except Exception as e:
            logger.error(f"Categories fetch failed: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def register(data: dict) -> dict:
        """Submit a new registration."""
        try:
            r = requests.post(
                f"{EXPOBETON_API_URL}?action=register",
                json=data,
                headers=api_headers(),
                timeout=30,
            )
            return r.json()
        except Exception as e:
            logger.error(f"Registration failed: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def upload_document(ref: str, doc_type: str, file_content: bytes, filename: str) -> dict:
        """Upload a document (logo or passport) for a registration."""
        upload_base = os.getenv(
            "EXPOBETON_UPLOAD_URL",
            "https://expobetonrdc.com/upload_documents.php"
        )
        try:
            r = requests.post(
                f"{upload_base}?ref={ref}&type={doc_type}",
                files={"file": (filename, file_content)},
                headers={
                    "Authorization": f"Bearer {EXPOBETON_API_KEY}",
                    "User-Agent": "RasaChatbot/1.0 ExpoBeton",
                },
                timeout=60,
            )
            return r.json()
        except Exception as e:
            logger.error(f"Document upload failed: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def submit_ambassador(data: dict) -> dict:
        """Submit a new ambassador application."""
        try:
            r = requests.post(
                f"{EXPOBETON_API_URL}?action=ambassador",
                json=data,
                headers=api_headers(),
                timeout=30,
            )
            return r.json()
        except Exception as e:
            logger.error(f"Ambassador submission failed: {e}")
            return {"success": False, "error": str(e)}


# ═══════════════════════════════════════════════════════════════════════
# Action: Show available registration categories
# ═══════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════
# Action: Personalized registration start
# ═══════════════════════════════════════════════════════════════════════

class ActionStartRegistration(Action):
    """Show registration info and ASK the user for confirmation before starting the form.

    Sets the ``registration_pending`` slot to ``True``; the form itself is only
    activated by a follow-up rule once the user confirms with ``affirm``.
    """

    def name(self) -> Text:
        return "action_start_registration"

    def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict
    ) -> List[Dict[Text, Any]]:
        # Skip if a registration form is already active (prevents duplicate launches
        # caused by the user sending the same message twice).
        if tracker.active_loop_name in ("registration_form", "registration_review_form"):
            return []

        person = tracker.get_slot('person')
        greeting = ""
        if person:
            first_name = str(person).strip().split()[0].title()
            greeting = f", {first_name}"

        dispatcher.utter_message(
            text=(
                f'Pour participer à **ExpoBeton RDC 2026** (07-10 octobre, Kinshasa), '
                f'vous devez vous inscrire{greeting}.\n\n'
                f'📋 **3 catégories disponibles :**\n'
                f'1️⃣ 🏆 **Sponsor** (Platinum/Gold/Bronze/Silver — de 10.000 $ à 40.000 $)\n'
                f'2️⃣ 🏗️ **Exposant** (stand 3×3m à 5.000 $ ou 2×3m à 3.500 $)\n'
                f'3️⃣ 👤 **Participant Simple** (Gratuit)\n\n'
                f'👉 **Souhaitez-vous que je vous aide à vous inscrire maintenant ?**\n'
                f'Répondez **« oui »** pour commencer l\'inscription étape par étape, '
                f'ou **« non »** si vous préférez d\'abord poser d\'autres questions. 😊'
            )
        )
        # Mark registration as pending user confirmation. The form will be
        # activated by rule "User confirms registration" when the user affirms.
        return [SlotSet("registration_pending", True)]


# ═══════════════════════════════════════════════════════════════════════
# Action: Clear the registration_pending flag
# ═══════════════════════════════════════════════════════════════════════

class ActionClearRegPending(Action):
    """Reset the ``registration_pending`` slot (used after affirm/deny)."""

    def name(self) -> Text:
        return "action_clear_reg_pending"

    def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict
    ) -> List[Dict[Text, Any]]:
        return [SlotSet("registration_pending", None)]


# ═══════════════════════════════════════════════════════════════════════
# Action: Show available registration categories
# ═══════════════════════════════════════════════════════════════════════

class ActionShowCategories(Action):
    def name(self) -> Text:
        return "action_show_categories"

    def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict
    ) -> List[Dict[Text, Any]]:

        msg = (
            "📋 **ExpoBeton RDC 2026 — Catégories d'inscription**\n\n"
            "1️⃣ **🏆 Sponsor** (paliers de partenariat)\n"
            "   • Platinum — 40.000 $ (stand 45 m², 5 pass)\n"
            "   • Gold — 20.000 $ (stand 20 m², 3 pass)\n"
            "   • Bronze — 15.000 $ (stand 15 m², 2 pass)\n"
            "   • Silver — 10.000 $ (stand 12 m², 2 pass)\n\n"
            "2️⃣ **🏗️ Exposant** (stands du site principal)\n"
            "   • Stand 3×3m — 9 m² — 5.000 $ (2 pass délégués, 30 places)\n"
            "   • Stand 2×3m — 6 m² — 3.500 $ (1 pass délégué, 5 places)\n\n"
            "3️⃣ **👤 Participant Simple** (Gratuit)\n\n"
            "💰 Montants en USD hors TVA (EXPO BÉTON ASBL, non assujettie à la TVA).\n"
            "Quelle catégorie vous intéresse ?"
        )
        dispatcher.utter_message(text=msg)
        return []


# ═══════════════════════════════════════════════════════════════════════
# Form Validation: Registration Form
# ═══════════════════════════════════════════════════════════════════════

VALID_CATEGORIES = [
    "Platinum", "Gold", "Silver", "Bronze",
    "Exposant Stand 3x3m", "Exposant Stand 2x4m", "Exposant Stand 2x3m",
    "Participant Simple",
]

VALID_PAYMENT_METHODS = [
    "Chèque", "Veuillez Facturer",
]

CATEGORY_MAP = {
    # Numbers (main menu)
    "1": "_sponsor_",
    "2": "_exposant_",
    "3": "Participant Simple",
    # Sponsor sub-levels (dotted numbers) — ordre du site : Bronze avant Silver
    "1.1": "Platinum", "1.2": "Gold", "1.3": "Bronze", "1.4": "Silver",
    # Direct names
    "platinum": "Platinum",
    "gold": "Gold",
    "silver": "Silver",
    "bronze": "Bronze",
    "exposant 3x3": "Exposant Stand 3x3m",
    "exposant 2x3": "Exposant Stand 2x3m",
    "participant": "Participant Simple",
    "participant simple": "Participant Simple",
    "sponsor": "_sponsor_",
    "sponsor platinum": "Platinum",
    "sponsor gold": "Gold",
    "sponsor silver": "Silver",
    "sponsor bronze": "Bronze",
    # Comma-separated shortcuts ("Sponsor, Platinum" etc.)
    "sponsor, platinum": "Platinum",
    "sponsor,platinum": "Platinum",
    "sponsor, gold": "Gold",
    "sponsor,gold": "Gold",
    "sponsor, silver": "Silver",
    "sponsor,silver": "Silver",
    "sponsor, bronze": "Bronze",
    "sponsor,bronze": "Bronze",
    "exposant, 3x3": "Exposant Stand 3x3m",
    "exposant, 2x3": "Exposant Stand 2x3m",
    # Stand variations — deux formats seulement (le 2×4m n'est plus commercialisé).
    # Les formes « stand 3x3m » / « stand 2x3m » sont indispensables : sans elles,
    # la sous-chaîne « stand 2x3 » est rejetée par la borne de mot finale (le « m »
    # qui suit) et c'est la clé générique « stand », plus longue que « 2x3m », qui
    # l'emporte — l'utilisateur retombe alors sur le sous-menu au lieu du format voulu.
    "stand 3x3": "Exposant Stand 3x3m",
    "stand 2x3": "Exposant Stand 2x3m",
    "stand 3x3m": "Exposant Stand 3x3m",
    "stand 2x3m": "Exposant Stand 2x3m",
    "3x3": "Exposant Stand 3x3m",
    "2x3": "Exposant Stand 2x3m",
    "3x3m": "Exposant Stand 3x3m",
    "2x3m": "Exposant Stand 2x3m",
    # Formes en m² et formulations libres vues en conversation réelle.
    # Le « ² » est normalisé en « 2 » par match_category, d'où les clés en "m2".
    "9 m2": "Exposant Stand 3x3m",
    "9m2": "Exposant Stand 3x3m",
    "grand stand": "Exposant Stand 3x3m",
    "6 m2": "Exposant Stand 2x3m",
    "6m2": "Exposant Stand 2x3m",
    "petit stand": "Exposant Stand 2x3m",
    "exposant": "_exposant_",
    "stand": "_exposant_",
    # Participant variations
    "gratuit": "Participant Simple",
    "free": "Participant Simple",
    "simple": "Participant Simple",
    "visiteur": "Participant Simple",
    # Formes féminines / statutaires vues en conversation réelle. « participante »
    # n'était pas reconnu : la borne de mot empêchait la sous-chaîne « participant ».
    "participante": "Participant Simple",
    "participante simple": "Participant Simple",
    "etudiant": "Participant Simple",
    "étudiant": "Participant Simple",
    "etudiante": "Participant Simple",
    "étudiante": "Participant Simple",
    "eleve": "Participant Simple",
    "élève": "Participant Simple",
}


# ═══════════════════════════════════════════════════════════════════════
# Helpers shared by the smart handlers (affirm / inform outside forms)
# ═══════════════════════════════════════════════════════════════════════

def _last_bot_message(tracker: Tracker) -> str:
    """Return the lowercased text of the last bot message, or '' if none."""
    for event in reversed(tracker.applied_events()):
        if event.get("event") == "bot":
            return str(event.get("text") or "").lower()
    return ""


def match_category(text: str) -> Optional[str]:
    """Match free-form user text against CATEGORY_MAP.

    Returns a VALID_CATEGORIES value, "_sponsor_"/"_exposant_" for the
    sub-menu families, or None when no category can be detected.
    """
    if not text:
        return None
    raw = str(text).lower()
    # Normalisations AVANT le filtrage : la classe de caractères ci-dessous
    # remplace tout ce qui n'est pas [0-9a-zà-ÿ .,-+] par une espace. Sans cet
    # ordre, « 2×3m » devenait « 2 3m » et « 9 m² » devenait « 9 m », donc
    # aucune clé ne correspondait — alors que le bot affiche précisément ces
    # formes dans ses menus et que les utilisateurs les recopient telles quelles.
    raw = raw.replace("\u00d7", "x")   # × (signe multiplication) -> x
    raw = raw.replace("\u00b2", "2")   # ² (exposant deux) -> 2
    raw = raw.replace("\u2082", "2")   # ₂ (indice deux) -> 2, par précaution
    cleaned = re.sub(r"[^0-9a-zà-ÿ .,\-+]", " ", raw)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .,")
    if not cleaned:
        return None
    # Exact match first (handles "1", "2", "3", "participant simple"…)
    if cleaned in CATEGORY_MAP:
        return CATEGORY_MAP[cleaned]
    # Then longest-key substring match ("je veux participant simple"…)
    for key in sorted(CATEGORY_MAP.keys(), key=len, reverse=True):
        if len(key) >= 3 and re.search(
            r"(?<![0-9a-z])" + re.escape(key) + r"(?![0-9a-z])", cleaned
        ):
            return CATEGORY_MAP[key]
    return None


# ═══════════════════════════════════════════════════════════════════════
# Action: Smart affirm — bare "oui/ok" outside the pending rule
# ═══════════════════════════════════════════════════════════════════════

class ActionHandleAffirm(Action):
    """Handle a bare « oui / ok / d'accord » when the pending rule did not fire.

    The bot itself instructs users to answer « oui » in several places
    (registration offer, press accreditation offer). If the last bot message
    proposed registration, start the form directly; otherwise show the menu.
    """

    def name(self) -> Text:
        return "action_handle_affirm"

    def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict
    ) -> List[Dict[Text, Any]]:
        # Never interfere while a form is active (form rules handle affirm).
        if tracker.active_loop_name:
            return []

        # Pending flag set (e.g. right after action_start_registration).
        if tracker.get_slot("registration_pending"):
            dispatcher.utter_message(
                text="Parfait ! Je lance votre inscription étape par étape. 🚀"
            )
            return [
                SlotSet("registration_pending", None),
                FollowupAction("registration_form"),
            ]

        # The bot just proposed registration ("Répondez « oui »…" etc.).
        last_bot = _last_bot_message(tracker)
        offer_markers = (
            "souhaitez-vous",
            "« oui »",
            "vous inscrire maintenant",
            "commencer l'inscription",
        )
        if any(marker in last_bot for marker in offer_markers):
            dispatcher.utter_message(
                text="Parfait ! Je lance votre inscription étape par étape. 🚀"
            )
            return [
                SlotSet("registration_pending", None),
                FollowupAction("registration_form"),
            ]

        # Unrelated affirm — guide the user with the main menu.
        dispatcher.utter_message(
            text=(
                "Très bien ! 😊 Que souhaitez-vous faire ?\n\n"
                "• Tapez **« dates »** pour les dates de l'événement\n"
                "• Tapez **« catégories »** pour les options d'inscription\n"
                "• Tapez **« je veux m'inscrire »** pour commencer l'inscription\n"
                "• Ou posez directement votre question sur ExpoBeton RDC."
            )
        )
        return []


# ═══════════════════════════════════════════════════════════════════════
# Action: Inform outside any form (e.g. "Participant simple" after the offer)
# ═══════════════════════════════════════════════════════════════════════

class ActionHandleInformOutsideForm(Action):
    """When the user names a category outside the form, start registration
    with that category pre-filled. Anything else is routed to the answer
    engine (action_answer_expobeton)."""

    def name(self) -> Text:
        return "action_handle_inform_outside_form"

    def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict
    ) -> List[Dict[Text, Any]]:
        if tracker.active_loop_name:
            return []

        text = tracker.latest_message.get("text", "")
        lowered = text.lower()

        # ── Participant VIP : souscription payante distincte (300 $ / jour) ──
        # « participant vip » contient la clé « participant » et démarrerait une
        # inscription gratuite : promesse fausse. On explique avant tout mapping.
        if re.search(r"\bvip\b", lowered):
            dispatcher.utter_message(
                text=(
                    "🌟 Le **Participant VIP** est une souscription distincte : "
                    "**300 $ par jour**, avec accès privilégiés et branding dédié sur "
                    "les journées choisies (07-10 octobre 2026).\n\n"
                    "Elle se règle en ligne ici :\n"
                    "👉 https://expobetonrdc.com/sponsor/souscription-vip.php\n\n"
                    "Ce chat gère les inscriptions **Sponsor**, **Exposant** et "
                    "**Participant Simple** (gratuit). Pour l'accès gratuit, tapez "
                    "**« Participant Simple »** et je démarre votre inscription."
                )
            )
            return [SlotSet("registration_pending", None)]

        matched = match_category(text)

        # ── Stand 2×4m retiré du catalogue : informer plutôt que laisser le moteur
        # de réponses traiter « 2x4 » comme une question ouverte ──
        if re.search(r"2\s*[x×*]\s*4", lowered):
            dispatcher.utter_message(
                text=(
                    "ℹ️ Le **stand 2×4m n'est plus proposé** pour l'édition 2026.\n\n"
                    "Deux formats sont disponibles :\n"
                    "• **3×3m** (9 m²) — 5.000 $ — 2 pass délégués, 30 places\n"
                    "• **2×3m** (6 m²) — 3.500 $ — 1 pass délégué, 5 places\n\n"
                    "👉 Tapez **« 3×3m »** ou **« 2×3m »** pour démarrer votre "
                    "inscription exposant."
                )
            )
            return [SlotSet("registration_pending", None)]

        if not matched:
            # Not a category — let the keyword answer engine try.
            return [FollowupAction("action_answer_expobeton")]

        events = [
            SlotSet("registration_pending", None),
            SlotSet("_reg_category_phase", None),
        ]

        if matched == "_sponsor_":
            dispatcher.utter_message(
                text=(
                    "Excellent ! 🏆 Je démarre votre inscription **Sponsor** — "
                    "je vous demanderai votre niveau (Platinum / Gold / Silver / Bronze) "
                    "pendant le formulaire. 🚀"
                )
            )
            events.append(SlotSet("_reg_category_phase", "sponsor"))
        elif matched == "_exposant_":
            dispatcher.utter_message(
                text=(
                    "Excellent ! 🏗️ Je démarre votre inscription **Exposant** — "
                    "je vous demanderai votre type de stand pendant le formulaire. 🚀"
                )
            )
            events.append(SlotSet("_reg_category_phase", "exposant"))
        else:
            dispatcher.utter_message(
                text="Excellent choix ! 🚀 Je démarre votre inscription en catégorie **%s**." % matched
            )
            events.append(SlotSet("reg_category", matched))
            if matched == "Participant Simple":
                # Free category — skip the payment question.
                events.append(SlotSet("reg_payment", "N/A"))

        events.append(FollowupAction("registration_form"))
        return events



# ═══════════════════════════════════════════════════════════════════════
# Custom ask action for reg_category (replaces utter_ask_reg_category)
# ═══════════════════════════════════════════════════════════════════════

class ActionAskRegCategory(Action):
    """Custom ask action that shows the correct menu based on _reg_category_phase."""

    def name(self) -> Text:
        return "action_ask_reg_category"

    def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict
    ) -> List[Dict[Text, Any]]:
        phase = tracker.get_slot("_reg_category_phase")

        # Ordre et tarifs alignés sur le tunnel de souscription du site
        # (sponsor/assets/sousc-common.js -> window.EB12.PRICES).
        if phase == "sponsor":
            dispatcher.utter_message(
                text="🏆 **Choisissez votre palier de sponsoring :**\n\n"
                     "1️⃣ Platinum — 40.000 $ (stand 45 m², 5 pass)\n"
                     "2️⃣ Gold — 20.000 $ (stand 20 m², 3 pass)\n"
                     "3️⃣ Bronze — 15.000 $ (stand 15 m², 2 pass)\n"
                     "4️⃣ Silver — 10.000 $ (stand 12 m², 2 pass)\n\n"
                     "💵 Montants en USD hors TVA.\n"
                     "Tapez le numéro ou le nom du palier."
            )
        elif phase == "exposant":
            dispatcher.utter_message(
                text="🏗️ **Choisissez votre type de stand :**\n\n"
                     "1️⃣ Stand 3×3m — 9 m² — 5.000 $ (2 pass délégués, 30 places)\n"
                     "2️⃣ Stand 2×3m — 6 m² — 3.500 $ (1 pass délégué, 5 places)\n\n"
                     "💵 Montants en USD hors TVA.\n"
                     "Tapez le numéro ou le type de stand."
            )
        else:
            dispatcher.utter_message(
                text="📋 Pour quelle catégorie souhaitez-vous vous inscrire ?\n\n"
                     "1️⃣ 🏆 **Sponsor** (Platinum, Gold, Bronze, Silver)\n"
                     "2️⃣ 🏗️ **Exposant** (Stand 3×3m ou 2×3m)\n"
                     "3️⃣ 👤 **Participant Simple** (Gratuit)\n\n"
                     "Tapez le numéro ou le nom de la catégorie."
            )
        return []


class ValidateRegistrationForm(FormValidationAction):
    """Validates slots collected by the registration_form."""

    def name(self) -> Text:
        return "validate_registration_form"

    @staticmethod
    def _first_name(tracker: Tracker) -> str:
        """Get the user's first name from the person slot, or empty string."""
        person = tracker.get_slot("person")
        if person:
            return str(person).strip().split()[0].title()
        return ""

    # Une question entière était enregistrée comme nom d'entreprise : une jeune
    # étudiante avait répondu « Faut il acheter les billets pour y participer
    # étant jeune étudiante » à l'étape 1, et cette phrase était repartie telle
    # quelle vers l'API dans le champ société.
    _QUESTION_OPENERS = (
        "faut", "comment", "est-ce", "est ce", "pourquoi", "quel", "quelle",
        "quels", "quelles", "qui ", "où ", "quand", "combien", "puis-je",
        "puis je", "est-il", "je voudrais savoir", "je veux savoir",
        "is ", "how ", "why ", "what ", "when ", "where ", "can i", "do i",
    )

    def validate_reg_company(
        self, slot_value: Any, dispatcher: CollectingDispatcher,
        tracker: Tracker, domain: DomainDict
    ) -> Dict[Text, Any]:
        raw = str(slot_value or '').strip()
        lowered = raw.lower()

        # Libellé aligné sur le site : l'étape 1 accepte une société, une
        # institution OU une profession (indépendants, étudiants compris).
        ask = (
            "🏢 J'ai besoin du nom de votre **société, institution ou "
            "organisation**.\n\n"
            "Si vous n'en avez pas (indépendant, étudiant, particulier), indiquez "
            "votre **profession** ou votre **établissement**.\n\n"
            "Exemples : *Cimenterie de Kinshasa SA*, *Ministère de l'Urbanisme*, "
            "*Indépendant*, *Étudiante — ISTA*."
        )

        if raw.endswith("?") or raw.endswith("？") or lowered.startswith(self._QUESTION_OPENERS):
            dispatcher.utter_message(
                text=(
                    "🙂 Je vois que vous me posez une question — je vais y répondre, "
                    "mais ici j'ai besoin du **nom de votre société, institution ou "
                    "organisation**.\n\n"
                    "Si vous n'en avez pas, indiquez votre **profession** ou votre "
                    "établissement (ex. *Indépendant*, *Étudiante — ISTA*).\n\n"
                    "💡 Pour poser votre question librement, tapez "
                    "**« contact humain »** et notre équipe vous répondra."
                )
            )
            return _bump_fail(tracker, dispatcher, "reg_company")

        if len(raw) > 90:
            dispatcher.utter_message(
                text=(
                    "✂️ Cette réponse est trop longue pour un nom d'organisation. "
                    "Merci d'indiquer uniquement le **nom** (90 caractères maximum), "
                    "par exemple *Expo Béton ASBL*."
                )
            )
            return _bump_fail(tracker, dispatcher, "reg_company")

        if len(raw) >= 2:
            return {"reg_company": raw, "_reg_validation_fails": 0}
        dispatcher.utter_message(text=ask)
        return _bump_fail(tracker, dispatcher, "reg_company")

    def validate_reg_contact_name(
        self, slot_value: Any, dispatcher: CollectingDispatcher,
        tracker: Tracker, domain: DomainDict
    ) -> Dict[Text, Any]:
        if slot_value and len(str(slot_value).strip()) >= 2:
            return {"reg_contact_name": slot_value.strip(), "_reg_validation_fails": 0}
        dispatcher.utter_message(text="Veuillez fournir le nom complet de la personne de contact.")
        return _bump_fail(tracker, dispatcher, "reg_contact_name")

    def validate_reg_email(
        self, slot_value: Any, dispatcher: CollectingDispatcher,
        tracker: Tracker, domain: DomainDict
    ) -> Dict[Text, Any]:
        if slot_value and re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', str(slot_value).strip()):
            return {"reg_email": slot_value.strip().lower(), "_reg_validation_fails": 0}
        dispatcher.utter_message(text="Veuillez fournir une adresse email valide (exemple : nom@domaine.com).")
        return _bump_fail(tracker, dispatcher, "reg_email")

    def validate_reg_phone(
        self, slot_value: Any, dispatcher: CollectingDispatcher,
        tracker: Tracker, domain: DomainDict
    ) -> Dict[Text, Any]:
        # Phone is MANDATORY: a valid number (>= 8 digits) is required to
        # proceed — skipping is no longer allowed.
        raw = str(slot_value or '').strip()
        # Accept human-friendly inputs like "whatsapp : 00971 56 123 4567"
        # by extracting only digits and an optional leading '+'.
        digits = re.sub(r'\D', '', raw)
        has_plus = raw.lstrip().startswith('+')
        # International "00" prefix -> "+"
        if digits.startswith('00'):
            digits = digits[2:]
            has_plus = True
        if len(digits) >= 8:
            normalized = ('+' + digits) if has_plus else digits
            return {"reg_phone": normalized, "_reg_validation_fails": 0}
        dispatcher.utter_message(
            text=(
                "⚠️ Le numéro de téléphone est **obligatoire** pour finaliser "
                "votre inscription. Veuillez fournir un numéro valide "
                "(au moins 8 chiffres).\n\n"
                "Exemples : +243 81 234 5678 ou 00971 56 123 4567."
            )
        )
        return _bump_fail(tracker, dispatcher, "reg_phone")

    def validate_reg_country(
        self, slot_value: Any, dispatcher: CollectingDispatcher,
        tracker: Tracker, domain: DomainDict
    ) -> Dict[Text, Any]:
        if slot_value and len(str(slot_value).strip()) >= 2:
            val = slot_value.strip()
            # Normalize common country names
            country_map = {
                "rd congo": "RDC", "rdc": "RDC", "congo": "RDC",
                "république démocratique du congo": "RDC",
                "rep dem congo": "RDC", "dr congo": "RDC",
                "cd": "RDC", "drc": "RDC",
            }
            normalized = country_map.get(val.lower(), val)
            return {"reg_country": normalized, "_reg_validation_fails": 0}
        dispatcher.utter_message(text="Veuillez indiquer votre pays (exemple : RDC, France, Belgique).")
        return _bump_fail(tracker, dispatcher, "reg_country")

    def validate_reg_city(
        self, slot_value: Any, dispatcher: CollectingDispatcher,
        tracker: Tracker, domain: DomainDict
    ) -> Dict[Text, Any]:
        raw = str(slot_value or '').strip()
        # Detect phone-shaped input in the city slot (user pasted phone again)
        if _looks_like_phone(raw):
            dispatcher.utter_message(
                text=(
                    "📞 Je vois que vous avez tapé un numéro de téléphone, mais à cette "
                    "étape j'ai besoin de votre **ville**. \n\n🏙️ Dans quelle ville "
                    "êtes-vous basé ? (exemple : Kinshasa, Lubumbashi, Goma)"
                )
            )
            return _bump_fail(tracker, dispatcher, "reg_city")
        # Detect multi-city input "Lubumbashi, Kinshasa" or "Lubumbashi et Kinshasa"
        if re.search(r'\s*(,|;|\bet\b|\band\b|/|\+)\s*[A-Za-z\u00C0-\u017F]{2,}', raw):
            dispatcher.utter_message(
                text=(
                    "🏙️ Vous avez mentionné plusieurs villes. Quelle est votre **ville "
                    "principale** (siège social ou ville où vous résidez) ? Indiquez une seule ville."
                )
            )
            return _bump_fail(tracker, dispatcher, "reg_city")
        if raw and len(raw) >= 2:
            return {"reg_city": raw, "_reg_validation_fails": 0}
        dispatcher.utter_message(text="Veuillez indiquer votre ville (exemple : Kinshasa, Lubumbashi).")
        return _bump_fail(tracker, dispatcher, "reg_city")

    def validate_reg_category(
        self, slot_value: Any, dispatcher: CollectingDispatcher,
        tracker: Tracker, domain: DomainDict
    ) -> Dict[Text, Any]:
        """Validate category using _reg_category_phase to track sub-menu state.
        
        When a sub-menu is needed, we set the phase and return None.
        action_ask_reg_category will then display the correct menu.
        We do NOT dispatch messages here — the ask action handles all prompts.
        """
        # Numérotation alignée sur les menus affichés : paliers du site
        # (Bronze 15.000 $ avant Silver 10.000 $) et deux formats de stand.
        sponsor_num = {"1": "Platinum", "2": "Gold", "3": "Bronze", "4": "Silver"}
        stand_num = {"1": "Exposant Stand 3x3m", "2": "Exposant Stand 2x3m"}
        phase = tracker.get_slot("_reg_category_phase")

        if slot_value:
            raw = str(slot_value).strip()
            val = raw.lower()

            # Detect phone-shaped input in the category slot
            if _looks_like_phone(raw):
                dispatcher.utter_message(
                    text=(
                        "📞 Je vois que vous avez tapé un numéro de téléphone, mais ici j'ai besoin de "
                        "votre **catégorie d'inscription**. Tapez **1** (Sponsor), **2** (Exposant) ou **3** (Participant)."
                    )
                )
                return {"reg_category": None, "_reg_validation_fails": (tracker.get_slot("_reg_validation_fails") or 0) + 1}

            # Detect multi-value input "2 et 3", "1, 2", "sponsor + exposant"
            if re.search(r'\b(\d|sponsor|exposant|participant|platinum|gold|silver|bronze)\b.*?\s+(et|and|\+|,|/)\s+\b(\d|sponsor|exposant|participant|platinum|gold|silver|bronze)\b', val):
                dispatcher.utter_message(
                    text=(
                        "ℹ️ Vous ne pouvez choisir **qu'une seule catégorie** par inscription. "
                        "Si vous souhaitez plusieurs stands ou statuts, soumettez d'abord celui-ci, "
                        "puis recommencez l'inscription.\n\n👉 Quelle catégorie principale choisissez-vous ? "
                        "Tapez **1**, **2** ou **3**."
                    )
                )
                return {"reg_category": None, "_reg_validation_fails": (tracker.get_slot("_reg_validation_fails") or 0) + 1}

            # ── Stand 2×4m retiré du catalogue : informer au lieu de re-demander ──
            # Le site ne vend plus que 3×3m (5.000 $) et 2×3m (3.500 $). La valeur
            # technique « Exposant Stand 2x4m » reste dans VALID_CATEGORIES pour les
            # inscriptions historiques, mais aucun alias ne doit plus y mener.
            if re.search(r'2\s*[x×*]\s*4', val):
                dispatcher.utter_message(
                    text=(
                        "ℹ️ Le **stand 2×4m n'est plus proposé** pour l'édition 2026.\n\n"
                        "Deux formats sont disponibles :\n"
                        "• **3×3m** (9 m²) — 5.000 $ — 2 pass délégués, 30 places\n"
                        "• **2×3m** (6 m²) — 3.500 $ — 1 pass délégué, 5 places\n\n"
                        "👉 Tapez **1** (3×3m) ou **2** (2×3m)."
                    )
                )
                # On ouvre le sous-menu exposant : l'utilisateur veut clairement un stand.
                return _bump_fail(tracker, dispatcher, "reg_category",
                                  extra={"_reg_category_phase": phase or "exposant"})

            # ── Participant VIP : souscription en ligne distincte, hors formulaire ──
            # 300 $ / jour sur sponsor/souscription-vip.php. Ce n'est pas une
            # catégorie acceptée par l'API d'inscription : ne jamais la mapper sur
            # « Participant Simple » (gratuit), ce serait une fausse promesse.
            if re.search(r'\bvip\b', val):
                dispatcher.utter_message(
                    text=(
                        "🌟 Le **Participant VIP** est une souscription distincte : "
                        "**300 $ par jour**, avec accès privilégiés et branding dédié "
                        "sur les journées choisies (07-10 octobre 2026).\n\n"
                        "Elle se règle en ligne ici :\n"
                        "👉 https://expobetonrdc.com/sponsor/souscription-vip.php\n\n"
                        "Ce formulaire gère les catégories **Sponsor**, **Exposant** et "
                        "**Participant Simple** (gratuit). Laquelle choisissez-vous ?"
                    )
                )
                return _bump_fail(tracker, dispatcher, "reg_category",
                                  extra={"_reg_category_phase": None})

            # ── Sponsor sub-menu active ──
            if phase == "sponsor":
                if val in sponsor_num:
                    return _category_slot_updates(sponsor_num[val])
                name_match = CATEGORY_MAP.get(val)
                if name_match and name_match not in ("_sponsor_", "_exposant_"):
                    return _category_slot_updates(name_match)
                # Invalid input — keep phase, action_ask will re-show sponsor menu
                return _bump_fail(tracker, dispatcher, "reg_category", extra={"_reg_category_phase": phase})

            # ── Exposant sub-menu active ──
            if phase == "exposant":
                if val in stand_num:
                    return _category_slot_updates(stand_num[val])
                name_match = CATEGORY_MAP.get(val)
                if name_match and name_match not in ("_sponsor_", "_exposant_"):
                    return _category_slot_updates(name_match)
                # Invalid input — keep phase, action_ask will re-show exposant menu
                return _bump_fail(tracker, dispatcher, "reg_category", extra={"_reg_category_phase": phase})

            # ── Main menu context ──
            normalized = CATEGORY_MAP.get(val)
            if normalized == "_sponsor_":
                # Set phase so action_ask_reg_category shows sponsor sub-menu
                return {"reg_category": None, "_reg_category_phase": "sponsor", "_reg_validation_fails": 0}
            if normalized == "_exposant_":
                # Set phase so action_ask_reg_category shows exposant sub-menu
                return {"reg_category": None, "_reg_category_phase": "exposant", "_reg_validation_fails": 0}
            if normalized:
                return _category_slot_updates(normalized)
            if slot_value in VALID_CATEGORIES:
                return _category_slot_updates(slot_value)

        # Invalid input — reset to main menu and bump fail counter
        return _bump_fail(tracker, dispatcher, "reg_category", extra={"_reg_category_phase": None})

    def validate_reg_payment(
        self, slot_value: Any, dispatcher: CollectingDispatcher,
        tracker: Tracker, domain: DomainDict
    ) -> Dict[Text, Any]:
        category = tracker.get_slot("reg_category")
        # Participants don't need payment
        if category == "Participant Simple":
            return {"reg_payment": "N/A"}
        if slot_value:
            val = str(slot_value).strip().lower()
            payment_map = {
                "1": "Chèque", "cheque": "Chèque", "chèque": "Chèque",
                "2": "Veuillez Facturer", "facturer": "Veuillez Facturer",
                "facture": "Veuillez Facturer", "veuillez facturer": "Veuillez Facturer",
            }
            normalized = payment_map.get(val)
            if normalized:
                return {"reg_payment": normalized}
            # Fuzzy match
            for method in VALID_PAYMENT_METHODS:
                if val in method.lower() or method.lower() in val:
                    return {"reg_payment": method}
        dispatcher.utter_message(
            text=(
                "💳 Veuillez choisir un mode de paiement :\n\n"
                "1️⃣ **Chèque** — vous réglerez par chèque à l'ordre d'EXPO BÉTON ASBL\n"
                "2️⃣ **Veuillez Facturer** — nous vous envoyons une facture pro forma, "
                "à régler par virement bancaire\n\n"
                "👉 Tapez **1** ou **2**.\n\n"
                "ℹ️ Le paiement en ligne immédiat (Visa, MasterCard, M-Pesa, Orange "
                "Money, Airtel Money via FlexPay) se fait sur le tunnel du site : "
                "https://expobetonrdc.com/sponsor/paiement.html"
            )
        )
        return {"reg_payment": None}

    def validate_reg_visa(
        self, slot_value: Any, dispatcher: CollectingDispatcher,
        tracker: Tracker, domain: DomainDict
    ) -> Dict[Text, Any]:
        """Oui/non strict pour l'assistance visa.

        Sans validateur, le slot acceptait n'importe quel texte brut : un
        utilisateur qui répondait « **3** » voyait « 9. Visa : **3** » dans son
        récapitulatif, et cette valeur partait telle quelle vers l'API.
        """
        answer = _match_yesno(slot_value)
        if answer is True:
            dispatcher.utter_message(
                text=(
                    "🛂 Parfait. Une **lettre d'invitation officielle** vous sera "
                    "envoyée par e-mail après validation de votre inscription, pour "
                    "faciliter l'obtention de votre visa.\n\n"
                    "📄 Il vous sera demandé une **copie de votre passeport** valide "
                    "au moins 6 mois (PDF, 10 Mo maximum)."
                )
            )
            return {"reg_visa": "Oui", "_reg_validation_fails": 0}
        if answer is False:
            return {"reg_visa": "Non", "_reg_validation_fails": 0}
        dispatcher.utter_message(
            text=(
                "🛂 Avez-vous besoin d'une **lettre d'invitation** pour obtenir un "
                "visa pour la RDC ?\n\n👉 Répondez simplement **oui** ou **non**."
            )
        )
        return _bump_fail(tracker, dispatcher, "reg_visa")

    def validate_reg_history(
        self, slot_value: Any, dispatcher: CollectingDispatcher,
        tracker: Tracker, domain: DomainDict
    ) -> Dict[Text, Any]:
        """Oui/non strict pour « avez-vous déjà participé à une édition ».

        Même faille que ``reg_visa`` : aucun validateur n'existait, la valeur
        brute était transmise à l'API.
        """
        answer = _match_yesno(slot_value)
        if answer is True:
            return {"reg_history": "Oui", "_reg_validation_fails": 0}
        if answer is False:
            return {"reg_history": "Non", "_reg_validation_fails": 0}
        dispatcher.utter_message(
            text=(
                "📊 Avez-vous **déjà participé** à une édition précédente d'ExpoBeton ?\n\n"
                "👉 Répondez simplement **oui** ou **non**."
            )
        )
        return _bump_fail(tracker, dispatcher, "reg_history")


# ═══════════════════════════════════════════════════════════════════════
# Helper: build upload descriptors + Submit Registration + Review Form
# ═══════════════════════════════════════════════════════════════════════

def _display_first_name(tracker):
    """Return the user's first name for display, preferring the registration
    contact name over the ``person`` slot (which can be polluted by entity
    extraction on later form answers such as city/country).
    """
    contact = tracker.get_slot("reg_contact_name")
    if contact and str(contact).strip():
        return str(contact).strip().split()[0].title()
    person = tracker.get_slot("person")
    if person and str(person).strip():
        return str(person).strip().split()[0].title()
    return None


def _looks_like_phone(value):
    """Heuristic: is this string most likely a phone number a user pasted in
    the wrong slot?"""
    if not value:
        return False
    raw = str(value).strip()
    digits = re.sub(r'\D', '', raw)
    # At least 8 digits AND the digits make up the bulk of the string (>=70%)
    if len(digits) < 8:
        return False
    return (len(digits) / max(len(raw), 1)) >= 0.6


def _category_slot_updates(category):
    """Slot updates when a registration category has just been resolved.

    « Participant Simple » est gratuit : l'étape « Paiement » doit être sautée.
    Or ``reg_payment`` figure dans ``required_slots`` du formulaire — tant que le
    slot est vide, Rasa pose la question, puis le validateur la jette. Le
    pré-remplir avec « N/A » est le moyen natif de passer l'étape sans retoucher
    le domaine (un slot déjà rempli n'est pas redemandé).
    """
    out = {
        "reg_category": category,
        "_reg_category_phase": None,
        "_reg_validation_fails": 0,
    }
    if category == "Participant Simple":
        out["reg_payment"] = "N/A"
    return out


_YESNO = {
    "oui": True, "yes": True, "y": True, "o": True, "si": True,
    "yep": True, "yeah": True, "ok": True, "d'accord": True,
    "je veux": True, "j'en ai besoin": True, "besoin": True,
    "volontiers": True,
    "non": False, "no": False, "n": False, "nope": False,
    "non merci": False, "pas besoin": False, "aucun besoin": False,
}


def _match_yesno(value):
    """Interprète une réponse oui/non. Renvoie True, False ou None si ambigu.

    Les étapes « visa » et « historique » n'avaient aucun validateur : le slot
    acceptait n'importe quel texte brut — y compris « **3** » (markdown collé) ou
    une question entière — qui se retrouvait tel quel dans le récapitulatif
    envoyé à l'API.
    """
    if value is None:
        return None
    raw = str(value).strip().lower()
    # Markdown et ponctuation retirés : « **oui** » -> « oui », « **3** » -> « 3 ».
    raw = re.sub(r"[^0-9a-zà-ÿ' ]", " ", raw)
    raw = re.sub(r"\s+", " ", raw).strip()
    if not raw:
        return None
    if raw in _YESNO:
        return _YESNO[raw]
    # Formules négatives composées testées AVANT les affirmatives, sinon
    # « pas besoin » serait lu comme « besoin » (affirmatif).
    if re.search(r"\b(pas|aucun|aucune|no|non|never|jamais)\b", raw):
        return False
    if re.search(r"\b(oui|yes|besoin|veux|volontiers|ok|yep|yeah)\b", raw):
        return True
    return None


def _bump_fail(tracker, dispatcher, slot_name, extra=None):
    """Increment the consecutive validation-fail counter and, after 2+ fails,
    suggest help / human handoff while keeping the slot empty so the form
    re-asks the same question."""
    fails = (tracker.get_slot("_reg_validation_fails") or 0) + 1
    if fails >= 2:
        dispatcher.utter_message(
            text=(
                "🤝 On dirait que cette étape pose problème. \n\nà tout moment, vous pouvez :\n"
                "• Taper **« je comprends pas »** pour obtenir plus d'explications\n"
                "• Taper **« recommencer »** pour annuler et repartir de zéro\n"
                "• Taper **« contact humain »** pour qu'un membre de l'équipe vous aide\n"
                "• Ou écrire à **info@expobetonrdc.com**"
            )
        )
    out = {slot_name: None, "_reg_validation_fails": fails}
    if extra:
        out.update(extra)
    return out


def _build_upload_list(category, visa):
    """Return a list of upload descriptor dicts needed for this registration."""
    uploads = []
    if category and category != "Participant Simple":
        uploads.append({
            "type": "logo",
            "accept": ".jpg,.jpeg,.png,.gif,.svg",
            "max_size_mb": 10,
            "label": "Logo de votre entreprise",
            "description": "Votre logo sera utilisé sur les supports de communication.\nFormats acceptés : JPG, PNG, SVG - Max 10 MB",
        })
    if visa and str(visa).lower() == "oui":
        uploads.append({
            "type": "passport",
            "accept": ".pdf",
            "max_size_mb": 10,
            "label": "Copie de votre passeport",
            "description": "Nécessaire pour votre invitation visa.\nFormat accepté : PDF uniquement - Max 10 MB",
        })
    return uploads


REG_FIELDS = [
    (1,  "Entreprise",  "reg_company",      "Quel est le nom de votre entreprise ou organisation ?"),
    (2,  "Contact",     "reg_contact_name", "Quel est le nom complet de la personne de contact ?"),
    (3,  "Email",       "reg_email",        "Quelle est votre adresse email ?"),
    (4,  "Telephone",   "reg_phone",        "Quel est votre numero de telephone ?"),
    (5,  "Pays",        "reg_country",      "De quel pays venez-vous ?"),
    (6,  "Ville",       "reg_city",         "Dans quelle ville etes-vous ?"),
    (7,  "Categorie",   "reg_category",     "Quelle categorie ? (Platinum, Gold, Bronze, Silver, Exposant Stand 3x3m/2x3m, Participant Simple)"),
    (8,  "Paiement",    "reg_payment",      "Mode de paiement ? (1. Cheque  2. Veuillez Facturer)"),
    (9,  "Visa",        "reg_visa",         "Avez-vous besoin d'une assistance visa ? (oui/non)"),
    (10, "Historique",  "reg_history",      "Avez-vous deja participe a ExpoBeton ? (oui/non)"),
]


class ActionSubmitRegistration(Action):
    """Triggered when registration_form completes.
    Does NOT call the API yet - sends upload cards to the widget.
    After uploads, the widget triggers /registration_review.
    """

    def name(self) -> Text:
        return "action_submit_registration"

    def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict
    ) -> List[Dict[Text, Any]]:

        category = tracker.get_slot("reg_category")
        visa = tracker.get_slot("reg_visa") or "non"
        uploads = _build_upload_list(category, visa)

        first_name = _display_first_name(tracker)
        name_suffix = f" {first_name}" if first_name else ""

        upload_base = os.getenv(
            "EXPOBETON_UPLOAD_URL",
            "https://expobetonrdc.com/upload_documents.php"
        )

        events = []

        if uploads:
            dispatcher.utter_message(
                text=f"Merci{name_suffix} ! Avant de finaliser, veuillez fournir les documents suivants."
            )
            dispatcher.utter_message(
                json_message={
                    "upload_sequence": {
                        "uploads": uploads,
                        "upload_url_base": upload_base,
                        "auth_header": f"Bearer {EXPOBETON_API_KEY}",
                        "mode": "local_store",
                        "on_complete_trigger": "/registration_review",
                    }
                }
            )
            # Fallback for non-widget channels
            fallback = f"Documents à fournir{name_suffix} :\n\n"
            for u in uploads:
                fallback += f"- {u['label']}\n"
            fallback += "\nAprès avoir préparé vos documents, tapez « ok » pour continuer."
            dispatcher.utter_message(text=fallback)
            for u in uploads:
                events.append(SlotSet(f"_reg_{u['type']}_file", None))
        else:
            # No uploads needed - go straight to review
            dispatcher.utter_message(
                json_message={"trigger_message": "/registration_review"}
            )
            dispatcher.utter_message(
                text=f"Merci{name_suffix} ! Vérification de vos informations..."
            )

        return events


# ═══════════════════════════════════════════════════════════════════════
# Action: Show numbered summary (ask for _reg_confirmed)
# ═══════════════════════════════════════════════════════════════════════

class ActionAskRegConfirmed(Action):
    """Displays the numbered summary so the user can edit or confirm."""

    def name(self) -> Text:
        return "action_ask__reg_confirmed"

    def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict
    ) -> List[Dict[Text, Any]]:
        lines = ["📋 **Résumé de votre inscription**\n"]
        for num, label, slot, _ in REG_FIELDS:
            val = tracker.get_slot(slot) or "--"
            lines.append(f"{num}. {label} : {val}")

        # File status lines
        category = tracker.get_slot("reg_category")
        visa = tracker.get_slot("reg_visa") or "non"
        if category and category != "Participant Simple":
            logo_status = "sélectionné" if tracker.get_slot("_reg_logo_file") else "non fourni"
            lines.append(f"11. Logo : {logo_status}")
        if str(visa).lower() == "oui":
            passport_status = "sélectionné" if tracker.get_slot("_reg_passport_file") else "non fourni"
            lines.append(f"12. Passeport : {passport_status}")

        lines.append("\n👉 Tapez un numéro (1-12) pour modifier, ou « ok » pour confirmer.")
        dispatcher.utter_message(text="\n".join(lines))
        return [SlotSet("_reg_edit_field", None)]


# ═══════════════════════════════════════════════════════════════════════
# Validator: Registration Review Form
# ═══════════════════════════════════════════════════════════════════════

class ValidateRegistrationReviewForm(FormValidationAction):
    """Handles user input during the review summary."""

    def name(self) -> Text:
        return "validate_registration_review_form"

    def validate__reg_confirmed(
        self, slot_value: Any, dispatcher: CollectingDispatcher,
        tracker: Tracker, domain: DomainDict
    ) -> Dict[Text, Any]:
        text = str(slot_value).strip().lower()
        edit_field = tracker.get_slot("_reg_edit_field")

        # Currently in edit mode: save the new value
        if edit_field:
            target_slot = None
            for _, _, slot, _ in REG_FIELDS:
                if slot == edit_field:
                    target_slot = slot
                    break
            if target_slot:
                dispatcher.utter_message(text="✅ Mis à jour !")
                return {
                    "_reg_confirmed": None,
                    "_reg_edit_field": None,
                    target_slot: slot_value.strip() if isinstance(slot_value, str) else slot_value,
                }
            return {"_reg_confirmed": None, "_reg_edit_field": None}

        # Number 1-10: enter edit mode
        if text.isdigit():
            num = int(text)
            if 1 <= num <= 10:
                for n, label, slot, question in REG_FIELDS:
                    if n == num:
                        dispatcher.utter_message(text=question)
                        return {"_reg_confirmed": None, "_reg_edit_field": slot}
            if num == 11:
                category = tracker.get_slot("reg_category")
                if category and category != "Participant Simple":
                    upload_base = os.getenv(
                        "EXPOBETON_UPLOAD_URL",
                        "https://expobetonrdc.com/upload_documents.php"
                    )
                    dispatcher.utter_message(
                        json_message={
                            "single_upload_card": {
                                "type": "logo",
                                "accept": ".jpg,.jpeg,.png,.gif,.svg",
                                "max_size_mb": 10,
                                "label": "Logo de votre entreprise",
                                "description": "Formats acceptés : JPG, PNG, SVG - Max 10 MB",
                                "mode": "local_store",
                                "upload_url_base": upload_base,
                                "auth_header": f"Bearer {EXPOBETON_API_KEY}",
                                "on_complete_trigger": "/registration_review",
                            }
                        }
                    )
                    return {"_reg_confirmed": None}
                else:
                    dispatcher.utter_message(text="Le logo n'est pas requis pour votre catégorie.")
                    return {"_reg_confirmed": None}
            if num == 12:
                visa = tracker.get_slot("reg_visa") or "non"
                if str(visa).lower() == "oui":
                    upload_base = os.getenv(
                        "EXPOBETON_UPLOAD_URL",
                        "https://expobetonrdc.com/upload_documents.php"
                    )
                    dispatcher.utter_message(
                        json_message={
                            "single_upload_card": {
                                "type": "passport",
                                "accept": ".pdf",
                                "max_size_mb": 10,
                                "label": "Copie de votre passeport",
                                "description": "Format accepté : PDF uniquement - Max 10 MB",
                                "mode": "local_store",
                                "upload_url_base": upload_base,
                                "auth_header": f"Bearer {EXPOBETON_API_KEY}",
                                "on_complete_trigger": "/registration_review",
                            }
                        }
                    )
                    return {"_reg_confirmed": None}
                else:
                    dispatcher.utter_message(text="Le passeport n'est pas requis (visa = non).")
                    return {"_reg_confirmed": None}

        # Confirmation keywords
        if text in ("ok", "oui", "confirmer", "c'est bon", "valider", "confirm", "yes"):
            return {"_reg_confirmed": "confirmed"}

        # Unrecognised input
        dispatcher.utter_message(text="Tapez un numéro (1-12) pour modifier ou « ok » pour confirmer.")
        return {"_reg_confirmed": None}


# ═══════════════════════════════════════════════════════════════════════
# Action: Confirm registration - calls API then triggers file uploads
# ═══════════════════════════════════════════════════════════════════════

class ActionConfirmRegistration(Action):
    """Called after user confirms the summary.
    Calls the API, then sends do_uploads to the widget.
    """

    def name(self) -> Text:
        return "action_confirm_registration"

    def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict
    ) -> List[Dict[Text, Any]]:
        data = {
            "company":        tracker.get_slot("reg_company"),
            "edition":        12,  # current edition (Kinshasa 2026)
            "contact_name":   tracker.get_slot("reg_contact_name"),
            "email":          tracker.get_slot("reg_email"),
            "phone":          tracker.get_slot("reg_phone"),
            "prefix":         tracker.get_slot("reg_phone_prefix") or "+243",
            "country":        tracker.get_slot("reg_country"),
            "city":           tracker.get_slot("reg_city"),
            "address":        tracker.get_slot("reg_address") or "",
            "postal":         tracker.get_slot("reg_postal") or "",
            "category":       tracker.get_slot("reg_category"),
            "payment":        tracker.get_slot("reg_payment"),
            "visa":           tracker.get_slot("reg_visa") or "non",
            "history":        tracker.get_slot("reg_history") or "non",
        }

        first_name = _display_first_name(tracker)
        name_suffix = f" {first_name}" if first_name else ""

        dispatcher.utter_message(text="Soumission de votre inscription en cours...")

        result = ExpoBetonAPI.register(data)

        if result.get("success"):
            if result.get("duplicate"):
                ref = result.get("reference", "N/A")
                dispatcher.utter_message(
                    text=(
                        f"ℹ️ Vous êtes déjà inscrit(e) !\n"
                        f"Référence : **{ref}**\n"
                        f"Statut : {result.get('status', 'en attente')}\n\n"
                        f"Contactez info@expobetonrdc.com pour toute modification."
                    )
                )
                return [AllSlotsReset()]

            ref = result.get("data", {}).get("reference", "N/A")

            # Mirror the registration (session id + phone included) into the
            # admincb dashboard registrations table (fire-and-forget).
            try:
                requests.post(
                    f"{ADMINCB_ANALYTICS_URL}?action=registration&api_key={EXPOBETON_API_KEY}",
                    json={
                        "session_id":       tracker.sender_id,
                        "reference_number": ref,
                        "category":         data["category"],
                        "company":          data["company"],
                        "contact_name":     data["contact_name"],
                        "email":            data["email"],
                        "phone":            data["phone"],
                        "country":          data["country"],
                    },
                    headers={"Accept": "application/json", "User-Agent": "RasaChatbot/1.0 ExpoBeton"},
                    timeout=10,
                )
            except Exception as e:
                logger.error(f"AdminCB registration sync failed: {e}")

            upload_base = os.getenv(
                "EXPOBETON_UPLOAD_URL",
                "https://expobetonrdc.com/upload_documents.php"
            )

            # Tell widget to upload stored files now
            uploads = _build_upload_list(data["category"], data["visa"])
            if uploads:
                dispatcher.utter_message(
                    json_message={
                        "do_uploads": {
                            "ref": ref,
                            "upload_url_base": upload_base,
                            "auth_header": f"Bearer {EXPOBETON_API_KEY}",
                            "uploads": [u["type"] for u in uploads],
                        }
                    }
                )

            # Le bot affirmait systématiquement qu'un e-mail de confirmation avait
            # été envoyé. Or api_chatbot_register.php tourne en mode silencieux
            # ($SILENT_REGISTRATION = true) : le champ « email_sent » vaut false et
            # l'utilisateur attendait en vain un message qui n'arriverait jamais.
            # On lit donc la réponse réelle de l'API.
            email_sent = bool(result.get("data", {}).get("email_sent", False))
            if email_sent:
                email_line = (
                    f"📧 Un e-mail de confirmation a été envoyé à **{data['email']}** "
                    f"(pensez à vérifier vos courriers indésirables).\n\n"
                    f"🎫 Votre **badge d'accès** au format PDF vous parviendra par "
                    f"e-mail une fois le dossier validé."
                )
            else:
                email_line = (
                    f"⚠️ **Aucun e-mail automatique n'est envoyé pour le moment.** "
                    f"Votre inscription est bien **enregistrée** — conservez votre "
                    f"numéro de référence ci-dessus.\n\n"
                    f"👉 Notre équipe vous contactera à **{data['email']}** dans les "
                    f"48 heures pour la validation et l'envoi de votre **badge d'accès**."
                )

            dispatcher.utter_message(
                text=(
                    f"🎉 Félicitations{name_suffix} ! "
                    f"Votre inscription à **ExpoBeton RDC 2026** a bien été enregistrée.\n\n"
                    f"🔖 Numéro de référence : **{ref}**\n"
                    f"{email_line}\n\n"
                    f"Pour toute question : info@expobetonrdc.com"
                )
            )
        else:
            errors = result.get("errors", [])
            error_msg = "\n".join(f"- {e}" for e in errors) if errors else result.get("error", "Erreur inconnue")
            dispatcher.utter_message(
                text=f"L'inscription n'a pas pu être complétée :\n{error_msg}\n\nVeuillez réessayer ou contacter info@expobetonrdc.com"
            )

        return [AllSlotsReset()]


# ===================================================================
# Action: Submit Ambassador Application
# ===================================================================

class ActionSubmitAmbassador(Action):
    def name(self) -> Text:
        return "action_submit_ambassador"

    def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict
    ) -> List[Dict[Text, Any]]:

        data = {
            "identity":     tracker.get_slot("amb_identity"),
            "gender":       tracker.get_slot("amb_gender"),
            "phone":        tracker.get_slot("amb_phone"),
            "email":        tracker.get_slot("amb_email"),
            "company":      tracker.get_slot("amb_company"),
            "country":      tracker.get_slot("amb_country"),
            "city":         tracker.get_slot("amb_city"),
            "think_tank":   tracker.get_slot("amb_think_tank"),
            "contribution": tracker.get_slot("amb_contribution"),
            "experience":   tracker.get_slot("amb_experience") or "non",
        }

        dispatcher.utter_message(text="Soumission de votre candidature ambassadeur en cours...")

        result = ExpoBetonAPI.submit_ambassador(data)

        if result.get("success"):
            ref = result.get("data", {}).get("reference", "N/A")
            dispatcher.utter_message(
                text=(
                    f"🎉 Candidature ambassadeur soumise !\n\n"
                    f"🔖 Référence : **{ref}**\n"
                    f"Nous examinerons votre candidature et vous recontacterons.\n"
                    f"Contact : info@expobetonrdc.com"
                )
            )
        else:
            errors = result.get("errors", [])
            error_msg = "\n".join(f"- {e}" for e in errors) if errors else result.get("error", "Erreur inconnue")
            dispatcher.utter_message(
                text=f"La candidature n'a pas pu être soumise :\n{error_msg}"
            )

        return [AllSlotsReset()]


# ===================================================================
# Action: In-form contextual help (triggered by intent: dont_understand)
# ===================================================================

class ActionFormHelp(Action):
    """Provide context-aware help based on the slot the form is currently asking."""

    def name(self) -> Text:
        return "action_form_help"

    def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict
    ) -> List[Dict[Text, Any]]:
        slot = tracker.get_slot("requested_slot")
        phase = tracker.get_slot("_reg_category_phase")

        helps = {
            "reg_company": (
                "🏢 J'ai besoin du **nom de votre entreprise ou organisation**.\n\n"
                "Exemples : *Acme Construction SARL*, *Université de Kinshasa*, *Mairie de Lubumbashi*.\n\n"
                "Si vous êtes un particulier, indiquez votre nom complet."
            ),
            "reg_contact_name": (
                "👤 J'ai besoin du **nom et prénom** de la personne à contacter pour cette inscription.\n\n"
                "Exemples : *Jean Mukendi*, *Marie Kabasele*."
            ),
            "reg_email": (
                "📧 J'ai besoin d'une **adresse email valide** où nous pourrons vous envoyer la confirmation.\n\n"
                "Format : *nom@domaine.com* (par exemple : jean.mukendi@gmail.com)."
            ),
            "reg_phone": (
                "📞 J'ai besoin de votre **numéro de téléphone** (au moins 8 chiffres).\n\n"
                "Exemples : *+243 81 234 5678*, *0812345678*, *+33 6 12 34 56 78*."
            ),
            "reg_country": (
                "🌍 J'ai besoin de votre **pays de résidence ou de l'entreprise**.\n\n"
                "Exemples : *RDC*, *France*, *Belgique*, *Cameroun*."
            ),
            "reg_city": (
                "🏙️ J'ai besoin de votre **ville principale** (une seule).\n\n"
                "Exemples : *Kinshasa*, *Lubumbashi*, *Goma*, *Paris*."
            ),
            "reg_category": (
                "📋 Je vous demande dans quelle **catégorie** vous souhaitez participer :\n\n"
                "• 🏆 **Sponsor** — vous soutenez l'événement (visibilité maximale, "
                "de 10.000 $ à 40.000 $ selon le palier)\n"
                "• 🏗️ **Exposant** — vous avez un stand pour exposer vos produits "
                "(3×3m à 5.000 $ ou 2×3m à 3.500 $)\n"
                "• 👤 **Participant Simple** — vous assistez sans stand (gratuit)\n\n"
                "👉 Tapez **1**, **2** ou **3** selon votre choix."
            ),
            "reg_payment": (
                "💳 Je vous demande comment vous souhaitez **payer** votre inscription :\n\n"
                "• **Chèque** — vous nous enverrez un chèque après confirmation\n"
                "• **Veuillez Facturer** — nous vous envoyons une facture pro forma\n\n"
                "👉 Tapez **1** pour Chèque ou **2** pour Veuillez Facturer."
            ),
            "reg_visa": (
                "🛂 Je vous demande si vous avez besoin d'une **lettre d'invitation** pour obtenir un visa pour la RDC.\n\n"
                "👉 Répondez **oui** ou **non**."
            ),
            "reg_history": (
                "📊 Je vous demande si vous avez **déjà participé** à une édition précédente d'ExpoBeton.\n\n"
                "👉 Répondez **oui** ou **non**."
            ),
        }

        # Special-case sub-menus for category
        if slot == "reg_category" and phase == "sponsor":
            dispatcher.utter_message(
                text=(
                    "🏆 Choisissez votre **palier de sponsoring** :\n\n"
                    "• **Platinum** (40.000 $) — visibilité maximale, stand 45 m², 5 pass\n"
                    "• **Gold** (20.000 $) — forte visibilité, stand 20 m², 3 pass\n"
                    "• **Bronze** (15.000 $) — bonne visibilité, stand 15 m², 2 pass\n"
                    "• **Silver** (10.000 $) — visibilité de base, stand 12 m², 2 pass\n\n"
                    "👉 Tapez **1** (Platinum), **2** (Gold), **3** (Bronze) ou **4** (Silver)."
                )
            )
        elif slot == "reg_category" and phase == "exposant":
            dispatcher.utter_message(
                text=(
                    "🏗️ Choisissez votre **type de stand** :\n\n"
                    "• **3×3m** (9 m²) — 5.000 $ — stand grand format, "
                    "2 pass délégués et 30 places de parking\n"
                    "• **2×3m** (6 m²) — 3.500 $ — stand compact, idéal découverte, "
                    "1 pass délégué et 5 places\n\n"
                    "👉 Tapez **1** (3×3m) ou **2** (2×3m)."
                )
            )
        elif slot in helps:
            dispatcher.utter_message(text=helps[slot])
        else:
            dispatcher.utter_message(
                text=(
                    "Pas de souci, je vais reformuler. 😊\n\n"
                    "À tout moment, vous pouvez taper **« recommencer »** pour annuler l'inscription, "
                    "ou **« contact humain »** pour qu'un membre de l'équipe vous contacte."
                )
            )
        return []


# ===================================================================
# Action: Cancel an in-progress registration form
# ===================================================================

class ActionCancelRegistration(Action):
    """Reset all registration slots so the form can be restarted cleanly."""

    def name(self) -> Text:
        return "action_cancel_registration"

    def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict
    ) -> List[Dict[Text, Any]]:
        dispatcher.utter_message(
            text=(
                "🔄 D'accord, j'annule l'inscription en cours. Vos informations saisies sont effacées.\n\n"
                "Tapez **« je veux m'inscrire »** quand vous serez prêt à recommencer, ou posez-moi "
                "une autre question sur ExpoBeton RDC. 😊"
            )
        )
        from rasa_sdk.events import ActiveLoop
        # Reset all registration-related slots
        return [
            ActiveLoop(None),
            SlotSet("requested_slot", None),
            SlotSet("reg_company", None),
            SlotSet("reg_contact_name", None),
            SlotSet("reg_email", None),
            SlotSet("reg_phone", None),
            SlotSet("reg_country", None),
            SlotSet("reg_city", None),
            SlotSet("reg_category", None),
            SlotSet("reg_payment", None),
            SlotSet("reg_visa", None),
            SlotSet("reg_history", None),
            SlotSet("_reg_category_phase", None),
            SlotSet("_reg_validation_fails", 0),
            SlotSet("_reg_logo_file", None),
            SlotSet("_reg_passport_file", None),
            SlotSet("registration_pending", None),
        ]


# ===================================================================
# Action: Check API Health
# ===================================================================

class ActionCheckApiHealth(Action):
    def name(self) -> Text:
        return "action_check_api_health"

    def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict
    ) -> List[Dict[Text, Any]]:
        result = ExpoBetonAPI.health_check()
        if result.get("success"):
            dispatcher.utter_message(text="ExpoBeton registration system is online.")
        else:
            dispatcher.utter_message(text="Registration system is temporarily unavailable. Please try later.")
        return []
