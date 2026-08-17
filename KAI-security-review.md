# KAI Security Review

Repo: `RombotLabs/KAI` — reviewed at commit `4ffec8a` (main).

Ranked by severity. The first section needs action **today** because it involves data that's already public.

---

## 🔴 CRITICAL — act immediately

### 1. Real user data is committed and public right now
- `backup.sql` contains a live dump of your `users` table: 4 real usernames, roles, and **argon2 password hashes**.
- `data/user/3/1.json` contains an actual student's chat transcript.
- `info.txt` leaks your internal MySQL host (`10.254.0.185:3306`).

**Why it matters:** anyone can `git clone` this repo right now and get that data. Deleting the files in a new commit is *not* enough — they stay in git history forever until you rewrite it.

**Fix:**
1. Rotate everything that was exposed: reset all 4 accounts' passwords, change `SECRET_KEY` if it was ever committed (it doesn't look like it was — good).
2. Purge history with [`git filter-repo`](https://github.com/newren/git-filter-repo) (BFG works too), then force-push. Have any collaborators re-clone.
3. Add to `.gitignore`: `backup.sql`, `data/user/`, `info.txt`. None of these belong in version control — `backup.sql` should be a local/deploy-time artifact, and `data/user/` is student data (this is also a real DSGVO concern given the project's whole premise is being GDPR-friendly for schools).
4. Never seed a repo with a production/real dump again — use synthetic fixture data for `docker-compose`'s auto-import instead.

### 2. Shared global state leaks chats between concurrently logged-in users
In `app.py`:
```python
ufm = UFM()   # one instance, shared by the whole process
```
In `libs/ufm.py`, `current_user_path` is stored **on that single shared instance**:
```python
def setup(self, user_id):
    self.current_user_path = os.path.join(self.BASE_DATA_PATH, str(user_id))
```
`setup()` is called on every login. Flask handles requests concurrently (threaded dev server, or multiple gunicorn threads/workers sharing state if not careful). If two users are logged in at the same time, one user's request can overwrite `current_user_path` while another user's request is mid-flight — meaning **user A can end up reading, writing to, or deleting user B's chat files**. This isn't a theoretical edge case for a school app with concurrent logins; it's the normal usage pattern.

**Fix:** stop using instance state for per-user context. Either:
- Make `UFM` stateless — pass `user_id` into every method (`load_chat(user_id, chat_id)`, etc.) instead of storing it, or
- Instantiate a `UFM` per-request (e.g., store the path on `current_user` or in `g`), or
- At minimum, add an explicit ownership check on every chat route (see #5 below too) so a mismatch can't silently serve the wrong user's data.

### 3. Debug mode is the default, and it's live-RCE if it ever leaks through
- `app.py`: `app.run(debug=True)`
- `.env.example`: `FLASK_DEBUG=1`

If this ever runs in production (or is reachable) with debug on, the Werkzeug interactive debugger lets anyone who can trigger a 500 error get a Python console on your server — full remote code execution, not just a stack trace leak.

**Fix:** `app.run(debug=os.getenv("FLASK_DEBUG", "0") == "1")`, and make sure the real `.env` used for deployment has `FLASK_DEBUG=0`. Don't run via `app.run()` in production at all — use gunicorn/waitress.

### 4. MySQL exposed to the network with weak default credentials
`docker-compose.yml` publishes `3306:3306` and falls back to `rootpassword` / `kaiuser` / `kaipassword` if the real `.env` isn't set:
```yaml
MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD:-rootpassword}
```
If this compose file is ever run on a host without a proper `.env`, your DB is reachable from the network with credentials that are now public (they're in this public repo).

**Fix:** drop the weak defaults entirely (fail loudly if the env var isn't set), and don't publish 3306 to the host unless something outside the compose network genuinely needs it.

---

## 🟠 HIGH

### 5. Banned users aren't actually blocked (type bug)
```python
if current_user.banned == "1":   # comparing int to string
```
`banned` comes from MySQL as a Python `int` (0/1), not a string. `1 == "1"` is `False` in Python, so this check **never fires** — banned users keep full access to `/home`, `/chat/<id>`, `/chat/<id>/send`, `/chat/<id>/delete`, `/chats`. Same bug appears in `/ban`, `/unban`, `/set-rights` (`current_user.banned != "1"`), which affects whether a banned admin can still act.

**Fix:** compare to `1` (int), or better, cast once: `bool(current_user.banned)`.

### 6. No CSRF protection anywhere
No CSRF tokens on any form or fetch call, and no `flask-wtf`/CSRF library in `requirements.txt`. `/ban/<id>`, `/unban/<id>`, `/set-rights/<id>`, `/chat/<id>/delete`, `/chat/<id>/send` are all state-changing POST endpoints reachable with just a cookie. Flask's default `SameSite=Lax` gives partial mitigation, but that's incidental, not a real defense for admin actions like changing someone's rights.

**Fix:** add `flask-wtf`'s `CSRFProtect(app)`, or at minimum a custom header + origin check for your fetch-based endpoints.

### 7. No server-side input validation on register/login
`register.html` enforces `minlength="8"` and a username pattern via HTML attributes only. `app.py`'s `/register` does zero server-side checks:
```python
password = request.form.get("password")
password_hash = ph.hash(password)   # empty string works fine
```
Anyone bypassing the browser (curl, Burp, etc.) can register with a 1-character password or an empty username. There's also no rate limiting on `/login`, so brute-forcing is unthrottled.

**Fix:** re-validate length/charset server-side; add `flask-limiter` on `/login` and `/register`.

### 8. `/set-rights` doesn't validate the new role value
```python
new_rights = data.get('rights')
sql_handler.user_bearbeiten(user_id, {"rights": new_rights})
```
Any string is accepted and sent to the DB (the `rights` column is an enum, so MySQL itself will reject bad values, but this relies entirely on the DB catching it rather than the app).

**Fix:** whitelist against `{"student", "teacher", "admin", "owner"}` before calling the DB layer.

---

## 🟡 MEDIUM

### 9. Assistant messages are rendered with partial-only HTML escaping (stored XSS surface)
In `chat.html`:
```js
const rendered = role==='user' ? escapeHtml(content) : parseMarkdown(content)
...
msgDiv.innerHTML = `...${rendered}...`
```
User messages are escaped. **Assistant messages are not** — `parseMarkdown()` only escapes text inside code fences/inline code; everything else (headers, bold, links, plain text) is regex-substituted and dropped straight into `innerHTML`. Since the LLM's raw output becomes that text, a prompt-injected or adversarial response containing `<img src=x onerror=...>` or `<script>` outside a code block would execute in the browser. Given KAI is meant for students experimenting with prompts, this isn't far-fetched.

**Fix:** escape the *entire* string first, then apply your markdown regexes to the escaped text (so tag-like sequences from the model can never become real elements), or swap in a real sanitizer (e.g., DOMPurify) after markdown rendering.

### 10. Open self-registration, no verification
Anyone who finds the URL can create a `student` account — no email/invite verification, no school-domain restriction. For a school-only tool, that means outsiders can consume your (presumably limited) local LLM compute.

**Fix:** invite codes, an allowed-email-domain check, or admin-approval gating on new accounts.

### 11. Debug prints of sensitive data
`print(user)` and `print(user.keys())` in `/login` will dump the full user dict — including `password_hash` — to your server logs on every login attempt.

**Fix:** remove these, or at least redact `password_hash` before logging.

---

## 🟢 LOW / notes
- `requirements.txt` has no pinned versions (`flask`, `requests`, etc.) — fine for a school project, but means a `pip install` next month could silently pull a breaking or vulnerable version. Consider pinning once things stabilize.
- `app.py` hardcodes the internal LM Studio address (`LMSHandler("10.254.0.185", "1234")`) instead of reading it from `.env` like the rest of the config does — inconsistent, and leaks internal topology in the public repo for no benefit.
- SQL layer (`SQL_Handler.py`) is solid — all queries are parameterized, no injection found there. Good practice to keep up.

---

## Suggested order of operations
1. Rotate exposed credentials, purge git history of `backup.sql` / `data/user/` / `info.txt`, add them to `.gitignore`.
2. Fix the `banned` comparison bug and the shared-`UFM`-instance bug (#2, #5) — both are "one user affects another user's data" classes of bug.
3. Turn off debug-by-default, remove weak DB credential fallbacks.
4. Add CSRF protection and server-side validation.
5. Fix the XSS escaping gap in `chat.html`.
