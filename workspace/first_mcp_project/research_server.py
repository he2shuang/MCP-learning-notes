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
