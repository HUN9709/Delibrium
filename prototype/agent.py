from abc import ABC, abstractmethod

class BaseAgent(ABC):
    """
    Interface for all Agents
    """

    def __init__(self, agent_id: str):

        self.agent_id = agent_id

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        
        raise NotImplementedError
