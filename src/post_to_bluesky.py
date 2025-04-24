import os
import time
import hashlib
import feedparser
import json
import re
from datetime import datetime, timezone
from atproto import Client
import traceback
import google.generativeai as genai

# --- Helper Functions ---
def load_posted_entries():
    try:
        if os.path.exists('posted_entries.json'):
            with open('posted_entries.json', 'r') as f:
                return json.load(f)
        else:
            print("posted_entries.json not found, starting fresh.")
            return {}
    except Exception as e:
        print(f"Error loading posted entries: {str(e)}")
        return {}

def save_posted_entries(posted_entries):
    try:
        with open('posted_entries.json', 'w') as f:
            json.dump(posted_entries, f, indent=2)
    except Exception as e:
        print(f"Error saving posted entries: {str(e)}")

def generate_keyword_hashtags(title, description):
    """Generates 3 relevant hashtags using Gemini API or a fallback."""
    # List of words that should never be hashtags
    banned_words = {
        'article', 'news', 'report', 'story', 'update', 'read', 'more', 'about', 'from',
        'with', 'this', 'that', 'these', 'those', 'there', 'their', 'they', 'them',
        'what', 'when', 'where', 'which', 'who', 'whom', 'whose', 'why', 'how',
        'have', 'has', 'had', 'having', 'been', 'being', 'some', 'same', 'such',
        'time', 'year', 'people', 'world', 'make', 'just', 'know', 'take', 'into',
        'your', 'some', 'could', 'would', 'should', 'than', 'then', 'now', 'look',
        'only', 'come', 'over', 'think', 'also', 'back', 'after', 'use', 'two',
        'first', 'last', 'long', 'great', 'little', 'very', 'much', 'good', 'new'
    }

    # Get API key from environment variable
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        print("Warning: GEMINI_API_KEY not found in environment variables. Using basic hashtag generation.")
        # Fall back to basic hashtag generation
        return basic_hashtag_generation(title, description, banned_words)

    try:
        # Configure the Gemini API
        genai.configure(api_key=api_key)

        # Select the model
        model = genai.GenerativeModel('gemini-pro')

        # Combine title and description, clean up HTML
        text = f"Title: {title}\n\nContent: {description}"
        text = re.sub(r'<[^>]+>', '', text) # Basic HTML stripping

        # Create the prompt for Gemini
        prompt = f"""
        Analyze this climate news article and generate exactly 3 relevant hashtags.

        Article:
        {text}

        Instructions:
        1. Focus on specific climate topics mentioned in the article
        2. Make hashtags concise and relevant to climate discourse
        3. Format as CamelCase (e.g., ClimateAction, RenewableEnergy)
        4. Avoid generic terms like "Climate" alone
        5. NEVER use these words as hashtags (even as part of compound words): article, news, report, story, update, read, more, about, from, with, this, that, these, those
        6. Return ONLY the 3 hashtags as a comma-separated list, nothing else

        Example output format: RenewableEnergy,CarbonCapture,ClimatePolicy
        """

        # Generate response from Gemini
        print(f"Generating hashtags for: '{title}' using Gemini...")
        response = model.generate_content(prompt)

        # Extract and process hashtags
        hashtags_text = response.text.strip()

        # Split by commas and clean up
        hashtags = [tag.strip() for tag in hashtags_text.split(',') if tag.strip()]

        # Ensure proper formatting and filter banned words
        formatted_hashtags = []
        for tag in hashtags:
            # Remove # if present
            if tag.startswith('#'):
                tag = tag[1:]

            # Ensure CamelCase
            if tag and not tag[0].isupper():
                tag = tag[0].upper() + tag[1:]

            # Check if tag contains any banned words
            tag_lower = tag.lower()
            is_banned = False
            for banned in banned_words:
                if banned.lower() == tag_lower or banned.lower() in tag_lower:
                    is_banned = True
                    break
            if not is_banned and tag:
                formatted_hashtags.append(tag)

        # If we got fewer than 3 valid hashtags, add defaults
        default_hashtags = ['ClimateAction', 'ClimateJustice', 'ClimateChange', 'GlobalWarming', 'Sustainability']
        while len(formatted_hashtags) < 3 and default_hashtags:
            default_tag = default_hashtags.pop(0)
            if default_tag not in formatted_hashtags:
                formatted_hashtags.append(default_tag)

        final_hashtags = formatted_hashtags[:3] # Ensure exactly 3 hashtags
        print(f"Gemini generated hashtags: {final_hashtags}")
        return final_hashtags

    except Exception as e:
        print(f"Error using Gemini for hashtag generation: {str(e)}")
        print("Falling back to basic hashtag generation.")
        # Fall back to basic hashtag generation
        return basic_hashtag_generation(title, description, banned_words)

