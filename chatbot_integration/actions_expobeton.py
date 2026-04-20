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
EXPOBETON_API_URL = "https://expobetonrdc.com/api_chatbot_register.php"
EXPOBETON_API_KEY = "ebx-rasa-2026-kAlEmIe-be96bac9f905b106ed2b941dfe536b07"

# You can also load from environment variables:
# import os
# EXPOBETON_API_URL = os.getenv("EXPOBETON_API_URL", "https://expobetonrdc.com/api_chatbot_register.php")
# EXPOBETON_API_KEY = os.getenv("EXPOBETON_API_KEY", "")


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

class ActionShowCategories(Action):
    def name(self) -> Text:
        return "action_show_categories"

    def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict
    ) -> List[Dict[Text, Any]]:

        msg = (
            "📋 **ExpoBeton RDC 2026 — Registration Categories**\n\n"
            "**🏆 Sponsor Levels:**\n"
            "  • Platinum — $40,000\n"
            "  • Gold — $20,000\n"
            "  • Silver — $15,000\n"
            "  • Bronze — $12,000\n\n"
            "**🏗️ Exhibitor Stands:**\n"
            "  • 3×3 m — $5,000\n"
            "  • 2×4 m — $3,000\n"
            "  • 2×3 m — $2,000\n\n"
            "**👤 Simple Participant — Free**\n\n"
            "Which category interests you?"
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
    "Virement bancaire", "Mobile Money", "Western Union",
    "Carte bancaire", "Cash",
]

CATEGORY_MAP = {
    "platinum": "Platinum",
    "gold": "Gold",
    "silver": "Silver",
    "bronze": "Bronze",
    "exposant 3x3": "Exposant Stand 3x3m",
    "exposant 2x4": "Exposant Stand 2x4m",
    "exposant 2x3": "Exposant Stand 2x3m",
    "participant": "Participant Simple",
    "participant simple": "Participant Simple",
    "sponsor platinum": "Platinum",
    "sponsor gold": "Gold",
    "sponsor silver": "Silver",
    "sponsor bronze": "Bronze",
    "stand 3x3": "Exposant Stand 3x3m",
    "stand 2x4": "Exposant Stand 2x4m",
    "stand 2x3": "Exposant Stand 2x3m",
}


class ValidateRegistrationForm(FormValidationAction):
    """Validates slots collected by the registration_form."""

    def name(self) -> Text:
        return "validate_registration_form"

    def validate_reg_company(
        self, slot_value: Any, dispatcher: CollectingDispatcher,
        tracker: Tracker, domain: DomainDict
    ) -> Dict[Text, Any]:
        if slot_value and len(str(slot_value).strip()) >= 2:
            return {"reg_company": slot_value.strip()}
        dispatcher.utter_message(text="Please provide a valid company or organization name.")
        return {"reg_company": None}

    def validate_reg_contact_name(
        self, slot_value: Any, dispatcher: CollectingDispatcher,
        tracker: Tracker, domain: DomainDict
    ) -> Dict[Text, Any]:
        if slot_value and len(str(slot_value).strip()) >= 2:
            return {"reg_contact_name": slot_value.strip()}
        dispatcher.utter_message(text="Please provide the contact person's full name.")
        return {"reg_contact_name": None}

    def validate_reg_email(
        self, slot_value: Any, dispatcher: CollectingDispatcher,
        tracker: Tracker, domain: DomainDict
    ) -> Dict[Text, Any]:
        import re
        if slot_value and re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', str(slot_value).strip()):
            return {"reg_email": slot_value.strip().lower()}
        dispatcher.utter_message(text="Please provide a valid email address.")
        return {"reg_email": None}

    def validate_reg_phone(
        self, slot_value: Any, dispatcher: CollectingDispatcher,
        tracker: Tracker, domain: DomainDict
    ) -> Dict[Text, Any]:
        import re
        cleaned = re.sub(r'[\s\-\(\)]', '', str(slot_value or ''))
        if len(cleaned) >= 6 and cleaned.replace('+', '').isdigit():
            return {"reg_phone": slot_value.strip()}
        dispatcher.utter_message(text="Please provide a valid phone number (at least 6 digits).")
        return {"reg_phone": None}

    def validate_reg_country(
        self, slot_value: Any, dispatcher: CollectingDispatcher,
        tracker: Tracker, domain: DomainDict
    ) -> Dict[Text, Any]:
        if slot_value and len(str(slot_value).strip()) >= 2:
            return {"reg_country": slot_value.strip()}
        dispatcher.utter_message(text="Please provide your country.")
        return {"reg_country": None}

    def validate_reg_city(
        self, slot_value: Any, dispatcher: CollectingDispatcher,
        tracker: Tracker, domain: DomainDict
    ) -> Dict[Text, Any]:
        if slot_value and len(str(slot_value).strip()) >= 2:
            return {"reg_city": slot_value.strip()}
        dispatcher.utter_message(text="Please provide your city.")
        return {"reg_city": None}

    def validate_reg_category(
        self, slot_value: Any, dispatcher: CollectingDispatcher,
        tracker: Tracker, domain: DomainDict
    ) -> Dict[Text, Any]:
        if slot_value:
            normalized = CATEGORY_MAP.get(str(slot_value).strip().lower())
            if normalized:
                return {"reg_category": normalized}
            # Direct match
            if slot_value in VALID_CATEGORIES:
                return {"reg_category": slot_value}
        dispatcher.utter_message(
            text="Please choose a valid category:\n"
                 "• Platinum, Gold, Silver, Bronze (Sponsor)\n"
                 "• Exposant 3x3, 2x4, or 2x3\n"
                 "• Participant Simple"
        )
        return {"reg_category": None}

    def validate_reg_payment(
        self, slot_value: Any, dispatcher: CollectingDispatcher,
        tracker: Tracker, domain: DomainDict
    ) -> Dict[Text, Any]:
        category = tracker.get_slot("reg_category")
        # Participants don't need payment
        if category == "Participant Simple":
            return {"reg_payment": "N/A"}
        if slot_value:
            val = str(slot_value).strip()
            # Fuzzy match
            for method in VALID_PAYMENT_METHODS:
                if val.lower() in method.lower() or method.lower() in val.lower():
                    return {"reg_payment": method}
            if val in VALID_PAYMENT_METHODS:
                return {"reg_payment": val}
        dispatcher.utter_message(
            text="Please choose a payment method:\n"
                 "• Virement bancaire\n• Mobile Money\n"
                 "• Western Union\n• Carte bancaire\n• Cash"
        )
        return {"reg_payment": None}


