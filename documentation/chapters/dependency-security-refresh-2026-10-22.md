---
part: Runtime
status: shipped
updated: 2026-10-22
---
# Dependency security refresh (2026-10-22)

The root `package.json` has one dependency, `jsdom`, used only by `scripts/test_view_toggle.js`
(a dev check of the dashboard view toggle). Nothing here ships in the container.

## Audit
`npm audit`: before high 2, after 0 vulnerabilities.

## What changed (`package-lock.json` only, `npm audit fix --package-lock-only`)
| Package | From | To | Why |
|---|---|---|---|
| `ws` (via jsdom) | 8.18.3 | 8.22.0 | high advisory range 8.0.0 to 8.20.1 |
| `source-map-js` | 1.2.1 | 1.2.2 | high advisory range 1.0.0 to 1.2.1 |

## Validation
`npm ci` then `node scripts/test_view_toggle.js` on the primary checkout through `testrun`.
That script already prints "Assertion failed" lines for the table, charts and grid toggles before
this change and exits 0; its output is unchanged by the bump.

## Resolved tickets
| Ticket | Root cause | Commit |
|---|---|---|
| Dependency security refresh 2026-10-22 | `ws` and `source-map-js` inside advisory ranges | see git log (`build(deps): ...`) |
