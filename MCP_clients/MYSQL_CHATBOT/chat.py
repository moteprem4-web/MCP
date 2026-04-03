import asyncio
import os
import json
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, ToolMessage, AIMessage, SystemMessage
from langchain_mcp_adapters.client import MultiServerMCPClient

load_dotenv()

# --- Initialize LLM ---
# Using llama-3.3-70b-versatile for superior tool selection and SQL logic
llm = ChatGroq(
    groq_api_key=os.getenv("GROQ_API_KEY"),
    model_name="llama-3.3-70b-versatile", 
    temperature=0
)

# --- MCP Servers Configuration ---
SERVERS = {
    "mysql_db": {
        "transport": "stdio",
        "command": r"C:\Users\motep\AppData\Local\Programs\Python\Python312\python.exe",
        "args": [r"C:\Users\motep\Desktop\MYSQL_MCP_SERVER\main.py"]
    },
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

    # 2. Execute tools in real-time
    for tc in response.tool_calls:
        name = tc["name"]
        args = tc.get("args", {})
        print(f"    🔧 Executing Database Action: {name}...")

        try:
            tool = named_tools[name]
            raw = await tool.ainvoke(args)
            # Handle list/dict returns from fetch_table_data
            result = json.dumps(raw) if isinstance(raw, (dict, list)) else str(raw)
        except Exception as e:
            result = f"Error: {str(e)}"
        
        chat_history.append(ToolMessage(tool_call_id=tc["id"], content=result))

    # 3. Final synthesis of the database result
    final_response = await llm.ainvoke(chat_history)
    chat_history.append(final_response)
    
    return final_response.content

async def main():
    print("⏳ Connecting to MySQL MCP Ecosystem...")
    
    client = MultiServerMCPClient(SERVERS)
    
    try:
        tools = await client.get_tools()
        named_tools = {t.name: t for t in tools}
        llm_with_tools = llm.bind_tools(tools)
        print(f"✅ Connected! {len(tools)} Real-time CRUD tools loaded.")
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return

    # --- THE SYSTEM PROMPT: THE "BRAINS" OF THE AUTOMATION ---
    chat_history = [
        SystemMessage(content=(
            "You are an Expert MySQL Automation Agent. Your primary goal is to execute "
            "database operations in real-time based on natural language instructions."
            "\n\nCOMMAND LOGIC:"
            "1. CREATE DB: Call 'create_database' immediately."
            "2. CREATE TABLE: You must determine appropriate MySQL data types. "
            "   (e.g., 'name' -> VARCHAR(255), 'age' -> INT, 'id' -> INT AUTO_INCREMENT PRIMARY KEY)."
            "3. CRUD: Use 'insert_data', 'update_data', or 'delete_data' based on the request."
            "4. FETCH: Use 'fetch_table_data' to show users their information."
            "\n\nSTRICT RULES:"
            "- Do not explain that you are going to call a tool. Just do it."
            "- If a database name isn't specified but one exists in history, use the current one."
            "- Always confirm the success or failure of the operation based on the tool output."
            "- Current Date: 2026-04-03."
        ))
    ]

    print("🚀 Agent Ready! Try: 'Create a database for my library and add a table for books.'")
    
    while True:
        user_input = input("\n🧑 You: ").strip()
        if user_input.lower() in ("exit", "quit"): 
            print("👋 Closing connection. Goodbye!")
            break
        if not user_input: continue

        try:
            answer = await run_agent(user_input, llm_with_tools, named_tools, chat_history)
            print(f"🤖 Assistant: {answer}")
        except Exception as e:
            print(f"❌ Runtime Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())