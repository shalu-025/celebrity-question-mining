"""
Podcast Ingestion Pipeline
Ingests podcasts from RSS feeds
Downloads MP3 audio, transcribes, and extracts questions
"""

import feedparser
import requests
import os
from typing import List, Dict, Optional
import logging
from datetime import datetime
from urllib.parse import urlparse
import hashlib
from transcription.whisper_transcriber import get_transcriber
from processing.question_extractor import get_question_extractor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PodcastIngester:
    """
    Ingests podcasts from RSS feeds
    Searches for episodes mentioning the celebrity
    """

    # Popular podcast RSS feeds to search
    POPULAR_PODCASTS = [
        # Add popular interview podcasts here
        # Users can extend this list or provide custom feeds
    ]

    def __init__(self, download_dir: str = "data/downloads/podcasts"):
        self.download_dir = download_dir
        os.makedirs(download_dir, exist_ok=True)
        self.transcriber = get_transcriber()
        self.question_extractor = get_question_extractor(use_llm=True)

    def search_podcast_episodes(
        self,
        celebrity_name: str,
        rss_feeds: Optional[List[str]] = None,
        max_episodes: int = 5
    ) -> List[Dict]:
        """
        Search for podcast episodes mentioning the celebrity

        Args:
            celebrity_name: Name of the celebrity
            rss_feeds: List of RSS feed URLs to search (if None, uses popular feeds)
            max_episodes: Maximum number of episodes to return

        Returns:
            List of episode metadata dicts
        """
        if rss_feeds is None:
            rss_feeds = self.POPULAR_PODCASTS

        logger.info(f"Searching podcasts for: {celebrity_name}")

        episodes = []
        celebrity_lower = celebrity_name.lower()

        for feed_url in rss_feeds:
            try:
                logger.info(f"Checking feed: {feed_url}")
                feed = feedparser.parse(feed_url)

                podcast_title = feed.feed.get('title', 'Unknown Podcast')

                for entry in feed.entries:
                    # Check if celebrity is mentioned in title or description
                    title = entry.get('title', '').lower()
                    description = entry.get('description', '').lower()
                    summary = entry.get('summary', '').lower()

                    if (celebrity_lower in title or
                        celebrity_lower in description or
                        celebrity_lower in summary):

                        # Find audio enclosure
                        audio_url = None
                        for enclosure in entry.get('enclosures', []):
                            if 'audio' in enclosure.get('type', ''):
                                audio_url = enclosure.get('href')
                                break

                        if not audio_url:
                            continue

                        # Extract metadata
                        episode_info = {
                            'title': entry.get('title'),
                            'description': entry.get('description', entry.get('summary', '')),
                            'audio_url': audio_url,
                            'published': entry.get('published', entry.get('pubDate')),
                            'podcast_title': podcast_title,
                            'episode_url': entry.get('link'),
                            'duration': entry.get('itunes_duration'),
                        }

                        episodes.append(episode_info)

                        if len(episodes) >= max_episodes:
                            break

            except Exception as e:
                logger.error(f"Error parsing feed {feed_url}: {e}")
                continue

            if len(episodes) >= max_episodes:
                break

        logger.info(f"Found {len(episodes)} relevant podcast episodes")
        return episodes[:max_episodes]

    def download_audio(
        self,
        audio_url: str,
        episode_title: str
    ) -> Optional[str]:
        """
        Download podcast audio

        Args:
            audio_url: URL to audio file
            episode_title: Title for naming

        Returns:
            Path to downloaded audio file
        """
        # Create safe filename from title
        safe_title = "".join(c for c in episode_title if c.isalnum() or c in (' ', '-', '_'))[:50]
        file_hash = hashlib.md5(audio_url.encode()).hexdigest()[:8]
        filename = f"{safe_title}_{file_hash}.mp3"
        output_path = os.path.join(self.download_dir, filename)

        # Skip if already downloaded
        if os.path.exists(output_path):
            logger.info(f"Audio already exists: {output_path}")
            return output_path

        logger.info(f"Downloading podcast audio: {episode_title}")

        try:
            response = requests.get(audio_url, stream=True, timeout=30)
            response.raise_for_status()

            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logger.info(f"Downloaded: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Error downloading audio: {e}")
            return None

    def process_episode(
        self,
        episode_info: Dict,
        celebrity_name: str
    ) -> List[Dict]:
        """
        Download, transcribe, and extract questions from a podcast episode

        Args:
            episode_info: Episode metadata dict
            celebrity_name: Name of the celebrity

        Returns:
            List of extracted questions with metadata
        """
        episode_title = episode_info['title']
        audio_url = episode_info['audio_url']

        logger.info(f"Processing episode: {episode_title}")

        # Step 1: Download audio
        audio_path = self.download_audio(audio_url, episode_title)
        if not audio_path:
            return []

        # Step 2: Transcribe (use chunking for long episodes)
        try:
            logger.info(f"Transcribing podcast: {episode_title}")
            transcript_data = self.transcriber.transcribe_with_chunking(
                audio_path,
                chunk_length_ms=300000  # 5 minutes
            )

        except Exception as e:
            logger.error(f"Error transcribing podcast: {e}")
            return []

        # Step 3: Extract questions
        try:
            logger.info(f"Extracting questions from: {episode_title}")
            questions = self.question_extractor.extract_from_transcript(
                transcript_data,
                use_segments=True
            )

            # Add source metadata
            published = episode_info.get('published')
            if published:
                try:
                    date_str = datetime.strptime(published, '%a, %d %b %Y %H:%M:%S %z').strftime('%Y-%m-%d')
                except:
                    date_str = published
            else:
                date_str = None

            for question in questions:
                question['celebrity_name'] = celebrity_name
                question['source_type'] = 'podcast'
                question['source_url'] = episode_info.get('episode_url', audio_url)
                question['source_title'] = f"{episode_info['podcast_title']} - {episode_title}"
                question['date'] = date_str
                question['podcast_title'] = episode_info['podcast_title']

            logger.info(f"Extracted {len(questions)} questions from {episode_title}")
            return questions

        except Exception as e:
            logger.error(f"Error extracting questions: {e}")
            return []

    def ingest_from_feeds(
        self,
        celebrity_name: str,
        rss_feeds: Optional[List[str]] = None,
        max_episodes: int = 5
    ) -> List[Dict]:
        """
        Full ingestion pipeline from RSS feeds

        Args:
            celebrity_name: Name of the celebrity
            rss_feeds: List of RSS feed URLs
            max_episodes: Maximum number of episodes to process

        Returns:
            List of all extracted questions
        """
        logger.info(f"Starting podcast ingestion for: {celebrity_name}")

        # Step 1: Search for episodes
        episodes = self.search_podcast_episodes(
            celebrity_name,
            rss_feeds,
            max_episodes
        )

        if not episodes:
            logger.warning(f"No podcast episodes found for {celebrity_name}")
            return []

        # Step 2: Process each episode
        all_questions = []

        for idx, episode in enumerate(episodes):
            logger.info(f"Processing episode {idx+1}/{len(episodes)}")
            questions = self.process_episode(episode, celebrity_name)
            all_questions.extend(questions)

        logger.info(f"Podcast ingestion complete: {len(all_questions)} total questions from {len(episodes)} episodes")

        return all_questions

    def add_custom_feed(self, feed_url: str):
        """Add a custom RSS feed to search"""
        if feed_url not in self.POPULAR_PODCASTS:
            self.POPULAR_PODCASTS.append(feed_url)
            logger.info(f"Added custom feed: {feed_url}")

    def cleanup_audio(self, audio_path: str):
        """Delete downloaded audio file to save space"""
        if os.path.exists(audio_path):
            os.remove(audio_path)
            logger.info(f"Cleaned up audio: {audio_path}")


if __name__ == "__main__":
    # Test podcast ingester
    import sys

    if len(sys.argv) > 1:
        celebrity = sys.argv[1]
    else:
        celebrity = "Tim Ferriss"

    # Example RSS feeds to test
    test_feeds = [
        "https://feeds.megaphone.fm/the-tim-ferriss-show",  # Example: Tim Ferriss Show
        # Add more podcast RSS feeds here
    ]

    ingester = PodcastIngester()

    # Search only (don't process)
    episodes = ingester.search_podcast_episodes(celebrity, test_feeds, max_episodes=3)

    print(f"\nFound {len(episodes)} episodes mentioning {celebrity}:")
    for episode in episodes:
        print(f"\n- {episode['title']}")
        print(f"  Podcast: {episode['podcast_title']}")
        print(f"  Published: {episode.get('published', 'Unknown')}")
