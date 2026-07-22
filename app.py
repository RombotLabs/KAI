from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import os
from libs.ufm import *
from libs.lmsHandler import *

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    password = request.form['password']

@app.route('/chats', methods=['POST'])
def chats():
    pass

@app.route('/chat/<chat_id>', methods=['POST'])
def chat(chat_id):
    pass

@app.route('/chat/send/<chat_id>', methods=['GET'])
def send_message(chat_id):
    pass

def admin():
    pass
@app.route('/admin', methods=['GET'])
def admin():
    pass

@app.route('/ban/<user_id>', methods=['GET'])
def ban(user_id):
    pass

@app.route('/unban/<user_id>', methods=['GET'])
def unban(user_id):
    pass

@app.route('/set-rights/<user_id>', methods=['POST'])
def set_rights(user_id):
    pass

@app.route('/spectate/<user_id>', methods=['POST'])
def spectate(user_id):
    pass

if __name__ == "__main__":
    app.run(debug=True)
