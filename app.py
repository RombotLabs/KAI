from flask import Flask, render_template, request, jsonify, url_for, flash, redirect, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from dotenv import load_dotenv
import os
from libs.ufm import *
from libs.lmsHandler import *
from libs.SQL_Handler import *
from libs.model import User

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')
sql_handler = SQL_Handler()
ph = PasswordHasher()
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    daten = sql_handler.user_suchen_by_id(int(user_id))

    if daten:
        return User(daten)

    return None
@app.route('/')
def index():
    return render_template('index.html')

@app.route('login', methods=['GET', 'POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    hashed_password = ph.hash(password)
    user = sql_handler.user_suchen(username)
    try:
        ph.verify(
            user["password_hash"],
            password
        )
        login_user(User(user))

    except VerifyMismatchError:
        print("Falsches Passwort")


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        # Prüfen, ob User existiert
        vorhandener_user = sql_handler.user_suchen(username)
        if vorhandener_user:
            return "Username existiert bereits", 409
        # Passwort hashen
        password_hash = ph.hash(password)
        # User speichern
        user_id = sql_handler.user_hinzufuegen(
            username=username,
            openid_user="",
            password_hash=password_hash,
            rights="user",
            chat_folder_destination=f"data/user/{username}/",
            banned=0
        )
        # User aus DB laden
        daten = sql_handler.user_suchen_by_id(user_id)
        # Flask-Login Session erstellen
        login_user(User(daten))
        return redirect(url_for("home"))
    return render_template("register.html")

@app.route('/chats', methods=['POST'])
@login_required
def chats():
    if current_user.banned == "1":
        return redirect(url_for("login"))

@app.route('/chat/<user_id>/<chat_id>', methods=['POST'])
@login_required
def chat(user_id, chat_id):
    if current_user.banned == "1":
        return redirect(url_for("login"))

    return render_template("chat.html")

@app.route('/chat/send/<user_id>/<chat_id>', methods=['GET'])
@login_required
def send_message(user_id, chat_id):
    if current_user.banned == "1":
        return redirect(url_for("login"))

@app.route('/admin', methods=['GET'])
@login_required
def admin():
    if current_user.rights == "admin" and not current_user.banned == "1":
        return render_template("admin.html")
    else:
        return redirect(url_for("index"))

@app.route('/ban/<user_id>', methods=['GET'])
@login_required
def ban(user_id):
    pass

@app.route('/unban/<user_id>', methods=['GET'])
@login_required
def unban(user_id):
    pass

@app.route('/set-rights/<user_id>', methods=['POST'])
@login_required
def set_rights(user_id):
    pass

@app.route('/spectate/<user_id>', methods=['POST'])
@login_required
def spectate(user_id):
    pass

@app.errorhandler(403)
def forbidden(error):
    return render_template('403.html'), 403

@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404

if __name__ == "__main__":
    app.run(debug=True)
