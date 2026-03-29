from flask import Flask, render_template, request, session, redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pymysql
import os
pymysql.install_as_MySQLdb()
import json
from flask_mail import Mail
from werkzeug.utils import secure_filename
import math

# Load config (only for non-sensitive data)
with open('config.json','r') as c:
    params = json.load(c)["params"]

app = Flask(__name__)

@app.context_processor
def inject_params():
    return dict(params=params)

app.secret_key = 'super-secret-key'
app.config['UPLOAD_FOLDER'] = params['upload_location']

# ✅ MAIL CONFIG (FIXED)
app.config.update(
    MAIL_SERVER = 'smtp.gmail.com',
    MAIL_PORT = '465',
    MAIL_USE_SSL = True,
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME'),
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
)

mail = Mail(app)

# ✅ DATABASE
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
db = SQLAlchemy(app)

# ---------------- MODELS ----------------

class Contacts(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    phone_num = db.Column(db.String(12), nullable=False)
    msg = db.Column(db.String(120), nullable=False)
    date = db.Column(db.String(12), nullable=True)
    email = db.Column(db.String(20), nullable=False)

class Posts(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80), nullable=False)
    slug = db.Column(db.String(21), nullable=False)
    content = db.Column(db.String(120), nullable=False)
    date = db.Column(db.String(12), nullable=True)
    img_file = db.Column(db.String(12), nullable=True)
    tagline = db.Column(db.String(120), nullable=False)

# ---------------- ROUTES ----------------

@app.route('/')
def home():
    posts = Posts.query.all()
    last = math.ceil(len(posts)/int(params['no_of_posts']))

    page = request.args.get('page')
    if not str(page).isnumeric():
        page = 1
    page = int(page)

    posts = posts[(page-1)*int(params['no_of_posts']):(page-1)*int(params['no_of_posts'])+int(params['no_of_posts'])]

    if page == 1:
        prev = "#"
        next = "/?page=" + str(page+1)
    elif page == last:
        prev = "/?page=" + str(page-1)
        next = "#"
    else:
        prev = "/?page=" + str(page-1)
        next = "/?page=" + str(page+1)

    return render_template('index.html', params=params, posts=posts, prev=prev, next=next)

@app.route('/about')
def about():
    return render_template('about.html', params=params)

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user' in session and session['user'] == os.environ.get('ADMIN_USER'):
        posts = Posts.query.all()
        return render_template('dashboard.html', params=params, posts=posts)

    if request.method == 'POST':
        username = request.form.get("uname")
        userpass = request.form.get("pass")

        if username == os.environ.get('ADMIN_USER') and userpass == os.environ.get('ADMIN_PASSWORD'):
            session['user'] = username
            posts = Posts.query.all()
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

            # Save to DB
            entry = Contacts(name=name, phone_num=phone, msg=message, date=datetime.now(), email=email)
            db.session.add(entry)
            db.session.commit()

            # Send Mail (SAFE)
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
            return "Something went wrong. Try again."

    return render_template('contact.html', params=params)

@app.route("/post/<string:post_slug>")
def post_route(post_slug):
    post = Posts.query.filter_by(slug=post_slug).first()
    return render_template('post.html', params=params, post=post)

@app.route('/logout')
def logout():
    session.pop('user')
    return redirect('/dashboard')

if __name__ == "__main__":
    app.run()
