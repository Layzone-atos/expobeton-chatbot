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
    """Greet user by name and start the registration form."""

    def name(self) -> Text:
        return "action_start_registration"

    def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict
    ) -> List[Dict[Text, Any]]:
        # Try to get the person's name from the slot (set during greeting)
        person = tracker.get_slot("person")
        if person:
            # Use only first name for friendliness
            first_name = str(person).strip().split()[0].title()
            dispatcher.utter_message(
                text=(
                    f"D'accord {first_name}, je vais vous aider à vous inscrire "
                    f"étape par étape. 😊\n\n"
                    f"Commençons votre inscription à **ExpoBeton RDC 2026** !"
                )
            )
        else:
            dispatcher.utter_message(
                text=(
                    "D'accord, je vais vous aider à vous inscrire "
                    "étape par étape. 😊\n\n"
                    "Commençons votre inscription à **ExpoBeton RDC 2026** !"
                )
            )
        return [FollowupAction("registration_form")]


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
            return {"reg_company": slot_value.strip()}
        dispatcher.utter_message(text="Veuillez fournir un nom d'entreprise ou d'organisation valide.")
        return {"reg_company": None}

    def validate_reg_contact_name(
        self, slot_value: Any, dispatcher: CollectingDispatcher,
        tracker: Tracker, domain: DomainDict
    ) -> Dict[Text, Any]:
        if slot_value and len(str(slot_value).strip()) >= 2:
            return {"reg_contact_name": slot_value.strip()}
        dispatcher.utter_message(text="Veuillez fournir le nom complet de la personne de contact.")
        return {"reg_contact_name": None}

    def validate_reg_email(
        self, slot_value: Any, dispatcher: CollectingDispatcher,
        tracker: Tracker, domain: DomainDict
    ) -> Dict[Text, Any]:
        if slot_value and re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', str(slot_value).strip()):
            return {"reg_email": slot_value.strip().lower()}
        dispatcher.utter_message(text="Veuillez fournir une adresse email valide.")
        return {"reg_email": None}

    def validate_reg_phone(
        self, slot_value: Any, dispatcher: CollectingDispatcher,
        tracker: Tracker, domain: DomainDict
    ) -> Dict[Text, Any]:
        cleaned = re.sub(r'[\s\-\(\)]', '', str(slot_value or ''))
        if len(cleaned) >= 6 and cleaned.replace('+', '').isdigit():
            return {"reg_phone": cleaned}
        dispatcher.utter_message(text="Veuillez fournir un numéro de téléphone valide (au moins 6 chiffres).")
        return {"reg_phone": None}

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
            return {"reg_country": normalized}
        dispatcher.utter_message(text="Veuillez indiquer votre pays.")
        return {"reg_country": None}

    def validate_reg_city(
        self, slot_value: Any, dispatcher: CollectingDispatcher,
        tracker: Tracker, domain: DomainDict
    ) -> Dict[Text, Any]:
        if slot_value and len(str(slot_value).strip()) >= 2:
            return {"reg_city": slot_value.strip()}
        dispatcher.utter_message(text="Veuillez indiquer votre ville.")
        return {"reg_city": None}

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
            val = str(slot_value).strip().lower()

            # ── Sponsor sub-menu active ──
            if phase == "sponsor":
                if val in sponsor_num:
                    return {"reg_category": sponsor_num[val], "_reg_category_phase": None}
                name_match = CATEGORY_MAP.get(val)
                if name_match and name_match not in ("_sponsor_", "_exposant_"):
                    return {"reg_category": name_match, "_reg_category_phase": None}
                # Invalid input — keep phase, action_ask will re-show sponsor menu
                return {"reg_category": None}

            # ── Exposant sub-menu active ──
            if phase == "exposant":
                if val in stand_num:
                    return {"reg_category": stand_num[val], "_reg_category_phase": None}
                name_match = CATEGORY_MAP.get(val)
                if name_match and name_match not in ("_sponsor_", "_exposant_"):
                    return {"reg_category": name_match, "_reg_category_phase": None}
                # Invalid input — keep phase, action_ask will re-show exposant menu
                return {"reg_category": None}

            # ── Main menu context ──
            normalized = CATEGORY_MAP.get(val)
            if normalized == "_sponsor_":
                # Set phase so action_ask_reg_category shows sponsor sub-menu
                return {"reg_category": None, "_reg_category_phase": "sponsor"}
            if normalized == "_exposant_":
                # Set phase so action_ask_reg_category shows exposant sub-menu
                return {"reg_category": None, "_reg_category_phase": "exposant"}
            if normalized:
                return {"reg_category": normalized, "_reg_category_phase": None}
            if slot_value in VALID_CATEGORIES:
                return {"reg_category": slot_value, "_reg_category_phase": None}

        # Invalid input — reset to main menu
        return {"reg_category": None, "_reg_category_phase": None}

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

