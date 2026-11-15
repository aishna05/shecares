# SheCares

Live demo: https://shecares-mocha.vercel.app/

GitHub: https://github.com/aishna05/shecares

A website where women can talk to a gynecologist, keep their reports, and track periods or pregnancy — without running around between apps.

Patients search and book a clinic visit, optionally mark it urgent, keep prescriptions and reports in one login, and log periods or pregnancy. Gynecologists see only the patients they have a visit with, pick up urgent requests first, and write prescriptions. Admins approve doctor accounts, moderate the forum, handle complaints, and watch urgent-request delays. Admins cannot open medical files.

The site does not diagnose illness and it is not an emergency ward.

Built with React (Vite), Django, and SQL (SQLite for local use). Passwords are hashed. Uploaded reports are encrypted on disk and served only through a permission check.

## Guide

Group 6, IIIT Vadodara. Guide: Dr. Karan Verma.

| Name | Roll number |
| --- | --- |
| Aishna Bhatia | 202351003 |
| Sunita Choudhary | 202351141 |

## What is finished

The course project is complete and deployed. The live site above is the same app as this repo.

- A patient, a gynecologist, and an admin each get their own home after login.
- A patient can search or describe symptoms, pick a slot, book, or mark the visit urgent.
- Prescriptions and uploaded reports stay on her account. Reports are encrypted, and a download is allowed only after a permission check.
- She can log a period or a pregnancy. Saving a cycle or a booking adds a reminder.
- An approved doctor sees today's visits with urgent ones first, opens the record, and writes the prescription.
- A new doctor stays hidden until an admin approves the account.
- The admin approves doctors, removes forum posts, answers complaints, and sees how long an urgent request has waited. The admin cannot open medical files.
- Forum posts, doctor articles, visit ratings, and complaints are in the site.
- Privacy tests cover report access, the admin list, the access log, and that a stored file is not plaintext.

The sample password on the live demo is the same as local: `SheCares#2026`.

## Workflow

Everyone starts the same way: register or log in. The site checks the role and opens that person's home.

**Patient**

1. Open the live demo and log in, or create a patient account.
2. On the home page, read reminders, upcoming visits, and prescriptions already saved.
3. Go to Find a doctor. Type symptoms if you want a match, or search by name, clinic, or concern.
4. Open a doctor, click a free slot, write a note for that visit, then book it or mark it urgent.
5. Open Visits to see the booking. A finished visit can be rated.
6. Open Records to download a report or add a PDF or photo.
7. Open Cycle to save period dates or a pregnancy log.
8. Use Forum and Articles to read and post. Use Raise a complaint in the footer for a problem with the site, not a medical file.

**Gynecologist**

1. Log in with an approved doctor account. A doctor who is not approved yet only sees a waiting screen.
2. Today's list shows urgent visits first. Open a visit. That tells the admin desk the request was picked up.
3. Read the note, the reports, and the cycle dates for that patient. Another doctor with no visit cannot open them.
4. Write medicines, advice, and a note, then save. That completes the visit and shows the prescription on the patient's account.
5. On Schedule, keep the clinic profile and add free slots.
6. On Write, publish an article. Patients can read articles. They cannot publish them.

**Admin**

1. Log in as admin.
2. The overview counts doctors waiting, urgent requests not picked up, open complaints, and removed posts.
3. Approve or decline a doctor on Doctors.
4. Remove junk on Forum.
5. On Urgent, see who is waiting and for how long. The symptom note is not on this screen.
6. Answer a complaint, then read Logs. The log stores the action, not the symptom text, the prescription, or the file.

## Run it

From `backend`, with the virtualenv:

```powershell
.\.venv\Scripts\python manage.py migrate
.\.venv\Scripts\python manage.py seed
.\.venv\Scripts\python manage.py runserver
```

`seed` wipes existing accounts and loads the sample clinic. Password for every seeded account is `SheCares#2026`.

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
