# Testing

## Testphilosophie

CHAPPiE enthält sowohl **sichere lokale Prüfungen** als auch **live-/manuelle Tests**. Diese sollten bewusst getrennt betrachtet werden.

## Testtypen

| Typ | Ziel | Beispiele |
|---|---|---|
| Schnelle lokale Checks | Kernlogik ohne riskante Seiteneffekte prüfen | `tests/test_forgetting_curve.py`, `tests/test_life_simulation.py` |
| Struktur-/Kompatibilitätschecks | Module, Services und Dateien validieren | `tests/manual/test_compatibility.py` |
| Live-/Provider-Tests | Verhalten mit echten Modellen/APIs prüfen | `tests/test_brain_agents.py`, `tests/test_nvidia_api.py`, `tests/test_integration.py` |
| Interaktive Smoke-Tests | UI oder Chat manuell antesten | `tests/manual/test_chat_live.py`, `tests/manual/test_chappie.py` |

## Wichtige Regel

Nicht jeder Test ist für jeden Commit geeignet. Vor allem Live- und API-Tests können:

- externe Kosten verursachen
- auf lokale Services angewiesen sein
- Kontextdateien verändern
- langsamer oder fragiler sein

## Empfohlene Reihenfolge

1. **kleinster lokaler Test**
2. **passender Dateitest**
3. **Kompatibilitätscheck**
4. **erst dann Live-/API-Test**, wenn die Änderung das wirklich benötigt

## Sinnvolle schnelle Checks

- `python tests/test_forgetting_curve.py`
- `python tests/test_life_simulation.py`
- `python tests/manual/test_compatibility.py`

## Wenn Doku geändert wurde

Bei reinen Doku-Änderungen reichen meist:

- ein kurzer Struktur-/Import-Check
- ggf. ein schneller Python-Kompatibilitätscheck
- keine teuren Live-Modelltests

## Wenn Modelllogik geändert wurde

Dann zusätzlich prüfen:

- `config/config.py`
- `config/brain_config.py`
- `brain/agents/*.py`
- betroffene Live-/Agent-Tests

## Testkarte

Eine dateinahe Übersicht steht in [`tests/README.md`](../tests/README.md).

## Hinweise für Agents

Vor automatisierten Änderungen immer fragen:

1. Ist der Test lokal sicher?
2. Nutzt er echte APIs oder externe Kosten?
3. Verändert er Dateien in `data/`?
4. Ist ein kleinerer Test ausreichend?

## Weiterführend

- [`tests/README.md`](../tests/README.md)
- [Lokale Modelle & Fallbacks](local-models.md)
- [Deployment](deployment.md)

