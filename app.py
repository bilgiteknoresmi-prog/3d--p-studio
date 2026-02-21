# app.py — 3D IP Studio site (Flask + SQLite) — tek dosya
# Sayfalar: Ana / Ürünler / Blog / Vizyon-Misyon / İletişim (mesaj)
# Admin: ürün+blog ekle/sil, mesajları gör/sil
# Admin şifresi ENV: ADMIN_PASSWORD (asla UI'da gösterilmez)

from __future__ import annotations
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from flask import Flask, request, redirect, url_for, render_template_string, session, abort

BRAND = "3D IP Studio"
DB_PATH = Path("site.db")

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")  # boşsa admin login olmaz
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-this-secret-key")

# ---------- DB ----------
def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def init_db():
    with db() as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS products(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            short_desc TEXT NOT NULL,
            price TEXT NOT NULL,
            material TEXT,
            created_at TEXT NOT NULL
        )""")
        con.execute("""
        CREATE TABLE IF NOT EXISTS posts(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            slug TEXT NOT NULL UNIQUE,
            summary TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        )""")
        con.execute("""
        CREATE TABLE IF NOT EXISTS messages(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            subject TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL
        )""")

def seed():
    with db() as con:
        if con.execute("SELECT COUNT(*) c FROM products").fetchone()["c"] == 0:
            con.execute("INSERT INTO products(name,short_desc,price,material,created_at) VALUES(?,?,?,?,?)",
                        ("PS5 Standı (Kablo Kanallı)",
                         "Alt kısımdan kablo girişi, sağlam gövde. Renk özelleştirilebilir.",
                         "₺___",
                         "PLA / PETG",
                         now()))
            con.execute("INSERT INTO products(name,short_desc,price,material,created_at) VALUES(?,?,?,?,?)",
                        ("DualSense Standı (Çiftli)",
                         "2 kontrolcü için minimal stand. Masada çok şık durur.",
                         "₺___",
                         "PLA",
                         now()))
        if con.execute("SELECT COUNT(*) c FROM posts").fetchone()["c"] == 0:
            con.execute("INSERT INTO posts(title,slug,summary,content,created_at) VALUES(?,?,?,?,?)",
                        ("Baskı İpucu: Pürüzsüz Yüzey İçin 5 Ayar",
                         "puruzsuz-yuzey-icin-5-ayar",
                         "İlk katman, sıcaklık ve hız… pürüzsüz yüzey için 5 pratik ayar.",
                         "1) İlk katman hızını düşür\n2) Sıcaklığı kalibre et\n3) Fan ayarlarını doğru kur\n4) Retract'ı dengeli yap\n5) Üst katman sayısını artır\n\nİstersen yazıcına göre profil öneririm.",
                         now()))

def slugify(s: str) -> str:
    s = (s or "").strip().lower()
    rep = {"ç":"c","ğ":"g","ı":"i","İ":"i","ö":"o","ş":"s","ü":"u"," ":"-","_":"-"}
    for k,v in rep.items():
        s = s.replace(k, v)
    out, dash = [], False
    for ch in s:
        if ch.isalnum():
            out.append(ch); dash = False
        elif ch == "-" and not dash:
            out.append("-"); dash = True
    return "".join(out).strip("-") or "yazi"

# ---------- Auth ----------
def is_admin() -> bool:
    return session.get("is_admin") is True

def require_admin():
    if not is_admin():
        abort(403)

@app.before_request
def _setup():
    init_db()
    seed()

# ---------- UI ----------
BASE = """
<!doctype html><html lang="tr"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ title }} · {{ brand }}</title>
<style>
  body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial;margin:0;background:#fff;color:#111}
  .top{position:sticky;top:0;background:#fff;border-bottom:1px solid #eee;z-index:10}
  .wrap{max-width:1100px;margin:0 auto;padding:18px 20px}
  .nav{display:flex;justify-content:space-between;align-items:center;gap:14px}
  .brand{font-weight:900;font-size:20px}
  .muted{color:#666;font-size:13px}
  .links a{text-decoration:none;color:#111;padding:10px 10px;border-radius:12px;display:inline-block}
  .links a:hover{background:#f5f5f5}
  .active{background:#111;color:#fff !important}
  .grid{display:grid;grid-template-columns:2fr 1fr;gap:16px}
  .card{border:1px solid #e6e6e6;border-radius:18px;padding:16px;margin:12px 0;box-shadow:0 1px 0 rgba(0,0,0,.02)}
  .btn{padding:10px 14px;border-radius:12px;border:0;cursor:pointer;background:#111;color:#fff}
  .btn2{padding:10px 14px;border-radius:12px;border:1px solid #ccc;cursor:pointer;background:transparent}
  .danger{color:#b00020;border-color:#f0b6bf}
  input,textarea{width:100%;padding:10px;border-radius:12px;border:1px solid #ccc}
  label{display:block;margin:10px 0 6px;font-weight:700}
  .row{display:grid;grid-template-columns:1fr 1fr;gap:12px}
  .hr{height:1px;background:#eee;margin:16px 0}
  .pill{display:inline-block;font-size:12px;padding:4px 10px;border-radius:999px;border:1px solid #ddd;background:#fafafa}
  footer{border-top:1px solid #eee;margin-top:22px}
</style></head><body>

<div class="top">
  <div class="wrap nav">
    <div>
      <div class="brand">{{ brand }}</div>
      <div class="muted">3D yazıcıyla ürün basıp satıyorum · butik üretim · özel tasarım</div>
    </div>
    <div class="links">
      <a class="{{ 'active' if active=='home' else '' }}" href="{{ url_for('home') }}">Ana Sayfa</a>
      <a class="{{ 'active' if active=='products' else '' }}" href="{{ url_for('products') }}">Ürünler</a>
      <a class="{{ 'active' if active=='blog' else '' }}" href="{{ url_for('blog') }}">Blog</a>
      <a class="{{ 'active' if active=='vision' else '' }}" href="{{ url_for('vision') }}">Vizyon & Misyon</a>
      <a class="{{ 'active' if active=='contact' else '' }}" href="{{ url_for('contact') }}">İletişim</a>
      {% if is_admin %}
        <a class="{{ 'active' if active=='admin' else '' }}" href="{{ url_for('admin') }}"><span class="pill">Admin</span></a>
        <a class="muted" href="{{ url_for('admin_logout') }}">Çıkış</a>
      {% else %}
        <a class="muted" href="{{ url_for('admin_login') }}">Admin</a>
      {% endif %}
    </div>
  </div>
</div>

<div class="wrap">
  {{ body|safe }}
  <footer class="wrap muted">
    © {{ year }} · {{ brand }}
  </footer>
</div>

</body></html>
"""

def render(title: str, active: str, body: str, **ctx):
    return render_template_string(
        BASE,
        title=title,
        brand=BRAND,
        active=active,
        body=render_template_string(body, **ctx),
        year=datetime.now().year,
        is_admin=is_admin(),
    )

# ---------- Pages ----------
HOME_TPL = """
<div class="grid">
  <div>
    <div class="card">
      <h1 style="margin:0 0 6px;">Hoş geldin 👋</h1>
      <div class="muted">Ürünlerimi 3D yazıcıyla basıyorum. Blog’da baskı ipuçları paylaşıyorum. İletişimden mesaj bırakabilirsin.</div>
      <div class="hr"></div>
      <div style="display:flex;gap:10px;flex-wrap:wrap;">
        <a class="btn2" href="{{ url_for('products') }}">Ürünlere Bak</a>
        <a class="btn2" href="{{ url_for('blog') }}">Blog’a Git</a>
        <a class="btn" href="{{ url_for('contact') }}">Mesaj Yaz</a>
      </div>
    </div>

    <h2>Son Ürünler</h2>
    {% for p in products %}
      <div class="card">
        <div class="muted">{{ p.created_at }}</div>
        <h3 style="margin:8px 0 6px;">{{ p.name }}</h3>
        <div class="muted">Malzeme: {{ p.material or '-' }} · Fiyat: {{ p.price }}</div>
        <p style="margin-top:10px;">{{ p.short_desc }}</p>
      </div>
    {% endfor %}
  </div>

  <div>
    <div class="card">
      <h3>Hızlı İletişim</h3>
      <p class="muted">Özel tasarım / renk / ölçü için mesaj bırak.</p>
      <a class="btn" href="{{ url_for('contact') }}">İletişime Git</a>
    </div>

    <div class="card">
      <h3>Son Blog Yazıları</h3>
      {% for b in posts %}
        <div style="padding:10px 0;border-bottom:1px solid #eee;">
          <a href="{{ url_for('post_detail', slug=b.slug) }}"><strong>{{ b.title }}</strong></a>
          <div class="muted">{{ b.created_at }}</div>
        </div>
      {% endfor %}
      {% if posts|length == 0 %}
        <div class="muted">Henüz yazı yok.</div>
      {% endif %}
    </div>
  </div>
</div>
"""

PRODUCTS_TPL = """
<h1>Ürünler</h1>
<p class="muted">Stok, renk ve ölçü için iletişimden yazabilirsin.</p>

{% for p in products %}
  <div class="card">
    <div class="muted">{{ p.created_at }}</div>
    <div style="display:flex;justify-content:space-between;gap:12px;align-items:flex-start;flex-wrap:wrap;">
      <div>
        <h2 style="margin:8px 0 6px;">{{ p.name }}</h2>
        <div class="muted">Malzeme: {{ p.material or '-' }}</div>
      </div>
      <div class="pill">Fiyat: {{ p.price }}</div>
    </div>
    <p style="margin-top:10px;">{{ p.short_desc }}</p>
    <a class="btn2" href="{{ url_for('contact') }}">Sipariş / Soru</a>

    {% if is_admin %}
      <form method="post" action="{{ url_for('admin_delete_product', product_id=p.id) }}" style="margin-top:10px;">
        <button class="btn2 danger" type="submit" onclick="return confirm('Ürün silinsin mi?')">Ürünü Sil</button>
      </form>
    {% endif %}
  </div>
{% endfor %}
"""

BLOG_TPL = """
<h1>Blog</h1>
<p class="muted">Ürün güncellemeleri ve baskı ipuçları.</p>

{% for b in posts %}
  <div class="card">
    <div class="muted">{{ b.created_at }}</div>
    <h2 style="margin:8px 0 6px;"><a href="{{ url_for('post_detail', slug=b.slug) }}">{{ b.title }}</a></h2>
    <p>{{ b.summary }}</p>
  </div>
{% endfor %}
{% if posts|length == 0 %}
  <p class="muted">Henüz yazı yok.</p>
{% endif %}
"""

POST_TPL = """
<a class="muted" href="{{ url_for('blog') }}">← Blog’a dön</a>
<div class="card">
  <div class="muted">{{ post.created_at }}</div>
  <h1 style="margin:10px 0 6px;">{{ post.title }}</h1>
  <p class="muted">{{ post.summary }}</p>
  <div class="hr"></div>
  <div style="white-space:pre-wrap;line-height:1.6;">{{ post.content }}</div>
</div>
"""

VISION_TPL = """
<h1>Vizyon & Misyon</h1>

<div class="card">
  <h2>Vizyon</h2>
  <p>3D baskı ile günlük hayatta işe yarayan, şık ve sağlam ürünleri hızlıca üretmek ve herkesin ulaşabileceği hale getirmek.</p>
</div>

<div class="card">
  <h2>Misyon</h2>
  <ul>
    <li>Butik üretimle kişiye özel ölçü/renk seçenekleri sunmak</li>
    <li>Dayanıklılık odaklı tasarım ve baskı ayarları kullanmak</li>
    <li>Müşteri geri bildirimine göre tasarımları sürekli geliştirmek</li>
  </ul>
</div>

<div class="card">
  <h2>Üretim Notu</h2>
  <p class="muted">Siparişlerde malzeme (PLA/PETG), renk ve baskı süresi ürüne göre değişebilir.</p>
</div>
"""

CONTACT_TPL = """
<h1>İletişim</h1>
<p class="muted">Sipariş, özel tasarım, fiyat ve teslimat için mesaj bırak.</p>

<div class="grid">
  <div class="card">
    <h3>Mesaj Yaz</h3>
    <form method="post" action="{{ url_for('send_message') }}">
      <div class="row">
        <div>
          <label>İsim</label>
          <input name="name" required maxlength="40" placeholder="Adın">
        </div>
        <div>
          <label>E-posta</label>
          <input name="email" required type="email" maxlength="80" placeholder="ornek@mail.com">
        </div>
      </div>
      <label>Konu</label>
      <input name="subject" required maxlength="80" placeholder="Örn: PS5 standı - siyah renk">
      <label>Mesaj</label>
      <textarea name="message" required rows="6" maxlength="1500" placeholder="Detayları yaz..."></textarea>
      <div style="margin-top:10px;">
        <button class="btn" type="submit">Gönder</button>
      </div>
    </form>
    {% if msg %}
      <div class="muted" style="margin-top:10px;">{{ msg }}</div>
    {% endif %}
  </div>

  <div class="card">
    <h3>Adres / Not</h3>
    <p class="muted">İstersen mesajda şunları yaz:</p>
    <ul class="muted">
      <li>Ürün adı</li>
      <li>Renk</li>
      <li>Malzeme (PLA/PETG)</li>
      <li>Adet</li>
      <li>Teslimat tarihi</li>
    </ul>
    {% if is_admin %}
      <a class="btn2" href="{{ url_for('admin_messages') }}">Gelen Mesajları Gör (Admin)</a>
    {% endif %}
  </div>
</div>
"""

# ---------- Routes ----------
@app.get("/")
def home():
    with db() as con:
        products = con.execute("SELECT * FROM products ORDER BY id DESC LIMIT 3").fetchall()
        posts = con.execute("SELECT * FROM posts ORDER BY id DESC LIMIT 3").fetchall()
    return render("Ana Sayfa", "home", HOME_TPL, products=products, posts=posts)

@app.get("/products")
def products():
    with db() as con:
        products = con.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
    return render("Ürünler", "products", PRODUCTS_TPL, products=products)

@app.get("/blog")
def blog():
    with db() as con:
        posts = con.execute("SELECT * FROM posts ORDER BY id DESC").fetchall()
    return render("Blog", "blog", BLOG_TPL, posts=posts)

@app.get("/blog/<slug>")
def post_detail(slug):
    with db() as con:
        post = con.execute("SELECT * FROM posts WHERE slug = ?", (slug,)).fetchone()
    if not post:
        abort(404)
    return render(post["title"], "blog", POST_TPL, post=post)

@app.get("/vision")
def vision():
    return render("Vizyon & Misyon", "vision", VISION_TPL)

@app.get("/contact")
def contact():
    msg = request.args.get("ok")
    return render("İletişim", "contact", CONTACT_TPL, msg=msg)

@app.post("/contact/send")
def send_message():
    name = (request.form.get("name") or "").strip()[:40]
    email = (request.form.get("email") or "").strip()[:80]
    subject = (request.form.get("subject") or "").strip()[:80]
    message = (request.form.get("message") or "").strip()[:1500]
    if not (name and email and subject and message):
        return redirect(url_for("contact", ok="Tüm alanları doldur."))
    with db() as con:
        con.execute("""INSERT INTO messages(name,email,subject,message,created_at)
                       VALUES(?,?,?,?,?)""",
                    (name, email, subject, message, now()))
    return redirect(url_for("contact", ok="Mesajın alındı ✅"))

# ---------- Admin ----------
ADMIN_LOGIN_TPL = """
<h1>Admin Giriş</h1>
<div class="card">
  <form method="post" action="{{ url_for('admin_login_post') }}">
    <label>Şifre</label>
    <input type="password" name="password" required placeholder="Admin şifresi">
    <div style="margin-top:10px;">
      <button class="btn" type="submit">Giriş</button>
    </div>
  </form>
  {% if msg %}<div class="muted" style="margin-top:10px;">{{ msg }}</div>{% endif %}
  <div class="hr"></div>
  <div class="muted">
    Not: Şifre sitede tutulmaz/gösterilmez. ENV <code>ADMIN_PASSWORD</code> olarak ayarlanmalıdır.
  </div>
</div>
"""

ADMIN_TPL = """
<h1>Admin Panel</h1>
<p class="muted">Ürün ve blog yazısı ekle/sil. Gelen mesajları ayrıca gör.</p>

<div class="grid">
  <div>
    <div class="card">
      <h2>Ürün Ekle</h2>
      <form method="post" action="{{ url_for('admin_add_product') }}">
        <label>Ürün Adı</label>
        <input name="name" required maxlength="80" placeholder="Örn: Telefon Standı">
        <label>Kısa Açıklama</label>
        <textarea name="short_desc" required rows="3" maxlength="400" placeholder="Kısaca ürün..."></textarea>
        <div class="row">
          <div>
            <label>Fiyat</label>
            <input name="price" required maxlength="20" placeholder="₺___">
          </div>
          <div>
            <label>Malzeme</label>
            <input name="material" maxlength="40" placeholder="PLA / PETG">
          </div>
        </div>
        <div style="margin-top:10px;">
          <button class="btn" type="submit">Ekle</button>
        </div>
      </form>
    </div>

    <h2>Ürünler</h2>
    {% for p in products %}
      <div class="card">
        <strong>{{ p.name }}</strong> <span class="muted">· {{ p.created_at }}</span><br>
        <span class="muted">Fiyat: {{ p.price }} · Malzeme: {{ p.material or '-' }}</span>
        <div style="margin-top:8px;">{{ p.short_desc }}</div>
        <form method="post" action="{{ url_for('admin_delete_product', product_id=p.id) }}" style="margin-top:10px;">
          <button class="btn2 danger" type="submit" onclick="return confirm('Ürün silinsin mi?')">Sil</button>
        </form>
      </div>
    {% endfor %}
  </div>

  <div>
    <div class="card">
      <h2>Blog Yazısı Ekle</h2>
      <form method="post" action="{{ url_for('admin_add_post') }}">
        <label>Başlık</label>
        <input name="title" required maxlength="120" placeholder="Örn: Yeni ürün - ...">
        <label>Özet</label>
        <input name="summary" required maxlength="220" placeholder="Kısa özet...">
        <label>İçerik</label>
        <textarea name="content" required rows="7" maxlength="8000" placeholder="Detaylı içerik..."></textarea>
        <div style="margin-top:10px;">
          <button class="btn" type="submit">Yayınla</button>
        </div>
      </form>
    </div>

    <div class="card">
      <h2>Gelen Mesajlar</h2>
      <p class="muted">İletişim formundan gelenleri gör.</p>
      <a class="btn2" href="{{ url_for('admin_messages') }}">Mesajlara Git</a>
    </div>

    <h2>Blog Yazıları</h2>
    {% for b in posts %}
      <div class="card">
        <strong>{{ b.title }}</strong><br>
        <span class="muted">{{ b.created_at }} · slug: {{ b.slug }}</span>
        <form method="post" action="{{ url_for('admin_delete_post', post_id=b.id) }}" style="margin-top:10px;">
          <button class="btn2 danger" type="submit" onclick="return confirm('Yazı silinsin mi?')">Sil</button>
        </form>
      </div>
    {% endfor %}
  </div>
</div>
"""

ADMIN_MESSAGES_TPL = """
<h1>Gelen Mesajlar</h1>
<p class="muted">İletişim formundan gelen mesajlar.</p>

{% for m in messages %}
  <div class="card">
    <div style="display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;">
      <div>
        <strong>{{ m.name }}</strong> · <span class="muted">{{ m.email }}</span><br>
        <span class="muted">{{ m.created_at }}</span>
      </div>
      <form method="post" action="{{ url_for('admin_delete_message', message_id=m.id) }}">
        <button class="btn2 danger" type="submit" onclick="return confirm('Mesaj silinsin mi?')">Sil</button>
      </form>
    </div>
    <div class="hr"></div>
    <div><strong>Konu:</strong> {{ m.subject }}</div>
    <p style="white-space:pre-wrap;margin-top:10px;">{{ m.message }}</p>
  </div>
{% endfor %}
{% if messages|length == 0 %}
  <p class="muted">Mesaj yok.</p>
{% endif %}
"""

@app.get("/admin/login")
def admin_login():
    return render("Admin Giriş", "admin", ADMIN_LOGIN_TPL, msg=request.args.get("m"))

@app.post("/admin/login")
def admin_login_post():
    if not ADMIN_PASSWORD:
        return redirect(url_for("admin_login", m="ADMIN_PASSWORD ayarlı değil. Önce ortam değişkenini ayarla."))
    pw = request.form.get("password") or ""
    if pw == ADMIN_PASSWORD:
        session["is_admin"] = True
        return redirect(url_for("admin"))
    return redirect(url_for("admin_login", m="Şifre yanlış."))

@app.get("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("home"))

@app.get("/admin")
def admin():
    require_admin()
    with db() as con:
        products = con.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
        posts = con.execute("SELECT * FROM posts ORDER BY id DESC").fetchall()
    return render("Admin", "admin", ADMIN_TPL, products=products, posts=posts)

@app.post("/admin/product/add")
def admin_add_product():
    require_admin()
    name = (request.form.get("name") or "").strip()[:80]
    short_desc = (request.form.get("short_desc") or "").strip()[:400]
    price = (request.form.get("price") or "").strip()[:20]
    material = (request.form.get("material") or "").strip()[:40]
    if not (name and short_desc and price):
        return redirect(url_for("admin"))
    with db() as con:
        con.execute("INSERT INTO products(name,short_desc,price,material,created_at) VALUES(?,?,?,?,?)",
                    (name, short_desc, price, material, now()))
    return redirect(url_for("products"))

@app.post("/admin/product/<int:product_id>/delete")
def admin_delete_product(product_id: int):
    require_admin()
    with db() as con:
        con.execute("DELETE FROM products WHERE id=?", (product_id,))
    return redirect(request.headers.get("Referer") or url_for("admin"))

@app.post("/admin/post/add")
def admin_add_post():
    require_admin()
    title = (request.form.get("title") or "").strip()[:120]
    summary = (request.form.get("summary") or "").strip()[:220]
    content = (request.form.get("content") or "").strip()[:8000]
    if not (title and summary and content):
        return redirect(url_for("admin"))
    slug = slugify(title)
    with db() as con:
        base = slug
        i = 2
        while con.execute("SELECT 1 FROM posts WHERE slug=?", (slug,)).fetchone():
            slug = f"{base}-{i}"
            i += 1
        con.execute("INSERT INTO posts(title,slug,summary,content,created_at) VALUES(?,?,?,?,?)",
                    (title, slug, summary, content, now()))
    return redirect(url_for("post_detail", slug=slug))

@app.post("/admin/post/<int:post_id>/delete")
def admin_delete_post(post_id: int):
    require_admin()
    with db() as con:
        con.execute("DELETE FROM posts WHERE id=?", (post_id,))
    return redirect(request.headers.get("Referer") or url_for("admin"))

@app.get("/admin/messages")
def admin_messages():
    require_admin()
    with db() as con:
        messages = con.execute("SELECT * FROM messages ORDER BY id DESC").fetchall()
    return render("Mesajlar", "admin", ADMIN_MESSAGES_TPL, messages=messages)

@app.post("/admin/message/<int:message_id>/delete")
def admin_delete_message(message_id: int):
    require_admin()
    with db() as con:
        con.execute("DELETE FROM messages WHERE id=?", (message_id,))
    return redirect(url_for("admin_messages"))

if __name__ == "__main__":
    init_db()
    seed()

    if __name__ == "__main__":
    init_db()
    seed()

    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)


