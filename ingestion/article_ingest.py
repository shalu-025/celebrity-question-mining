"""
Article Ingestion Pipeline - WITH GOOGLE SEARCH IMPLEMENTATION
Extracts questions from written interview articles
"""

from newspaper import Article
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import logging
import re
from datetime import datetime
import os
from googleapiclient.discovery import build
from processing.question_extractor import get_question_extractor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ArticleIngester:
    """
    Ingests interview articles from the web
    Extracts Q&A format interviews and standalone questions
    NOW WITH AUTOMATIC SEARCH!
    """

    def __init__(self):
        self.question_extractor = get_question_extractor(use_llm=True)
        
        # Load Google API credentials
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.google_cse_id = os.getenv("GOOGLE_CSE_ID")
        
        if self.google_api_key and self.google_cse_id:
            self.search_enabled = True
            logger.info("Google Custom Search enabled")
        else:
            self.search_enabled = False
            logger.warning("Google API credentials not found - search disabled")

    def fetch_article(self, url: str) -> Optional[Dict]:
        """
        Fetch and parse an article from a URL

        Args:
            url: URL of the article

        Returns:
            Dict containing article metadata and text
        """
        logger.info(f"Fetching article: {url}")

        try:
            # Use newspaper3k for article extraction
            article = Article(url)
            article.download()
            article.parse()

            article_data = {
                'url': url,
                'title': article.title,
                'text': article.text,
                'authors': article.authors,
                'publish_date': article.publish_date,
                'top_image': article.top_image,
            }

            logger.info(f"Fetched article: {article.title}")
            return article_data

        except Exception as e:
            logger.error(f"Error fetching article with newspaper3k: {e}")

            # Fallback to basic requests + BeautifulSoup
            try:
                response = requests.get(url, timeout=15)
                response.raise_for_status()

                soup = BeautifulSoup(response.content, 'lxml')

                # Try to extract title
                title = soup.find('h1')
                title_text = title.get_text(strip=True) if title else url

                # Extract main text
                # Remove script and style elements
                for script in soup(['script', 'style']):
                    script.decompose()

                # Get text from common article containers
                article_text = ""
                for container in soup.find_all(['article', 'div'], class_=re.compile(r'(article|content|post|entry)')):
                    article_text += container.get_text(separator='\n', strip=True)

                if not article_text:
                    article_text = soup.get_text(separator='\n', strip=True)

                article_data = {
                    'url': url,
                    'title': title_text,
                    'text': article_text,
                    'authors': [],
                    'publish_date': None,
                    'top_image': None,
                }

                logger.info(f"Fetched article (fallback): {title_text}")
                return article_data

            except Exception as e2:
                logger.error(f"Error fetching article with fallback: {e2}")
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
        Search for interview articles using Google Custom Search API

        Args:
            celebrity_name: Name of the celebrity
            max_results: Maximum number of results (max 10 per query)

        Returns:
            List of article URLs
        """
        if not self.search_enabled:
            logger.warning("Google Custom Search not configured")
            logger.info("Set GOOGLE_API_KEY and GOOGLE_CSE_ID in .env file")
            return []

        logger.info(f"Searching for {celebrity_name} interview articles...")

        try:
            # Build the search service
            service = build("customsearch", "v1", developerKey=self.google_api_key)

            # Craft search query
            search_queries = [
                f'{celebrity_name} interview',
                f'{celebrity_name} Q&A',
            ]

            all_urls = []
            seen_urls = set()

            for query in search_queries:
                logger.info(f"Query: {query}")
                
                # Execute search (max 10 results per query)
                result = service.cse().list(
                    q=query,
                    cx=self.google_cse_id,
                    num=min(max_results, 10)  # Google CSE max is 10
                ).execute()

                # Extract URLs
                if 'items' in result:
                    for item in result['items']:
                        url = item.get('link')
                        title = item.get('title', '')
                        snippet = item.get('snippet', '')

                        # Filter for actual interview articles
                        if url and url not in seen_urls:
                            # Basic filter for interview content
                            content = (title + ' ' + snippet).lower()
                            if any(keyword in content for keyword in ['interview', 'q&a', 'talks', 'conversation', 'sits down']):
                                all_urls.append(url)
                                seen_urls.add(url)
                                logger.info(f"  Found: {title[:60]}...")

                if len(all_urls) >= max_results:
                    break

            logger.info(f"Found {len(all_urls)} article URLs")
            return all_urls[:max_results]

        except Exception as e:
            logger.error(f"Error searching articles: {e}")
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

        Args:
            celebrity_name: Name of the celebrity
            max_articles: Maximum number of articles to process

        Returns:
            List of all extracted questions
        """
        logger.info(f"Starting automatic article search and ingestion for: {celebrity_name}")

        # Step 1: Search for article URLs
        urls = self.search_articles(celebrity_name, max_results=max_articles)

        if not urls:
            logger.warning(f"No articles found for {celebrity_name}")
            return []

        # Step 2: Ingest the found articles
        return self.ingest_from_urls(celebrity_name, urls)


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