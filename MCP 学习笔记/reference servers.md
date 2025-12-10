## 使用reference servers

[modelcontextprotocol/servers: Model Context Protocol Servers](https://github.com/modelcontextprotocol/servers?tab=readme-ov-file#-reference-servers)

这里我们将以使用 [filesystem](https://github.com/modelcontextprotocol/servers/blob/main/src/fetch) 和 [fetch](https://github.com/modelcontextprotocol/servers/blob/main/src/filesystem) 作为示例来演示如何使用reference servers并且如何同时使用多个server。

1. 创建`server_config.json`文件
2. 初始化会话和客户端对象
3. 连接单个MCP服务器
4. 批量连接所有服务器
5. 处理用户查询的核心逻辑
6. 添加交互式聊天功能
7. 运行并测试

### `server_config.json`文件

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "."]
    },
  
    "research": {
      "command": "uv",
      "args": ["run", "research_server.py"]
    },
  
    "fetch": {
      "command": "uvx",
      "args": ["mcp-server-fetch"]
    }
  }
}
```

### 初始化会话和客户端对象

```python
    def __init__(self):
        # 初始化会话和客户端对象
        self.sessions: List[ClientSession] = []
        self.exit_stack = AsyncExitStack() 
        self.anthropic = Anthropic()
        self.available_tools: List[ToolDefinition] = []
        self.tool_to_session: Dict[str, ClientSession] = {} 
```

### 连接单个MCP服务器

```python
    async def connect_to_server(self, server_name: str, server_config: dict) -> None:
        """Connect to a single MCP server."""
        try:
            server_params = StdioServerParameters(**server_config)
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            ) 
            read, write = stdio_transport
            session = await self.exit_stack.enter_async_context(
                ClientSession(read, write)
            ) 
            await session.initialize()
            self.sessions.append(session)
            # List available tools for this session
            response = await session.list_tools()
            tools = response.tools
            print(f"\nConnected to {server_name} with tools:", [t.name for t in tools])
            for tool in tools:
                self.tool_to_session[tool.name] = session
                self.available_tools.append({
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema
                })
        except Exception as e:
            print(f"Failed to connect to {server_name}: {e}")
```

### 批量连接所有服务器

```python
    async def connect_to_servers(self):
        """Connect to all configured MCP servers."""
        try:
            with open("server_config.json", "r") as file:
                data = json.load(file)
            servers = data.get("mcpServers", {})
            for server_name, server_config in servers.items():
                await self.connect_to_server(server_name, server_config)
        except Exception as e:
            print(f"Error loading server configuration: {e}")
            raise
```


### 处理用户查询的核心逻辑

```python
    async def process_query(self, query):
        messages = [{'role':'user', 'content':query}]
        response = self.anthropic.messages.create(max_tokens = 2024,
                                      model = 'deepseek-chat',
                                      tools = self.available_tools,
                                      messages = messages)
        process_query = True
        while process_query:
            assistant_content = []
            for content in response.content:
                if content.type =='text':
                    print(content.text)
                    assistant_content.append(content)
                    if(len(response.content) == 1):
                        process_query= False
                elif content.type == 'tool_use':
                    assistant_content.append(content)
                    messages.append({'role':'assistant', 'content':assistant_content})
                    tool_id = content.id
                    tool_args = content.input
                    tool_name = content.name
                    print(f"Calling tool {tool_name} with args {tool_args}")
                    # Call a tool
                    session = self.tool_to_session[tool_name] # new
                    result = await session.call_tool(tool_name, arguments=tool_args)
                    messages.append({"role": "user",
                                      "content": [
                                          {
                                              "type": "tool_result",
                                              "tool_use_id":tool_id,
                                              "content": result.content
                                          }
                                      ]
                                    })
                    response = self.anthropic.messages.create(max_tokens = 2024,
                                      model = 'deepseek-chat',
                                      tools = self.available_tools,
                                      messages = messages)
                    if(len(response.content) == 1 and response.content[0].type == "text"):
                        print(response.content[0].text)
                        process_query= False
```

### 添加交互式聊天功能

```python
    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Chatbot Started!")
        print("Type your queries or 'quit' to exit.")
        while True:
            try:
                query = input("\nQuery: ").strip()
                if query.lower() == 'quit':
                    break
                await self.process_query(query)
                print("\n")
            except Exception as e:
                print(f"\nError: {str(e)}")
```

### 运行并测试

整个代码如下所示

```python
from dotenv import load_dotenv
from anthropic import Anthropic
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
from typing import List, Dict, TypedDict
from contextlib import AsyncExitStack
import json
import asyncio
  
load_dotenv()
  
class ToolDefinition(TypedDict):
    name: str
    description: str
    input_schema: dict
  
