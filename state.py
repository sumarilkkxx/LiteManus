#增加任务状态结构与步骤状态跟踪
from langgraph.graph import MessagesState
from typing import Optional, List, Dict, Literal

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

class Step(BaseModel):
    #单个步骤的状态跟踪
    title: str = ""
    description: str = ""
    status: Literal["pending", "completed"] = "pending"

class Plan(BaseModel):
    #整体计划：目标、思路、步骤列表
    goal: str = ""
    thought: str = ""
    steps: List[Step] = []

class State(MessagesState):
    #继承MessageState
    user_message: str = ""
    plan: Plan
    observations: List = []
    final_report: str =  ""

    
    

