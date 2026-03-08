from duckduckgo_search import DDGS
import json

def test_search(query):
    print(f"\n--- Searching: {query} ---")
    results = DDGS().text(query, max_results=3)
    for r in results:
        print(f"Title: {r.get('title')}")
        print(f"URL: {r.get('href')}")
        print(f"Snippet: {r.get('body')}\n")

test_search("Magic Spoon cereal brand")
test_search("Magic Spoon linkedin VP Growth")
