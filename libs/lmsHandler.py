import requests
import json

class LMSHandler:
    def __init__(self, LMSAddr, LMSPort):
        self.LMSAddr = LMSAddr
        self.LMSPort = LMSPort
        self.session = requests.Session()
        self.BASE_URL = "http://{self.LMSAddr}:{self.LMSPort}/v1/"

    def getModels(self):
        response = requests.get(f"{self.BASE_URL}models")

        response.raise_for_status()

        data = response.json()

        model_list = [model["id"] for model in data["data"]]

        return model_list

    def ask_ai(self, chat_file: str, model: str):
        try:
            with open(chat_file, "r", encoding="utf-8") as f:
                messages = json.load(f)

            payload = {

                "model": model,

                "messages": messages,

                "temperature": 0.7,

                "stream": False,

            }

            response = requests.post(

                f"{self.BASE_URL}chat/completions",

                json=payload,

                timeout=120,

            )

            response.raise_for_status()

            answer = response.json()["choices"][0]["message"]["content"]

            return answer
        except:
            return "Error Try Again!"

    def ask_ai_nochat(self, messages: str, model: str):
        try:

            payload = {

                "model": model,

                "messages": messages,

                "temperature": 0.7,

                "stream": False,

            }

            response = requests.post(

                f"{self.BASE_URL}chat/completions",

                json=payload,

                timeout=120,

            )

            response.raise_for_status()

            answer = response.json()["choices"][0]["message"]["content"]

            return answer
        except:
            return "Error Try Again!"