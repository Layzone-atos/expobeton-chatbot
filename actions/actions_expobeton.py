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
                f'Pour participer à **ExpoBeton RDC 2026** (27-30 mai, Kalemie), '
                f'vous devez vous inscrire{greeting}.\n\n'
                f'📋 **3 catégories disponibles :**\n'
                f'1️⃣ 🏆 **Sponsor** (Platinum/Gold/Silver/Bronze)\n'
                f'2️⃣ 🏗️ **Exposant** (stand 3×3m, 2×4m ou 2×3m)\n'
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
            "1️⃣ **🏆 Sponsor**\n"
            "   • Platinum — 40.000 $\n"
            "   • Gold — 20.000 $\n"
            "   • Silver — 15.000 $\n"
            "   • Bronze — 12.000 $\n\n"
            "2️⃣ **🏗️ Exposant**\n"
            "   • Stand 3×3m — 5.000 $\n"
            "   • Stand 2×4m — 3.000 $\n"
            "   • Stand 2×3m — 2.000 $\n\n"
            "3️⃣ **👤 Participant Simple** (Gratuit)\n\n"
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
    # Sponsor sub-levels (dotted numbers)
    "1.1": "Platinum", "1.2": "Gold", "1.3": "Silver", "1.4": "Bronze",
    # Direct names
    "platinum": "Platinum",
    "gold": "Gold",
    "silver": "Silver",
    "bronze": "Bronze",
    "exposant 3x3": "Exposant Stand 3x3m",
    "exposant 2x4": "Exposant Stand 2x4m",
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
    "exposant, 2x4": "Exposant Stand 2x4m",
    "exposant, 2x3": "Exposant Stand 2x3m",
    # Stand variations
    "stand 3x3": "Exposant Stand 3x3m",
    "stand 2x4": "Exposant Stand 2x4m",
    "stand 2x3": "Exposant Stand 2x3m",
    "3x3": "Exposant Stand 3x3m",
    "2x4": "Exposant Stand 2x4m",
    "2x3": "Exposant Stand 2x3m",
    "3x3m": "Exposant Stand 3x3m",
    "2x4m": "Exposant Stand 2x4m",
    "2x3m": "Exposant Stand 2x3m",
    "exposant": "_exposant_",
    "stand": "_exposant_",
    # Participant variations
    "gratuit": "Participant Simple",
    "free": "Participant Simple",
    "simple": "Participant Simple",
    "visiteur": "Participant Simple",
}


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

        if phase == "sponsor":
            dispatcher.utter_message(
                text="🏆 **Choisissez votre niveau de sponsoring :**\n\n"
                     "1️⃣ Platinum — 40.000 $\n"
                     "2️⃣ Gold — 20.000 $\n"
                     "3️⃣ Silver — 15.000 $\n"
                     "4️⃣ Bronze — 12.000 $\n\n"
                     "Tapez le numéro ou le nom du niveau."
            )
        elif phase == "exposant":
            dispatcher.utter_message(
                text="🏗️ **Choisissez votre type de stand :**\n\n"
                     "1️⃣ Stand 3×3m — 5.000 $\n"
                     "2️⃣ Stand 2×4m — 3.000 $\n"
                     "3️⃣ Stand 2×3m — 2.000 $\n\n"
                     "Tapez le numéro ou le type de stand."
            )
        else:
            dispatcher.utter_message(
                text="📋 Pour quelle catégorie souhaitez-vous vous inscrire ?\n\n"
                     "1️⃣ 🏆 **Sponsor** (Platinum, Gold, Silver, Bronze)\n"
                     "2️⃣ 🏗️ **Exposant** (Stand 3×3m, 2×4m, 2×3m)\n"
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

    def validate_reg_company(
        self, slot_value: Any, dispatcher: CollectingDispatcher,
        tracker: Tracker, domain: DomainDict
    ) -> Dict[Text, Any]:
        if slot_value and len(str(slot_value).strip()) >= 2:
            return {"reg_company": slot_value.strip(), "_reg_validation_fails": 0}
        dispatcher.utter_message(text="Veuillez fournir un nom d'entreprise ou d'organisation valide (au moins 2 caractères).")
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
        # Accept human-friendly inputs like "whatsapp : 00971 56 123 4567"
        # by extracting only digits and an optional leading '+'.
        raw = str(slot_value or '')
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
                "Veuillez fournir un numéro de téléphone valide (au moins 8 chiffres). "
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
        sponsor_num = {"1": "Platinum", "2": "Gold", "3": "Silver", "4": "Bronze"}
        stand_num = {"1": "Exposant Stand 3x3m", "2": "Exposant Stand 2x4m", "3": "Exposant Stand 2x3m"}
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

            # ── Sponsor sub-menu active ──
            if phase == "sponsor":
                if val in sponsor_num:
                    return {"reg_category": sponsor_num[val], "_reg_category_phase": None, "_reg_validation_fails": 0}
                name_match = CATEGORY_MAP.get(val)
                if name_match and name_match not in ("_sponsor_", "_exposant_"):
                    return {"reg_category": name_match, "_reg_category_phase": None, "_reg_validation_fails": 0}
                # Invalid input — keep phase, action_ask will re-show sponsor menu
                return _bump_fail(tracker, dispatcher, "reg_category", extra={"_reg_category_phase": phase})

            # ── Exposant sub-menu active ──
            if phase == "exposant":
                if val in stand_num:
                    return {"reg_category": stand_num[val], "_reg_category_phase": None, "_reg_validation_fails": 0}
                name_match = CATEGORY_MAP.get(val)
                if name_match and name_match not in ("_sponsor_", "_exposant_"):
                    return {"reg_category": name_match, "_reg_category_phase": None, "_reg_validation_fails": 0}
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
                return {"reg_category": normalized, "_reg_category_phase": None, "_reg_validation_fails": 0}
            if slot_value in VALID_CATEGORIES:
                return {"reg_category": slot_value, "_reg_category_phase": None, "_reg_validation_fails": 0}

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
            text="Veuillez choisir un mode de paiement :\n\n"
                 "1️⃣ Chèque\n"
                 "2️⃣ Veuillez Facturer\n\n"
                 "Tapez le numéro ou le nom."
        )
        return {"reg_payment": None}


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
    (7,  "Categorie",   "reg_category",     "Quelle categorie ? (Platinum, Gold, Silver, Bronze, Exposant Stand 3x3m/2x4m/2x3m, Participant Simple)"),
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

            dispatcher.utter_message(
                text=(
                    f"🎉 Félicitations{name_suffix} ! "
                    f"Votre inscription à **ExpoBeton RDC 2026** a bien été enregistrée.\n\n"
                    f"🔖 Numéro de référence : **{ref}**\n"
                    f"📧 Un email de confirmation a été envoyé à **{data['email']}**.\n\n"
                    f"Notre équipe vous contactera dans les 48 heures.\n"
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
                "• 🏆 **Sponsor** — vous soutenez l'événement (visibilité maximale, à partir de 12.000 $)\n"
                "• 🏗️ **Exposant** — vous avez un stand pour exposer vos produits (à partir de 2.000 $)\n"
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
                    "🏆 Choisissez votre **niveau de sponsoring** :\n\n"
                    "• **Platinum** (40.000 $) — visibilité maximale, logo en tête d'affiche\n"
                    "• **Gold** (20.000 $) — forte visibilité + stand premium\n"
                    "• **Silver** (15.000 $) — bonne visibilité + stand standard\n"
                    "• **Bronze** (12.000 $) — visibilité de base + stand standard\n\n"
                    "👉 Tapez **1** (Platinum), **2** (Gold), **3** (Silver) ou **4** (Bronze)."
                )
            )
        elif slot == "reg_category" and phase == "exposant":
            dispatcher.utter_message(
                text=(
                    "🏗️ Choisissez votre **type de stand** :\n\n"
                    "• **3×3m** (5.000 $) — stand grand format, recommandé pour grosse exposition\n"
                    "• **2×4m** (3.000 $) — stand moyen, bon rapport qualité-prix\n"
                    "• **2×3m** (2.000 $) — stand compact, idéal découverte\n\n"
                    "👉 Tapez **1** (3×3m), **2** (2×4m) ou **3** (2×3m)."
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