def basic_hashtag_generation(title, description, banned_words):
    """Fallback method if Gemini API fails or is not configured."""
    print(f"Using basic hashtag generation for: '{title}'")
    # Climate-specific relevant terms to prioritize
    climate_terms = {
        'climate', 'carbon', 'emission', 'emissions', 'warming', 'global',
        'renewable', 'sustainability', 'sustainable', 'environment', 'environmental',
        'green', 'energy', 'solar', 'wind', 'hydro', 'biodiversity', 'conservation',
        'pollution', 'fossil', 'fuel', 'methane', 'co2', 'greenhouse', 'temperature',
        'ocean', 'sea', 'level', 'ice', 'glacier', 'arctic', 'antarctic', 'drought',
        'flood', 'wildfire', 'hurricane', 'storm', 'extreme', 'weather', 'policy',
        'agreement', 'paris', 'ipcc', 'net', 'zero', 'adaptation', 'mitigation',
        'resilience', 'justice', 'crisis', 'emergency', 'action', 'activism'
    }

    # Default climate hashtags
    default_hashtags = ['ClimateAction', 'ClimateJustice', 'ClimateChange', 'GlobalWarming', 'Sustainability']

    # Try to extract some basic keywords
    text = f"{title} {description}"
    text = re.sub(r'<[^>]+>', '', text) # Basic HTML stripping
    words = re.findall(r'\b\w+\b', text.lower())

    # Filter words
    filtered_words = [
        word for word in words
        if word in climate_terms
        and word not in banned_words
        and len(word) > 3
    ]

    # Create hashtags from climate terms found in the article
    hashtags = []
    processed_words = set()
    for word in filtered_words:
        if len(hashtags) >= 3:
            break
        if word not in processed_words:
            hashtags.append(word.capitalize())
            processed_words.add(word)

    # Add default hashtags if needed
    while len(hashtags) < 3 and default_hashtags:
        default_tag = default_hashtags.pop(0)
        if default_tag not in hashtags and default_tag.lower() not in processed_words:
            hashtags.append(default_tag)

    final_hashtags = hashtags[:3]
    print(f"Basic generated hashtags: {final_hashtags}")
    return final_hashtags

def create_post_with_facets(client, entry_title, entry_link, hashtags_keywords):
    """Creates a post with clickable link and hashtags using facets."""
    try:
        # Create the post text
        # Format: Title + "Read more" (which will be the clickable link) + hashtags
        title_text = entry_title
        link_text = "\n\nRead more"

        # Add hashtags with # prefix
        hashtag_section = "\n\n"
        hashtags_with_prefix = [f"#{tag}" for tag in hashtags_keywords]
        hashtag_text = " ".join(hashtags_with_prefix)

        # Full post text
        full_text = title_text + link_text + hashtag_section + hashtag_text

        # Initialize facets list
        facets = []

        # Calculate byte positions for the link
        title_bytes = title_text.encode('utf-8')
        link_text_bytes = link_text.encode('utf-8')

        # The link starts after the title
        link_start = len(title_bytes)
        # The link ends after the link text
        link_end = link_start + len(link_text_bytes)

        # Add link facet
        facets.append({
            "index": {
                "byteStart": link_start,
                "byteEnd": link_end
            },
            "features": [{
                "$type": "app.bsky.richtext.facet#link",
                "uri": entry_link
            }]
        })

        # Calculate byte positions for each hashtag
        # First, get the byte position where hashtags start
        content_before_hashtags = title_text + link_text + hashtag_section
        hashtag_start_pos = len(content_before_hashtags.encode('utf-8'))

        # Track current position
        current_pos = hashtag_start_pos

        # Add facet for each hashtag
        for hashtag in hashtags_with_prefix:
            # The hashtag itself (with #)
            hashtag_bytes = hashtag.encode('utf-8')
            hashtag_length = len(hashtag_bytes)

            # Add facet for this hashtag
            facets.append({
                "index": {
                    "byteStart": current_pos,
                    "byteEnd": current_pos + hashtag_length
                },
                "features": [{
                    "$type": "app.bsky.richtext.facet#tag",
                    "tag": hashtag[1:]  # Remove # prefix for the tag value
                }]
            })

            # Move position past this hashtag and the space after it
            current_pos += hashtag_length
            if current_pos < len(full_text.encode('utf-8')):
                # Add space if not the last hashtag
                current_pos += 1  # 1 byte for space

        print(f"Post text ({len(full_text)} chars):\n{full_text}")
        print(f"Created {len(facets)} facets: 1 link + {len(hashtags_keywords)} hashtags")

        # Post to Bluesky with the facets
        response = client.send_post(
            text=full_text,
            facets=facets
        )

        return response

    except Exception as e:
        print(f"Error creating post with facets: {str(e)}")
        traceback.print_exc()

        # Fall back to simple post without facets
        print("Falling back to simple post without clickable elements...")
        simple_text = f"{entry_title}\n\n{entry_link}\n\n" + " ".join([f"#{tag}" for tag in hashtags_keywords])
        return client.send_post(text=simple_text)

