# 🌿 StaffMark — Green Integrated Pest Control

Employee Attendance & Salary Management System

---

## Files
- `app.py` — Python Flask backend (server + database + login)
- `requirements.txt` — Python packages
- `Procfile` — Railway start command
- `railway.toml` — Railway config
- `templates/index.html` — Main app (Staff, Attendance, Salary, History)
- `templates/login.html` — Login page

---

## Default Login

| Field | Value |
|---|---|
| Email | `admin@greenpestcontrol.com` |
| Password | `GIPC@2026` |

**Change these before going live** — set the `ADMIN_EMAIL` and `ADMIN_PASSWORD` environment variables on Railway (see Step 3 below), or log in once deployed and use the change-password option.

---

## 🚀 Deploy for Free on Railway.app

### Step 1 — Create a GitHub Account
Go to github.com and sign up for a free account.

### Step 2 — Create a Repository
1. Click "New Repository"
2. Name it `staffmark`
3. Keep it public
4. Upload all the files from this folder (app.py, requirements.txt, Procfile, railway.toml, templates/ folder)

### Step 3 — Deploy on Railway
1. Go to railway.app
2. Click "Start a New Project"
3. Choose "Deploy from GitHub repo"
4. Select your `staffmark` repository
5. (Recommended) Add environment variables under Settings → Variables:
   - `ADMIN_EMAIL` = your email
   - `ADMIN_PASSWORD` = a strong password
   - `SECRET_KEY` = any random long string
6. Railway will deploy automatically

### Step 4 — Get Your Link
Railway gives you a free link like:
`https://staffmark-production.up.railway.app`

This works from any phone or computer — just log in with your email and password.

---

## Features
✅ Secure login (email + password)
✅ Add / edit / delete employees
✅ Daily attendance — Present / Absent / Half Day
✅ Advance / partial payment tracking
✅ Overtime tracking
✅ Automatic salary calculation
✅ PDF salary slip download (per employee or all at once)
✅ Salary History — finalize and store past months
✅ Cloud database — your data is safe
✅ Mobile and desktop friendly

---

## Tech Stack
- Backend: Python Flask
- Database: SQLite
- Frontend: HTML + CSS + JavaScript
- Hosting: Railway.app (Free tier)
