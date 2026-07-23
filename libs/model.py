from flask_login import UserMixin


class User(UserMixin):
    def __init__(self, daten):
        self.id = daten["id"]
        self.username = daten["username"]
        self.openid_user = daten["openid_user"]
        self.password_hash = daten["password_hash"]
        self.creation_date = daten["creation_date"]
        self.rights = daten["rights"]
        self.chat_folder_destination = daten["chat_folder_destination"]
        self.banned = daten["banned"]