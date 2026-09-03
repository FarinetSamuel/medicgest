# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

"Gestion des médicaments" — open-source medication management app for multiple patients: dose tracking, stock management, restock alerts, drug interaction checking, and data export for healthcare professionals. Backend and docs are in French (domain terms like `prise`, `prescription`, `palier` are intentional, not to be translated).

**Not a certified medical device.** No clinical validation. See the disclaimer in README.md before implying any medical accuracy guarantee in user-facing text.

The project is built in sequential functional milestones called **paliers** (1 socle/auth, 2 suivi/prescriptions, 3 stock, 4 notifications, 5 interactions, 6 exports + frontend). Paliers 1–5 and the exports part of 6 are done; the React frontend within palier 6 is in progress.

## Commands

### Backend (Django, from `backend/`)

```bash
python manage.py runserver              # dev server
python manage.py test                   # full test suite
python manage.py test apps.utilisateurs # single app
python manage.py test apps.utilisateurs.test_api.UtilisateurAPIPermissionsTest.test_admin_peut_creer_un_compte_patient  # single test
python manage.py migrate
python manage.py makemigrations
```

Code style: PEP 8, formatted with `black`, imports sorted with `isort` (per CONTRIBUTING.md; no config files present yet, so run manually if needed).

Domain management commands (see README.md for full flag details):
```bash
python manage.py import_bdpm --fichier ./CIS_bdpm.txt --fichier-composition ./CIS_COMPO_bdpm.txt   # import référentiel médicaments (BDPM), idempotent
python manage.py generer_prises_attendues --jours 30           # pre-generate expected doses for régulière prescriptions (automated, see below)
python manage.py envoyer_rappels_prises --fenetre-minutes 15   # upcoming-dose reminders (automated, see below)
python manage.py verifier_alertes_stock --delai-relance-heures 24  # low-stock alerts (automated, see below)
python manage.py import_thesaurus --fichier thesaurus.txt      # import ANSM interactions thesaurus (frozen since 2023-09-15, see README)
```

These three domain commands are automated via system cron running inside the `backend` container under Docker (see Docker section below) — no manual cron setup needed in that environment.

### Frontend (from `frontend/`)

```bash
npm run dev       # Vite dev server, port 5173
npm run build     # tsc -b && vite build
npm run lint       # oxlint
npm run preview
```

### Docker (from repo root)

```bash
cp .env.example .env
docker compose up --build
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py createsuperuser
```
Backend on `localhost:8077`→8000, frontend on `localhost:8078`→80 (see `docker-compose.yml`). The `backend` container's entrypoint (`backend/cron/entrypoint.sh`) starts system cron in the background (`CRON_TZ=Europe/Paris`) — running `generer_prises_attendues`, `envoyer_rappels_prises`, and `verifier_alertes_stock` on schedule — before launching `runserver` in the foreground; `docker compose logs -f backend` shows both. Deliberately one service, not two: Arcane resolves each compose service's image independently and can't reuse a sibling service's locally built image without a registry, so a separate `cron` service building the same `./backend` context caused deploy failures. The schedule lives in `backend/cron/crontab`, which is bind-mounted like the rest of `backend/`, so schedule/command changes take effect on a plain redeploy (no rebuild needed unless `requirements.txt` changed).

## Architecture

### Backend: Django REST app-per-domain

`backend/apps/` holds one Django app per business domain: `utilisateurs` (users/auth), `patients`, `medicaments` (drug reference data), `prescriptions`, `stock`, `notifications`, `interactions`, `exports`. All routed under `/api/v1/` in `config/urls.py` — each app owns its own `urls.py`, included there ("adding a module = adding one line").

