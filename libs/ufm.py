import json
import os

def get_next_file_number(folder):

    os.makedirs(folder, exist_ok=True)

    numbers = []

    for filename in os.listdir(folder):

        if filename.endswith(".json"):

            name = filename[:-5]

            if name.isdigit():

                numbers.append(int(name))

    if numbers:

        return max(numbers) + 1

    return 1

def create_json_file(folder, data):

    number = get_next_file_number(folder)

    filepath = os.path.join(folder, f"{number}.json")

    with open(filepath, "w", encoding="utf-8") as file:

        json.dump(

            data,

            file,

            indent=4,

            ensure_ascii=False

        )

    return filepath

# UFM User File Management
class UFM:
    def __init__(self):
        pass

    def setup(self, user_id):
        os.chdir("/home/Felix/developing/python/schule/projektwoche/KAI/data/user")
        os.mkdir(user_id)
        os.chdir(user_id)

    def new_chat(self, user_id, model):
        os.chdir("/home/Felix/developing/python/schule/projektwoche/KAI/data/user")
        os.mkdir(user_id)
        os.chdir(user_id)
        new_file = create_json_file(
        """
            {
              "role": "system",
              "content": "Du bist ein hilfreicher Assistent."
            },
            {
              "role": "user",
              "content": "Hallo, wie geht es dir?"
            }
        """
        )

    def load_chat(self, user_id, chat_id):
        with open(f"{user_id}/{chat_id}.json", "r", encoding="utf-8") as file:
            data = json.load(file)

        return data

    def save_chat(self, user_id, chat_id, last_message, role):
        filename = f"{chat_id}.json"

        # Nachricht, die hinzugefügt werden soll

        new_message = {

            "role": role,

            "content": last_message

        }

        # JSON-Datei laden

        with open(filename, "r", encoding="utf-8") as file:
            chat = json.load(file)

        # Nachricht an den Chat anhängen

        chat["messages"].append(new_message)

        # JSON-Datei wieder speichern

        with open(filename, "w", encoding="utf-8") as file:
            json.dump(

                chat,

                file,

                indent=4,

                ensure_ascii=False

            )



    def get_chats(self, user_id):
        return os.listdir().replace(".json", "")

    def remove_chats(self, user_id, chat_id):
        os.remove(f"{user_id}/{chat_id}.json")
        file = open(f"{user_id}/{chat_id}.json", "r", encoding="utf-8")
        file.close()
