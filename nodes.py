import json, logging, os
from typing import Annotated, Literal
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.types import Command, interrupt
from langchain_openai import ChatOpenAI
from state import State
from prompts import *
from tools import *

# API_KEY设置命令 $env:API_KEY=""
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.0,
    base_url=os.getenv("BASE_URL", "https://api.getgoapi.com/v1"),
    api_key=os.getenv("API_KEY"),
)

# 预绑定工具，避免在循环里重复 bind
llm_execute_tools = llm.bind_tools([create_file, str_replace, shell_exec])
llm_report_tools = llm.bind_tools([create_file, shell_exec])

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
hander = logging.StreamHandler()
hander.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
hander.setFormatter(formatter)
logger.addHandler(hander)


def extract_json(text):
    if '```json' not in text:
        return text
    text = text.split('```json')[1].split('```')[0].strip()
    return text


def extract_answer(text):
    if '</think>' in text:
        answer = text.split("</think>")[-1]
        return answer.strip()
    return text


def _get_tool_calls(ai_msg):
    """兼容不同 langchain 版本的 tool_calls 字段位置。"""
    tool_calls = getattr(ai_msg, "tool_calls", None)
    if tool_calls:
        return tool_calls
    try:
        return ai_msg.additional_kwargs.get("tool_calls", [])
    except Exception:
        return []


def create_planner_node(state: State):
    logger.info("***正在运行Create Planner node***")
    messages = [
        SystemMessage(content=PLAN_SYSTEM_PROMPT),
        HumanMessage(content=PLAN_CREATE_PROMPT.format(user_message=state['user_message']))
    ]
    response = llm.invoke(messages)
    response = response.model_dump_json(indent=4, exclude_none=True)
    response = json.loads(response)
    plan = json.loads(extract_json(extract_answer(response['content'])))
    state['messages'] += [AIMessage(content=json.dumps(plan, ensure_ascii=False))]
    return Command(goto="execute", update={"plan": plan})


def update_planner_node(state: State):
    logger.info("***正在运行Update Planner node***")
    plan = state['plan']
    goal = plan['goal']
    state['messages'].extend([
        SystemMessage(content=PLAN_SYSTEM_PROMPT),
        HumanMessage(content=UPDATE_PLAN_PROMPT.format(plan=plan, goal=goal))
    ])
    messages = state['messages']
    while True:
        try:
            response = llm.invoke(messages)
            response = response.model_dump_json(indent=4, exclude_none=True)
            response = json.loads(response)
            plan = json.loads(extract_json(extract_answer(response['content'])))
            state['messages'] += [AIMessage(content=json.dumps(plan, ensure_ascii=False))]
            return Command(goto="execute", update={"plan": plan})
        except Exception as e:
            messages += [HumanMessage(content=f"json格式错误:{e}")]


def execute_node(state: State):
    logger.info("***正在运行execute_node***")

    plan = state['plan']
    steps = plan['steps']
    current_step = None
    current_step_index = 0

    # 获取第一个未完成STEP
    for i, step in enumerate(steps):
        status = step['status']
        if status == 'pending':
            current_step = step
            current_step_index = i
            break

    logger.info(f"当前执行STEP:{current_step}")

    # 这里只是简单跳转到report节点，实际应该根据当前STEP的描述进行判断
    if current_step is None or current_step_index == len(steps) - 1:
        return Command(goto='report')

    messages = state['observations'] + [
        SystemMessage(content=EXECUTE_SYSTEM_PROMPT),
        HumanMessage(content=EXECUTION_PROMPT.format(
            user_message=state['user_message'],
            step=current_step['description']
        ))
    ]

    tools = {"create_file": create_file, "str_replace": str_replace, "shell_exec": shell_exec}

    # tool calling循环
    while True:
        ai_msg = llm_execute_tools.invoke(messages)
        messages.append(ai_msg)  # 关键：把带 tool_calls 的 assistant 消息原样加入上下文

        tool_calls = _get_tool_calls(ai_msg)

        if tool_calls:
            for tc in tool_calls:
                tool_name = tc["name"]
                tool_args = tc.get("args", {})
                tool_result = tools[tool_name].invoke(tool_args)
                logger.info(f"tool_name:{tool_name},tool_args:{tool_args}\ntool_result:{tool_result}")

                messages.append(
                    ToolMessage(
                        content=json.dumps(tool_result, ensure_ascii=False),
                        tool_call_id=tc["id"],
                    )
                )
            continue

        # 模型不用原生tool_calls，而是在文本里输出 <tool_call> ... </tool_call>
        content = getattr(ai_msg, "content", "") or ""
        if '<tool_call>' in content:
            tool_call = content.split('<tool_call>')[-1].split('</tool_call>')[0].strip()
            tool_call = json.loads(tool_call)
            tool_name = tool_call['name']
            tool_args = tool_call.get('args', {})
            tool_result = tools[tool_name].invoke(tool_args)
            logger.info(f"tool_name:{tool_name},tool_args:{tool_args}\ntool_result:{tool_result}")
            messages.append(HumanMessage(content=f"tool_result:{tool_result}"))
            continue

        break

    final_text = extract_answer(ai_msg.content)
    logger.info(f"当前STEP执行总结:{final_text}")
    state['messages'] += [AIMessage(content=final_text)]
    state['observations'] += [AIMessage(content=final_text)]
    return Command(goto='update_planner', update={'plan': plan})


def report_node(state: State):
    """Report node that write a final report."""
    logger.info("***正在运行report_node***")

    observations = state.get("observations")
    messages = observations + [SystemMessage(content=REPORT_SYSTEM_PROMPT)]

    tools = {"create_file": create_file, "shell_exec": shell_exec}

    while True:
        ai_msg = llm_report_tools.invoke(messages)
        messages.append(ai_msg)

        tool_calls = _get_tool_calls(ai_msg)
        if tool_calls:
            for tc in tool_calls:
                tool_name = tc["name"]
                tool_args = tc.get("args", {})
                tool_result = tools[tool_name].invoke(tool_args)
                logger.info(f"tool_name:{tool_name},tool_args:{tool_args}\ntool_result:{tool_result}")
                messages.append(
                    ToolMessage(
                        content=json.dumps(tool_result, ensure_ascii=False),
                        tool_call_id=tc["id"],
                    )
                )
            continue

        content = getattr(ai_msg, "content", "") or ""
        if '<tool_call>' in content:
            tool_call = content.split('<tool_call>')[-1].split('</tool_call>')[0].strip()
            tool_call = json.loads(tool_call)
            tool_name = tool_call['name']
            tool_args = tool_call.get('args', {})
            tool_result = tools[tool_name].invoke(tool_args)
            logger.info(f"tool_name:{tool_name},tool_args:{tool_args}\ntool_result:{tool_result}")
            messages.append(HumanMessage(content=f"tool_result:{tool_result}"))
            continue

        break

    return {"final_report": ai_msg.content}