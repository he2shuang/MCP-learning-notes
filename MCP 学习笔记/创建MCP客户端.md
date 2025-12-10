# 第一次尝试

在有了[[環境構築#创建 MCP Client 所需的环境|MCP Client 环境]]后，可以使用`FStdioServerParameters`，`stdio_client` 等库来快速构建一个MCP客户端。

我们通过以下几步快速构建使用MCP服务器的MCP客户端并测试：
1. 设置API密钥
2. 创建基本客户端结构
3. 实现服务器连接管理
4. 补充查询处理逻辑
5. 添加交互式聊天功能
6. 运行并测试


## 设置API密钥

可以像[[環境構築#创建 MCP Client 所需的环境|MCP Client 环境]]中一样直接添加到虚拟环境中，不过更好的方式是使用`.env`文件来管理

创建一个 `.env` 文件来存储它：
```
# 按照实际使用的LLM决定如何设置
# echo "ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic" > .env
echo "ANTHROPIC_API_KEY=your-api-key-goes-here" > .env
```

将 `.env 添加到` `.gitignore` 中：
```
echo ".env" >> .gitignore
```


## 创建基本客户端结构

首先，让我们设置导入并创建基本的客户端类：

```
from dotenv import load_dotenv
from anthropic import Anthropic
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
from typing import List
import asyncio
import nest_asyncio
  
nest_asyncio.apply()
  
load_dotenv()
  
class MCP_ChatBot:
  
    def __init__(self):
        # Initialize session and client objects
        self.session: ClientSession = None
        self.anthropic = Anthropic()
        self.available_tools: List[dict] = []
    # methods will go here
```


## 实现服务器连接管理

接下来，我们将实现连接到 MCP 服务器的方法：

```
async def connect_to_server_and_run(self):
        # Create server parameters for stdio connection
        server_params = StdioServerParameters(
            command="uv",  # Executable
            args=["run", "research_server.py"],  # Optional command line arguments
            env=None,  # Optional environment variables
        )
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                self.session = session
                # Initialize the connection
                await session.initialize()
                # List available tools
                response = await session.list_tools()
                tools = response.tools
                print("\nConnected to server with tools:", [tool.name for tool in tools])
                self.available_tools = [{
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema
                } for tool in response.tools]
                await self.chat_loop()
```

## 补充查询处理逻辑

现在我们来补充处理查询和处理工具调用的核心功能：

```
    async def process_query(self, query):
        messages = [{'role':'user', 'content':query}]
        response = self.anthropic.messages.create(max_tokens = 2024,
                                      model = 'deepseek-chat',
                                      tools = self.available_tools, # tools exposed to the LLM
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
                    #result = execute_tool(tool_name, tool_args): not anymore needed
                    # tool invocation through the client session
                    result = await self.session.call_tool(tool_name, arguments=tool_args)
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

## 添加交互式聊天功能

现在我们会加入聊天循环功能：

```
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

最后，我们会添加主要的执行逻辑：
```
async def main():
    chatbot = MCP_ChatBot()
    await chatbot.connect_to_server_and_run()
if __name__ == "__main__":
    asyncio.run(main())
```


## 运行并测试

将上述内容整理保存到 `mcp_chatbot.py` 文件中,执行下面的命令运行

```
uv run mcp_chatbot.py
```


以下是运行结果，包括和用户的交互过程：
从运行结果来看，MCP 客户端可以成功使用MCP 服务器的tool。在3和5中分别使用了MCP服务器中我们自定义的tool：“search_papers”和“extract_info”，并且成功返回了结果。说明我们成功使用了MCP 客户端和MCP服务器。

|     |         |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| --- | ------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | chatbot | MCP Chatbot Started!<br>Type your queries or 'quit' to exit.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| 2   | user    | give me some papers about "AI Agent", 3 is enough                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| 3   | chatbot | I'll search for papers about "AI Agent" and retrieve 3 results for you.<br>Calling tool search_papers with args {'topic': 'AI Agent', 'max_results': 3}<br>Here are 3 papers about "AI Agent" that I found:<br><br>1. **Paper ID: 2501.02842v1**<br>2. **Paper ID: 2503.12687v1** <br>3. **Paper ID: 2509.00961v1**<br><br>Would you like me to get more detailed information about any of these specific papers? I can extract their titles, abstracts, and other metadata for you.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| 4   | user    | i want to get information about 2509.00961v1                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| 5   | chatbot | I'll help you get information about paper 2509.00961v1. Let me search for it across the available directories.<br>Calling tool extract_info with args {'paper_id': '2509.00961v1'}<br>Here's the information about paper 2509.00961v1:<br><br>**Title:** Ultra Strong Machine Learning: Teaching Humans Active Learning Strategies via Automated AI Explanations<br><br>**Authors:** Lun Ai, Johannes Langer, Ute Schmid, Stephen Muggleton<br><br>**Published:** August 31, 2025<br><br>**Summary:** This paper introduces LENS (Logic Programming Explanation via Neural Summarisation), a neuro-symbolic method that combines symbolic program synthesis with large language models (LLMs) to automate the explanation of machine-learned logic programs in natural language. The research focuses on Ultra Strong Machine Learning (USML) systems that can teach their acquired knowledge to improve human performance. The authors conducted systematic evaluations showing that LENS generates superior explanations compared to direct LLM prompting and hand-crafted templates. However, human learning experiments across three domains showed no significant performance improvements, suggesting that comprehensive LLM responses may overwhelm users for simpler problems.<br><br>**PDF URL:** https://arxiv.org/pdf/2509.00961v1<br><br>The source code for this research is available at: https://github.com/lun-ai/LENS.git<br> |
| 6   | user    | quit                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |


```
(first_mcp_project) PS C:\limeng\MCP\workspace\first_mcp_project> uv run mcp_chatbot.py

Connected to server with tools: ['search_papers', 'extract_info']

MCP Chatbot Started!
Type your queries or 'quit' to exit.

Query: give me some papers about "AI Agent", 3 is enough
I'll search for papers about "AI Agent" and retrieve 3 results for you.
Calling tool search_papers with args {'topic': 'AI Agent', 'max_results': 3}
Here are 3 papers about "AI Agent" that I found:

1. **Paper ID: 2501.02842v1**
2. **Paper ID: 2503.12687v1** 
3. **Paper ID: 2509.00961v1**

Would you like me to get more detailed information about any of these specific papers? I can extract their titles, abstracts, and other metadata for you.



Query: i want to get information about 2509.00961v1
I'll help you get information about paper 2509.00961v1. Let me search for it across the available directories.
Calling tool extract_info with args {'paper_id': '2509.00961v1'}
Here's the information about paper 2509.00961v1:

**Title:** Ultra Strong Machine Learning: Teaching Humans Active Learning Strategies via Automated AI Explanations

**Authors:** Lun Ai, Johannes Langer, Ute Schmid, Stephen Muggleton

**Published:** August 31, 2025

**Summary:** This paper introduces LENS (Logic Programming Explanation via Neural Summarisation), a neuro-symbolic method that combines symbolic program synthesis with large language models (LLMs) to automate the explanation of machine-learned logic programs in natural language. The research focuses on Ultra Strong Machine Learning (USML) systems that can teach their acquired knowledge to improve human performance. The authors conducted systematic evaluations showing that LENS generates superior explanations compared to direct LLM prompting and hand-crafted templates. However, human learning experiments across three domains showed no significant performance improvements, suggesting that comprehensive LLM responses may overwhelm users for simpler problems.

**PDF URL:** https://arxiv.org/pdf/2509.00961v1

The source code for this research is available at: https://github.com/lun-ai/LENS.git



Query:quit
```

## How it works?

提交查询时：

1. 客户端从服务器获得可用工具列表
2. 你的查询会连同工具描述一起发送到 Claude
3. Claude 决定使用哪些工具（如果有的话）
4. 客户端通过服务器执行任何请求的工具调用
5. 结果会发回 Claude
6. Claude 提供自然语言的响应
7. 回答会显示给你