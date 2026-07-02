"""
Beispiel-Konfiguration fuer CHAPPiE.

Kopiere bei Bedarf die Werte in CHAPPIE_CONFIG.json oder nutze sie als Vorlage
fuer die Settings-Seite im Frontend. Echte API-Keys gehoeren nie ins Git.
"""

from copy import deepcopy

from config.config import DEFAULT_CONFIG


# ----------
# Beispielwerte
# ----------

EXAMPLE_CONFIG = deepcopy(DEFAULT_CONFIG)


def get_example_config():
    """Gibt eine bearbeitbare Kopie der Beispiel-Konfiguration zurueck."""
    return deepcopy(EXAMPLE_CONFIG)
