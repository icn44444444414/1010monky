"""
AI-som (Milestone 11 - byggs in nu, aktiveras senare).

Detta ar avsiktligt en INERT hook. Den anropas efter att ett besoksmeddelande
sparats, men gor inget sa lange CHAT_AI_ENABLED inte ar satt. Sa har blir
arkitekturen AI-redo utan att vi bygger AI an: nar AI aktiveras sparar den ett
svar som ChatMessage med sender_type='bot', och widgeten visar det automatiskt
(den renderar pa sender_type, inte pa avsandarens identitet).

Principer for nar AI val byggs (M11):
  * AI svarar ENBART fran godkand kunskapsbas (tjanster, pris, process, FAQ).
  * AI latsas aldrig vara Matias - tydlig disclosure, sender_type='bot'.
  * Besokaren kan alltid valja "Prata med Matias" -> AI slutar svara, status
    satts sa admin tar over.
  * Hittar inte pa, lovar inte exakta priser utan underlag.
"""
import os

CHAT_AI_ENABLED = os.getenv('CHAT_AI_ENABLED', 'false').lower() == 'true'


def maybe_bot_reply(conversation, visitor_text):
    """Anropas efter ett besoksmeddelande. Avstangd tills AI byggs i M11.

    Returnerar None idag. Nar aktiverad: skapar ev. en ChatMessage med
    sender_type='bot' och committar. Halls medvetet tom nu sa beteendet ar
    identiskt med en ren livechatt.
    """
    if not CHAT_AI_ENABLED:
        return None
    # M11: kunskapsbas-uppslag + svar som sender_type='bot' + handoff-logik.
    return None
