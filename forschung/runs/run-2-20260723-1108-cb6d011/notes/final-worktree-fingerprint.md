# Finaler Worktree- und Artefakt-Fingerprint

Zeitpunkt: `2026-07-26T06:57:07Z`  
Branch/Commit: `main` / `cb6d01147d7e793a767bccecd5d0c8e6bede263f`

Der Run entstand bewusst in einem bereits veränderten Worktree. Der Commit
allein rekonstruiert den Forschungsstand daher nicht.

- SHA-256 des binären Git-Diffs aller getrackten Änderungen:
  `a97cf993e616158fa6e79b720f99dbdc9dd24cac439463c3f20f4224b1a6423f`
- Diffstat: 61 Dateien, 10.146 Einfügungen, 790 Löschungen
- `git status --short`: 117 Einträge, davon 56 ungetrackt
- Der Diffhash deckt ungetrackte Dateien nicht ab. Für diese sind die
  nachstehenden Schlüsselartefakthashes und die im Manifest gelisteten
  Session-/Runwurzeln maßgeblich.

## Schlüsselartefakte

| Datei | SHA-256 |
|---|---|
| `forschung/report/CHAPPiE-Forschungsbericht-Run-2.html` | `517d41dae5500b64c38692c67e74f68dc506625c94bdc754f2565f4aaac4f31e` |
| `forschung/report/report-plan.md` | `7112fa161de7930bebb529c40d2c7d1ca5447de0cfb54889c2080b73c91fbce1` |
| `forschung/report/report-plan.html` | `a5832ea228d5b66c414ce02a049e05f90173d3508e11099134b453e20ec2d4fc` |
| `known-issues-comparison.csv` | `50b260b6ce12525267ab4a9d7a3e7c6fc12def3b977abc32541c44ac40d43530` |
| `processed/final-research-findings.json` | `7352b82cf1cc4159687d84a234d2dc5f848265fec3678118004a2cdf963c11ba` |

Die Hashes dienen der Integritätskontrolle, nicht als Behauptung eines
sauberen oder ausschließlich diesem Run zuordenbaren Git-Commits.
