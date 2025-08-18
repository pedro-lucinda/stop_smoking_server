from langchain_tavily import TavilySearch

search = TavilySearch(max_results=2)  # requires TAVILY_API_KEY


TOOLS = [search]
