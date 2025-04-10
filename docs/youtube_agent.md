# YouTube Metadata Extraction Agent

This agent extracts metadata from YouTube videos, channels, and search results using the YouTube Data API v3.

## Features

- Extract detailed metadata from YouTube videos
- Get channel information and statistics
- Search for videos and extract their metadata
- Retrieve video comments
- Save all extracted data as JSON files
- Find YouTubers in specific niches with subscriber count filtering
- Generate spreadsheet-ready lists of channels for outreach or analysis

## Setup

1. First, you need to obtain YouTube Data API credentials:
   - Go to the [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project
   - Enable the YouTube Data API v3
   - Create credentials (API key and/or OAuth 2.0 client ID)

2. Add your credentials to the `.env` file:
   ```
   YOUTUBE_API_KEY=your_youtube_api_key_here
   YOUTUBE_CLIENT_SECRETS_FILE=path_to_your_client_secrets_file.json
   ```

3. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

### As a module in your code

```python
from src.agents.youtube_agent import YouTubeAgent

# Initialize the agent
youtube_agent = YouTubeAgent()

# Extract metadata from a video
results = youtube_agent.run(video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ")

# Extract metadata from a channel
results = youtube_agent.run(channel_url="https://www.youtube.com/c/GoogleDevelopers")

# Search for videos
results = youtube_agent.run(search_query="machine learning tutorials")

# Find channels in a specific niche with subscriber filtering
channels = youtube_agent.find_channels_by_niche(
    niche="crypto trading",
    min_subscribers=10000,
    max_subscribers=100000
)
```

### From the command line

#### Basic YouTube Data Extraction

```bash
# Extract video metadata
python -m src.agents.youtube_agent video "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# Extract channel metadata
python -m src.agents.youtube_agent channel "https://www.youtube.com/c/GoogleDevelopers"

# Search for videos
python -m src.agents.youtube_agent search "machine learning tutorials"

# Find channels in a specific niche
python -m src.agents.youtube_agent find-channels "crypto trading" 10000 100000
```

#### Using the YouTuber Finder Tool

For more advanced channel searching and list generation, use the dedicated YouTuber Finder script:

```bash
# Basic usage
python -m src.scripts.youtuber_finder "fitness"

# With subscriber range and other options
python -m src.scripts.youtuber_finder "crypto trading" --min-subs 10000 --max-subs 100000 --max-results 100 --verbose

# Save to a specific output file
python -m src.scripts.youtuber_finder "gaming" --output "my_gaming_channels.json"
```

## Data Output

All extracted data is saved in the `youtube_data` directory (configurable) as JSON files:

- Video metadata: `video_{video_id}.json`
- Video comments: `video_{video_id}_comments.json`
- Channel metadata: `channel_{channel_id}.json`
- Channel videos: `channel_{channel_id}_videos.json`
- Search results: `search_{query}.json`
- Channel lists: `channels_{niche}_{min_subs}-{max_subs}.json` and `.csv`

## YouTuber Finder Features

The YouTuber Finder functionality allows you to:

1. Search for channels in any niche or topic
2. Filter by subscriber count (minimum and maximum)
3. Generate both JSON and CSV exports for easy analysis
4. Get detailed channel information including:
   - Subscriber count
   - Total view count
   - Number of videos
   - Country
   - Channel description
   - Creation date
   - Direct YouTube URL

This is perfect for:
- Influencer marketing research
- Competitive analysis
- Content creator outreach
- Niche market research

## Metadata Example

### Video Metadata

```json
{
  "id": "dQw4w9WgXcQ",
  "title": "Rick Astley - Never Gonna Give You Up (Official Music Video)",
  "description": "...",
  "published_at": "2009-10-25T06:57:33Z",
  "channel_id": "UCuAXFkgsw1L7xaCfnd5JJOw",
  "channel_title": "Rick Astley",
  "tags": ["Rick Astley", "Never Gonna Give You Up", ...],
  "category_id": "10",
  "duration": "PT3M33S",
  "view_count": 1234567890,
  "like_count": 12345678,
  "comment_count": 1234567,
  "privacy_status": "public",
  "thumbnails": { ... },
  "extracted_at": "2023-07-05T12:34:56.789Z"
}
```

## Rate Limits

The YouTube Data API has daily quota limits. By default:
- API key: 10,000 units per day
- OAuth 2.0: Higher quotas available

Different API methods consume different quota amounts:
- Simple read operations: 1 unit
- Search operations: 100 units
- Video uploads: 1,600 units

For more details, see the [YouTube Data API Quota Calculator](https://developers.google.com/youtube/v3/determine_quota_cost).

## Error Handling

The agent has built-in error handling for:
- API authentication failures
- Invalid video/channel URLs
- Network errors
- API quota exhaustion

Errors are logged and included in the returned results dictionary. 