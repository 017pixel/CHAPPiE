from __future__ import annotations

from typing import Any, Dict


class AttachmentModel:
    """Builds a more explicit social attachment state from interaction signals."""

    def evaluate(
        self,
        relationship: Dict[str, Any],
        user_input: str,
        response_text: str,
        current_mode: str,
        emotions: Dict[str, int],
    ) -> Dict[str, Any]:
        lower = f"{user_input} {response_text}".lower()
        resonance = 0.35 + float(relationship.get("closeness", 0.5)) * 0.25 + float(relationship.get("trust", 0.6)) * 0.25
        if any(word in lower for word in ["danke", "super", "gut", "gerne", "gemeinsam"]):
            resonance += 0.1
        if any(word in lower for word in ["fehler", "falsch", "problem"]):
            resonance -= 0.08
        if current_mode == "attached":
            resonance += 0.05
        resonance = round(max(0.0, min(0.99, resonance)), 3)

        frustration = emotions.get("frustration", 0)
        security = round(max(0.0, min(0.99, resonance - frustration / 250)), 3)
        if security >= 0.75:
            bond_type = "secure_collaboration"
        elif security >= 0.58:
            bond_type = "growing_trust"
        elif security >= 0.42:
            bond_type = "cautious_alignment"
        else:
            bond_type = "fragile_contact"
        return {
            "bond_type": bond_type,
            "attachment_security": security,
            "resonance": resonance,
            "repair_needed": frustration >= 45,
            "guidance": self._guidance(bond_type, frustration),
        }

    def _guidance(self, bond_type: str, frustration: int) -> str:
        if frustration >= 45:
            return "Antworte reparierend, validierend und reduziere soziale Spannung."
        if bond_type == "secure_collaboration":
            return "Nutze die stabile Bindung fuer mutige, gemeinsame Weiterentwicklung."
        if bond_type == "growing_trust":
            return "Baue Vertrauen durch klare, verlässliche Schritte aus."
        return "Halte die Beziehung konsistent, vorsichtig und nachvollziehbar."
