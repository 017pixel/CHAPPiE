# Cloud-Konfigurationsaudit

Stand: `2026-07-23T21:24:24.293757+00:00` · Gesamtstatus: **PASS**

| Prüfung | Status | Detail |
|---|---|---|
| manifest_config_count | PASS | 10 |
| manifest_paths_exist | PASS |  |
| primary_five_configs | PASS | 5 configs for openai/gpt-oss-120b |
| primary_seed_set | PASS | [11, 23, 37, 53, 71] |
| primary_model_contract | PASS | openai/gpt-oss-120b |
| fallback_five_configs | PASS | 5 configs for openai/gpt-oss-20b |
| fallback_seed_set | PASS | [11, 23, 37, 53, 71] |
| fallback_model_contract | PASS | openai/gpt-oss-20b |
| same_stratified_selection | PASS | identische 21 Fragen über 14 Kategorien |
| no_duplicate_hashes_across_roles | PASS | Model/Seed-Metadaten halten jede Config unterscheidbar |

> Dieser GPU-freie Audit startet keine Cloudanfrage. Die Ausführung bleibt bis zum validierten Ende der lokalen automatisierten Bedingungen gesperrt.
