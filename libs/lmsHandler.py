import requests
import json
from typing import List, Dict, Optional


class LMSHandler:
    """Handle communication with LM Studio or compatible LLM endpoints"""

    def __init__(self, lms_addr: str, lms_port: str):
        self.lms_addr = lms_addr
        self.lms_port = lms_port
        self.session = requests.Session()
        self.base_url = f"http://{self.lms_addr}:{self.lms_port}/v1"
        self.api_url = f"http://{self.lms_addr}:{self.lms_port}/api/v1"
        self.current_model = None

    def get_models(self) -> List[str]:
        """Fetch available chat models from LMS"""
        try:
            response = self.session.get(
                f"{self.base_url}/models",
                timeout=10
            )

            response.raise_for_status()
            data = response.json()

            models = []

            for model in data.get("data", []):
                model_id = model["id"]

                # Embedding-Modelle entfernen
                if "embed" not in model_id.lower():
                    models.append(model_id)

            return models

        except requests.RequestException as e:
            print(f"Error fetching models: {e}")
            return []

    def ask_ai(self, messages: List[Dict], model: str, temperature: float = 0.7) -> Optional[str]:
        """Send messages to AI and get response (for chat)"""
        try:
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "stream": False,
            }

            response = self.session.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                timeout=120,
            )
            response.raise_for_status()

            answer = response.json()["choices"][0]["message"]["content"]
            return answer
        except requests.RequestException as e:
            print(f"Error asking AI: {e}")
            return None
        except (KeyError, IndexError) as e:
            print(f"Error parsing response: {e}")
            return None

    def ask_ai_nochat(self, messages: List[Dict], model: str, temperature: float = 0.7) -> Optional[str]:
        """Send messages to AI (without chat history assumption)"""
        return self.ask_ai(messages, model, temperature)

    def is_model_loaded(self, model: str) -> bool:
        """Check if a model is already loaded in LM Studio"""
        try:
            response = self.session.get(
                f"http://{self.lms_addr}:{self.lms_port}/api/v1/models",
                timeout=10
            )

            data = response.json()

            for item in data.get("data", []):
                if item.get("id") == model:
                    return True

            return False

        except Exception as e:
            print(f"Error checking loaded model: {e}")
            return False

    def load_model(self, model: str) -> bool:
        """Load model in LM Studio"""
        try:
            response = self.session.post(
                f"http://{self.lms_addr}:{self.lms_port}/api/v1/models/load",
                json={
                    "model": model
                },
                timeout=120
            )

            print("MODEL LOAD STATUS:", response.status_code)
            print("MODEL LOAD RESPONSE:", response.text)

            return response.status_code == 200

        except requests.RequestException as e:
            print(f"Error loading model: {e}")
            return False

    def ensure_model_loaded(self, model: str) -> bool:
        """Load model only if needed"""

        if self.is_model_loaded(model):
            print(f"Model already loaded: {model}")
            return True

        print(f"Loading model: {model}")
        return self.load_model(model)