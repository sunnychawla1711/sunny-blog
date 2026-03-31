from flask import Flask, render_template, request, session, redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pymysql
import os
import json
from flask_mail import Mail

pymysql.install_as_MySQLdb()

# Load config
with open('config.json', 'r', encoding='utf-8') as c:
    params = json.load(c)["params"]

app = Flask(__name__)

@app.context_processor
def inject_params():
    return dict(params=params)

app.secret_key = 'super-secret-key'
app.config['UPLOAD_FOLDER'] = params['upload_location']

# MAIL CONFIG
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT='465',
    MAIL_USE_SSL=True,
    MAIL_USERNAME=os.environ.get('MAIL_USERNAME'),
    MAIL_PASSWORD=os.environ.get('MAIL_PASSWORD')
)

mail = Mail(app)

# DATABASE (only for contact form)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
db = SQLAlchemy(app)

# ---------------- MODELS ----------------

class Contacts(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    phone_num = db.Column(db.String(12), nullable=False)
    msg = db.Column(db.String(500), nullable=False)
    date = db.Column(db.String(50), nullable=True)
    email = db.Column(db.String(50), nullable=False)

with app.app_context():
    db.create_all()

# ---------------- JSON HELPERS ----------------

def load_posts():
    try:
        with open('posts.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

# ---------------- ROUTES ----------------

@app.route('/')
def home():
    posts = load_posts()
    no_of_posts = int(params['no_of_posts'])

    total_posts = len(posts)
    last = (total_posts + no_of_posts - 1) // no_of_posts
    if last == 0:
        last = 1

    page = request.args.get('page')
    if not str(page).isnumeric():
        page = 1
    page = int(page)

    start = (page - 1) * no_of_posts
    end = start + no_of_posts
    posts = posts[start:end]

    if page <= 1:
        prev = "#"
        next = "/?page=2" if total_posts > no_of_posts else "#"
    elif page >= last:
        prev = f"/?page={page-1}"
        next = "#"
    else:
        prev = f"/?page={page-1}"
        next = f"/?page={page+1}"

    return render_template('index.html', params=params, posts=posts, prev=prev, next=next)

@app.route('/about')
def about():
    return render_template('about.html', params=params)

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user' in session and session['user'] == os.environ.get('ADMIN_USER'):
        posts = load_posts()
        return render_template('dashboard.html', params=params, posts=posts)

    if request.method == 'POST':
        username = request.form.get("uname")
        userpass = request.form.get("pass")

        if username == os.environ.get('ADMIN_USER') and userpass == os.environ.get('ADMIN_PASSWORD'):
            session['user'] = username
            posts = load_posts()
            return render_template('dashboard.html', params=params, posts=posts)

    return render_template('login.html', params=params)

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            email = request.form.get('email')
            phone = request.form.get('phone')
            message = request.form.get('message')

            entry = Contacts(
                name=name,
                phone_num=phone,
                msg=message,
                date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                email=email
            )
            db.session.add(entry)
            db.session.commit()

            if os.environ.get('MAIL_USERNAME'):
                mail.send_message(
                    'New message from ' + name,
                    sender=os.environ.get('MAIL_USERNAME'),
                    recipients=[os.environ.get('MAIL_USERNAME')],
                    body=message + "\n" + phone
                )

            return "Message sent successfully!"

        except Exception as e:
            print("ERROR:", e)
            return "Something went wrong."

    return render_template('contact.html', params=params)

@app.route("/post/<string:post_slug>")
def post_route(post_slug):
    posts = load_posts()
    post = None

    for p in posts:
        if p['slug'] == post_slug:
            post = p
            break

    if post is None:
        return "Post not found", 404

    return render_template('post.html', params=params, post=post)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/dashboard')

if __name__ == "__main__":
    app.run()
