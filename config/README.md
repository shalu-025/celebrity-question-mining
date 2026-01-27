# Celebrity Sources Configuration Guide

This guide explains how to configure article URLs and podcast RSS feeds for ingesting celebrity interview data.

## Configuration File

The configuration is stored in `config/celebrity_sources.json`.

## Structure

```json
{
  "celebrities": {
    "Celebrity Name": {
      "podcast_feeds": [
        "https://example.com/podcast/rss"
      ],
      "article_urls": [
        "https://example.com/interview-article"
      ]
    }
  },
  "default_podcast_feeds": [
    "https://feeds.megaphone.fm/the-tim-ferriss-show"
  ]
}
```

## Adding a New Celebrity

To configure sources for a new celebrity, add an entry under `"celebrities"`:

```json
{
  "celebrities": {
    "New Celebrity": {
      "podcast_feeds": [
        "https://podcast-feed-1.com/rss",
        "https://podcast-feed-2.com/rss"
      ],
      "article_urls": [
        "https://magazine.com/celebrity-interview-1",
        "https://news-site.com/exclusive-interview"
      ]
    }
  }
}
```

## Finding Podcast RSS Feeds

### Popular Interview Podcast Feeds:

1. **The Tim Ferriss Show**
   - RSS: `https://feeds.megaphone.fm/the-tim-ferriss-show`

2. **Joe Rogan Experience**
   - RSS: `https://joeroganexp.joerogan.libsynpro.com/rss`

3. **SmartLess**
   - RSS: `https://feeds.simplecast.com/54nAGcIl`

4. **Armchair Expert**
   - RSS: `https://www.omnycontent.com/d/playlist/aaea4e69-af51-495e-afc9-a9760146922b/14a43378-edb2-49be-8511-ab0d000a7030/d1b9612f-bb1b-4b85-9c0e-ab0d004ab37a/podcast.rss`

5. **WTF with Marc Maron**
   - RSS: `https://feeds.simplecast.com/wgl4xEgL`

### How to Find RSS Feeds:

1. **From Podcast Website**: Look for an RSS icon or "Subscribe via RSS" link
2. **From Apple Podcasts**: Right-click the podcast → Copy Link → Remove `/id` from URL
3. **From Spotify**: Use a tool like `podcastindex.org` to search for the podcast
4. **Browser Extension**: Use extensions like "Get RSS Feed URL" for Chrome/Firefox

## Finding Article URLs

### What Articles to Include:

✅ **Good Sources:**
- Magazine interviews (GQ, Esquire, Rolling Stone, etc.)
- News site interviews (The Guardian, The New York Times, etc.)
- Sports interviews (ESPN, The Athletic, etc.)
- Entertainment interviews (Variety, The Hollywood Reporter, etc.)

❌ **Avoid:**
- Paywalled content (may fail to scrape)
- Video-only content (use YouTube ingestion instead)
- Social media posts (not enough content)

### Example Article URLs:

```json
"article_urls": [
  "https://www.esquire.com/entertainment/movies/a29436579/keanu-reeves-covers-esquire-interview-2019/",
  "https://www.theguardian.com/film/2021/may/16/keanu-reeves-interview-the-matrix-4",
  "https://www.espncricinfo.com/story/virat-kohli-interview-2023"
]
```

## Default Podcast Feeds

The `"default_podcast_feeds"` array contains RSS feeds that will be searched for **any** celebrity if no specific feeds are configured:

```json
"default_podcast_feeds": [
  "https://feeds.megaphone.fm/the-tim-ferriss-show",
  "https://joeroganexp.joerogan.libsynpro.com/rss"
]
```

The system will automatically search these feeds for episodes mentioning the celebrity's name.

## How It Works

### Podcast Ingestion:
1. System loads RSS feeds from config
2. Searches all episodes for celebrity name in title/description
3. Downloads matching episode audio
4. Transcribes audio using Whisper
5. Extracts questions from transcript

### Article Ingestion:
1. System loads article URLs from config
2. Scrapes article content
3. Extracts questions using Q&A pattern matching + LLM
4. Indexes questions with metadata

## Testing Your Configuration

After adding sources, test with:

```bash
python main.py --celebrity "Celebrity Name" --question "test question" --force-ingest
```

The `--force-ingest` flag will trigger re-ingestion and use your configured sources.

## Troubleshooting

### No Podcasts Found
- Verify RSS feed URLs are valid (test in a feed reader)
- Check that celebrity name appears in episode titles/descriptions
- Try adding more popular interview podcast feeds

### Articles Failing to Scrape
- Check if article is behind a paywall
- Verify URL is accessible in a browser
- Some sites may block scrapers (use VPN or alternative sources)

### No Questions Extracted
- Verify content is in interview/Q&A format
- Check that questions are clearly marked (Q:, Question:, etc.)
- Try manually reviewing the article to ensure it contains questions

## Best Practices

1. **Start Small**: Add 2-3 podcast feeds and 2-3 article URLs initially
2. **Quality over Quantity**: Better to have 5 high-quality sources than 20 low-quality ones
3. **Regular Updates**: Check for new interviews and update config periodically
4. **Test First**: Always test with `--force-ingest` after adding new sources
5. **Check Logs**: Review logs to see what was found and what failed

## Example: Full Configuration

```json
{
  "celebrities": {
    "Keanu Reeves": {
      "podcast_feeds": [
        "https://feeds.megaphone.fm/the-tim-ferriss-show",
        "https://feeds.simplecast.com/54nAGcIl",
        "https://joeroganexp.joerogan.libsynpro.com/rss"
      ],
      "article_urls": [
        "https://www.esquire.com/entertainment/movies/a29436579/keanu-reeves-covers-esquire-interview-2019/",
        "https://www.theguardian.com/film/2021/may/16/keanu-reeves-interview-the-matrix-4"
      ]
    },
    "Virat Kohli": {
      "podcast_feeds": [
        "https://anchor.fm/s/rcbpodcast/podcast/rss",
        "https://feeds.megaphone.fm/the-tim-ferriss-show"
      ],
      "article_urls": [
        "https://www.espncricinfo.com/story/virat-kohli-interview-2023",
        "https://www.thehindu.com/sport/cricket/virat-kohli-exclusive-interview/article67890123.ece"
      ]
    }
  },
  "default_podcast_feeds": [
    "https://feeds.megaphone.fm/the-tim-ferriss-show",
    "https://joeroganexp.joerogan.libsynpro.com/rss",
    "https://feeds.simplecast.com/54nAGcIl"
  ]
}
```

## Support

For issues or questions:
- Check logs in `Logging/` directory
- Review extraction results in `data/` directory
- Ensure all dependencies are installed (`pip install -r requirements.txt`)
