"""
Article Ingestion Pipeline - WITH GOOGLE SEARCH + TAVILY FALLBACK
Extracts questions from written interview articles
SUPPORTS: Google Custom Search, Tavily API (fallback), newspaper3k, BeautifulSoup
"""

from newspaper import Article
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import logging
import re
from datetime import datetime
import os
import time
from googleapiclient.discovery import build
from processing.question_extractor import get_question_extractor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Common headers to avoid 403/404 blocks
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}


class ArticleIngester:
    """
    Ingests interview articles from the web
    Extracts Q&A format interviews and standalone questions
    WITH: Google Search + Tavily API fallback for search AND fetch
    """

    def __init__(self):
        self.question_extractor = get_question_extractor(use_llm=True)

        # Load Google API credentials
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.google_cse_id = os.getenv("GOOGLE_CSE_ID")

        # Load Tavily API credentials (fallback)
        self.tavily_api_key = os.getenv("TAVILY_API_KEY")

        # Search providers
        self.google_search_enabled = bool(self.google_api_key and self.google_cse_id)
        self.tavily_enabled = bool(self.tavily_api_key)

        if self.google_search_enabled:
            logger.info("Google Custom Search enabled")
        if self.tavily_enabled:
            logger.info("Tavily API enabled (search + content fallback)")

        if not self.google_search_enabled and not self.tavily_enabled:
            logger.warning("No search APIs configured - automatic article discovery disabled")

        self.search_enabled = self.google_search_enabled or self.tavily_enabled

    def fetch_article(self, url: str, max_retries: int = 3) -> Optional[Dict]:
        """
        Fetch and parse an article from a URL
        WITH: Retry logic, proper headers, and Tavily fallback

        Args:
            url: URL of the article
            max_retries: Maximum retry attempts

        Returns:
            Dict containing article metadata and text
        """
        logger.info(f"Fetching article: {url}")

        # Method 1: newspaper3k with custom config
        article_data = self._fetch_with_newspaper3k(url, max_retries)
        if article_data and article_data.get('text'):
            return article_data

        # Method 2: requests + BeautifulSoup with proper headers
        article_data = self._fetch_with_requests(url, max_retries)
        if article_data and article_data.get('text'):
            return article_data

        # Method 3: Tavily API (extracts content from any URL)
        if self.tavily_enabled:
            article_data = self._fetch_with_tavily(url)
            if article_data and article_data.get('text'):
                return article_data

        logger.error(f"All fetch methods failed for: {url}")
        return None

    def _fetch_with_newspaper3k(self, url: str, max_retries: int = 3) -> Optional[Dict]:
        """Fetch article using newspaper3k with retry logic"""
        for attempt in range(max_retries):
            try:
                # Configure newspaper3k with custom headers
                config = Article(url)
                config.headers = DEFAULT_HEADERS

                article = Article(url, config=config)
                article.download()
                article.parse()

                if not article.text or len(article.text) < 100:
                    raise ValueError("Article text too short or empty")

                article_data = {
                    'url': url,
                    'title': article.title or url,
                    'text': article.text,
                    'authors': article.authors,
                    'publish_date': article.publish_date,
                    'top_image': article.top_image,
                }

                logger.info(f"Fetched with newspaper3k: {article.title[:50] if article.title else url}")
                return article_data

            except Exception as e:
                logger.debug(f"newspaper3k attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1 * (attempt + 1))  # Exponential backoff
                continue

        logger.warning(f"newspaper3k failed for: {url}")
        return None

    def _fetch_with_requests(self, url: str, max_retries: int = 3) -> Optional[Dict]:
        """Fetch article using requests + BeautifulSoup with retry logic"""
        for attempt in range(max_retries):
            try:
                response = requests.get(
                    url,
                    headers=DEFAULT_HEADERS,
                    timeout=30,
                    allow_redirects=True
                )
                response.raise_for_status()

                soup = BeautifulSoup(response.content, 'lxml')

                # Try to extract title
                title = soup.find('h1')
                if not title:
                    title = soup.find('title')
                title_text = title.get_text(strip=True) if title else url

                # Remove script, style, nav, footer elements
                for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                    element.decompose()

                # Get text from common article containers (prioritized)
                article_text = ""

                # Try specific article selectors first
                selectors = [
                    ('article', {}),
                    ('div', {'class': re.compile(r'(article|content|post|entry|story)[-_]?(body|text|content)?', re.I)}),
                    ('div', {'id': re.compile(r'(article|content|post|entry|story)', re.I)}),
                    ('main', {}),
                ]

                for tag, attrs in selectors:
                    containers = soup.find_all(tag, attrs) if attrs else soup.find_all(tag)
                    for container in containers:
                        text = container.get_text(separator='\n', strip=True)
                        if len(text) > len(article_text):
                            article_text = text

                # Fallback to body text
                if not article_text or len(article_text) < 200:
                    body = soup.find('body')
                    if body:
                        article_text = body.get_text(separator='\n', strip=True)

                if not article_text or len(article_text) < 100:
                    raise ValueError("Could not extract meaningful content")

                article_data = {
                    'url': url,
                    'title': title_text,
                    'text': article_text,
                    'authors': [],
                    'publish_date': None,
                    'top_image': None,
                }

                logger.info(f"Fetched with requests/BS4: {title_text[:50]}")
                return article_data

            except Exception as e:
                logger.debug(f"requests/BS4 attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1 * (attempt + 1))
                continue

        logger.warning(f"requests/BS4 failed for: {url}")
        return None

    def _fetch_with_tavily(self, url: str) -> Optional[Dict]:
        """
        FALLBACK: Fetch article content using Tavily API
        Tavily can extract content from URLs that block scrapers
        """
        if not self.tavily_api_key:
            return None

        logger.info(f"Trying Tavily API for: {url}")

        try:
            # Tavily Extract API endpoint
            tavily_url = "https://api.tavily.com/extract"

            payload = {
                "api_key": self.tavily_api_key,
                "urls": [url]
            }

            response = requests.post(
                tavily_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            response.raise_for_status()

            data = response.json()

            if data.get('results') and len(data['results']) > 0:
                result = data['results'][0]

                raw_content = result.get('raw_content', '')

                if raw_content and len(raw_content) > 100:
                    article_data = {
                        'url': url,
                        'title': result.get('title', url),
                        'text': raw_content,
                        'authors': [],
                        'publish_date': None,
                        'top_image': None,
                    }

                    logger.info(f"Fetched with Tavily: {article_data['title'][:50]}")
                    return article_data

            logger.warning(f"Tavily returned no content for: {url}")
            return None

        except Exception as e:
            logger.error(f"Tavily fetch failed: {e}")
            return None

    def extract_qa_format(self, text: str) -> List[Dict]:
        """
        Extract Q&A format questions from article text
        Looks for patterns like "Q:", "Question:", "Interviewer:", etc.

        Args:
            text: Article text

        Returns:
            List of question dicts with text
        """
        questions = []

        # Common Q&A patterns
        qa_patterns = [
            r'Q:\s*(.+?)(?=\nA:|$)',
            r'Question:\s*(.+?)(?=\nAnswer:|$)',
            r'Interviewer:\s*(.+?)(?=\n[A-Z][a-z]+:|$)',
            r'\*\*Q:\*\*\s*(.+?)(?=\*\*A:\*\*|$)',
            r'\*\*Question:\*\*\s*(.+?)(?=\*\*Answer:\*\*|$)',
        ]

        for pattern in qa_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            for match in matches:
                question_text = match.group(1).strip()

                # Clean up the question
                question_text = re.sub(r'\s+', ' ', question_text)

                if question_text and len(question_text.split()) >= 5:
                    # Ensure it ends with question mark
                    if not question_text.endswith('?'):
                        question_text += '?'

                    questions.append({
                        'text': question_text,
                        'extraction_method': 'qa_format'
                    })

        logger.info(f"Extracted {len(questions)} Q&A format questions")
        return questions

    def extract_questions_from_text(self, text: str) -> List[Dict]:
        """
        Extract questions from article text using heuristics + LLM

        Args:
            text: Article text

        Returns:
            List of question dicts
        """
        # First try Q&A format extraction
        qa_questions = self.extract_qa_format(text)

        if qa_questions:
            # If Q&A format found, prioritize these
            return qa_questions

        # Otherwise, use general question extractor
        potential_questions = self.question_extractor.extract_questions_heuristic(text)

        if not potential_questions:
            return []

        # Refine with LLM
        refined_questions = self.question_extractor.refine_questions_with_llm(potential_questions)

        questions = [{'text': q, 'extraction_method': 'heuristic'} for q in refined_questions]

        logger.info(f"Extracted {len(questions)} questions from article text")
        return questions

    def process_article(
        self,
        url: str,
        celebrity_name: str
    ) -> List[Dict]:
        """
        Process a single article and extract questions

        Args:
            url: URL of the article
            celebrity_name: Name of the celebrity

        Returns:
            List of extracted questions with full metadata
        """
        logger.info(f"Processing article: {url}")

        # Step 1: Fetch article
        article_data = self.fetch_article(url)
        if not article_data:
            return []

        # Step 2: Extract questions
        questions = self.extract_questions_from_text(article_data['text'])

        if not questions:
            logger.warning(f"No questions found in article: {url}")
            return []

        # Step 3: Add metadata
        publish_date = article_data.get('publish_date')
        if publish_date:
            if isinstance(publish_date, datetime):
                date_str = publish_date.strftime('%Y-%m-%d')
            else:
                date_str = str(publish_date)
        else:
            date_str = None

        for question in questions:
            question['celebrity_name'] = celebrity_name
            question['source_type'] = 'article'
            question['source_url'] = url
            question['source_title'] = article_data['title']
            question['date'] = date_str
            question['timestamp'] = None  # Articles don't have timestamps
            question['authors'] = article_data.get('authors', [])

        logger.info(f"Extracted {len(questions)} questions from article")
        return questions

    def search_articles(
        self,
        celebrity_name: str,
        max_results: int = 10
    ) -> List[str]:
        """
        Search for interview articles using Google Custom Search + Tavily fallback

        Args:
            celebrity_name: Name of the celebrity
            max_results: Maximum number of results

        Returns:
            List of article URLs
        """
        all_urls = []

        # Method 1: Google Custom Search
        if self.google_search_enabled:
            google_urls = self._search_with_google(celebrity_name, max_results)
            all_urls.extend(google_urls)

        # Method 2: Tavily Search (fallback or supplement)
        if self.tavily_enabled and len(all_urls) < max_results:
            remaining = max_results - len(all_urls)
            tavily_urls = self._search_with_tavily(celebrity_name, remaining)
            # Add URLs not already found
            seen = set(all_urls)
            for url in tavily_urls:
                if url not in seen:
                    all_urls.append(url)
                    seen.add(url)

        if not all_urls:
            logger.warning(f"No articles found for {celebrity_name}")
            if not self.google_search_enabled and not self.tavily_enabled:
                logger.info("Configure GOOGLE_API_KEY/GOOGLE_CSE_ID or TAVILY_API_KEY in .env")

        logger.info(f"Total found: {len(all_urls)} article URLs")
        return all_urls[:max_results]

    def _search_with_google(
        self,
        celebrity_name: str,
        max_results: int = 10
    ) -> List[str]:
        """Search for articles using Google Custom Search API"""
        if not self.google_search_enabled:
            return []

        logger.info(f"Google Search: {celebrity_name} interview articles...")

        try:
            service = build("customsearch", "v1", developerKey=self.google_api_key)

            search_queries = [
                f'{celebrity_name} interview',
                f'{celebrity_name} Q&A',
            ]

            all_urls = []
            seen_urls = set()

            for query in search_queries:
                logger.info(f"  Query: {query}")

                result = service.cse().list(
                    q=query,
                    cx=self.google_cse_id,
                    num=min(max_results, 10)
                ).execute()

                if 'items' in result:
                    for item in result['items']:
                        url = item.get('link')
                        title = item.get('title', '')
                        snippet = item.get('snippet', '')

                        if url and url not in seen_urls:
                            content = (title + ' ' + snippet).lower()
                            if any(keyword in content for keyword in ['interview', 'q&a', 'talks', 'conversation', 'sits down', 'speaks', 'discusses']):
                                all_urls.append(url)
                                seen_urls.add(url)
                                logger.info(f"    Found: {title[:60]}...")

                if len(all_urls) >= max_results:
                    break

            logger.info(f"Google found {len(all_urls)} URLs")
            return all_urls[:max_results]

        except Exception as e:
            logger.error(f"Google search error: {e}")
            return []

    def _search_with_tavily(
        self,
        celebrity_name: str,
        max_results: int = 10
    ) -> List[str]:
        """
        Search for interview articles using Tavily Search API
        Tavily provides high-quality search results optimized for LLMs
        """
        if not self.tavily_api_key:
            return []

        logger.info(f"Tavily Search: {celebrity_name} interview articles...")

        try:
            tavily_url = "https://api.tavily.com/search"

            search_queries = [
                f'{celebrity_name} interview article',
                f'{celebrity_name} Q&A interview',
            ]

            all_urls = []
            seen_urls = set()

            for query in search_queries:
                logger.info(f"  Query: {query}")

                payload = {
                    "api_key": self.tavily_api_key,
                    "query": query,
                    "search_depth": "advanced",
                    "include_domains": [],  # No domain restrictions
                    "exclude_domains": ["youtube.com", "twitter.com", "facebook.com", "instagram.com"],  # Exclude social media
                    "max_results": min(max_results, 10)
                }

                response = requests.post(
                    tavily_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=30
                )
                response.raise_for_status()

                data = response.json()

                if data.get('results'):
                    for result in data['results']:
                        url = result.get('url')
                        title = result.get('title', '')
                        content = result.get('content', '')

                        if url and url not in seen_urls:
                            # Filter for interview content
                            text = (title + ' ' + content).lower()
                            if any(keyword in text for keyword in ['interview', 'q&a', 'talks', 'conversation', 'sits down', 'speaks', 'discusses']):
                                all_urls.append(url)
                                seen_urls.add(url)
                                logger.info(f"    Found: {title[:60]}...")

                if len(all_urls) >= max_results:
                    break

                time.sleep(0.5)  # Rate limiting

            logger.info(f"Tavily found {len(all_urls)} URLs")
            return all_urls[:max_results]

        except Exception as e:
            logger.error(f"Tavily search error: {e}")
            return []

    def search_and_fetch_with_tavily(
        self,
        celebrity_name: str,
        max_results: int = 5
    ) -> List[Dict]:
        """
        COMBINED: Search AND fetch article content in one Tavily call
        More efficient when Tavily is the primary search method

        Args:
            celebrity_name: Name of the celebrity
            max_results: Maximum number of articles

        Returns:
            List of article data dicts with content already fetched
        """
        if not self.tavily_api_key:
            logger.warning("Tavily API not configured")
            return []

        logger.info(f"Tavily search+fetch for: {celebrity_name}")

        try:
            tavily_url = "https://api.tavily.com/search"

            query = f'{celebrity_name} interview article Q&A'

            payload = {
                "api_key": self.tavily_api_key,
                "query": query,
                "search_depth": "advanced",
                "include_raw_content": True,  # Get full article content
                "exclude_domains": ["youtube.com", "twitter.com", "facebook.com", "instagram.com"],
                "max_results": max_results
            }

            response = requests.post(
                tavily_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=60
            )
            response.raise_for_status()

            data = response.json()
            articles = []

            if data.get('results'):
                for result in data['results']:
                    raw_content = result.get('raw_content', '')
                    content = result.get('content', '')

                    # Use raw_content if available, otherwise use content
                    text = raw_content if raw_content and len(raw_content) > len(content) else content

                    if text and len(text) > 100:
                        article_data = {
                            'url': result.get('url'),
                            'title': result.get('title', 'Unknown'),
                            'text': text,
                            'authors': [],
                            'publish_date': None,
                            'top_image': None,
                        }
                        articles.append(article_data)
                        logger.info(f"  Got: {article_data['title'][:60]}...")

            logger.info(f"Tavily returned {len(articles)} articles with content")
            return articles

        except Exception as e:
            logger.error(f"Tavily search+fetch error: {e}")
            return []

    def ingest_from_urls(
        self,
        celebrity_name: str,
        urls: List[str]
    ) -> List[Dict]:
        """
        Ingest multiple articles from a list of URLs

        Args:
            celebrity_name: Name of the celebrity
            urls: List of article URLs

        Returns:
            List of all extracted questions
        """
        logger.info(f"Starting article ingestion for: {celebrity_name}")
        logger.info(f"Processing {len(urls)} articles")

        all_questions = []

        for idx, url in enumerate(urls):
            logger.info(f"Processing article {idx+1}/{len(urls)}")
            questions = self.process_article(url, celebrity_name)
            all_questions.extend(questions)

        logger.info(f"Article ingestion complete: {len(all_questions)} total questions from {len(urls)} articles")

        return all_questions

    def ingest_with_search(
        self,
        celebrity_name: str,
        max_articles: int = 10
    ) -> List[Dict]:
        """
        Search for articles AND ingest them automatically
        WITH: Tavily combined search+fetch for better success rate

        Args:
            celebrity_name: Name of the celebrity
            max_articles: Maximum number of articles to process

        Returns:
            List of all extracted questions
        """
        logger.info(f"Starting automatic article search and ingestion for: {celebrity_name}")

        all_questions = []
        processed_urls = set()

        # Method 1: Try Tavily combined search+fetch first (most reliable)
        if self.tavily_enabled:
            logger.info("Trying Tavily search+fetch (combined)...")
            tavily_articles = self.search_and_fetch_with_tavily(celebrity_name, max_articles)

            for article_data in tavily_articles:
                if article_data['url'] in processed_urls:
                    continue
                processed_urls.add(article_data['url'])

                # Extract questions directly from fetched content
                questions = self._extract_questions_from_article_data(article_data, celebrity_name)
                all_questions.extend(questions)

            if all_questions:
                logger.info(f"Tavily search+fetch: {len(all_questions)} questions from {len(tavily_articles)} articles")

        # Method 2: If we need more, search and fetch separately
        if len(all_questions) < 5 and len(processed_urls) < max_articles:
            remaining = max_articles - len(processed_urls)
            logger.info(f"Searching for {remaining} more articles...")

            urls = self.search_articles(celebrity_name, max_results=remaining)

            # Filter out already processed URLs
            new_urls = [url for url in urls if url not in processed_urls]

            if new_urls:
                more_questions = self.ingest_from_urls(celebrity_name, new_urls)
                all_questions.extend(more_questions)

        if not all_questions:
            logger.warning(f"No questions extracted for {celebrity_name}")

        logger.info(f"Total: {len(all_questions)} questions from articles")
        return all_questions

    def _extract_questions_from_article_data(
        self,
        article_data: Dict,
        celebrity_name: str
    ) -> List[Dict]:
        """
        Extract questions from pre-fetched article data

        Args:
            article_data: Dict with 'url', 'title', 'text'
            celebrity_name: Name of the celebrity

        Returns:
            List of question dicts with metadata
        """
        if not article_data.get('text'):
            return []

        # Extract questions
        questions = self.extract_questions_from_text(article_data['text'])

        if not questions:
            return []

        # Add metadata
        publish_date = article_data.get('publish_date')
        if publish_date:
            if isinstance(publish_date, datetime):
                date_str = publish_date.strftime('%Y-%m-%d')
            else:
                date_str = str(publish_date)
        else:
            date_str = None

        for question in questions:
            question['celebrity_name'] = celebrity_name
            question['source_type'] = 'article'
            question['source_url'] = article_data['url']
            question['source_title'] = article_data['title']
            question['date'] = date_str
            question['timestamp'] = None
            question['authors'] = article_data.get('authors', [])

        logger.info(f"Extracted {len(questions)} questions from: {article_data['title'][:50]}")
        return questions


if __name__ == "__main__":
    # Test article ingester
    import sys
    from dotenv import load_dotenv
    
    load_dotenv()

    if len(sys.argv) > 1:
        celebrity = sys.argv[1]
    else:
        celebrity = "Keanu Reeves"

    ingester = ArticleIngester()

    # Test search functionality
    print(f"\n{'='*60}")
    print(f"Testing Article Search for: {celebrity}")
    print('='*60)

    urls = ingester.search_articles(celebrity, max_results=5)
    
    print(f"\nFound {len(urls)} article URLs:")
    for i, url in enumerate(urls, 1):
        print(f"{i}. {url}")

    # Optionally process the articles
    if urls:
        user_input = input("\nProcess these articles? (y/n): ")
        if user_input.lower() == 'y':
            questions = ingester.ingest_from_urls(celebrity, urls)
            print(f"\nExtracted {len(questions)} total questions")
            
            if questions:
                print("\nSample questions:")
                for q in questions[:5]:
                    print(f"\n- {q['text']}")
                    print(f"  Source: {q['source_title']}")