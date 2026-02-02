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
    WITH FALLBACK: YouTube search for podcast-style interviews
    """

    # Popular podcast RSS feeds that commonly feature celebrity interviews
    POPULAR_PODCASTS = [
        # Long-form interview podcasts
        "https://feeds.megaphone.fm/the-tim-ferriss-show",
        "https://feeds.simplecast.com/54nAGcIl",  # Lex Fridman Podcast
        "https://joeroganexp.joerogan.libsynpro.com/rss",  # Joe Rogan Experience
        "https://www.omnycontent.com/d/playlist/aaea4e69-af51-495e-afc9-a9760146922b/14a43378-edb2-49be-8511-ab0d000a7030/d1b9612f-bb1b-4b85-9c0e-ab0d004ab37a/podcast.rss",  # Armchair Expert
        "https://feeds.simplecast.com/wgl4xEgL",  # SmartLess
        "https://rss.art19.com/conan-obrien-needs-a-friend",  # Conan O'Brien
        "https://feeds.megaphone.fm/HSW7835889191",  # WTF with Marc Maron
        "https://feeds.simplecast.com/dHoohVNH",  # Off Camera with Sam Jones
        "https://feeds.acast.com/public/shows/happy-sad-confused",  # Happy Sad Confused
        "https://feeds.npr.org/510053/podcast.xml",  # NPR Fresh Air
        # Entertainment focused
        "https://feeds.megaphone.fm/entdaily",  # Entertainment Weekly
        "https://rss.art19.com/variety-awards-circuit",  # Variety Awards Circuit
        "https://feeds.megaphone.fm/hollywoodreporter",  # Hollywood Reporter
    ]

    def __init__(self, download_dir: str = "data/downloads/podcasts"):
        self.download_dir = download_dir
        os.makedirs(download_dir, exist_ok=True)
        self.transcriber = get_transcriber()
        self.question_extractor = get_question_extractor(use_llm=True)

    def _name_matches(self, celebrity_name: str, text: str) -> bool:
        """
        Check if celebrity name matches text with flexible matching
        Handles partial matches (first name, last name, common variations)
        """
        celebrity_lower = celebrity_name.lower().strip()
        text_lower = text.lower()

        # Exact full name match
        if celebrity_lower in text_lower:
            return True

        # Split name into parts
        name_parts = celebrity_lower.split()

        if len(name_parts) >= 2:
            # Check if both first AND last name appear (not necessarily together)
            first_name = name_parts[0]
            last_name = name_parts[-1]

            # Both names must appear for partial match
            if first_name in text_lower and last_name in text_lower:
                return True

            # Check for "Last, First" format
            if f"{last_name}, {first_name}" in text_lower:
                return True

            # Last name alone only if it's distinctive (>4 chars)
            if len(last_name) > 4 and last_name in text_lower:
                # Verify it's not a common word
                common_words = {'smith', 'brown', 'jones', 'white', 'black', 'green', 'young', 'king', 'hill'}
                if last_name not in common_words:
                    return True

        return False

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

        for feed_url in rss_feeds:
            try:
                logger.info(f"Checking feed: {feed_url}")

                # Add timeout and headers
                feed = feedparser.parse(
                    feed_url,
                    request_headers={'User-Agent': 'Mozilla/5.0 (compatible; PodcastBot/1.0)'}
                )

                if feed.bozo and not feed.entries:
                    logger.warning(f"Feed error for {feed_url}: {feed.get('bozo_exception', 'Unknown error')}")
                    continue

                podcast_title = feed.feed.get('title', 'Unknown Podcast')

                for entry in feed.entries:
                    # Check if celebrity is mentioned in title or description
                    title = entry.get('title', '')
                    description = entry.get('description', entry.get('summary', ''))
                    combined_text = f"{title} {description}"

                    if self._name_matches(celebrity_name, combined_text):
                        # Find audio enclosure - try multiple approaches
                        audio_url = None

                        # Method 1: Standard enclosures
                        for enclosure in entry.get('enclosures', []):
                            enc_type = enclosure.get('type', '')
                            if 'audio' in enc_type or enc_type.startswith('audio/'):
                                audio_url = enclosure.get('href') or enclosure.get('url')
                                break

                        # Method 2: Check links for audio
                        if not audio_url:
                            for link in entry.get('links', []):
                                if 'audio' in link.get('type', ''):
                                    audio_url = link.get('href')
                                    break

                        # Method 3: Check media content
                        if not audio_url:
                            media_content = entry.get('media_content', [])
                            for media in media_content:
                                if 'audio' in media.get('type', ''):
                                    audio_url = media.get('url')
                                    break

                        if not audio_url:
                            logger.debug(f"No audio URL found for episode: {title[:50]}")
                            continue

                        # Extract metadata
                        episode_info = {
                            'title': entry.get('title'),
                            'description': description[:500] if description else '',
                            'audio_url': audio_url,
                            'published': entry.get('published', entry.get('pubDate')),
                            'podcast_title': podcast_title,
                            'episode_url': entry.get('link'),
                            'duration': entry.get('itunes_duration'),
                        }

                        episodes.append(episode_info)
                        logger.info(f"  Found episode: {title[:60]}...")

                        if len(episodes) >= max_episodes:
                            break

            except Exception as e:
                logger.error(f"Error parsing feed {feed_url}: {e}")
                continue

            if len(episodes) >= max_episodes:
                break

        logger.info(f"Found {len(episodes)} relevant podcast episodes from RSS")
        return episodes[:max_episodes]

    def search_youtube_podcasts(
        self,
        celebrity_name: str,
        max_results: int = 5
    ) -> List[Dict]:
        """
        FALLBACK: Search YouTube for podcast-style interviews
        Uses yt-dlp to search for podcast interviews

        Args:
            celebrity_name: Name of the celebrity
            max_results: Maximum number of results

        Returns:
            List of episode metadata dicts compatible with podcast format
        """
        logger.info(f"YouTube fallback: Searching for {celebrity_name} podcast interviews")

        try:
            import yt_dlp

            search_queries = [
                f"{celebrity_name} podcast interview",
                f"{celebrity_name} full interview",
                f"{celebrity_name} long form interview",
            ]

            episodes = []
            seen_urls = set()

            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
                'force_generic_extractor': False,
            }

            for query in search_queries:
                if len(episodes) >= max_results:
                    break

                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        search_url = f"ytsearch{max_results}:{query}"
                        result = ydl.extract_info(search_url, download=False)

                        if not result or 'entries' not in result:
                            continue

                        for entry in result['entries']:
                            if not entry:
                                continue

                            video_url = entry.get('url') or f"https://www.youtube.com/watch?v={entry.get('id')}"

                            if video_url in seen_urls:
                                continue
                            seen_urls.add(video_url)

                            # Filter for longer videos (likely full interviews)
                            duration = entry.get('duration', 0) or 0
                            if duration < 300:  # Skip videos under 5 minutes
                                continue

                            episode_info = {
                                'title': entry.get('title', 'Unknown'),
                                'description': entry.get('description', '')[:500],
                                'audio_url': video_url,  # Will be processed by YouTube ingester
                                'published': entry.get('upload_date'),
                                'podcast_title': f"YouTube - {entry.get('uploader', 'Unknown Channel')}",
                                'episode_url': video_url,
                                'duration': duration,
                                'source': 'youtube_fallback'
                            }

                            episodes.append(episode_info)
                            logger.info(f"  Found YouTube: {entry.get('title', '')[:60]}...")

                            if len(episodes) >= max_results:
                                break

                except Exception as e:
                    logger.debug(f"YouTube search query failed: {e}")
                    continue

            logger.info(f"YouTube fallback found {len(episodes)} podcast-style interviews")
            return episodes

        except ImportError:
            logger.warning("yt-dlp not installed, YouTube fallback unavailable")
            return []
        except Exception as e:
            logger.error(f"YouTube fallback search failed: {e}")
            return []

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
        max_episodes: int = 5,
        use_youtube_fallback: bool = True
    ) -> List[Dict]:
        """
        Full ingestion pipeline from RSS feeds WITH YOUTUBE FALLBACK

        Args:
            celebrity_name: Name of the celebrity
            rss_feeds: List of RSS feed URLs
            max_episodes: Maximum number of episodes to process
            use_youtube_fallback: If True, search YouTube when RSS finds nothing

        Returns:
            List of all extracted questions
        """
        logger.info(f"Starting podcast ingestion for: {celebrity_name}")

        # Step 1: Search for episodes in RSS feeds
        episodes = self.search_podcast_episodes(
            celebrity_name,
            rss_feeds,
            max_episodes
        )

        # Step 2: FALLBACK - If no RSS episodes found, try YouTube
        if not episodes and use_youtube_fallback:
            logger.info(f"No RSS episodes found, trying YouTube fallback...")
            episodes = self.search_youtube_podcasts(celebrity_name, max_episodes)

        if not episodes:
            logger.warning(f"No podcast episodes found for {celebrity_name} (RSS + YouTube)")
            return []

        # Step 3: Process each episode
        all_questions = []

        for idx, episode in enumerate(episodes):
            logger.info(f"Processing episode {idx+1}/{len(episodes)}")

            # Handle YouTube fallback episodes differently
            if episode.get('source') == 'youtube_fallback':
                questions = self._process_youtube_episode(episode, celebrity_name)
            else:
                questions = self.process_episode(episode, celebrity_name)

            all_questions.extend(questions)

        logger.info(f"Podcast ingestion complete: {len(all_questions)} total questions from {len(episodes)} episodes")

        return all_questions

    def _process_youtube_episode(
        self,
        episode_info: Dict,
        celebrity_name: str
    ) -> List[Dict]:
        """
        Process a YouTube podcast episode
        Downloads audio and extracts questions

        Args:
            episode_info: Episode metadata from YouTube search
            celebrity_name: Name of the celebrity

        Returns:
            List of extracted questions
        """
        try:
            import yt_dlp

            video_url = episode_info['audio_url']
            episode_title = episode_info['title']

            logger.info(f"Processing YouTube episode: {episode_title[:60]}...")

            # Create safe filename
            safe_title = "".join(c for c in episode_title if c.isalnum() or c in (' ', '-', '_'))[:50]
            file_hash = hashlib.md5(video_url.encode()).hexdigest()[:8]
            output_path = os.path.join(self.download_dir, f"{safe_title}_{file_hash}")

            # Download audio with yt-dlp
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': f"{output_path}.%(ext)s",
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'quiet': True,
                'no_warnings': True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])

            audio_path = f"{output_path}.mp3"

            if not os.path.exists(audio_path):
                logger.error(f"Audio download failed for: {episode_title}")
                return []

            # Transcribe
            logger.info(f"Transcribing YouTube podcast: {episode_title[:50]}...")
            transcript_data = self.transcriber.transcribe_with_chunking(
                audio_path,
                chunk_length_ms=300000
            )

            # Extract questions
            logger.info(f"Extracting questions from: {episode_title[:50]}...")
            questions = self.question_extractor.extract_from_transcript(
                transcript_data,
                use_segments=True
            )

            # Add metadata
            for question in questions:
                question['celebrity_name'] = celebrity_name
                question['source_type'] = 'youtube_podcast'
                question['source_url'] = video_url
                question['source_title'] = f"{episode_info['podcast_title']} - {episode_title}"
                question['date'] = episode_info.get('published')

            logger.info(f"Extracted {len(questions)} questions from YouTube: {episode_title[:50]}")
            return questions

        except ImportError:
            logger.error("yt-dlp not installed for YouTube processing")
            return []
        except Exception as e:
            logger.error(f"Error processing YouTube episode: {e}")
            return []

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
