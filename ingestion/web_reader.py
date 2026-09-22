# we will use langchain version, so ignore this file. output is same from both

import os
import trafilatura
from urllib.parse import urlparse

# Define paths based on your folder structure
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
WEBSITES_FILE = os.path.join(DATA_DIR, 'websites.txt')
WEB_DOCS_DIR = os.path.join(DATA_DIR, 'md_web') # Folder to save the markdown outputs

def load_web_page(url: str) -> dict:
    """
    Fetches a web page, strips HTML boilerplate using trafilatura, 
    and returns a clean document dictionary matching the PDF schema.
    """
    print(f"--- Processing Website: {url} ---")
    
    # 1. Fetch raw HTML
    downloaded = trafilatura.fetch_url(url)
    if downloaded is None:
        print(f"  [ERROR] Failed to fetch content. The site might be offline or blocking scrapers.")
        return None

    # 2. Extract content directly into Markdown format
    # include_links=False prevents the markdown from being bloated with navigation URLs
    # include_images=False prevents image tags from polluting the text
    clean_markdown = trafilatura.extract(
        downloaded,
        output_format="markdown",
        include_tables=True,
        include_links=False,
        include_images=False
    )

    if not clean_markdown:
        print(f"  [ERROR] Could not extract text. It might be a JS-heavy React/Vue site.")
        return None

    # 3. Extract page metadata (title, author, sitename, etc.)
    metadata = trafilatura.extract_metadata(downloaded)
    
    # Fallback to the URL path if the page has no HTML <title> tag
    page_title = metadata.title if (metadata and metadata.title) else urlparse(url).path

    # 4. Return the standardized document dictionary
    return {
        "text": clean_markdown,
        "source": url,
        "title": page_title,
        "doc_type": "web"
    }

def read_websites() -> list[dict]:
    """
    Reads URLs from data/websites.txt, extracts them, and saves them as .md files.
    """
    documents = []
    
    # 1. Ensure the data directory and websites.txt exist
    os.makedirs(WEB_DOCS_DIR, exist_ok=True)
    
    if not os.path.exists(WEBSITES_FILE):
        print(f"[WARNING] {WEBSITES_FILE} not found. Creating a sample one.")
        with open(WEBSITES_FILE, 'w', encoding='utf-8') as f:
            f.write("# Add your URLs below (one per line). Lines starting with # are ignored.\n")

        print(f"Please add your URLs to data/websites.txt and run again.")
        return documents

    # 2. Read URLs line by line
    with open(WEBSITES_FILE, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    for line in lines:
        url = line.strip()
        
        # Skip empty lines or commented lines
        if not url or url.startswith("#"):
            continue
            
        # 3. Extract the website
        doc = load_web_page(url)
        if doc:
            documents.append(doc)
            
            # 4. Save the extracted Markdown so you can inspect it visually
            # We clean the title so it is safe to use as a filename
            safe_title = "".join(c for c in doc["title"] if c.isalnum() or c in (' ', '_')).rstrip()
            output_path = os.path.join(WEB_DOCS_DIR, f"{safe_title[:50]}.md")
            
            with open(output_path, 'w', encoding='utf-8') as out_file:
                out_file.write(doc["text"])
            print(f"  [SUCCESS] Clean Markdown saved to: {output_path}")

    return documents

# Allows you to test this file directly without running the whole RAG pipeline
if __name__ == "__main__":
    print("================================================================================")
    print("TESTING WEB INGESTION")
    print("================================================================================")
    docs = read_websites()
    print(f"\nTotal websites successfully processed: {len(docs)}")