import os
import sys
from contextlib import contextmanager
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Tipp: 'pip install python-dotenv' installieren, um .env zu nutzen.")

try:
    import mysql.connector
except ImportError:
    print("Fehlendes Paket! Bitte ausführen: pip install mysql-connector-python")
    sys.exit(1)


class SQL_Handler:
    def __init__(self):
        self.config = {
            "host":     os.getenv("DB_HOST", ""),
            "port":     int(os.getenv("DB_PORT", "3306")),
            "user":     os.getenv("DB_USER", ""),
            "password": os.getenv("DB_PASS", ""),
            "database": "KAI",
            "charset":  "utf8mb4",
            "use_pure": True,
        }
        ssl_ca = os.getenv("SSL_CA", "").strip()
        if ssl_ca:
            self.config["ssl_ca"]       = ssl_ca
            self.config["ssl_disabled"] = False

        self.TABELLE = "users"

    # ── Verbindungs-Kontextmanager ─────────────────────────────────────────────
    @contextmanager
    def _verbindung(self):
        cnx = mysql.connector.connect(**self.config)
        try:
            yield cnx
        finally:
            cnx.close()

    @contextmanager
    def _cursor(self, cnx, als_dict=False):
        cur = cnx.cursor(dictionary=als_dict)
        try:
            yield cur
        finally:
            cur.close()

    # ── Nächste ID manuell berechnen ───────────────────────────────────────────
    def _naechste_id(self, cnx, cur) -> int:
        cur.execute(f"SELECT COALESCE(MAX(id), 0) + 1 FROM `{self.TABELLE}`")
        return cur.fetchone()[0]

    # ── User: Alle anzeigen ────────────────────────────────────────────────────
    def alle_user(self):
        sql = f"""
        SELECT id, username, openid_user, creation_date,
               rights, chat_folder_destination, banned
        FROM `{self.TABELLE}`
        ORDER BY id
        """
        with self._verbindung() as cnx, self._cursor(cnx, als_dict=True) as cur:
            cur.execute(sql)
            return cur.fetchall()

    # ── User: Suchen ──────────────────────────────────────────────────────────
    def user_suchen(self, username: str):
        sql = f"""
        SELECT id, username, openid_user, creation_date,
               rights, chat_folder_destination, banned
        FROM `{self.TABELLE}`
        WHERE username = %s
        """
        with self._verbindung() as cnx, self._cursor(cnx, als_dict=True) as cur:
            cur.execute(sql, (username,))
            return cur.fetchone()

    def user_suchen_by_id(self, user_id: int):
        sql = f"""
        SELECT id, username, openid_user, creation_date,
               rights, chat_folder_destination, banned
        FROM `{self.TABELLE}`
        WHERE id = %s
        """
        with self._verbindung() as cnx, self._cursor(cnx, als_dict=True) as cur:
            cur.execute(sql, (user_id,))
            return cur.fetchone()

    # ── User: Hinzufügen ───────────────────────────────────────────────────────
    def user_hinzufuegen(self, username: str, password_hash: str,
                         rights: str, chat_folder_destination: str,
                         openid_user: str = None, banned: int = 0) -> int:
        sql = f"""
        INSERT INTO `{self.TABELLE}`
            (id, username, openid_user, password_hash, creation_date,
             rights, chat_folder_destination, banned)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        creation_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            with self._verbindung() as cnx, self._cursor(cnx) as cur:
                neue_id = self._naechste_id(cnx, cur)

                werte = (neue_id, username,
                         openid_user or None,
                         password_hash, creation_date,
                         rights, chat_folder_destination, banned)

                cur.execute(sql, werte)
                cnx.commit()
                return neue_id

        except mysql.connector.Error as e:
            print(f"Fehler beim Hinzufügen: {e}")
            return -1

    # ── User: Bearbeiten ───────────────────────────────────────────────────────
    def user_bearbeiten(self, user_id: int, daten: dict) -> int:
        erlaubte_spalten = {
            "username", "openid_user", "password_hash",
            "rights", "chat_folder_destination", "banned"
        }
        daten = {k: v for k, v in daten.items() if k in erlaubte_spalten}
        if not daten:
            print("Keine gültigen Spalten zum Bearbeiten.")
            return 0
        set_teil = ", ".join(f"`{k}` = %s" for k in daten.keys())
        sql      = f"UPDATE `{self.TABELLE}` SET {set_teil} WHERE id = %s"
        werte    = list(daten.values()) + [user_id]
        with self._verbindung() as cnx, self._cursor(cnx) as cur:
            cur.execute(sql, werte)
            cnx.commit()
            return cur.rowcount

    # ── User: Rechte bearbeiten ────────────────────────────────────────────────
    def rechte_bearbeiten(self, user_id: int, neue_rechte: str) -> int:
        """Ändert die Rechte eines Users anhand der ID."""
        return self.user_bearbeiten(user_id, {"rights": neue_rechte})

    # ── User: Löschen ──────────────────────────────────────────────────────────
    def user_loeschen(self, user_id: int) -> int:
        sql = f"DELETE FROM `{self.TABELLE}` WHERE id = %s"
        with self._verbindung() as cnx, self._cursor(cnx) as cur:
            cur.execute(sql, (user_id,))
            cnx.commit()
            return cur.rowcount

    # ── User: Bannen/Entbannen ─────────────────────────────────────────────────
    def user_bannen(self, user_id: int) -> int:
        return self.user_bearbeiten(user_id, {"banned": 1})

    def user_entbannen(self, user_id: int) -> int:
        return self.user_bearbeiten(user_id, {"banned": 0})

    # ── Ausgabe Hilfsfunktion ──────────────────────────────────────────────────
    def _user_ausgeben(self, user: dict):
        if not user:
            print("  ❌ User nicht gefunden.")
            return
        print(f"""
  ┌─────────────────────────────────────┐
  │ ID:           {user['id']}
  │ Username:     {user['username']}
  │ OpenID:       {user['openid_user'] or '–'}
  │ Erstellt:     {user['creation_date']}
  │ Rechte:       {user['rights']}
  │ Chat-Ordner:  {user['chat_folder_destination']}
  │ Gebannt:      {'🚫 Ja' if user['banned'] else '✅ Nein'}
  └─────────────────────────────────────┘""")

    # ── Interaktives Menü ──────────────────────────────────────────────────────
    def menu(self):
        print("\n" + "="*45)
        print("  👤 User Verwaltung – KAI.users")
        print("="*45)
        print("1) Alle User anzeigen")
        print("2) User suchen (nach Username)")
        print("3) User suchen (nach ID)")
        print("4) User hinzufügen")
        print("5) User bearbeiten")
        print("6) User löschen")
        print("7) User bannen")
        print("8) User entbannen")
        print("9) Rechte bearbeiten")  # ← NEU
        print("0) Beenden")
        print("="*45)
        return input("Auswahl: ").strip()

    def starten(self):
        print("\n👤 User Verwaltung gestartet.")
        print("Datenbank: KAI  |  Tabelle: users\n")

        while True:
            wahl = self.menu()

            if wahl == "1":
                try:
                    users = self.alle_user()
                    if users:
                        print(f"\n{len(users)} User gefunden:")
                        for u in users:
                            self._user_ausgeben(u)
                    else:
                        print("Keine User gefunden.")
                except Exception as e:
                    print(f"Fehler: {e}")

            elif wahl == "2":
                username = input("Username: ").strip()
                try:
                    self._user_ausgeben(self.user_suchen(username))
                except Exception as e:
                    print(f"Fehler: {e}")

            elif wahl == "3":
                try:
                    user_id = int(input("User-ID: ").strip())
                    self._user_ausgeben(self.user_suchen_by_id(user_id))
                except ValueError:
                    print("Bitte eine gültige Zahl eingeben.")
                except Exception as e:
                    print(f"Fehler: {e}")

            elif wahl == "4":
                print("\nNeuen User anlegen:")
                username                = input("  Username:                  ").strip()
                password_hash           = input("  Passwort-Hash:             ").strip()
                rights                  = input("  Rechte:                    ").strip()
                chat_folder_destination = input("  Chat-Ordner:               ").strip()
                openid_user             = input("  OpenID (leer = NULL):      ").strip() or None
                banned_input            = input("  Gebannt? (0/1):            ").strip()
                banned                  = int(banned_input) if banned_input in ("0", "1") else 0

                try:
                    new_id = self.user_hinzufuegen(
                        username, password_hash, rights,
                        chat_folder_destination, openid_user, banned
                    )
                    if new_id != -1:
                        print(f"✅ User angelegt! Neue ID: {new_id}")
                    else:
                        print("❌ User konnte nicht angelegt werden.")
                except Exception as e:
                    print(f"Fehler: {e}")

            elif wahl == "5":
                try:
                    user_id = int(input("User-ID zum Bearbeiten: ").strip())
                    user    = self.user_suchen_by_id(user_id)
                    if not user:
                        print("❌ User nicht gefunden.")
                        continue
                    self._user_ausgeben(user)
                    print("\nFelder ändern (leer lassen = überspringen):")
                    daten = {}
                    for feld in ["username", "openid_user", "password_hash",
                                 "rights", "chat_folder_destination", "banned"]:
                        wert = input(f"  {feld} [{user.get(feld, '')}]: ").strip()
                        if wert != "":
                            daten[feld] = wert
                    if daten:
                        n = self.user_bearbeiten(user_id, daten)
                        print(f"✅ {n} Feld(er) aktualisiert.")
                    else:
                        print("Keine Änderungen vorgenommen.")
                except ValueError:
                    print("Bitte eine gültige Zahl eingeben.")
                except Exception as e:
                    print(f"Fehler: {e}")

            elif wahl == "6":
                try:
                    user_id = int(input("User-ID zum Löschen: ").strip())
                    user    = self.user_suchen_by_id(user_id)
                    if not user:
                        print("❌ User nicht gefunden.")
                        continue
                    self._user_ausgeben(user)
                    bestaet = input("Wirklich löschen? (ja/nein): ").strip().lower()
                    if bestaet == "ja":
                        n = self.user_loeschen(user_id)
                        print(f"✅ {n} User gelöscht.")
                    else:
                        print("Abgebrochen.")
                except ValueError:
                    print("Bitte eine gültige Zahl eingeben.")
                except Exception as e:
                    print(f"Fehler: {e}")

            elif wahl == "7":
                try:
                    user_id = int(input("User-ID zum Bannen: ").strip())
                    n = self.user_bannen(user_id)
                    print(f"🚫 User {user_id} gebannt." if n else "❌ User nicht gefunden.")
                except ValueError:
                    print("Bitte eine gültige Zahl eingeben.")
                except Exception as e:
                    print(f"Fehler: {e}")

            elif wahl == "8":
                try:
                    user_id = int(input("User-ID zum Entbannen: ").strip())
                    n = self.user_entbannen(user_id)
                    print(f"✅ User {user_id} entbannt." if n else "❌ User nicht gefunden.")
                except ValueError:
                    print("Bitte eine gültige Zahl eingeben.")
                except Exception as e:
                    print(f"Fehler: {e}")

            # ── Rechte bearbeiten ──────────────────────────────────────────────
            elif wahl == "9":
                try:
                    user_id = int(input("User-ID: ").strip())
                    user    = self.user_suchen_by_id(user_id)
                    if not user:
                        print("❌ User nicht gefunden.")
                        continue
                    self._user_ausgeben(user)
                    neue_rechte = input(f"  Neue Rechte [{user['rights']}]: ").strip()
                    if neue_rechte:
                        n = self.rechte_bearbeiten(user_id, neue_rechte)
                        print(f"✅ Rechte auf '{neue_rechte}' gesetzt." if n else "❌ Fehler.")
                    else:
                        print("Keine Änderung vorgenommen.")
                except ValueError:
                    print("Bitte eine gültige Zahl eingeben.")
                except Exception as e:
                    print(f"Fehler: {e}")

            elif wahl == "0":
                print("Auf Wiedersehen!")
                break

            else:
                print("Ungültige Auswahl, bitte nochmal.")


# ── Programm starten ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    handler = SQL_Handler()
    handler.starten()
