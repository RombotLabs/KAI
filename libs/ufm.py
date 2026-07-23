import json
import os
from pathlib import Path


class UFM:
    """User File Management - Handle chat creation, loading, saving, and deletion"""

    BASE_DATA_PATH = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data",
        "user"
    )

    def __init__(self):
        self.current_user_path = None

    def setup(self, user_id):
        print("BASE_DATA_PATH:", self.BASE_DATA_PATH)
        self.current_user_path = os.path.join(
            self.BASE_DATA_PATH,
            str(user_id)
        )
        print("USER PATH:", self.current_user_path)
        os.makedirs(self.current_user_path, exist_ok=True)

    def _get_next_chat_number(self):
        """Get the next available chat number"""
        if not self.current_user_path:
            raise RuntimeError("UFM not initialized. Call setup() first.")

        numbers = []
        if os.path.exists(self.current_user_path):
            for filename in os.listdir(self.current_user_path):
                if filename.endswith(".json"):
                    name = filename[:-5]
                    if name.isdigit():
                        numbers.append(int(name))
        return max(numbers) + 1 if numbers else 1

    def new_chat(self, model: str) -> int:
        """Create a new chat and return chat_id"""
        if not self.current_user_path:
            raise RuntimeError("UFM not initialized. Call setup() first.")

        chat_id = self._get_next_chat_number()
        filepath = os.path.join(self.current_user_path, f"{chat_id}.json")

        chat_data = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "Du bist ein hilfreicher Assistent."
                }
            ]
        }

        with open(filepath, "w", encoding="utf-8") as file:
            json.dump(chat_data, file, indent=4, ensure_ascii=False)

        return chat_id

    def load_chat(self, chat_id):
        """Load chat messages from JSON file"""
        if not self.current_user_path:
            raise RuntimeError("UFM not initialized. Call setup() first.")

        filepath = os.path.join(self.current_user_path, f"{chat_id}.json")

        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Chat {chat_id} not found")

        with open(filepath, "r", encoding="utf-8") as file:
            data = json.load(file)

        return data

    def save_chat(self, chat_id: int, message: str, role: str = "user"):
        """Add a message to the chat and save it"""
        if not self.current_user_path:
            raise RuntimeError("UFM not initialized. Call setup() first.")

        filepath = os.path.join(self.current_user_path, f"{chat_id}.json")

        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Chat {chat_id} not found")

        # Load existing chat
        with open(filepath, "r", encoding="utf-8") as file:
            chat = json.load(file)

        # Add new message
        new_message = {
            "role": role,
            "content": message
        }
        chat["messages"].append(new_message)

        # Save updated chat
        with open(filepath, "w", encoding="utf-8") as file:
            json.dump(chat, file, indent=4, ensure_ascii=False)

    def get_chats(self) -> list:
        """Get list of all chat IDs for current user"""
        if not self.current_user_path:
            raise RuntimeError("UFM not initialized. Call setup() first.")

        if not os.path.exists(self.current_user_path):
            return []

        chats = []
        for filename in os.listdir(self.current_user_path):
            if filename.endswith(".json"):
                chat_id = filename[:-5]
                if chat_id.isdigit():
                    chats.append(int(chat_id))

        return sorted(chats)

    def delete_chat(self, chat_id):
        """Delete a chat file"""
        if not self.current_user_path:
            raise RuntimeError("UFM not initialized. Call setup() first.")

        filepath = os.path.join(self.current_user_path, f"{chat_id}.json")

        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Chat {chat_id} not found")

        os.remove(filepath)

    def get_chat_summary(self, chat_id: int) -> dict:
        """Get metadata about a chat (model, message count, etc.)"""
        if not self.current_user_path:
            raise RuntimeError("UFM not initialized. Call setup() first.")

        chat = self.load_chat(chat_id)
        return {
            "chat_id": chat_id,
            "model": chat.get("model", "unknown"),
            "message_count": len(chat.get("messages", [])),
            "has_system": any(msg.get("role") == "system" for msg in chat.get("messages", []))
        }