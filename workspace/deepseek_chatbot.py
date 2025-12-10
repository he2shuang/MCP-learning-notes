import arxiv
import json
import os
import time
from typing import List
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
import openai  # 使用OpenAI兼容的API调用DeepSeek

PAPER_DIR = "papers"

# Initialize FastMCP server
mcp = FastMCP("research")

# 工具函数保持不变
@mcp.tool()
def search_papers(topic: str, max_results: int = 5) -> List[str]:
    """
    Search for papers on arXiv based on a topic and store their information.
    
    Args:
        topic: The topic to search for
        max_results: Maximum number of results to retrieve (default: 5)
        
    Returns:
        List of paper IDs found in the search
    """
    
    try:
        # Use arxiv to find the papers 
        client = arxiv.Client()

        # Search for the most relevant articles matching the queried topic
        search = arxiv.Search(
            query=topic,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance
        )

        papers = list(client.results(search))
        
        # Create directory for this topic
        path = os.path.join(PAPER_DIR, topic.lower().replace(" ", "_"))
        os.makedirs(path, exist_ok=True)
        
        file_path = os.path.join(path, "papers_info.json")

        # Try to load existing papers info
        try:
            with open(file_path, "r", encoding='utf-8') as json_file:
                papers_info = json.load(json_file)
        except (FileNotFoundError, json.JSONDecodeError):
            papers_info = {}

        # Process each paper and add to papers_info  
        paper_ids = []
        for paper in papers:
            paper_id = paper.entry_id.split('/')[-1]
            paper_ids.append(paper_id)
            paper_info = {
                'title': paper.title,
                'authors': [author.name for author in paper.authors],
                'summary': paper.summary,
                'pdf_url': paper.pdf_url,
                'published': str(paper.published.date()) if paper.published else 'Unknown'
            }
            papers_info[paper_id] = paper_info
        
        # Save updated papers_info to json file
        with open(file_path, "w", encoding='utf-8') as json_file:
            json.dump(papers_info, json_file, indent=2, ensure_ascii=False)
        
        print(f"成功搜索到 {len(papers)} 篇论文")
        print(f"结果保存在: {file_path}")
        
        return paper_ids
        
    except Exception as e:
        print(f"搜索论文时出错: {e}")
        print("请检查网络连接或稍后重试")
        return []

@mcp.tool()
def extract_info(paper_id: str) -> str:
    """
    Search for information about a specific paper across all topic directories.
    
    Args:
        paper_id: The ID of the paper to look for
        
    Returns:
        JSON string with paper information if found, error message if not found
    """
 
    for item in os.listdir(PAPER_DIR):
        item_path = os.path.join(PAPER_DIR, item)
        if os.path.isdir(item_path):
            file_path = os.path.join(item_path, "papers_info.json")
            if os.path.isfile(file_path):
                try:
                    with open(file_path, "r", encoding='utf-8') as json_file:
                        papers_info = json.load(json_file)
                        if paper_id in papers_info:
                            return json.dumps(papers_info[paper_id], indent=2, ensure_ascii=False)
                except (FileNotFoundError, json.JSONDecodeError) as e:
                    print(f"Error reading {file_path}: {str(e)}")
                    continue
    
    return f"没有找到与论文 {paper_id} 相关的保存信息。"

# 工具定义
tools = [
    {
        "type": "function",
        "function": {
            "name": "search_papers",
            "description": "Search for papers on arXiv based on a topic and store their information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "The topic to search for"
                    }, 
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to retrieve",
                        "default": 5
                    }
                },
                "required": ["topic"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "extract_info",
            "description": "Search for information about a specific paper across all topic directories.",
            "parameters": {
                "type": "object",
                "properties": {
                    "paper_id": {
                        "type": "string",
                        "description": "The ID of the paper to look for"
                    }
                },
                "required": ["paper_id"]
            }
        }
    }
]

# 工具映射
mapping_tool_function = {
    "search_papers": search_papers,
    "extract_info": extract_info
}

def execute_tool(tool_name, tool_args):
    result = mapping_tool_function[tool_name](**tool_args)

    if result is None:
        result = "操作已完成但没有返回任何结果。"
        
    elif isinstance(result, list):
        result = ', '.join(result)
        
    elif isinstance(result, dict):
        # Convert dictionaries to formatted JSON strings
        result = json.dumps(result, indent=2, ensure_ascii=False)
    
    else:
        # For any other type, convert using str()
        result = str(result)
    return result

# 加载环境变量
load_dotenv()

# DeepSeek客户端将在process_query函数中初始化
client = None

def process_query(query):
    global client
    # 初始化DeepSeek客户端
    if client is None:
        api_key = os.getenv('DEEPSEEK_API_KEY')
        if not api_key:
            print("错误: 未找到DeepSeek API密钥。请检查.env文件是否已配置DEEPSEEK_API_KEY。")
            return
        
        client = openai.OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com/v1"  # DeepSeek API端点
        )
    
    messages = [{'role': 'user', 'content': query}]
    
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",  # 使用DeepSeek Chat模型
            messages=messages,
            tools=tools,
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
                    
                    # 执行工具
                    result = execute_tool(tool_name, tool_args)
                    
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
                        "content": result
                    })
                    
                    # 获取新的响应
                    response = client.chat.completions.create(
                        model="deepseek-chat",
                        messages=messages,
                        tools=tools,
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

def chat_loop():
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
    
            process_query(query)
            print("\n" + "="*50)
            
        except KeyboardInterrupt:
            print("\n\n程序被用户中断。")
            break
        except Exception as e:
            print(f"\n错误: {str(e)}")

if __name__ == "__main__":
    chat_loop()
