import os
import feedparser
import time
from atproto import Client
from datetime import datetime, timezone
import json
import hashlib
import re

# First, let's fix the NLTK setup
def setup_nltk():
    import nltk
    # Download necessary NLTK data with explicit paths
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)

# Create a simpler hashtag generation function that doesn't rely on external APIs
def extract_relevant_hashtags(text):
    # Common words to filter out
    common_words = {
        'the', 'and', 'for', 'that', 'this', 'with', 'from', 'have', 'has', 'had',
        'are', 'were', 'was', 'will', 'would', 'could', 'should', 'been', 'being',
        'said', 'says', 'according', 'like', 'just', 'now', 'get', 'one', 'two',
        'three', 'new', 'time', 'year', 'years', 'day', 'days', 'week', 'weeks',
        'month', 'months', 'today', 'tomorrow', 'yesterday', 'say', 'said', 'says',
        'told', 'report', 'reported', 'reports', 'people', 'person', 'man', 'woman',
        'men', 'women', 'they', 'their', 'them', 'what', 'when', 'where', 'why',
        'how', 'who', 'which', 'there', 'here', 'than', 'then', 'some', 'more',
        'most', 'many', 'much', 'such', 'only', 'very', 'also', 'but', 'not',
        'can', 'about', 'into', 'over', 'after', 'before', 'between', 'under',
        'during', 'through', 'above', 'below', 'since', 'until', 'while'
    }

    # Simple word extraction without NLTK
    # Convert to lowercase and split by non-alphanumeric characters
    words = re.findall(r'\b[a-zA-Z0-9]{4,}\b', text.lower())

    # Filter out common words and short words
    relevant_words = [word for word in words if
                     word not in common_words and
                     len(word) > 3 and
                     not word.isdigit()]

    # Return unique words
    return list(set(relevant_words))

def generate_hashtags(title, description):
    # Combine title and description for better context
    full_text = f"{title} {description}"

    # Extract relevant words
    relevant_words = extract_relevant_hashtags(full_text)

    # Convert to hashtags (take up to 5)
    hashtags = [f"#{word}" for word in relevant_words[:5]]

    # If we don't have enough hashtags, add some generic ones based on the RSS feed topic
    if len(hashtags) < 3:
        generic_tags = ["#ClimateChange", "#Environment", "#ClimateAction",
                        "#ClimateNews", "#GlobalWarming"]
        hashtags.extend(generic_tags[:5-len(hashtags)])

    return hashtags[:5]  # Ensure we return at most 5 hashtags

def load_posted_entries():
    try:
        with open('posted_entries.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_posted_entries(posted):
    with open('posted_entries.json', 'w') as f:
        json.dump(posted, f)

def create_bluesky_post(entry, hashtags):
    title = entry.get('title', '')
    link = entry.get('link', '')

    # Create post content with title and hashtags
    # The link will be added as a facet (hyperlink) later
    content = f"{title}\n\n{link}\n\n{' '.join(hashtags)}"

    # Ensure content doesn't exceed Bluesky's character limit (300)
    if len(content) > 300:
        # Truncate title if necessary
        available_space = 300 - len(link) - len(' '.join(hashtags)) - 4  # 4 for newlines
        title = title[:available_space] + '...'
        content = f"{title}\n\n{link}\n\n{' '.join(hashtags)}"

    return content

def post_to_bluesky(client, content, link):
    # Find the position of the link in the content
    link_start = content.find(link)

    if link_start != -1:
        # Create a facet (hyperlink) for the URL
        facets = [
            {
                "index": {
                    "byteStart": link_start,
                    "byteEnd": link_start + len(link)
                },
                "features": [
                    {
                        "$type": "app.bsky.richtext.facet#link",
                        "uri": link
                    }
                ]
            }
        ]

        # Post with the facet to create a hyperlink
        return client.send_post(text=content, facets=facets)
    else:
        # Fallback if link not found in content
        return client.send_post(text=content)

def main():
    try:
        # Initialize Bluesky client
        client = Client()
        client.login(os.environ['BLUESKY_HANDLE'], os.environ['BLUESKY_PASSWORD'])

        # RSS feed URL - replace with your desired RSS feed
        rss_url = "https://www.theguardian.com/environment/climate-crisis/rss"

        # Load previously posted entries
        posted_entries = load_posted_entries()

        # Parse RSS feed
        feed = feedparser.parse(rss_url)

        for entry in feed.entries:
            # Create unique identifier for entry
            entry_id = hashlib.md5(entry.link.encode()).hexdigest()

            # Skip if already posted
            if entry_id in posted_entries:
                continue

            # Generate hashtags using our simplified method
            hashtags = generate_hashtags(
                entry.title,
                entry.get('description', '')
            )

            # Create post content
            content = create_bluesky_post(entry, hashtags)

            try:
                # Post to Bluesky with hyperlinked URL
                post_to_bluesky(client, content, entry.link)

                # Save entry as posted
                posted_entries[entry_id] = {
                    'title': entry.title,
                    'date_posted': datetime.now(timezone.utc).isoformat(),
                    'hashtags': hashtags
                }

                print(f"Successfully posted: {entry.title}")
                print(f"Generated hashtags: {' '.join(hashtags)}")

                # Wait between posts to avoid rate limiting
                time.sleep(2)

            except Exception as e:
                print(f"Error posting {entry.title}: {str(e)}")

        # Save updated posted entries
        save_posted_entries(posted_entries)

    except Exception as e:
        print(f"Fatal error: {str(e)}")
        raise

if __name__ == "__main__":
    main()
