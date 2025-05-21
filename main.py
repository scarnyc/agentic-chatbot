"""
Python-based agentic workflow powered by Anthropic 3.7 Sonnet & LangGraph.
This agent is capable of using Tavily web search, and executing code;
It also has access to Wikipedia info while incorporating memory.
"""

import os
from typing import Annotated
from dotenv import load_dotenv
from typing_extensions import TypedDict
from langchain_anthropic import ChatAnthropic
from langgraph.graph import MessagesState, START, END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder

from tools.prompt import get_prompt
from tools.wiki_tools import create_wikipedia_tool
from tools.search_tools import create_tavily_search_tool
from tools.code_tools import get_code_tools

load_dotenv()

anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
if not anthropic_api_key:
    print("ANTHROPIC_API_KEY environment variable not set.")
    print(
        "Please set the ANTHROPIC_API_KEY environment variable in your .env file"
    )

tavily_api_key = os.getenv("TAVILY_API_KEY")
if not tavily_api_key:
    print("TAVILY_API_KEY environment variable not set.")
    print(
        "Please set the TAVILY_API_KEY environment variable in your .env file"
    )

if anthropic_api_key:
    try:
        llm = ChatAnthropic(
            model_name="claude-3-7-sonnet-latest",
            anthropic_api_key=anthropic_api_key,
            max_tokens=1500,
            thinking={
                "type": "enabled",
                "budget_tokens": 1024
            })
        print("Successfully initialized Claude model")
    except Exception as e:
        print(f"Failed to initialize Claude model: {e}")
        raise RuntimeError(f"Failed to initialize Claude model: {e}")
else:
    raise ValueError("ANTHROPIC_API_KEY environment variable not set")

if tavily_api_key:
    tavily_search_tool = create_tavily_search_tool(tavily_api_key)

wikipedia_tool = create_wikipedia_tool()
code_tools = get_code_tools()

tools = [wikipedia_tool, tavily_search_tool] + code_tools
tool_node = ToolNode(tools)
model_with_tools = llm.bind_tools(tools)
prompt_template = ChatPromptTemplate.from_messages([
    ("system", get_prompt()),
    MessagesPlaceholder(variable_name="messages"),
    ])
model_chain = prompt_template | model_with_tools


def should_continue(state: MessagesState) -> str:
    """
    Determines whether the agent should continue processing or end.
    Args:
        state: The current state of the graph, containing messages.
    Returns:
        "tools" if the last message contains tool calls, END otherwise.
    """
    last_message = state["messages"][-1]
    if isinstance(last_message, AIMessage) and hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        if any(tc.get('name') in [t.name for t in tools] for tc in last_message.tool_calls):
             return "tools"

    if isinstance(last_message, AIMessage) and last_message.additional_kwargs.get("tool_calls"):
         pass

    return END


def call_model(state: MessagesState) -> dict:
    """
    The main agent node function. Invokes the LLM.
    Args:
        state: The current state of the graph.
    Returns:
        A dictionary containing the updated messages list.
    """
    messages = state["messages"]
    response = model_chain.invoke({"messages": messages})
    return {"messages": [response]}


workflow = StateGraph(MessagesState)
workflow.add_node("chatbot", call_model)
workflow.add_node("tools", tool_node)
workflow.set_entry_point("chatbot")
workflow.add_conditional_edges(
    "chatbot",
    should_continue,
    {
        "tools": "tools", 
        END: END
    }
)
workflow.add_edge("tools", "chatbot")
memory = MemorySaver()
store = InMemoryStore()
app = workflow.compile(checkpointer=memory, store=store)


def stream_memory_responses(user_input: str, thread_id: str):
    """
    Streams all events from the graph execution for a single input.
    Args:
        user_input: The user's input string.
        thread_id: The unique identifier for the conversation thread.
    """
    config = {"configurable": {"thread_id": thread_id}}
    print(f"\n--- Streaming Events (Thread: {thread_id}, Input: '{user_input}') ---")

    for event in app.stream({"messages": [("user", user_input)]}, config):

        for value in event.values():
            if "messages" in value and value["messages"]:
                print("Agent:", value["messages"])


if __name__ == "__main__":
    print("Starting Agentic LangGraph Script...")

    thread3_id = "thread-example-3-stream"
    # stream_memory_responses("What is the Colosseum?", thread3_id)
    stream_memory_responses("Write a python function that calculates the factorial of 100", thread3_id)
    # stream_memory_responses("What's the weather today in queens, nyc?", thread3_id)

    print("\nScript finished.")
