from typing import List, Literal

from langgraph.graph import MessagesState
from pydantic import BaseModel, Field


class Step(BaseModel):
    title: str = ""
    description: str = ""
    status: Literal["pending", "completed"] = "pending"


class Plan(BaseModel):
    goal: str = ""
    thought: str = ""
    steps: List[Step] = Field(default_factory=list)


class State(MessagesState):
    """Graph state.

    - MessagesState 已包含 messages: list[BaseMessage]
    - 其余字段用于规划、执行与最终报告
    """

    user_message: str = ""
    plan: Plan = Field(default_factory=Plan)
    observations: List = Field(default_factory=list)
    final_report: str = ""