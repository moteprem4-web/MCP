import asyncio
import os
import json
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, ToolMessage, AIMessage, SystemMessage
from langchain_mcp_adapters.client import MultiServerMCPClient

load_dotenv()

# --- Initialize LLM ---
# Note: Using 8b-instant to stay within free-tier rate limits
llm = ChatGroq(
    groq_api_key=os.getenv("GROQ_API_KEY"),
    model_name="openai/gpt-oss-20b", 
    temperature=0
)

# --- MCP Servers Configuration ---
SERVERS = {
    "math": {
        "transport": "stdio",
        "command": "python",
        "args": [r"C:\Users\motep\Desktop\MATH_MCP_SERVER\main.py"]
    },
    "expense": {
        "transport": "stdio",
        "command": "python",
        "args": [r"C:\Users\motep\Desktop\Expense_Tracker_mcp_server\main.py"]
    },
    "manim": {
        "transport": "stdio",
        "command": "python",
        "args": [r"C:\Users\motep\Desktop\manim-mcp-server\src\manim_server.py"]
    }
}

async def run_agent(prompt: str, llm_with_tools, named_tools, chat_history: list) -> str:
    chat_history.append(HumanMessage(content=prompt))

    # 1. Get initial response
    response = await llm_with_tools.ainvoke(chat_history)
    
    # GROQ FIX: Prevent 400 error by ensuring content is empty when tool_calls are present
    if response.tool_calls:
        response = AIMessage(content="", tool_calls=response.tool_calls)
    
    chat_history.append(response)

    if not response.tool_calls:
        return response.content

    # 2. Execute tools
    for tc in response.tool_calls:
        name = tc["name"]
        args = tc.get("args", {})
        print(f"    🔧 Executing: {name}...")

        try:
            tool = named_tools[name]
            raw = await tool.ainvoke(args)
            result = json.dumps(raw) if isinstance(raw, (dict, list)) else str(raw)
        except Exception as e:
            result = f"Error: {str(e)}"
        
        chat_history.append(ToolMessage(tool_call_id=tc["id"], content=result))

    # 3. Final synthesis
    final_response = await llm.ainvoke(chat_history)
    chat_history.append(final_response)
    
    return final_response.content

async def main():
    print("⏳ Connecting to MCP servers...")
    
    client = MultiServerMCPClient(SERVERS)
    
    try:
        tools = await client.get_tools()
        named_tools = {t.name: t for t in tools}
        llm_with_tools = llm.bind_tools(tools)
        # Verify the number of tools - should be around 5-7 for expenses alone
        print(f"✅ Connected! Loaded {len(tools)} tools.")
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return

    # --- CRITICAL CHANGES HERE ---
    # We update the SystemMessage to guide the LLM on using Update/Delete/Summary
    chat_history = [
        SystemMessage(content=(
            "You are a professional assistant and expert expense manager. "
            "Current date: 2026-04-03. "
            "\nDATABASE CAPABILITIES:"
            "1. ADD: Use 'add_expense'."
            "2. LIST: Use 'list_expenses'. Always check the ID before editing or deleting."
            "3. EDIT: Use 'edit_expense'. You MUST have the expense_id. If you don't have it, list expenses first."
            "4. DELETE: Use 'delete_expense'. You MUST have the expense_id."
            "5. SUMMARY: Use 'get_spending_summary' to show totals by category."
            "\nSTRICT RULE: When using tools, do not explain what you are doing. Just call the tool."
        ))
    ]

    print("🚀 Ready! You can now Add, List, Edit, Delete, or Summarize expenses.")
    while True:
        user_input = input("\n🧑 You: ").strip()
        if user_input.lower() in ("exit", "quit"): break
        if not user_input: continue

        try:
            answer = await run_agent(user_input, llm_with_tools, named_tools, chat_history)
            print(f"🤖 Assistant: {answer}")
        except Exception as e:
            print(f"❌ Runtime Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())