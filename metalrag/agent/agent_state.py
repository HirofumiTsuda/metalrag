from enum import Enum, auto

class AgentState(Enum):
    """States where an agent resides"""
    BEGIN = auto()
    BAND = auto()
    ALBUM = auto()
    DONE = auto()
    DECISION = auto()
    EXTRACT = auto()
    INVALID = auto()
    
    @classmethod
    def get_map(cls) -> dict:
        return {
            cls.BEGIN: "BEGIN",
            cls.BAND: "BAND",
            cls.ALBUM: "ALBUM",
            cls.DONE: "DONE",
            cls.DECISION: "DECISION",
            cls.EXTRACT: "EXTRACT",
            cls.INVALID: "INVALID"
        }
    
    @classmethod
    def enumToStr(cls, state: "AgentState") -> str:
        return cls.get_map()[state]
    
    @classmethod
    def strToEnum(cls, state: str) -> "AgentState":
        return {
            v: k for k, v in cls.get_map().items()
        }[state]
        