def _build_upload_list(category, visa):
    """Return a list of upload descriptor dicts needed for this registration."""
    uploads = []
    if category and category != "Participant Simple":
        uploads.append({
            "type": "logo",
            "accept": ".jpg,.jpeg,.png,.gif,.svg",
            "max_size_mb": 10,
            "label": "Logo de votre entreprise",
            "description": "Votre logo sera utilise sur les supports de communication.\nFormats acceptes : JPG, PNG, SVG - Max 10 MB",
        })
    if visa and str(visa).lower() == "oui":
        uploads.append({
            "type": "passport",
            "accept": ".pdf",
            "max_size_mb": 10,
            "label": "Copie de votre passeport",
            "description": "Necessaire pour votre invitation visa.\nFormat accepte : PDF uniquement - Max 10 MB",
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

        person = tracker.get_slot("person")
        first_name = str(person).strip().split()[0].title() if person else None
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
            fallback = f"Documents a fournir{name_suffix} :\n\n"
            for u in uploads:
                fallback += f"- {u['label']}\n"
            fallback += "\nApres avoir prepare vos documents, tapez 'ok' pour continuer."
            dispatcher.utter_message(text=fallback)
            for u in uploads:
                events.append(SlotSet(f"_reg_{u['type']}_file", None))
        else:
            # No uploads needed - go straight to review
            dispatcher.utter_message(
                json_message={"trigger_message": "/registration_review"}
            )
            dispatcher.utter_message(
                text=f"Merci{name_suffix} ! Verification de vos informations..."
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
        lines = ["Resume de l'inscription\n"]
        for num, label, slot, _ in REG_FIELDS:
            val = tracker.get_slot(slot) or "--"
            lines.append(f"{num}. {label} : {val}")

        # File status lines
        category = tracker.get_slot("reg_category")
        visa = tracker.get_slot("reg_visa") or "non"
        if category and category != "Participant Simple":
            logo_status = "selectionne" if tracker.get_slot("_reg_logo_file") else "non fourni"
            lines.append(f"11. Logo : {logo_status}")
        if str(visa).lower() == "oui":
            passport_status = "selectionne" if tracker.get_slot("_reg_passport_file") else "non fourni"
            lines.append(f"12. Passeport : {passport_status}")

        lines.append("\nTapez un numero (1-12) pour modifier, ou \"ok\" pour confirmer.")
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
                dispatcher.utter_message(text="Mis a jour !")
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
                                "description": "Formats acceptes : JPG, PNG, SVG - Max 10 MB",
                                "mode": "local_store",
                                "upload_url_base": upload_base,
                                "auth_header": f"Bearer {EXPOBETON_API_KEY}",
                                "on_complete_trigger": "/registration_review",
                            }
                        }
                    )
                    return {"_reg_confirmed": None}
                else:
                    dispatcher.utter_message(text="Le logo n'est pas requis pour votre categorie.")
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
                                "description": "Format accepte : PDF uniquement - Max 10 MB",
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
        dispatcher.utter_message(text="Tapez un numero (1-12) pour modifier ou \"ok\" pour confirmer.")
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

        person = tracker.get_slot("person")
        first_name = str(person).strip().split()[0].title() if person else None
        name_suffix = f" {first_name}" if first_name else ""

        dispatcher.utter_message(text="Soumission de votre inscription en cours...")

        result = ExpoBetonAPI.register(data)

        if result.get("success"):
            if result.get("duplicate"):
                ref = result.get("reference", "N/A")
                dispatcher.utter_message(
                    text=(
                        f"Vous etes deja inscrit(e) !\n"
                        f"Reference : {ref}\n"
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
                    f"Felicitation{name_suffix} ! "
                    f"Inscription reussie avec succes pour ExpoBeton 2026 !\n\n"
                    f"Votre numero de reference : {ref}\n"
                    f"Un email de confirmation a ete envoye a {data['email']}.\n\n"
                    f"Notre equipe vous contactera dans les 48 heures.\n"
                    f"Pour toute question : info@expobetonrdc.com"
                )
            )
        else:
            errors = result.get("errors", [])
            error_msg = "\n".join(f"- {e}" for e in errors) if errors else result.get("error", "Erreur inconnue")
            dispatcher.utter_message(
                text=f"L'inscription n'a pas pu etre completee :\n{error_msg}\n\nVeuillez reessayer ou contacter info@expobetonrdc.com"
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
                    f"Candidature ambassadeur soumise !\n\n"
                    f"Reference : {ref}\n"
                    f"Nous examinerons votre candidature et vous recontacterons.\n"
                    f"Contact : info@expobetonrdc.com"
                )
            )
        else:
            errors = result.get("errors", [])
            error_msg = "\n".join(f"- {e}" for e in errors) if errors else result.get("error", "Erreur inconnue")
            dispatcher.utter_message(
                text=f"La candidature n'a pas pu etre soumise :\n{error_msg}"
            )

        return [AllSlotsReset()]


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
