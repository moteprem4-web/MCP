import streamlit as st
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

@st.cache_resource
def get_llm():
    return ChatGroq(
        groq_api_key=os.getenv("GROQ_API_KEY"),
        model_name="llama-3.1-8b-instant",  # ✅ fast & free
        temperature=0.5
    )

llm = get_llm()

st.title("🤖 Groq Chatbot (LLaMA3)")

user_input = st.text_input("Ask something:")

if st.button("Send"):
    if user_input:
        try:
            response = llm.invoke(user_input)
            st.success("✅ Response:")
            st.write(response.content)
        except Exception as e:
            st.error(f"❌ Error: {e}")



import asyncio
import os
import json
import re
from datetime import date
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, ToolMessage, AIMessage, SystemMessage
from langchain_mcp_adapters.client import MultiServerMCPClient

load_dotenv()

# ── LLM ─────────────────────────────────────────────
llm = ChatGroq(
    groq_api_key=os.getenv("GROQ_API_KEY"),
    model_name="llama-3.1-8b-instant",
    temperature=0
)

# ── MCP SERVERS ─────────────────────────────────────
SERVERS = {
    # "math": {
    #     "transport": "stdio",
    #     "command": "python",
    #     "args": [r"C:\Users\motep\Desktop\MATH_MCP_SERVER\main.py"]
    # },
    "expense": {
        "transport": "stdio",
        "command": "python",
        "args": [r"C:\Users\motep\Desktop\Expense_Tracker_mcp_server\main.py"]
    },
    # "manim": {
    #     "transport": "stdio",
    #     "command": "python",
    #     "args": [r"C:\Users\motep\Desktop\manim-mcp-server\src\manim_server.py"]
    # }
}

# ── HELPER ─────────────────────────────────────────
def extract_tool_result(raw_result):
    if isinstance(raw_result, (dict, list)):
        return json.dumps(raw_result, indent=2)
    return str(raw_result)

# ── 🔥 FORCE TOOL LOGIC ────────────────────────────
async def force_tool_if_needed(prompt, named_tools):
    prompt_lower = prompt.lower()

    # Extract amount
    amount_match = re.search(r"\d+", prompt)
    amount = float(amount_match.group()) if amount_match else None

    # Extract category
    categories = ["food", "travel", "shopping", "education"]
    category = next((c.capitalize() for c in categories if c in prompt_lower), "Food")

    today = str(date.today())

    # ───── ADD ─────
    if "add" in prompt_lower and "expense" in prompt_lower:
        print("⚡ Forcing add_expense")

        return await named_tools["add_expense"].ainvoke({
            "date": today,
            "amount": amount or 0,
            "category": category
        })

    # ───── UPDATE ─────
    if "update" in prompt_lower or "edit" in prompt_lower:
        print("⚡ Forcing edit_expense")

        id_match = re.search(r"id\s*(\d+)", prompt_lower)
        expense_id = int(id_match.group(1)) if id_match else 1

        return await named_tools["edit_expense"].ainvoke({
            "expense_id": expense_id,
            "amount": amount,
            "category": category
        })

    # ───── DELETE ─────
    if "delete" in prompt_lower or "remove" in prompt_lower:
        print("⚡ Forcing delete_expenses")

        id_match = re.search(r"id\s*(\d+)", prompt_lower)
        expense_id = int(id_match.group(1)) if id_match else None

        return await named_tools["delete_expenses"].ainvoke({
            "expense_id": expense_id,
            "category": category if not expense_id else None
        })

    return None

# ── AGENT ─────────────────────────────────────────
async def run_agent(prompt, llm_with_tools, named_tools, chat_history):

    # 🔥 FORCE TOOL FIRST
    forced = await force_tool_if_needed(prompt, named_tools)
    if forced:
        return f"✅ Action completed: {forced}"

    # Normal flow
    chat_history.append(HumanMessage(content=prompt))

    response = await llm_with_tools.ainvoke(chat_history)
    tool_calls = getattr(response, "tool_calls", None)

    if not tool_calls:
        chat_history.append(response)
        return response.content

    # GROQ fix
    if response.content:
        response = AIMessage(content="", tool_calls=response.tool_calls)

    chat_history.append(response)

    tool_messages = []

    for tc in tool_calls:
        name = tc["name"]
        args = tc.get("args", {})

        print(f"🔧 Executing Tool: {name}")
        print(f"📦 Args: {args}")

        try:
            tool = named_tools[name]
            raw = await tool.ainvoke(args)
            result = extract_tool_result(raw)
        except Exception as e:
            result = f"❌ Error: {str(e)}"

        tool_messages.append(
            ToolMessage(tool_call_id=tc["id"], content=result)
        )

    chat_history.extend(tool_messages)

    final_response = await llm.ainvoke(chat_history)
    chat_history.append(final_response)

    return final_response.content

# ── MAIN ─────────────────────────────────────────
async def main():
    print("⏳ Connecting to MCP servers...")

    try:
        client = MultiServerMCPClient(SERVERS)
        tools = await client.get_tools()
        named_tools = {t.name: t for t in tools}

        print("✅ Connected Tools:", list(named_tools.keys()))

        llm_with_tools = llm.bind_tools(tools)

    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return

    chat_history = [
        SystemMessage(content=(
            "You are an AI Expense Manager.\n"
            "Always use tools for expense actions.\n"
        ))
    ]

    print("\n✅ Ready! Type 'exit' to quit.")

    while True:
        user_input = input("\n🧑 You: ").strip()

        if user_input.lower() in ("exit", "quit"):
            break
        if not user_input:
            continue

        try:
            answer = await run_agent(
                user_input,
                llm_with_tools,
                named_tools,
                chat_history
            )
            print(f"🤖 Assistant: {answer}")

        except Exception as e:
            print(f"❌ Runtime Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())