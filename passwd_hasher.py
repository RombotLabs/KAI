from argon2 import PasswordHasher


ph = PasswordHasher()

password = "DEIN_PASSWORT"

hashed_password = ph.hash(password)

print(hashed_password)