# ═══════════════════════════════════════════════════════════════════════
# Action: Submit Registration to ExpoBeton API
# ═══════════════════════════════════════════════════════════════════════

class ActionSubmitRegistration(Action):
    def name(self) -> Text:
        return "action_submit_registration"

    def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict
    ) -> List[Dict[Text, Any]]:

        # Collect all slots
        data = {
            "company":        tracker.get_slot("reg_company"),
            "contact_name":   tracker.get_slot("reg_contact_name"),
            "email":          tracker.get_slot("reg_email"),
            "phone":          tracker.get_slot("reg_phone"),
            "phone_prefix":   tracker.get_slot("reg_phone_prefix") or "+243",
            "country":        tracker.get_slot("reg_country"),
            "city":           tracker.get_slot("reg_city"),
            "address":        tracker.get_slot("reg_address") or "",
            "postal":         tracker.get_slot("reg_postal") or "",
            "category":       tracker.get_slot("reg_category"),
            "payment_method": tracker.get_slot("reg_payment"),
            "visa_required":  tracker.get_slot("reg_visa") or "non",
            "previous_participation": tracker.get_slot("reg_history") or "non",
        }

        # Show summary before submission
        category = data["category"]
        dispatcher.utter_message(
            text=(
                f"📝 **Registration Summary**\n\n"
                f"• Company: **{data['company']}**\n"
                f"• Contact: **{data['contact_name']}**\n"
                f"• Email: {data['email']}\n"
                f"• Phone: {data['phone_prefix']} {data['phone']}\n"
                f"• Location: {data['city']}, {data['country']}\n"
                f"• Category: **{category}**\n"
                f"• Payment: {data['payment_method']}\n\n"
                f"Submitting your registration..."
            )
        )

        # Call the API
        result = ExpoBetonAPI.register(data)

        if result.get("success"):
            if result.get("duplicate"):
                ref = result.get("reference", "N/A")
                dispatcher.utter_message(
                    text=(
                        f"ℹ️ You are already registered!\n"
                        f"Reference: **{ref}**\n"
                        f"Status: {result.get('status', 'pending')}\n\n"
                        f"Contact info@expobetonrdc.com for any changes."
                    )
                )
            else:
                ref = result.get("data", {}).get("reference", "N/A")
                dispatcher.utter_message(
                    text=(
                        f"✅ **Registration successful!**\n\n"
                        f"Your reference number: **{ref}**\n"
                        f"A confirmation email has been sent to {data['email']}.\n\n"
                        f"Our team will contact you within 48 hours.\n"
                        f"For questions: info@expobetonrdc.com"
                    )
                )
        else:
            errors = result.get("errors", [])
            error_msg = "\n".join(f"• {e}" for e in errors) if errors else result.get("error", "Unknown error")
            dispatcher.utter_message(
                text=f"❌ Registration could not be completed:\n{error_msg}\n\nPlease try again or contact info@expobetonrdc.com"
            )

        return [AllSlotsReset()]


# ═══════════════════════════════════════════════════════════════════════
# Action: Submit Ambassador Application
# ═══════════════════════════════════════════════════════════════════════

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

        dispatcher.utter_message(text="Submitting your ambassador application...")

        result = ExpoBetonAPI.submit_ambassador(data)

        if result.get("success"):
            ref = result.get("data", {}).get("reference", "N/A")
            dispatcher.utter_message(
                text=(
                    f"✅ **Ambassador application submitted!**\n\n"
                    f"Reference: **{ref}**\n"
                    f"We will review your application and get back to you.\n"
                    f"Contact: info@expobetonrdc.com"
                )
            )
        else:
            errors = result.get("errors", [])
            error_msg = "\n".join(f"• {e}" for e in errors) if errors else result.get("error", "Unknown error")
            dispatcher.utter_message(
                text=f"❌ Application could not be submitted:\n{error_msg}"
            )

        return [AllSlotsReset()]


# ═══════════════════════════════════════════════════════════════════════
# Action: Check API Health
# ═══════════════════════════════════════════════════════════════════════

class ActionCheckApiHealth(Action):
    def name(self) -> Text:
        return "action_check_api_health"

    def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict
    ) -> List[Dict[Text, Any]]:
        result = ExpoBetonAPI.health_check()
        if result.get("success"):
            dispatcher.utter_message(text="✅ ExpoBeton registration system is online.")
        else:
            dispatcher.utter_message(text="⚠️ Registration system is temporarily unavailable. Please try later.")
        return []