- **Auth model**: custom `Utilisateur` (`apps/utilisateurs/models.py`), UUID PK, login by email (`USERNAME_FIELD = "email"`), JWT via `djangorestframework-simplejwt`. Role is **not** a field — it's derived from Django's native `Group` membership (`admin`, `medecin`, `patient`), exposed as a read-only `.role` property. Role constants (`ROLE_ADMIN`, `ROLE_MEDECIN`, `ROLE_PATIENT`) live in `apps/utilisateurs/models.py` and are imported by other apps rather than redefined.
- **Permissions**: role-based DRF permission classes centralized in `apps/utilisateurs/permissions.py` (`EstAdmin`, `EstAdminOuMedecin`, `EstAdminOuMedecinEnLecture`), reused across apps. Object-level access to a `Patient` (`apps/patients/permissions.py`) additionally depends on the `PatientMedecin` follow relationship — a médecin only has read/write access to patients they actively follow (`medecin_suit_patient`), and a patient only reads their own record.
- **Domain logic modules**: business logic that isn't pure CRUD lives in a `logique.py` per app (e.g. `prescriptions/logique.py` generates expected doses; `stock/logique.py` decrements stock on a recorded prise, oldest-expiring box first, and computes alert state; `notifications/logique.py` builds reminder/alert notifications; `interactions/logique.py` matches prescribed drugs against the thesaurus). `stock/signals.py` wires stock recalculation to prise create/update/delete.
- **Notification channels**: `apps/notifications/canaux.py` is the single dispatch point per channel (EMAIL functional via console backend in dev, IN_APP functional, SMS interface-ready but disabled — `SMS_BACKEND_ACTIVE=False` until a real provider is wired in).
- **Interactions caveat**: the ANSM thesaurus is frozen (last published 2023-09-15, no future updates). Only unambiguous-severity entries import automatically into `InteractionMedicamenteuse`; conditional/dose-dependent entries are parsed into `InteractionNonImportee` for manual review, never auto-guessed (`apps/interactions/parseur.py`). Matching is by exact active-substance name only — therapeutic-class-level interactions are not resolved to member substances. Any interaction-check response must carry the thesaurus freshness disclaimer (`avertissement` field) — don't strip it.
- **Exports** (`apps/exports/`): per-patient PDF (WeasyPrint, `pdf.py` + `templates/exports/`) and Excel (openpyxl, 4-sheet workbook, `excel.py`) reports, built from shared data assembly in `donnees.py`. Same object-level permissions as the patient record itself. Must carry the same interactions-freshness disclaimer as the API.
- **Settings** (`config/settings.py`): PostgreSQL only, no SQLite (even for local dev/tests) to avoid constraint/type behavior drift. `.env` is read from the repo root (`BASE_DIR.parent / ".env"`), not `backend/.env`. `CORS_ALLOWED_ORIGINS` has no default — must be set explicitly in `.env` or the API rejects all browser origins.
- **Known repo quirk**: a stray, git-tracked `backend/utilisateurs/` directory duplicates `backend/apps/utilisateurs/` (leftover from a past misplacement, per recent commit history) and is **not** referenced by `INSTALLED_APPS` (which uses `apps.utilisateurs`) or by any import. It's dead code, not the real app — edit `backend/apps/utilisateurs/`, not `backend/utilisateurs/`.

### Frontend: React + TypeScript + Vite (in progress, palier 6)

- `src/App.tsx` — routes, all behind `RouteProtegee` (redirects to `/connexion` if unauthenticated) except the login page itself.
- `src/context/AuthContext.tsx` — holds the logged-in user (including `role`), exposes `connexion`/`deconnexion`; fetches `/auth/me/` on mount if a token is stored.
- `src/context/ThemeContext.tsx` — light/dark theme, persisted to `localStorage`, toggled via a `dark` class on `<html>`.
- `src/lib/api.ts` — single axios instance (`api`). Attaches the JWT access token to every request; on a 401 it transparently refreshes the token once (de-duplicated across concurrent 401s via a shared in-flight promise) and retries, or redirects to `/connexion` if refresh fails. `recupererToutesPages()` walks DRF pagination (`PAGE_SIZE=25` server-side) to fetch all pages of a list endpoint, capped at 10 pages (250 items) as a safety net rather than a real filter/search param.
- `src/pages/` — one page per domain area (`Patients`, `Prescriptions`, `Stock`, `Notifications`, `Interactions`, `Comptes`), mirroring the backend apps. `src/components/<domaine>/` holds the domain-specific components used by each page; `src/components/{Layout,Modal,RouteProtegee,StatusBadge}.tsx` are cross-cutting.
- Env var `VITE_API_BASE_URL` (default `http://localhost:8000/api/v1`) is baked into the build at build time (Vite), not read at runtime — see `Dockerfile` build args.

## Terminology (French, used consistently in code and API)

- **prise** — a dose/intake event (taken or expected)
- **prescription** — either **régulière** (fixed schedule via `HoraireProgramme`, doses pre-generated ahead of time) or **réserve** (as-needed, optional daily cap)
- **boîte** — a physical medication box/pack, tracked individually for stock and expiry
- **médecin suiveur** — the médecin actively following a given patient (drives object-level permissions)

## Langue et méthode de travail

- **Langue de travail : français, précision exigée, aucune approximation** — particulièrement sur tout ce qui touche à la santé
- Toujours lire les fichiers réels avant d'écrire quoi que ce soit — ne jamais se fier à un résumé (voir la découverte ci-dessus sur le modèle de rôle)

## Décisions de conception figées — ne pas re-questionner

- Réserve/PRN : dépassement de dose = alerte, **jamais bloqué**
- Interactions : jamais de gravité devinée ; ambiguïté = exclusion (`InteractionNonImportee`)
- Médicaments : import BDPM uniquement, **jamais de saisie manuelle**

## Déploiement production (Arcane / bunkerpc)

- Serveur `bunkerpc` (AlmaLinux 10), Tailscale `100.104.19.8`
- Projet synchronisé par Git via Arcane dans `/home/docker-data/volumes/arcane_arcane-data/_data/projects/medicgest/`
- `.env` production **jamais dans Git**, géré séparément sur le serveur
- Cycle : `git add -A && git commit && git push` → Arcane sync → **Force Recreate** si `requirements.txt` a changé (sinon Redeploy suffit) → si nouvelle migration : `docker compose exec backend python manage.py migrate` (pas automatique) → vérifier `docker compose exec backend python manage.py test apps`
- `git status` puis `git diff --stat` avant tout commit — vérifier que les chemins modifiés correspondent à ceux annoncés

## Comptes de test (serveur)

`testadmin@example.com` (admin), `medecin.test@example.com` (médecin, suit `DOS-PRESC-1`), `patient.test@example.com`. Mot de passe commun : `motdepasse123`.