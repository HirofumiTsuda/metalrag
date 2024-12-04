from pydantic import BaseModel, ConfigDict
from metalrag.llm.llm_base import LLMBase
from metalrag.agent.agent_state import AgentState
from copy import deepcopy
import json
import metallum
from metalrag.agent.utils import (
    band2dict,
    album2dict,
)
import yaml

class AgentMessage(BaseModel):
    message: str
    metadata: list[dict[str, str]]
    

class Agent(BaseModel):
    """A agent class to handle LLMs."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    llm: LLMBase
    messages: list[dict[str, str]]
    process_messages: list[dict[str, str]]
    state: AgentState
    limit: int
    count: int
    
    def __init__(self, llm: LLMBase, limit = 2) -> None:
        initial_messages = [
            {
                "role": "system",
                "content": """
                    You are familiar with heavy metal music. 
                    You can use additional information fetched from metallum (heavy metal archives)
                    and that information is explicitly ingested.
                    """
            },
        ]
        super().__init__(
            llm=llm, messages=initial_messages, process_messages=[],
            state=AgentState.BEGIN, limit=limit, count=0
        )
        
    def add_to_user_messages(self, message: str) -> None:
        self.messages.append(
            {
                "role": "user",
                "content": message,
            }
        )
        
    def add_to_process_messages(self, message: str) -> None:
        self.process_messages.append(
            {
                "role": "user",
                "content": message,
            }
        )
        
    def add_to_assistant_messages(self, message: str) -> None:
        self.messages.append(
            {
                "role": "assistant",
                "content": message,
            }
        )
        
    def get_integrated_messages(self) -> list[dict[str, str]]:
        messages = deepcopy(self.messages)
        messages.extend(self.process_messages)
        return messages
        
    def chat(self, message: str) -> str:
        self.add_to_user_messages(message=message)
        agent_message = AgentMessage(
            message=message,
            metadata=[{}]
        )
        while self.state != AgentState.DONE:
            agent_message, state = self.move(agent_message)
            self.state = state
        self.count = 0
        response = agent_message.metadata[0].get("response", "")
        self.add_to_assistant_messages(response)
        self.process_messages = []
        self.state = AgentState.BEGIN
        return response
    
    def move(self, agent_message: AgentMessage) -> tuple[AgentMessage, AgentState]:
        if self.state == AgentState.BEGIN:
            return self.check_validness(agent_message) 
        elif self.state == AgentState.DECISION:
            self.count += 1
            return self.check_enough(agent_message)
        elif self.state == AgentState.EXTRACT:
            return self.extract_keywords(agent_message)
        elif self.state == AgentState.BAND:
            return self.search_band(agent_message)
        elif self.state == AgentState.ALBUM:
            return self.search_album(agent_message)
        elif self.state == AgentState.INVALID:
            return self.create_invalid_response(agent_message)
        raise ValueError(
            f"state error: no corresponding status: {self.state}"
        )
        
    def search_album(self, agent_message: AgentMessage) -> tuple[AgentMessage, AgentState]:
        albums = [ data["album"] for data in agent_message.metadata ]
        bands = [ data.get("band") for data in agent_message.metadata ]
        album_searches = [
            metallum.album_search(title=album, band=band) for album, band in zip(albums, bands)
        ]
        album_data = []
        for search_results in album_searches:
            for data in search_results:
                album_data.append(album2dict(data.get()))
        prompt = f"""
        Please answer to the following question.
        
        {agent_message.message}
        
        The following information can be used.
        
        {yaml.dump(album_data)}
        """
        self.add_to_process_messages(prompt)
        messages = self.get_integrated_messages()
        response, _ = self.llm.chat(
            messages=messages, 
        )
        return AgentMessage(
            message=agent_message.message,
            metadata=[{
                "response": response
            }]
        ), AgentState.DECISION  
    
    def search_band(self, agent_message: AgentMessage) -> tuple[AgentMessage, AgentState]:
        keywords = [ data["band"] for data in agent_message.metadata ]
        band_searches = [
            metallum.band_search(k) for k in keywords
        ]
        band_data = []
        for search_results in band_searches:
            for data in search_results:
                band_data.append(band2dict(data.get()))
        prompt = f"""
        Please answer to the following question.
        
        "{agent_message.message}"
        
        The following information can be used.
        
        {yaml.dump(band_data)}
        """
        print(prompt)
        self.add_to_process_messages(prompt)
        messages = self.get_integrated_messages()
        response, _ = self.llm.chat(
            messages=messages,
        )
        return AgentMessage(
            message=agent_message.message,
            metadata=[{
                "response": response
            }]
        ), AgentState.DECISION
        
    
    def check_validness(self, agent_message: AgentMessage) -> tuple[AgentMessage, AgentState]:
        prompt = f"""
        Please check if the following message is a question.
        Note that question may ask about bands.
        
        {agent_message.message}
        """
        self.add_to_process_messages(prompt)
        
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "check_and_move_next",
                    "description": "Checking if a given message is a valid question and return the next state",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "message": {
                                "type": "string",
                                "description": """
                                    The answer to the message. If the message is neither a question nor
                                    involved with heavy metal, a message referring that is returned.
                                      
                                    """,                                
                            },
                            "state": {
                                "type": "string",
                                "description": """
                                    The next state. If a given message is valid, EXTRACT is returned.
                                    If the message is not valid, INVALID is returned.    
                                    """,
                                "enum": [
                                    AgentState.enumToStr(AgentState.EXTRACT),
                                    AgentState.enumToStr(AgentState.INVALID),
                                ]                                
                            }
                        },
                        "required": ["message", "state"],
                    },
                },
            },
        ]
        
        messages = self.get_integrated_messages()
        _, function_data = self.llm.chat(
            messages=messages,
            tools=tools,
            tool_choice="required", 
        )
        state = AgentState.strToEnum(function_data[0]["arguments"]["state"])
        response = function_data[0]["arguments"]["message"]
        return AgentMessage(
            message=agent_message.message,
            metadata=[{"response": response}]
        ), state
    
    
    def extract_keywords(self, agent_message: AgentMessage)  -> tuple[AgentMessage, AgentState]:
        prompt = f"""
        Please extract some keywords from the following message.
        That keyword is either of the band name or album names with the band name.
        That fetched keyword is used to search information from metallum
        and using that a more sophisticated answer will be created.
        
        {agent_message.message}

        """
        self.add_to_process_messages(prompt)
        
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "check_and_move_next",
                    "description": "Checking if a given message is a valid question and return the next state",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "keywords": {
                                "type": "string",
                                "description": """
                                    Keywords for fetching data about ALBUM or BAND.
                                    For example, let us think of the following question.
                                    
                                    Please tell me about the bands called megadeth and anthrax.
                                    
                                    Then the question requires information about two bands, megadeth and anthrax. 
                                    Then an expected answer is: 
                                    [{"band": "megadeth"}, {"band": "anthrax"}]. 
                                    
                                    Please write the answer in a list of dictionaries with a key being "band" and
                                    a value being a band name.
                                    
                                    If a question is like "please tell me about the megadeth's albums called
                                    rust in peace and Dystopia", then an expected answer is:
                                    
                                    [{"album": "rust in peace"}, {"album": Dystopia}]
                                    
                                    or by giving the band name explicitly,
                                    
                                    [{"band": "megadeth", "album": "rust in peace"}, {"band": "megadeth", "album": Dystopia}]
                                    
                                    Please write the answer in in a list of dictionaries.
                                    The keys are "band" and "album" and values are corresponding name.
                                    Note that the key "album" and the corresponding value are not always necessary.
                                    If you don't get any band name, the key "band" is not necessary.
                                    """,                                
                            },
                            "state": {
                                "type": "string",
                                "description": """
                                    Either of ALBUM or BAND is returned and that variable
                                    (ALBUM or BAND) is used for what kind of information is fetched
                                    to make a more sophisticated answer. 
                                    """,
                                "enum": [
                                    AgentState.enumToStr(AgentState.ALBUM),
                                    AgentState.enumToStr(AgentState.BAND),
                                ]                                
                            }
                        },
                        "required": ["keywords", "state"],
                    },
                },
            },
        ]
        
        messages = self.get_integrated_messages()
        
        _, function_data = self.llm.chat(
            messages=messages,
            tools=tools,
            tool_choice="required", 
        )
        metadata = json.loads(function_data[0]["arguments"]["keywords"])
        state = AgentState.strToEnum(function_data[0]["arguments"]["state"])        
        return AgentMessage(message=agent_message.message, metadata=metadata), state      
            
    
    def check_enough(self, agent_message: AgentMessage) -> tuple[AgentMessage, AgentState]:
        if self.count >= self.limit:
            return agent_message, AgentState.DONE
        prompt = f"""
        Please check if the following response is enough to the given question.
        
        question: "{agent_message.message}"
        
        response: "{agent_message.metadata[0]["response"]}"
        
        If more information is required to answer to the question. Please say so.
        """
        self.add_to_process_messages(prompt)
        
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "check_and_move_next",
                    "description": "Checking if a given response is a valid response and return the next state",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "state": {
                                "type": "string",
                                "description": """
                                    The next state. If the response is an answer to the question,
                                    DONE is returned.  Otherwise, EXTRACT is returned. Note that
                                    if you think any more information could not be fetched from metallum
                                    website, DONE is returned.
                                    """,
                                "enum": [
                                    AgentState.enumToStr(AgentState.DONE),
                                    AgentState.enumToStr(AgentState.EXTRACT),
                                ]                                
                            }
                        },
                        "required": ["state"],
                    },
                },
            },
        ]
        
        messages = self.get_integrated_messages()
        _, function_data = self.llm.chat(
            messages=messages,
            tools=tools,
            tool_choice="required", 
        )
        state = AgentState.strToEnum(function_data[0]["arguments"]["state"])        
        return agent_message, state      
    
    def create_invalid_response(self, agent_message: AgentMessage) -> tuple[AgentMessage, AgentState]:
        prompt = f"""
        The following question is invalid as a question about heavy metal music.
        
        question: "{agent_message.message}"
        
        Please tell me about that.
        """
        self.add_to_process_messages(prompt)
        
        messages = self.get_integrated_messages()
        response, _ = self.llm.chat(
            messages=messages,
        )
        return AgentMessage(
            message=agent_message.message,
            metadata=[{
                "response": response
            }]
        ), AgentState.DONE
    