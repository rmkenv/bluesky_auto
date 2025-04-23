# Bluesky Auto-Poster with Smart Hashtag Generation

Automatically post RSS feed content to Bluesky Social with intelligently generated relevant hashtags using GitHub Actions.

## Features

- 🤖 Automated posting from RSS feeds to Bluesky
- 🏷️ Smart hashtag generation with natural language processing
- 🔗 Properly hyperlinked URLs and clickable hashtags
- 🔄 Runs on schedule (configurable)
- 📝 Tracks posted content to avoid duplicates
- ⚡ Easy setup using GitHub Actions
- 🛡️ Robust error handling and fallback mechanisms

## Setup

### Prerequisites

- A Bluesky account
- A GitHub account
- An RSS feed to monitor

### Installation

1. **Fork this repository**

2. **Set up environment secrets**

   Go to your repository's Settings > Secrets and variables > Actions:
   - Add the following repository secrets:
     - `BLUESKY_HANDLE`: Your Bluesky handle (without @)
     - `BLUESKY_PASSWORD`: Your Bluesky password

3. **Configure RSS Feed**

   Edit `src/post_to_bluesky.py` and replace the RSS feed URL: 
   rss_url = "https://your-rss-feed-url.com/feed"

4. **Enable GitHub Actions**

   Go to Actions tab in your repository and enable workflows.

## How It Works

1. The GitHub Action runs on schedule (configurable in `.github/workflows/bluesky-poster.yml`)
2. It fetches new posts from your RSS feed
3. For each new post:
   - Extracts and filters relevant terms for hashtags
   - Creates a Bluesky post with the title, properly hyperlinked URL, and interactive hashtags
   - Tracks posted content to avoid duplicates
4. Changes are committed back to the repository

## Configuration

### Modifying Schedule

Edit the cron schedule in `.github/workflows/bluesky-poster.yml`:
```yaml
on:
  schedule:
    - cron: '0 */4 * * *'  # Runs every 4 hours
```

### Customizing Post Format

Edit the `create_bluesky_post` function in `src/post_to_bluesky.py` to modify how posts appear.

### Customizing Hashtag Generation

Modify the `extract_relevant_hashtags` function to adjust which words are filtered out or included in hashtag generation.

## Files

- `src/post_to_bluesky.py`: Main script for posting to Bluesky
- `.github/workflows/bluesky-poster.yml`: GitHub Actions workflow
- `requirements.txt`: Python dependencies
- `posted_entries.json`: Tracks posted content (auto-generated)

## Dependencies

- atproto: Bluesky API client
- feedparser: RSS feed parser

## Troubleshooting

1. **Posts not appearing?**
   - Check the Actions tab for error logs
   - Verify your Bluesky credentials
   - Ensure RSS feed URL is correct

2. **Hashtags not clickable?**
   - Ensure you're using the latest version of the code
   - Check that facets are properly configured

3. **Workflow not running?**
   - Ensure GitHub Actions is enabled
   - Check if the repository secrets are properly configured
   - Verify workflow file syntax

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the GPL 3 - see the LICENSE file for details.

## Acknowledgments

- Bluesky Social for the platform
- The open source community for libraries and tools
