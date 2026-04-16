"""Agent state definition."""
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage
import operator


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    chat_id: str
    inventory_snapshot: str
    preferences_summary: str
    shopping_list_summary: str
    working_memory: dict
