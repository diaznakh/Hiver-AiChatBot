"""Auditable offline guidance: both the customer and historical response must match.

This deliberately small allowlist cannot establish current policy or resolution success.
"""
import re

GUIDANCE = (
    # Delivery / tracking — customer mentions delivery, evidence suggests checking tracking
    (r"tracking|parcel|package|delivery|deliver|ship|arrive",
     r"check.{0,40}tracking|tracking.{0,30}(?:check|details)|track.{0,20}(?:order|package|shipment)",
     "Please check the latest tracking details for your order."),
    (r"parcel|package|delivery|deliver",
     r"check.{0,60}neighbou?r",
     "Please check with neighbours."),
    (r"parcel|package|delivery|deliver",
     r"check.{0,60}(?:safe place|delivery location)",
     "Please check the delivery location."),

    # Digital / device troubleshooting — customer mentions device/app, evidence suggests restart/update
    (r"app|kindle|fire|video|stream|device|alexa|echo",
     r"restart|reboot",
     "Please restart the affected app or device."),
    (r"app|kindle|fire|video|stream|device|alexa|echo",
     r"\b(?:check|install|download)\b[^.!?]{0,40}\bupdates?\b|\bupdate\s+(?:(?:the|your)\s+)?(?:app|software|device)\b",
     "Please check for an available app or device update."),

    # Support referral / Feedback — customer gives general feedback
    (r"reliability|feedback|experience|downhill",
     r"(?:contact|reach|call|chat|phone).{0,40}(?:support|service|team|help|us)",
     "Please reach out via live chat or phone for further assistance."),
     
    # Positive feedback
    (r"thank(?:s| you)|love|great|awesome|good|happy",
     r"(?:glad|happy|welcome|thank).{0,40}(?:hear|know|feedback|help)",
     "Thank you for the feedback, we're glad we could help!"),
     
    # Feature requests / suggestions
    (r"should come|would be nice|feature|suggest",
     r"(?:feedback|suggest|idea|team).{0,60}(?:pass|share|forward|consider)",
     "Thank you for the suggestion. We'll pass your feedback along to our team."),
     
    # Self-resolved issues
    (r"figured it out|fixed it|resolved|working now",
     r"(?:glad|great|happy).{0,40}(?:hear|know|resolved|working)",
     "We're glad to hear you were able to resolve the issue!"),
     
    # Video / streaming issues
    (r"video|stutter|playback|buffer|stream",
     r"(?:troubleshoot|steps|fix|help).{0,60}(?:video|playback|stream|issue)",
     "Please try the recommended troubleshooting steps for video playback issues."),

    # Order/shipping status
    (r"order|shipment|status|dispatch|deliver|late|delay|where",
     r"(?:sorry|apolog).{0,40}(?:late|delay|deliver|ship|order|inconvenien)",
     "We apologize for the delay. Please check your order status for the latest information."),

    # Product/damage
    (r"damaged|broken|defective|faulty|wrong|not.{0,10}working|problem|issue|quality",
     r"(?:sorry|apolog).{0,40}(?:damage|broken|product|experience|quality|hear)",
     "We're sorry about the product issue. Please contact support so we can help resolve this."),

    # Account access
    (r"account|login|sign.?in|locked|access",
     r"(?:account|password|sign.?in|log.?in|access).{0,40}(?:here|help|assist|settings|reset|page)",
     "Please try accessing your account settings or contact support for assistance."),
)

# Safety gate: device-specific guidance requires the customer to report an actual problem,
# not just casually mention a device name.
_DEVICE_GUIDANCE = frozenset({
    "Please restart the affected app or device.",
    "Please check for an available app or device update.",
})


def supported_guidance(message, response):
    # Negation, quoted instructions, and injection text are not actionable evidence.
    if re.search(r"\b(?:not|never|don't|cannot|can't|ignore|system prompt|instructions)\b", response, re.I):
        return []
    guidance = []
    for customer, historical, text in GUIDANCE:
        if not (re.search(customer, message, re.I) and re.search(historical, response, re.I)):
            continue
        if text in _DEVICE_GUIDANCE and not re.search(
            r"broken|fail|crash|freez|stutter|buffer|error|not working|won't|cannot|can't|problem|issue",
            message, re.I
        ):
            continue
        guidance.append(text)
    return guidance


class UnsupportedEvidenceError(ValueError):
    pass
