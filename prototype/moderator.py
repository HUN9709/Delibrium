from openai import OpenAI

from dataclasses import dataclass


class Moderator:
    def __init__(self):
        self.client = OpenAI()
        self.model = "gpt-5.1-chat-latest"

    def moderate(self,
                 max_rounds: int = 3):
        
        for round_num in range(max_rounds):
            pass
