# Monitoring Log · Bedingung A (Qwen)

| UTC | Dienst/PID | Fortschritt | stdout | GPU | Sperrprozesse | kritische Fehler | Vertrag/Artefakte |
|---|---|---:|---:|---|---|---|---|
| 13:16 | active / 631153 | 6/430 | 8,5 KB | 10.137 MiB, 97 %, 58 °C | 480679/480681 `Tsl` | keine | Qwen-/Provider-Audit noch nicht vorhanden |
| 13:21 | active / 631153 | 32/430 | 42,5 KB | 9.897 MiB, 62 %, 70 °C | 480679/480681 `Tsl` | keine | Qwen-/Provider-Audit noch nicht vorhanden |
| 13:27 | active / 631153 | 69/430 | 93,3 KB | 10.081 MiB, 98 %, 70 °C | 480679/480681 `Tsl` | keine | Qwen-/Provider-Audit noch nicht vorhanden |
| 13:32 | active / 631153 | 100/430 | 135,9 KB | 9.841 MiB, 97 %, 70 °C | 480679/480681 `Tsl` | keine | Vertrag: vLLM, `Qwen/Qwen3.5-4B`, FP16, Thinking aus, 5 Seeds; Provider-Audit noch nicht vorhanden |
| 13:39 | active / 631153 | 125/430 | 178,6 KB | 11.021 MiB, 98 %, 70 °C | 480679/480681 `Tsl` | keine | Vertrag unverändert; zwei Qwen-Review-Summaries vorhanden, Provider-Audit noch nicht vorhanden |
| 13:43 | active / 631153 | 151/430 | 212,5 KB | 11.143 MiB, 97 %, 69 °C | 480679/480681 `Tsl` | keine | Vertrag unverändert; Provider-Audit noch nicht vorhanden |
| 13:49 | active / 631153 | 180/430 | 255,1 KB | 9.343 MiB, 97 %, 70 °C | 480679/480681 `Tsl` | keine | Vertrag unverändert; Provider-Audit noch nicht vorhanden |
| 13:57 | active / 631153 | 219/430 | 306,2 KB | 8.467 MiB, 92 %, 69 °C | 480679/480681 `Tsl` | keine | Vertrag unverändert; Qwen-Review-Summaries wachsen, Provider-Audit noch nicht vorhanden |
| 14:03 | active / 631153 | 248/430 | 348,8 KB | 10.669 MiB, 100 %, 70 °C | 480679/480681 `Tsl` | keine | Vertrag unverändert; Provider-Audit noch nicht vorhanden |
| 14:08 | active / 631153 | 276/430 | 391,2 KB | 11.205 MiB, 97 %, 70 °C | 480679/480681 `Tsl` | keine | Vertrag unverändert; Provider-Audit noch nicht vorhanden |

Geprüfte kritische Muster: Traceback, OOM/CUDA-Fehler, HTTP 429/Rate-Limit, Provider- und Verbindungsfehler sowie unerwarteter Prozessabbruch. Das Monitoring löst keine Modellantwort aus. Prozessstatus wird ausschließlich über `systemctl --user` ermittelt.