# --- Main Function ---
def main():
    print("--- Script starting ---")
    try:
        # Check for required environment variables
        bluesky_handle = os.environ.get('BLUESKY_HANDLE')
        bluesky_password = os.environ.get('BLUESKY_PASSWORD')

        if not bluesky_handle or not bluesky_password:
            print("Error: BLUESKY_HANDLE and BLUESKY_PASSWORD environment variables must be set.")
            return

        # Initialize Bluesky client
        client = Client()
        print(f"Attempting Bluesky login for handle: {bluesky_handle}...")
        client.login(bluesky_handle, bluesky_password)
        print("Bluesky login successful!")

        # --- List of RSS feed URLs ---
        rss_urls = [
            "https://www.theguardian.com/environment/climate-crisis/rss",
            "https://www.nature.com/nclimate.rss"
        ]

        posted_entries = load_posted_entries()
        print(f"Loaded {len(posted_entries)} previously posted entries.")

        new_posts_count = 0
        for rss_url in rss_urls:
            print(f"\n--- Processing feed: {rss_url} ---")
            try:
                feed = feedparser.parse(rss_url)
                if not feed.entries:
                    print("No entries found in this feed.")
                    continue

                print(f"Found {len(feed.entries)} entries in feed.")
                for entry in feed.entries:
                    entry_title = entry.get('title', 'No Title Provided').strip()
                    entry_link = entry.get('link', '')
                    entry_desc = entry.get('description', entry.get('summary', ''))

                    if not entry_link:
                        print(f"Skipping entry with no link: '{entry_title}'")
                        continue

                    # Use link as the unique identifier
                    entry_id = hashlib.md5(entry_link.encode()).hexdigest()

                    if entry_id in posted_entries:
                        print(f"Skipping (already posted): {entry_title}")
                        continue

                    print(f"\nAttempting to post: {entry_title}")

                    # Generate custom hashtags
                    hashtags_keywords = generate_keyword_hashtags(entry_title, entry_desc)

                    try:
                        # Create and post with clickable link and hashtags
                        response = create_post_with_facets(
                            client,
                            entry_title,
                            entry_link,
                            hashtags_keywords
                        )

                        # Record successful post
                        posted_entries[entry_id] = {
                            'title': entry_title,
                            'link': entry_link,
                            'date_posted': datetime.now(timezone.utc).isoformat(),
                            'hashtags': [f"#{tag}" for tag in hashtags_keywords],
                            'post_uri': getattr(response, 'uri', 'Unknown URI')
                        }
                        new_posts_count += 1

                        print(f"Successfully posted: {entry_title}")
                        print(f"Post URI: {posted_entries[entry_id]['post_uri']}")
                        print(f"Generated hashtags: {' '.join([f'#{tag}' for tag in hashtags_keywords])}")

                        # Save after each successful post
                        save_posted_entries(posted_entries)

                        # Wait between posts
                        time.sleep(5)

                    except Exception as post_error:
                        print(f"Error posting '{entry_title}': {str(post_error)}")
                        traceback.print_exc()

            except Exception as feed_error:
                print(f"Error processing feed {rss_url}: {str(feed_error)}")
                traceback.print_exc()

        print(f"\n--- Feed processing complete. Posted {new_posts_count} new entries. ---")

    except Exception as e:
        print(f"Fatal error: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
