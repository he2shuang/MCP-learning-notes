import json
import asyncio
import nest_asyncio
import os
import openai  # 使用OpenAI兼容的API调用DeepSeek
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
from typing import List

nest_asyncio.apply()

# 加载环境变量
load_dotenv()

class MCP_ChatBot:

    def __init__(self):
        # Initialize session and client objects
        self.session: ClientSession = None
        self.client = None
        self.available_tools: List[dict] = []

    async def process_query(self, query):
        # global client
        # 初始化DeepSeek客户端
        if self.client is None:
            api_key = os.getenv('DEEPSEEK_API_KEY')
            if not api_key:
                print("错误: 未找到DeepSeek API密钥。请检查.env文件是否已配置DEEPSEEK_API_KEY。")
                return

            self.client = openai.OpenAI(
                api_key=api_key,
                base_url="https://api.deepseek.com/v1"  # DeepSeek API端点
            )
    
        messages = [{'role':'user', 'content':query}]

        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",  # 使用DeepSeek Chat模型
                messages=messages,
                tools = self.available_tools,
                tool_choice="auto"
            )
            
            process_query = True
            while process_query:
                assistant_message = response.choices[0].message
                
                # 处理文本响应
                if assistant_message.content:
                    print(assistant_message.content)
                
                # 处理工具调用
                if assistant_message.tool_calls:
                    for tool_call in assistant_message.tool_calls:
                        tool_name = tool_call.function.name
                        tool_args = json.loads(tool_call.function.arguments)
                        
                        print(f"调用工具 {tool_name} 参数: {tool_args}")
                        # Call a tool
                        #result = execute_tool(tool_name, tool_args): not anymore needed
                        # tool invocation through the client session
                        result = await self.session.call_tool(tool_name, arguments=tool_args)
                        
                        # 添加工具调用和结果到消息历史
                        messages.append({
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": tool_call.id,
                                    "type": "function",
                                    "function": {
                                        "name": tool_name,
                                        "arguments": tool_call.function.arguments
                                    }
                                }
                            ]
                        })
                        
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": result.content
                        })
                        
                        # 获取新的响应
                        response = self.client.chat.completions.create(
                            model="deepseek-chat",
                            messages=messages,
                            tools=self.available_tools,
                            tool_choice="auto"
                        )
                        
                        # 如果新响应只有文本，则处理并结束
                        if response.choices[0].message.content and not response.choices[0].message.tool_calls:
                            print(response.choices[0].message.content)
                            process_query = False
                else:
                    process_query = False
                    
        except Exception as e:
            print(f"处理查询时出错: {e}")

    
    
    
    async def chat_loop(self):
        print("\nMCP Chatbot Started!")
        print("=== DeepSeek 论文助手 ===")
        print("输入您的查询或输入 'quit' 退出。")
        print("示例查询:")
        print("- 搜索关于'机器学习'的3篇论文")
        print("- 查找论文'1312.3300v1'的信息")
        print()

        while True:
            try:
                query = input("\n查询: ").strip()
                if query.lower() == 'quit':
                    print("再见！")
                    break
                 
                await self.process_query(query)
                print("\n" + "="*50)

            except KeyboardInterrupt:
                print("\n\n程序被用户中断。")
                break
            except Exception as e:
                print(f"\n错误: {str(e)}")
    
    async def connect_to_server_and_run(self):
        # Create server parameters for stdio connection
        server_params = StdioServerParameters(
            command="uv",  # Executable
            args=["run", "research_server.py"],  # Optional command line arguments
            env=None,  # Optional environment variables
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

async def main():
    chatbot = MCP_ChatBot()
    await chatbot.connect_to_server_and_run()
  

if __name__ == "__main__":
    asyncio.run(main())