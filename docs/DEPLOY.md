# Deploying Apex Prep (Neon + GitHub + Render)

You'll end up with one web app at `https://<name>.onrender.com`, backed by a free Neon Postgres database. Plan for about 20 minutes. Everything here is free-tier.

## 1. Create the database (Neon)

1. Sign up at <https://neon.tech> and create a project named `apex-prep`.
   - **Region:** *AWS Europe Central 1 (Frankfurt)*. It matches `region: frankfurt` in `render.yaml`. If you pick another region, change that line to the nearest Render region.
   - Postgres version: 16 or newer.
2. On the project dashboard, click **Connect**. You need **two** connection strings:
   - **Pooled:** with *Connection pooling* switched **on**. The host contains `-pooler`. This becomes `DATABASE_URL`.
   - **Direct:** with *Connection pooling* switched **off**. This becomes `DATABASE_URL_DIRECT`, which the migrations use.
   Both look like `postgresql://user:password@ep-....neon.tech/neondb?sslmode=require&channel_binding=require`. Copy them exactly as shown; the app handles the `sslmode`/`channel_binding` parts itself.
   Keep them private: the password is in the string.

## 2. Push the code to GitHub

1. Create a **private** repository on <https://github.com/new> (e.g. `apex-prep`). Don't add a README or .gitignore; the project already has them.
2. In this folder:
   ```bash
   git remote add origin https://github.com/<you>/apex-prep.git
   git push -u origin main
   ```
3. On GitHub, open the **Actions** tab. The *CI* workflow should turn green within a few minutes.

## 3. Create the web service (Render)

1. Sign up at <https://render.com> with your GitHub account.
2. **New → Blueprint**, select the `apex-prep` repository. Render reads `render.yaml` and proposes one web service, `apex-prep`.
3. It asks for the variables marked as secret:

   | Variable | Value |
   |---|---|
   | `DATABASE_URL` | Neon **pooled** string |
   | `DATABASE_URL_DIRECT` | Neon **direct** string |
   | `ANTHROPIC_API_KEY` | leave empty (generation runs locally or in GitHub Actions, see §5) |
   | `VITE_DESMOS_API_KEY` | leave empty (a built-in calculator is used) |

   `SECRET_KEY` is generated automatically. `ALLOW_REGISTRATION` starts as `true`.
4. Click **Apply**. The first build takes about 5 minutes. On every start, the service runs the database migrations, then starts the app.
5. Open `https://<name>.onrender.com/api/health`. You should see `{"status":"ok"}`.

> **Free-tier sleep:** after 15 minutes without traffic, Render stops the service. The next visit shows "Waking up the server…" for 30–60 seconds. That's expected, not an error.

## 4. Create your account, then lock registration

1. Open `https://<name>.onrender.com`, click **No account yet? Register**, and sign up. Use a password of at least 10 characters.
2. In Render: **apex-prep → Environment**, set `ALLOW_REGISTRATION` to `false`, and save. Render redeploys automatically.
3. Check: signing out and trying to register again should say "Registration is closed".

## 5. Later

- **Questions/skills (milestone 2+):** loaded automatically on every start with `python -m app.seed`. It's idempotent, so there's nothing to run by hand.
- **Generating more Reading & Writing questions:** the web app never calls the Anthropic API; it only serves stored questions. Generation is a separate command that writes straight into the database, so the key doesn't need to be on Render.
  - **Locally:** put `ANTHROPIC_API_KEY` in `.env`, point `DATABASE_URL` at Neon's *direct* URL, then run `cd backend && uv run python -m app.generate rw --skill RW.SEC --n 3` (add `--dry-run` to preview without saving). `--skill` takes a sub-skill or any parent node; `--difficulty` is `easy`, `medium`, `hard`, or `mixed`.
  - **From GitHub:** add repository secrets `ANTHROPIC_API_KEY` and `DATABASE_URL_DIRECT`, then **Actions → Generate R&W questions → Run workflow**.
  - Each item is blind-solved by a second model call that never sees the key; items with a mismatched or ambiguous answer, or that nearly duplicate a stored passage, are dropped. The command prints how many were accepted and why others were rejected.
- **Updating:** `git push` to `main`. CI runs, and Render redeploys on its own.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Deploy log: `SECRET_KEY must be set…` | Environment → `SECRET_KEY` → *Generate* |
| Deploy log: `password authentication failed` / `ssl` errors | Re-copy both Neon strings; make sure pooled/direct aren't swapped |
| `prepared statement … does not exist` | `DATABASE_URL` must be the pooled host containing `-pooler`; the app turns off statement caching for it |
| Health check fails right after Neon was idle | Neon wakes in about 1 s; Render retries the check, so wait a minute |
