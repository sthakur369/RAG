import os
import asyncio
import httpx
import trafilatura
from urllib.parse import urlparse

from config.config import (
    WEBSITES_INPUT_FOLDER, 
    WEBSITES_OUTPUT_FOLDER, 
    MAX_CONCURRENT_REQUESTS
    )


async def process_single_url(url, index, web_docs_dir, client, semaphore):
    async with semaphore:
        print(f"[{index}] Fetching: {url}")

        try:
            response = await client.get(url, follow_redirects=True, timeout=15)
            response.raise_for_status()
        except Exception as e:
            print(f"  [ERROR] Could not download {url}: {e}")
            return None

        html = response.text

        text = await asyncio.to_thread(
            trafilatura.extract, html,
            output_format="markdown",
            include_tables=True,
            include_links=False,
            include_images=False
        )

        if not text:
            print(f"  [ERROR] No content extracted from: {url}")
            return None

        meta = await asyncio.to_thread(trafilatura.extract_metadata, html)
        title = meta.title if meta and meta.title else urlparse(url).path

        file_path = os.path.join(web_docs_dir, f"web_doc_{index}.md")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text)

        print(f"  [SAVED] {file_path}")
        return {"text": text, "source": url, "title": title, "doc_type": "web"}


async def read_websites_langchain_async():
    websites_file = WEBSITES_INPUT_FOLDER
    web_docs_dir = WEBSITES_OUTPUT_FOLDER

    os.makedirs(web_docs_dir, exist_ok=True)

    if not os.path.exists(websites_file):
        print(f"[WARNING] {websites_file} not found.")
        return []

    with open(websites_file, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f
                if line.strip() and not line.startswith("#")]

    if not urls:
        print("No URLs found in websites.txt.")
        return []

    print(f"--- Processing {len(urls)} websites ---")

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    # Define a realistic browser User-Agent
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    async with httpx.AsyncClient(http2=True, headers=headers) as client:
        tasks = [
            process_single_url(url, i, web_docs_dir, client, semaphore)
            for i, url in enumerate(urls, 1)
        ]
        results = await asyncio.gather(*tasks)

    documents = [result for result in results if result]
    print(f"Successfully processed {len(documents)} web page(s).")
    return documents


# results = asyncio.run(read_websites_langchain_async("data"))