from mcp.server.fastmcp import FastMCP

# Create MCP server
mcp = FastMCP("Math Operations Server")


@mcp.tool()
def add(a: float, b: float) -> float:
    """Add two numbers"""
    return a + b


@mcp.tool()
def subtract(a: float, b: float) -> float:
    """Subtract second number from first"""
    return a - b


@mcp.tool()
def multiply(a: float, b: float) -> float:
    """Multiply two numbers"""
    return a * b


@mcp.tool()
def divide(a: float, b: float) -> float:
    """Divide first number by second"""
    if b == 0:
        return "Error: Division by zero not allowed"
    return a / b


if __name__ == "__main__":
    mcp.run()