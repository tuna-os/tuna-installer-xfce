# TunaOS XFCE Installer — Roadmap

**Last updated**: 2026-09-16 | **Maintainer**: tuna-os

---

## Mission

Ship the XFCE desktop's install experience: a GTK3 frontend that drives the
fisherman bootc backend — welcome, image selection, disk selection, filesystem
and encryption, account, confirmation, install progress, completion — so a
first-time XFCE user gets a native install from first boot to desktop.

---

## Current Status

- **App**: GTK3 frontend for fisherman; CI-rendered walkthrough in `docs/gui-walkthrough.md`.
- **Distribution**: image-baked flatpak — no standalone GitHub Releases (by design, documented policy).
- **Parity**: covered by `installer-smoke.yml` + `docs/INSTALLER-FRONTENDS.md` checks (readiness stamp, non-blank, advances, per-screen OCR).
- **Health**: active; verified fisherman pin `#67` landed; CI test suite execution and flatpak multi-arch publishing active.

### Priorities

| Priority | Item | Tracking | Status |
|----------|------|----------|--------|
| P1 | Standardize release versioning metadata & release tagging | #68 | 🟡 In progress |
| P2 | ROADMAP-coverage entry in org ROADMAP tally | #1295 | 🟢 Complete |

---

## Quarterly Goals

### Current Quarter (2026 Q3)

**Theme**: backend stability and multi-arch distribution

| Goal | Owner | Tracking | Status |
|------|-------|----------|--------|
| Multi-arch (aarch64/x86_64) flatpak publishing | tuna-os | #62 | 🟢 Completed |
| Update fisherman backend pin to verified release | tuna-os | #67 | 🟢 Completed |

### Next Quarter (2026 Q4)

**Theme**: release cadence and frontend parity

| Goal | Owner | Tracking | Status |
|------|-------|----------|--------|
| Document release/versioning model (image-baked vs tagged) | tuna-os | #68 | 🟡 In progress |
| Continuous pre-merge GUI regression testing | tuna-os | #69 | ⬜ Not started |

---

