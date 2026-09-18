# TunaOS XFCE Installer — Roadmap

**Last updated**: 2026-09-18 | **Maintainer**: tuna-os (hanthor)
**Lifecycle Status**: Deprecated / Sunset (Migrated to `tuna-os/bootc-installer` -> `frontends/xfce/`)

---

## Mission

Ship the XFCE desktop's install experience: a GTK3 frontend that drives the
fisherman bootc backend — welcome, image selection, disk selection, filesystem
and encryption, account, confirmation, install progress, completion — so a
first-time XFCE user gets a native install from first boot to desktop.

---

## Current Status

- **Monorepo Migration**: On 2026-09-17, the XFCE installer code and history were
  formally imported into [tuna-os/bootc-installer](https://github.com/tuna-os/bootc-installer/tree/dev/frontends/xfce).
- **Standalone Repository Status**: Deprecated. Active development, issue tracking, and PRs
  are transitioning to `tuna-os/bootc-installer`.
- **App**: GTK3 frontend for fisherman; CI-rendered walkthrough in
  `docs/gui-walkthrough.md`.
- **Distribution**: image-baked flatpak — no standalone GitHub Releases.

### Priorities

| Priority | Item | Tracking | Status |
|----------|------|----------|--------|
| P0 | Re-home active open issues and PRs to `tuna-os/bootc-installer` | #77 | 🟡 In Progress |
| P1 | Transition standalone repository to read-only archive | #76 | 🟡 In Progress |
| P2 | Wire unit tests and test automation in `bootc-installer` CI | bootc-installer #23 | ⬜ Re-homed |

---

## Quarterly Goals

### Current Quarter (2026 Q3)

**Theme**: monorepo migration and repository sunset

| Goal | Owner | Tracking | Status |
|------|-------|----------|--------|
| Import XFCE frontend into `bootc-installer` monorepo | tuna-os | #75 | ✅ Complete |
| Re-home open issues/PRs to `tuna-os/bootc-installer` | hanthor | #77 | 🟡 In Progress |

### Next Quarter (2026 Q4)

**Theme**: archive and monorepo maintenance

| Goal | Owner | Tracking | Status |
|------|-------|----------|--------|
| Archive standalone `tuna-installer-xfce` repository as read-only | tuna-os | #76 | ⬜ Scheduled |
| Parity and CI integration within `bootc-installer` | tuna-os | bootc-installer | ⬜ Scheduled |
