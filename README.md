# SheCares

A website where women can talk to a gynecologist, keep their reports, and track periods or pregnancy — without running around between apps.

Patients search and book a clinic visit, optionally mark it urgent, keep prescriptions and reports in one login, and log periods or pregnancy. Gynecologists see only the patients they have a visit with, pick up urgent requests first, and write prescriptions. Admins approve doctor accounts, moderate the forum, handle complaints, and watch urgent-request delays. Admins cannot open medical files.

The site does not diagnose illness and it is not an emergency ward.

Built with React (Vite), Django, and SQL (SQLite for local use). Passwords are hashed. Uploaded reports are encrypted on disk and served only through a permission check.

## Run it

From `backend`, with the virtualenv:

```powershell
.\.venv\Scripts\python manage.py migrate
.\.venv\Scripts\python manage.py seed
.\.venv\Scripts\python manage.py runserver
```

`seed` wipes existing accounts and loads the demo. Password for every demo account is `SheCares#2026`.

| Who | Email |
| --- | --- |
| Patient | aisha@shecares.local |
| Patient | priya@shecares.local |
| Gynecologist | meera@shecares.local |
| Gynecologist with the urgent visit | ananya@shecares.local |
| Doctor waiting for approval | neha@shecares.local |
| Admin | admin@shecares.local |

From `frontend`:

```powershell
npm install
npm run dev
```

Open http://127.0.0.1:5173. The dev server proxies `/api` to Django on port 8000.

## Checks

```powershell
.\.venv\Scripts\python manage.py test core
```

The privacy tests check that another patient, an unrelated doctor, and an admin cannot download a report, that symptom text does not appear in the admin list or the access log, and that a stored file is not plaintext.
