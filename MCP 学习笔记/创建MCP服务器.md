# 第一次尝试

在有了[[環境構築#创建 MCP Server 所需的环境|MCP Server 环境]]后，可以使用名为`FastMCP` 的库来快速构建一个MCP服务器。

我们通过以下几步快速构建含有tool的MCP服务器并测试：
1. 引入FastMCP
2. 用MCP将函数定义为tool
3. 启动MCP服务器并在浏览器中进行测试


#### 1、引入FastMCP包和设置实例
```
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("research")
```

#### 2、用MCP将函数定义为tool
用`@mcp.tool()`装饰对应的函数：
```
@mcp.tool()
def test():
    print("Hello from first-mcp-project!")
```

#### 3、启动MCP服务器并在浏览器中进行测试
本地运行时通常使用`standard IO`传输：
```
if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')
```

启动测试工具 inspector ：
```
npx @modelcontextprotocol/inspector uv run research_server.py
```
#### 最简单的示例

创建一个名为`research_server.py`的文件内容为：
```
import arxiv
import json
import os
from typing import List
from mcp.server.fastmcp import FastMCP
  
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
  
  
if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')
```

##### 在 inspector 中测试MCP服务器

设置传输类型为`STDIO`，命令为`uv`，Arguments为`run research_server.py`，然后点击 `Connect` 。

![[Pasted image 20251118171656.png]]

连接成功后我们可以看到可用的基础功能模块，包括：Resources、Prompts、Tools、Sampling、Elicitations、Roots等等。这里我们来到Tools板块，这里应该会出现我们用`@mcp.tool()`定义的两个tool，在右边输入参数可以测试tool是否可用。
![[Pasted image 20251118172555.png]]

这里我们可以看到工具成功返回了结果，证明我们构建的MCP Server可以成功运行，并且定义的Tools也能正常工作。
![[Pasted image 20251118172752.png]]




# 添加 resources 和 prompts

资源是 MCP 服务器可以向 LLM 应用暴露的只读数据。资源类似于 REST API 中的 GET 端点——它们提供数据，但不应该执行大量计算或带来副作用。例如，资源可以是目录中的文件夹列表，或文件夹中文件的内容。这里，MCP 服务器提供两个资源：
- 论文目录下可用的主题文件夹列表;
- 论文信息存储在一个主题文件夹下。

这里有一个代码片段，展示了资源在 MCP 服务器中如何定义的，再次使用 `FastMCP` 装饰器 `@mcp.resource(uri)` 。你可以在文件夹 `mcp_project` 中找到完整的代码。内部 `@mcp.resource()` 定义的 URI 用于唯一标识资源，作为服务器开发者，你可以自定义 URI。但一般来说，它遵循以下方案： `sth://xyz/xcv` 。在本例中，使用了两种类型的 URI：

- static URI: `papers://folders` （代表可用主题列表）
- dynamic URI: `papers://{topic}` （代表论文在运行时客户端指定的主题下的信息）

```python
@mcp.resource("papers://folders")
def get_available_folders() -> str:
    """
    List all available topic folders in the papers directory.
    
    This resource provides a simple list of all available topic folders.
    """
    folders = []
    
    # Get all topic directories
    if os.path.exists(PAPER_DIR):
        for topic_dir in os.listdir(PAPER_DIR):
            topic_path = os.path.join(PAPER_DIR, topic_dir)
            if os.path.isdir(topic_path):
                papers_file = os.path.join(topic_path, "papers_info.json")
                if os.path.exists(papers_file):
                    folders.append(topic_dir)
    
    # Create a simple markdown list
    content = "# Available Topics\n\n"
    if folders:
        for folder in folders:
            content += f"- {folder}\n"
        content += f"\nUse @{folder} to access papers in that topic.\n"
    else:
        content += "No topics found.\n"
    
    return content

@mcp.resource("papers://{topic}")
def get_topic_papers(topic: str) -> str:
    """
    Get detailed information about papers on a specific topic.
    
    Args:
        topic: The research topic to retrieve papers for
    """
    topic_dir = topic.lower().replace(" ", "_")
    papers_file = os.path.join(PAPER_DIR, topic_dir, "papers_info.json")
    
    if not os.path.exists(papers_file):
        return f"# No papers found for topic: {topic}\n\nTry searching for papers on this topic first."
    
    try:
        with open(papers_file, 'r') as f:
            papers_data = json.load(f)
        
        # Create markdown content with paper details
        content = f"# Papers on {topic.replace('_', ' ').title()}\n\n"
        content += f"Total papers: {len(papers_data)}\n\n"
        
        for paper_id, paper_info in papers_data.items():
            content += f"## {paper_info['title']}\n"
            content += f"- **Paper ID**: {paper_id}\n"
            content += f"- **Authors**: {', '.join(paper_info['authors'])}\n"
            content += f"- **Published**: {paper_info['published']}\n"
            content += f"- **PDF URL**: [{paper_info['pdf_url']}]({paper_info['pdf_url']})\n\n"
            content += f"### Summary\n{paper_info['summary'][:500]}...\n\n"
            content += "---\n\n"
        
        return content
    except json.JSONDecodeError:
        return f"# Error reading papers data for {topic}\n\nThe papers data file is corrupted."
```

![[Pasted image 20251210170318.png]]

![[Pasted image 20251210170404.png]]

![[Pasted image 20251210170437.png]]
![[Pasted image 20251210170513.png]]

服务器还可以提供提示模板。你可以在 MCP 服务器中使用装饰器 `@mcp.prompt()` 定义此功能，如下面的代码片段所示。MCP 会将 Prompt 命名为 ， `generate_search_prompt` 从 函数的参数推断 prompt 参数，从 doc 字符串推断提示词的描述。

```python
@mcp.prompt()
def generate_search_prompt(topic: str, num_papers: int = 5) -> str:
    """Generate a prompt for Claude to find and discuss academic papers on a specific topic."""
    return f"""Search for {num_papers} academic papers about '{topic}' using the search_papers tool. Follow these instructions:
    1. First, search for papers using search_papers(topic='{topic}', max_results={num_papers})
    2. For each paper found, extract and organize the following information:
       - Paper title
       - Authors
       - Publication date
       - Brief summary of the key findings
       - Main contributions or innovations
       - Methodologies used
       - Relevance to the topic '{topic}'
    
    3. Provide a comprehensive summary that includes:
       - Overview of the current state of research in '{topic}'
       - Common themes and trends across the papers
       - Key research gaps or areas for future investigation
       - Most impactful or influential papers in this area
    
    4. Organize your findings in a clear, structured format with headings and bullet points for easy readability.
    
    Please present both detailed information about each paper and a high-level synthesis of the research landscape in {topic}."""
```

![[Pasted image 20251210170729.png]]

![[Pasted image 20251210170749.png]]

![[Pasted image 20251210170842.png]]

![[Pasted image 20251210170944.png]]