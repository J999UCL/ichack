from anthropic import Anthropic
import requests
from bs4 import BeautifulSoup
import io
import logging
import PyPDF2
import ast
from anytree import Node
from googlesearch import search
from firecrawl import FirecrawlApp

from scrape import crawl
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from random import randint
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MockSocketIO:
    def emit(self, event, data):
        print(f"Emitting event '{event}' with data: {data}")

class Claude:
    def __init__(self, socketio):
        self.articles = []
        self.socketio = socketio
        self.anthropic = Anthropic(
            api_key="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"
        )
        self.crawl = crawl()

    def url_to_info_pls(self, url):
        print(url)
        return self.crawl.crawl_url(url)

    def url_to_info(self, url):
        try:
            response = requests.get(url)
            logging.info(f"URL: {url}, Status Code: {response.status_code}")
        except Exception as e:
            logging.error(f"Error fetching URL: {url}, Exception: {e}")
            return None

        if response.status_code != 200:
            logging.warning(f"Non-200 status code for URL: {url}")
            return None

        content_type = response.headers.get("Content-Type", "").lower()
        logging.info(f"Content-Type for URL: {url} is {content_type}")

        if "github.com" in url and "raw" not in url:
            # Convert GitHub URL to raw content URL
            url = url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
            response = requests.get(url)
            if response.status_code != 200:
                logging.warning(f"Non-200 status code for raw GitHub URL: {url}")
                return None
            return response.text

        if "pdf" in content_type:
            # Process PDF content
            pdf_file = io.BytesIO(response.content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            return text.strip()
        else:
            soup = BeautifulSoup(response.content, 'html.parser')
            for element in soup(["script", "style"]):
                element.decompose()
            text = soup.get_text(separator=" ", strip=True)
            logging.info(f"Extracted text length for URL: {url} is {len(text)}")
            return text if text else None

    def claude_summarize(self, text):
        message = self.anthropic.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=500,
            temperature=0,
            system="""
                Summarize the text emphasizing clues of its historical and causal antecedents to aid in discovering prior related articles, papers, or posts.
                Write this analysis explicity then a delimiter then formulate 3 hypotheses of search queries that should yield relevant predecessors
                in the format: analysis !!! [hypothesis1, hypothesis2, hypothesis3] do not put anything after the closing square bracket. You must add !!! no matter what. If there is insufficient data make up three hypotheses just from the url name
            """,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": text
                        }
                    ]
                }
            ]
        )

        text = message.content[0].text
        print(text)
        summary, hypotheses = text.split("!!!")
        hypotheses = ast.literal_eval(hypotheses.strip())
        return summary, hypotheses


    def search_results(self, hypothesis, max_results=5):
    # Perform a Google search and get the top 5 results
        search_results = []
        for url in search(hypothesis, num_results=20):
            
            if len(search_results) == max_results:
                break
            # Check if the URL is like an article
            if any(keyword in url for keyword in ['article', 'news', 'blog', 'post']):
                search_results.append(url)
        return search_results

    def recurse(self, parent, url, depth, max_depth=3):
        logging.info(f"Processing URL: {url} at depth: {depth}")
        self.socketio.emit('processing_article', {'url': url})
        if depth >= max_depth:
            self.articles.append(url)
            return

        text = self.url_to_info(url)
        if text is None:
            logging.info("No text found for URL")
            return
        summary, hypotheses = self.claude_summarize(text[:2000])
        results = []
        for hypothesis in hypotheses:
            search_results = self.search_results(hypothesis, max_results=2)
            for url in search_results:
                logging.info(f"Searching article URL: {url}")
                self.socketio.emit('processing_article', {'url': url})
                info = self.url_to_info(url)
                if info is None:
                    continue
                results.append((url, info))
                if len(results) == 3:
                    break

        top3 = results[:3]  # Ensure top3 has at most 3 elements
        if not top3:
            return

        for i in range(len(top3)):
            self.recurse(Node(top3[i], parent=parent), top3[i][0], depth + 1)

    def main(self, url):
        root = Node(url)
        self.recurse(root, url, 0)
        output = self.link_articles(root,self.articles)
        print(output)
        return root, output

    def link_articles(self, root, articles):
        root_content = self.url_to_info(root.name)
        if root_content is None:
            logging.warning("No content found for the root article")
            return None

        # Collect content of all previous articles
        articles_content = []
        for article in articles:
            content = self.url_to_info(article)
            if content:
                articles_content.append(content)

        # Concatenate all content
        all_content = root_content + "\n\n" + "\n\n".join(articles_content)

        message = self.anthropic.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=1000,
            temperature=0,
            system="""
                        Can you link all the first article to all the following articles. Generate a short summary.
                    """,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": all_content
                        }
                    ]
                }
            ]
        )

        return message.content[0].text

# c = Claude()
# c.main('https://arxiv.org/abs/1706.03762')