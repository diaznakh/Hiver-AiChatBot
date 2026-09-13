"""Auditable offline guidance: both the customer and historical response must match.

This deliberately small allowlist cannot establish current policy or resolution success.
"""
import re

GUIDANCE = (
    (r"tracking|parcel|package|delivery", r"check.{0,40}tracking|tracking.{0,30}(?:check|details)", "Please check the latest tracking details."),
    (r"parcel|package|delivery", r"check.{0,60}neighbou?r", "Please check with neighbours."),
    (r"parcel|package|delivery", r"check.{0,60}(?:safe place|delivery location)", "Please check the delivery location."),
    (r"app|kindle|fire|video|stream|device|alexa|echo", r"restart|reboot", "Please restart the affected app or device."),
    (r"app|kindle|fire|video|stream|device|alexa|echo", r"(?:check|install|download).{0,40}update|update.{0,30}(?:app|software|device)", "Please check for an available app or device update."),
)


def supported_guidance(message, response):
    # Negation, quoted instructions, and injection text are not actionable evidence.
    if re.search(r"\b(?:not|never|don't|cannot|can't|ignore|system prompt|instructions)\b", response, re.I):
        return []
    return [text for customer, historical, text in GUIDANCE
            if re.search(customer, message, re.I) and re.search(historical, response, re.I)]


class UnsupportedEvidenceError(ValueError):
    pass
