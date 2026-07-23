from flask import Flask, render_template, request, jsonify, url_for, redirect, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from dotenv import load_dotenv
import os
from datetime import datetime
from libs.ufm import UFM
from libs.lmsHandler import LMSHandler
from libs.SQL_Handler import SQL_Handler
from libs.model import User

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')
sql_handler = SQL_Handler()
ph = PasswordHasher()
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'
lms = LMSHandler("127.0.0.1", "1234")
ufm = UFM()

print("MODEL TEST:")
print(lms.get_models())

@app.template_global()
def now():
    return datetime.now()

@login_manager.user_loader
def load_user(user_id):
    daten = sql_handler.user_suchen_by_id(int(user_id))
    if daten:
        return User(daten)
    return None


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/freechat', methods=['GET', 'POST'])
def freechat():
    return render_template('freechat.html', models=lms.get_models())

@app.route("/freechat/models")
def freechat_models():
    models = lms.get_models()
    # Embedding Modelle entfernen
    models = [
        model for model in models
        if "embed" not in model.lower()
    ]
    return jsonify({
        "models": models
    })

@app.route("/freechat/api", methods=["POST"])
def freechat_api():
    data = request.json

    print("FREECHAT API AUFGERUFEN")
    print(data)

    message = data["message"]
    model = data["model"]
    temperature = data["temperature"]

    response = lms.ask_ai_nochat(
        messages=[
            {
                "role": "user",
                "content": message
            }
        ],
        model=model,
        temperature=temperature
    )

    print("LM STUDIO RESPONSE:")
    print(response)

    return jsonify({
        "response": response
    })
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        username = request.form.get('username')
        password = request.form.get('password')

        user = sql_handler.user_suchen(username)
        print(user)
        print(user.keys())
        if not user:
            return render_template('login.html', error="User not found"), 401

        try:
            ph.verify(user["password_hash"], password)
            user_obj = User(user)
            login_user(user_obj)
            ufm.setup(user["id"])
            return redirect(url_for("home"))
        except VerifyMismatchError:
            return render_template('login.html', error="Wrong password"), 401

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        # Check if user exists
        vorhandener_user = sql_handler.user_suchen(username)
        if vorhandener_user:
            return render_template('register.html', error="Username already exists"), 409

        # Hash password and create user
        password_hash = ph.hash(password)
        user_id = sql_handler.user_hinzufuegen(
            username=username,
            openid_user="",
            password_hash=password_hash,
            rights="student",
            chat_folder_destination=f"data/user/{username}/",
            banned=0
        )

        # Load user and login
        daten = sql_handler.user_suchen_by_id(user_id)
        login_user(User(daten))
        ufm.setup(daten["id"])
        return redirect(url_for("home"))

    return render_template("register.html")


@app.route('/home')
@login_required
def home():
    """Home page with chat list"""
    if current_user.banned == "1":
        return redirect(url_for("login"))

    try:
        chats = ufm.get_chats()
        chat_summaries = []
        for chat_id in chats:
            try:
                summary = ufm.get_chat_summary(chat_id)
                chat_summaries.append(summary)
            except Exception as e:
                print(f"Error loading chat {chat_id}: {e}")

        return render_template("home.html", chats=chat_summaries)
    except Exception as e:
        print(f"Error loading chats: {e}")
        return render_template("home.html", chats=[])


@app.route('/chat/new', methods=['GET', 'POST'])
@login_required
def new_chat():
    data = request.get_json()
    model = data.get("model")
    if not model:
        return jsonify({
            "error": "Model not specified"
        }), 400
    try:
        if not lms.load_model(model):
            return jsonify({
                "error": "Could not load model"
            }), 500
        chat_id = ufm.new_chat(model)
        return jsonify({
            "chat_id": chat_id,
            "success": True
        })
    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500

@app.route("/api/models")
@login_required
def api_models():
    models = lms.get_models()

    return jsonify({
        "models": models
    })

