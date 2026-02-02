"""
YouTube Ingestion Pipeline
Downloads and processes YouTube interviews using yt-dlp
Extracts audio, transcribes, and extracts questions
"""

import yt_dlp
import os
from typing import List, Dict, Optional
import logging
from datetime import datetime
from transcription.whisper_transcriber import get_transcriber
from processing.question_extractor import get_question_extractor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class YouTubeIngester:
    """
    Ingests YouTube interviews for a celebrity
    Uses ytsearch to find relevant interviews
    """

    def __init__(self, download_dir: str = "data/downloads/youtube"):
        self.download_dir = download_dir
        os.makedirs(download_dir, exist_ok=True)
        self.transcriber = get_transcriber()
        # 🔴 CRITICAL: use_llm=True (NO LLM for extraction per constraints)
        self.question_extractor = get_question_extractor(use_llm=True)

    def search_videos(
        self,
        celebrity_name: str,
        max_results: int = 10
    ) -> List[Dict]:
        """
        Search for celebrity interviews on YouTube

        Args:
            celebrity_name: Name of the celebrity
            max_results: Maximum number of videos to find

        Returns:
            List of video metadata dicts
        """
        search_query = f"ytsearch{max_results}:{celebrity_name} interview podcast"

        logger.info(f"Searching YouTube for: {celebrity_name}")

        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,  # Don't download, just get metadata
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                result = ydl.extract_info(search_query, download=False)

                if 'entries' not in result:
                    logger.warning("No videos found")
                    return []

                videos = []
                for entry in result['entries']:
                    if entry:
                        video_info = {
                            'video_id': entry.get('id'),
                            'title': entry.get('title'),
                            'url': entry.get('url') or f"https://youtube.com/watch?v={entry.get('id')}",
                            'duration': entry.get('duration'),
                            'upload_date': entry.get('upload_date'),
                            'channel': entry.get('channel'),
                            'view_count': entry.get('view_count'),
                        }
                        videos.append(video_info)

                logger.info(f"Found {len(videos)} videos")
                return videos

        except Exception as e:
            logger.error(f"Error searching YouTube: {e}")
            return []

    def download_audio(
        self,
        video_url: str,
        video_id: str
    ) -> Optional[str]:
        """
        Download audio from YouTube video

        Args:
            video_url: URL of the video
            video_id: Video ID for naming

        Returns:
            Path to downloaded audio file, or None if failed
        """
        output_path = os.path.join(self.download_dir, f"{video_id}.wav")

        # Skip if already downloaded
        if os.path.exists(output_path):
            logger.info(f"Audio already exists: {output_path}")
            return output_path

        logger.info(f"Downloading audio: {video_id}")

        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
            }],
            'outtmpl': os.path.join(self.download_dir, f"{video_id}.%(ext)s"),
            'quiet': True,
            'no_warnings': True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])

            if os.path.exists(output_path):
                logger.info(f"Audio downloaded: {output_path}")
                return output_path
            else:
                logger.error(f"Download failed: {output_path} not found")
                return None

        except Exception as e:
            logger.error(f"Error downloading audio: {e}")
            return None

    def process_video(
        self,
        video_info: Dict,
        celebrity_name: str
    ) -> List[Dict]:
        """
        Download, transcribe, and extract questions from a video

        Args:
            video_info: Video metadata dict
            celebrity_name: Name of the celebrity

        Returns:
            List of extracted questions with metadata
        """
        video_id = video_info['video_id']
        video_url = video_info['url']
        video_title = video_info['title']

        logger.info(f"Processing video: {video_title}")

        # Step 1: Download audio
        audio_path = self.download_audio(video_url, video_id)
        if not audio_path:
            return []

        # Step 2: Transcribe
        try:
            logger.info(f"Transcribing video: {video_id}")

            # Use chunking for long videos (>30 minutes)
            duration = video_info.get('duration', 0)
            if duration > 1800:  # 30 minutes
                transcript_data = self.transcriber.transcribe_with_chunking(audio_path)
            else:
                transcript_data = self.transcriber.transcribe_audio(audio_path)

        except Exception as e:
            logger.error(f"Error transcribing video: {e}")
            return []

        # Step 3: Extract questions
        try:
            logger.info(f"Extracting questions from: {video_id}")
            questions = self.question_extractor.extract_from_transcript(
                transcript_data,
                use_segments=True
            )

            # Add source metadata
            upload_date = video_info.get('upload_date')
            if upload_date:
                try:
                    date_str = datetime.strptime(upload_date, '%Y%m%d').strftime('%Y-%m-%d')
                except:
                    date_str = upload_date
            else:
                date_str = None

            for question in questions:
                question['celebrity_name'] = celebrity_name
                question['source_type'] = 'youtube'
                question['source_url'] = self.transcriber.get_timestamped_url(
                    video_url,
                    question.get('timestamp', 0),
                    'youtube'
                )
                question['source_title'] = video_title
                question['date'] = date_str
                question['video_id'] = video_id

            logger.info(f"Extracted {len(questions)} questions from {video_title}")
            return questions

        except Exception as e:
            logger.error(f"Error extracting questions: {e}")
            return []

    def ingest_celebrity(
        self,
        celebrity_name: str,
        max_videos: int = 10
    ) -> List[Dict]:
        """
        Full ingestion pipeline for a celebrity

        Args:
            celebrity_name: Name of the celebrity
            max_videos: Maximum number of videos to process

        Returns:
            List of all extracted questions
        """
        logger.info(f"Starting YouTube ingestion for: {celebrity_name}")

        # Step 1: Search for videos
        videos = self.search_videos(celebrity_name, max_videos)

        if not videos:
            logger.warning(f"No videos found for {celebrity_name}")
            return []

        # Step 2: Process each video
        all_questions = []

        for idx, video in enumerate(videos):
            logger.info(f"Processing video {idx+1}/{len(videos)}")
            questions = self.process_video(video, celebrity_name)
            all_questions.extend(questions)

        logger.info(f"YouTube ingestion complete: {len(all_questions)} total questions from {len(videos)} videos")

        return all_questions

    def cleanup_audio(self, video_id: str):
        """Delete downloaded audio file to save space"""
        audio_path = os.path.join(self.download_dir, f"{video_id}.wav")
        if os.path.exists(audio_path):
            os.remove(audio_path)
            logger.info(f"Cleaned up audio: {video_id}")


if __name__ == "__main__":
    # Test YouTube ingester
    import sys

    if len(sys.argv) > 1:
        celebrity = sys.argv[1]
    else:
        celebrity = "Keanu Reeves"

    ingester = YouTubeIngester()

    # Search only (don't process)
    videos = ingester.search_videos(celebrity, max_results=5)

    print(f"\nFound {len(videos)} videos for {celebrity}:")
    for video in videos[:5]:
        print(f"\n- {video['title']}")
        print(f"  URL: {video['url']}")
        print(f"  Duration: {video.get('duration', 0) // 60} minutes")
