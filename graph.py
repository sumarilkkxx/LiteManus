from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySever
from state import State
from nodes import (report_node, execute_node, create_planner_node, update_planner_node)

def _build_base_graph():
    """构建基本的状态图，包含所有的节点和边"""
    builder = StateGraph(State)
    builder.add_edge(START, "create_planner")
    builder.add_node("create_planner", create_planner_node)
    builder.add_node("update_planner", update_planner_node)
    builder.add_node("execute", execute_node)
    builder.add_node("report", report_node)
    builder.add_edge("report", END)
    return builder

def build_graph_with_memory():
    """构建并返回带有memory的代理工作流程图"""
    memory = MemorySever()
    builder = _build_base_graph()
    return builder.compile(checkpointer=memory)

def build_graph():
    """构建并返回不带memory的代理工作流程图"""
    #构建状态图
    builder = _build_base_graph()
    return builder.compile()

graph = build_graph()

inputs = {"user_message": "对所给文档进行分析，生成分析报告", 
          "plan": None,
          "observations": [], 
          "final_report": ""}

graph.invoke(inputs, {"recursion_limit":100})