@app.route('/chat/<int:chat_id>', methods=['GET'])
@login_required
def chat(chat_id):
    """Load and display a chat"""
    if current_user.banned == "1":
        return redirect(url_for("login"))

    try:
        chat_data = ufm.load_chat(chat_id)
        summary = ufm.get_chat_summary(chat_id)
        return render_template(
            "chat.html",
            chat_id=chat_id,
            messages=chat_data['messages'],
            model=chat_data.get('model'),
            summary=summary
        )
    except FileNotFoundError:
        return render_template("404.html"), 404
    except Exception as e:
        print(f"Error loading chat {chat_id}: {e}")
        return render_template("error.html", error=str(e)), 500


@app.route('/chat/<int:chat_id>/send', methods=['POST'])
@login_required
def send_message(chat_id):
    """Send a message in a chat and get AI response"""
    if current_user.banned == "1":
        return redirect(url_for("login"))

    data = request.get_json()
    message = data.get('message')

    if not message:
        return jsonify({"error": "Message is empty"}), 400

    try:
        # Load chat
        chat_data = ufm.load_chat(chat_id)
        model = chat_data.get('model')
        messages = chat_data.get('messages', [])

        # Save user message
        ufm.save_chat(chat_id, message, role="user")

        # Get AI response
        answer = lms.ask_ai(messages + [{"role": "user", "content": message}], model)

        if answer:
            # Save AI response
            ufm.save_chat(chat_id, answer, role="assistant")
            return jsonify({
                "success": True,
                "response": answer,
                "user_message": message
            })
        else:
            return jsonify({
                "success": False,
                "error": "Could not get response from AI"
            }), 500

    except FileNotFoundError:
        return jsonify({"error": "Chat not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/chat/<int:chat_id>/delete', methods=['POST'])
@login_required
def delete_chat(chat_id):
    """Delete a chat"""
    if current_user.banned == "1":
        return redirect(url_for("login"))

    try:
        ufm.delete_chat(chat_id)
        return jsonify({"success": True, "message": "Chat deleted"})
    except FileNotFoundError:
        return jsonify({"error": "Chat not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/chats', methods=['GET'])
@login_required
def chats():
    """Get list of all chats (JSON API)"""
    if current_user.banned == "1":
        return jsonify({"error": "User is banned"}), 403

    try:
        chats = ufm.get_chats()
        return jsonify({"chats": chats})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    if current_user.rights == "admin" and current_user.banned != 1:
        return render_template(
            "admin.html",
            now=datetime.now()
        )
    else:
        return redirect(url_for("index"))


@app.route('/admin/users')
@login_required
def admin_users():
    if current_user.rights != "admin":
        return jsonify({"error": "Unauthorized"}), 403

    users = sql_handler.alle_user()

    return jsonify({
        "users": users
    })

@app.route('/ban/<user_id>', methods=['POST'])
@login_required
def ban(user_id):
    if current_user.rights == "admin" and current_user.banned != "1":
        try:
            sql_handler.user_bannen(user_id)
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
        return redirect(url_for("index"))


@app.route('/unban/<user_id>', methods=['POST'])
@login_required
def unban(user_id):
    if current_user.rights == "admin" and current_user.banned != "1":
        try:
            sql_handler.user_entbannen(user_id)
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
        return redirect(url_for("index"))


@app.route('/set-rights/<user_id>', methods=['POST'])
@login_required
def set_rights(user_id):
    if current_user.rights == "admin" and current_user.banned != "1":
        data = request.get_json()
        new_rights = data.get('rights')
        try:
            sql_handler.user_bearbeiten(user_id, {"rights": new_rights})
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return redirect(url_for("index"))


@app.route('/logout', methods=['POST', 'GET'])
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


@app.errorhandler(403)
def forbidden(error):
    return render_template('403.html'), 403


@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404


@app.errorhandler(500)
def server_error(error):
    return render_template('500.html'), 500


if __name__ == "__main__":
    app.run(debug=True)