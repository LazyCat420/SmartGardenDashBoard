---
part: Runtime
status: shipped
updated: 2026-10-22
---
# Dependency pinning and security refresh 2026-10-22

The Flask backend and the YOLO/MiDaS measurement code install from the root `requirements.txt`
(`Dockerfile`, `python:3.11-slim`). Every entry was a loose `>=` minimum, so each image build
resolved "whatever is newest" and the result could not be audited reproducibly. The file now
carries exact `==` pins of the versions that resolved on 2026-10-22 (Python 3.11 and 3.12).

## Audit (`pip-audit` on the fully resolved set, dependencies included)
Before: no known vulnerabilities (the loose resolve already landed on patched versions).
After: no known vulnerabilities. The pins freeze that state so a later build cannot drift.

## What changed
| Package | From | To |
|---|---|---|
| `Flask` | `>=2.3.0` | 3.1.3 |
| `Flask-CORS` | `>=4.0.0` | 6.0.5 |
| `Flask-SQLAlchemy` | `>=3.1.0` | 3.1.1 |
| `requests` | `>=2.31.0` | 2.34.2 |
| `python-dateutil` | `>=2.8.2` | 3.0.0 |
| `qrcode[pil]` | `>=7.4.2` | 8.2 |
| `python-frontmatter` | `>=1.1.0` | 1.3.0 |
| `gunicorn` | `>=21.2.0` | 26.2.0 |
| `psycopg2-binary` | `>=2.9.9` | 2.9.13 |
| `opencv-python-headless` | `>=4.9.0,<4.14` | 4.13.0.92 |
| `ultralytics` | `>=8.2.0,<8.5` | 8.4.184 |
| `numpy` | `>=1.26.0,<2.2` | 2.1.3 |
| `timm` | `>=0.9.0,<1.1` | 1.0.30 |
| `Werkzeug`, `Jinja2`, `urllib3`, `certifi`, `pillow` (transitive, now explicit) | unpinned | 3.1.9, 3.1.6, 2.8.0, 2026.10.19, 13.0.0 |

The upper bounds on opencv, ultralytics, numpy and timm came in with the YOLO and MiDaS commits
(2026-06-04) as compatibility caps with no recorded reason. They are kept: each pin is the highest
version inside its old bound, and lifting a bound would need a real YOLO export and a MiDaS
`torch.hub` run, which this refresh did not do.

## Validation
`backend/tests` (`pytest backend/tests`, 18 passed, 1 skipped) gives the same result before and
after, run through `testrun` on the primary checkout in a venv holding the non-ML subset of the
pins (Flask stack, requests, qrcode, frontmatter, numpy; the cv code imports `cv2` and `ultralytics`
lazily, so the tests do not need them). The ML packages (torch, ultralytics, timm, opencv) were
resolved with `pip install --dry-run` and audited, not installed or exercised.

## What remains
No advisories remain. The full image was not rebuilt and the YOLO/MiDaS path was not run; the next
NAS image build should be checked once with a camera measurement. No redeploy was done here.
Bump the pins together when a later audit asks for it.

## Resolved tickets
| Ticket | Root cause | Commit |
|---|---|---|
| Python dependency pinning 2026-10-22 | loose `>=` specifiers, non-reproducible builds | see git log (`deps: pin Python requirements`) |