class MCP_ChatBot:
  
    def __init__(self):
        # 初始化会话和客户端对象
        self.sessions: List[ClientSession] = []
        self.exit_stack = AsyncExitStack() 
        self.anthropic = Anthropic()
        self.available_tools: List[ToolDefinition] = []
        self.tool_to_session: Dict[str, ClientSession] = {} 
  

    async def connect_to_server(self, server_name: str, server_config: dict) -> None:
        """Connect to a single MCP server."""
        try:
            server_params = StdioServerParameters(**server_config)
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            ) 
            read, write = stdio_transport
            session = await self.exit_stack.enter_async_context(
                ClientSession(read, write)
            ) 
            await session.initialize()
            self.sessions.append(session)
            # List available tools for this session
            response = await session.list_tools()
            tools = response.tools
            print(f"\nConnected to {server_name} with tools:", [t.name for t in tools])
            for tool in tools:
                self.tool_to_session[tool.name] = session
                self.available_tools.append({
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema
                })
        except Exception as e:
            print(f"Failed to connect to {server_name}: {e}")
  

    async def connect_to_servers(self):
        """Connect to all configured MCP servers."""
        try:
            with open("server_config.json", "r") as file:
                data = json.load(file)
            servers = data.get("mcpServers", {})
            for server_name, server_config in servers.items():
                await self.connect_to_server(server_name, server_config)
        except Exception as e:
            print(f"Error loading server configuration: {e}")
            raise

    async def process_query(self, query):
        messages = [{'role':'user', 'content':query}]
        response = self.anthropic.messages.create(max_tokens = 2024,
                                      model = 'deepseek-chat',
                                      tools = self.available_tools,
                                      messages = messages)
        process_query = True
        while process_query:
            assistant_content = []
            for content in response.content:
                if content.type =='text':
                    print(content.text)
                    assistant_content.append(content)
                    if(len(response.content) == 1):
                        process_query= False
                elif content.type == 'tool_use':
                    assistant_content.append(content)
                    messages.append({'role':'assistant', 'content':assistant_content})
                    tool_id = content.id
                    tool_args = content.input
                    tool_name = content.name
                    print(f"Calling tool {tool_name} with args {tool_args}")
                    # Call a tool
                    session = self.tool_to_session[tool_name] # new
                    result = await session.call_tool(tool_name, arguments=tool_args)
                    messages.append({"role": "user",
                                      "content": [
                                          {
                                              "type": "tool_result",
                                              "tool_use_id":tool_id,
                                              "content": result.content
                                          }
                                      ]
                                    })
                    response = self.anthropic.messages.create(max_tokens = 2024,
                                      model = 'deepseek-chat',
                                      tools = self.available_tools,
                                      messages = messages)
                    if(len(response.content) == 1 and response.content[0].type == "text"):
                        print(response.content[0].text)
                        process_query= False
  

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Chatbot Started!")
        print("Type your queries or 'quit' to exit.")
        while True:
            try:
                query = input("\nQuery: ").strip()
                if query.lower() == 'quit':
                    break
                await self.process_query(query)
                print("\n")
            except Exception as e:
                print(f"\nError: {str(e)}")

    async def cleanup(self): # new

        """Cleanly close all resources using AsyncExitStack."""

        await self.exit_stack.aclose()

  
  

async def main():
    chatbot = MCP_ChatBot()
    try:
        # the mcp clients and sessions are not initialized using "with"
        # like in the previous lesson
        # so the cleanup should be manually handled
        await chatbot.connect_to_servers() # new!
        await chatbot.chat_loop()
    finally:
        await chatbot.cleanup() #new!


if __name__ == "__main__":
    asyncio.run(main())
```

当我提出要求：
```
Fetch the content of this website: https://modelcontextprotocol.io/docs/concepts/architecture and save the content in the file "mcp_summary.md", create a visual diagram that summarizes the content of "mcp_summary.md" and save it in a text file
I'll help you fetch the content from the MCP website and save it to a file. Let me start by fetching the content from the URL you provided.
```

ai完成了一下工作：
```
1. **Fetched and saved the MCP architecture content** to `mcp_summary.md` - This file contains a comprehensive summary of the Model Context Protocol architecture based on the content from the website.

2. **Created a visual diagram summary** in `mcp_diagram.txt` - This file contains ASCII-based diagrams that visually represent the MCP architecture,

```

![[Pasted image 20251209170959.png]]
![[Pasted image 20251209171042.png]]
![[Pasted image 20251209171417.png]]

这就说明了ai利用了 reference server 中的 fetch 工具从网页中抓取了信息，然后利用 filesystem 工具在本项目中自主创建了`mcp_summary.md`和`mcp_diagram.txt`文件。这就意味着我们成功让ai在一次处理用户需求中使用了多个 MCP Server。




当我进一步提出要求：
```
Fetch deeplearning.ai and find an interesting term. Search for 2 papers around the term and then summarize your findings and write them to a file called results.txt
I'll help you with this task. Let me start by fetching the deeplearning.ai website to find an interesting term.
```

ai完成了一下工作：
```
1. **Fetched deeplearning.ai** and explored their website
2. **Found an interesting term**: "Agentic AI" - prominently featured in their newest course "Building Coding Agents with Tool Execution"
3. **Searched for 2 papers** on arXiv related to "agentic AI" and found:
   - Paper 1: "Trustworthy AI in the Agentic Lakehouse: from Concurrency to Governance" (Nov 2025)
   - Paper 2: "Foundations of GenIR" (Jan 2025)
4. **Summarized findings** and wrote them to a file called `results.txt`

```

可以看到ai依次使用了 fetch 、research 、filesystem 工具来实现我的要求：先用 fetch 获取网站中的信息，再利用我们自定义的 research 查找文献，最后总结的结果利用 filesystem 写入了 `results.txt` 文件中。

![[Pasted image 20251209171059.png]]
![[Pasted image 20251209171139.png]]

![[Pasted image 20251209171651.png]]