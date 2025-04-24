import os
import time
import hashlib
import feedparser
import json
import re
from datetime import datetime, timezone
from atproto import Client
import google.generativeai as genai

# --- Helper Functions ---
def load_posted_entries():
    try:
        if os.path.exists('posted_entries.json'):
            with open('posted_entries.json', 'r') as f:
                return json.load(f)
        else:
            return {}  # Return empty dict if file doesn't exist
    except Exception as e:
        print(f"Error loading posted entries: {str(e)}")
        return {}  # Return empty dict on error

def save_posted_entries(posted_entries):
    try:
        with open('posted_entries.json', 'w') as f:
            json.dump(posted_entries, f, indent=2)
    except Exception as e:
        print(f"Error saving posted entries: {str(e)}")

def generate_keyword_hashtags(title, description):
    import google.generativeai as genai
    import os

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
        print("Warning: GEMINI_API_KEY not found in environment variables")
        # Fall back to basic hashtag generation
        return basic_hashtag_generation(title, description, banned_words)

    # Configure the Gemini API
    genai.configure(api_key=api_key)

    # Select the model
    model = genai.GenerativeModel('gemini-pro')

    # Combine title and description, clean up HTML
    text = f"Title: {title}\n\nContent: {description}"
    text = re.sub(r'<[^>]+>', '', text)

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

    try:
        # Generate response from Gemini
        response = model.generate_content(prompt)

        # Extract and process hashtags
        hashtags_text = response.text.strip()

        # Split by commas and clean up
        hashtags = [tag.strip() for tag in hashtags_text.split(',')]

        # Ensure proper formatting and filter banned words
        formatted_hashtags = []
        for tag in hashtags:
            # Remove # if present
            if tag.startswith('#'):
                tag = tag[1:]
            
            # Ensure CamelCase
            if ' ' in tag:
                tag = ''.join(word.capitalize() for word in tag.split())
            elif tag and not tag[0].isupper():
                tag = tag[0].upper() + tag[1:]
            
            # Check if tag contains any banned words
            tag_lower = tag.lower()
            if not any(banned.lower() in tag_lower for banned in banned_words):
                formatted_hashtags.append(tag)

        # If we got fewer than 3 hashtags, add some defaults
        default_hashtags = ['ClimateAction', 'ClimateJustice', 'ClimateChange', 'GlobalWarming', 'Sustainability']
        while len(formatted_hashtags) < 3 and default_hashtags:
            default_tag = default_hashtags.pop(0)
            if default_tag not in formatted_hashtags:
                formatted_hashtags.append(default_tag)

        print(f"Gemini generated hashtags: {formatted_hashtags}")
        return formatted_hashtags[:3]  # Ensure exactly 3 hashtags

    except Exception as e:
        print(f"Error using Gemini for hashtag generation: {str(e)}")
        # Fall back to basic hashtag generation
        return basic_hashtag_generation(title, description, banned_words)

def basic_hashtag_generation(title, description, banned_words):
    """Fallback method if Gemini API fails"""
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
    text = re.sub(r'<[^>]+>', '', text)
    words = re.findall(r'\b\w+\b', text.lower())

    # Filter words
    filtered_words = [
        word for word in words 
        if word in climate_terms 
        and word not in banned_words 
        and len(word) > 4
    ]

    # Create hashtags from climate terms found in the article
    hashtags = []
    for word in set(filtered_words):
        if len(hashtags) >= 3:
            break
        hashtags.append(word.capitalize())

    # Add default hashtags if needed
    while len(hashtags) < 3 and default_hashtags:
        hashtags.append(default_hashtags.pop(0))

    return hashtags[:3]

def create_bluesky_post(entry, hashtags_keywords):
    # Implementation for creating post content
    entry_title = entry.get('title', 'No Title Provided')

    # Create the post content with just the title
    content = f"{entry_title}"

    # Add hashtags at the end
    if hashtags_keywords:
        hashtag_text = ' '.join([f"#{tag}" for tag in hashtags_keywords])
        content += f"\n\n{hashtag_text}"

    return content

def post_to_bluesky(client, content, entry_link, hashtags_keywords):
    # Create a facet for the URL to make it clickable
    facets = []

    # Only add link facet if we have a valid URL
    if entry_link:
        # Find where to put the link in the text
        # We'll add it at the end of the content
        link_text = "\n\nRead more"
        full_content = content + link_text

        # Calculate byte positions for the link
        link_start = len(content.encode('utf-8'))
        link_end = len(full_content.encode('utf-8'))

        # Create the facet for the link
        facets = [{
            "index": {
                "byteStart": link_start,
                "byteEnd": link_end
            },
            "features": [{
                "$type": "app.bsky.richtext.facet#link",
                "uri": entry_link
            }]
        }]
    else:
        full_content = content

    # Post to Bluesky
    response = client.send_post(
        text=full_content,
        facets=facets
    )

    return response

# --- Main Function ---
def main():
    try:
        # Initialize Bluesky client
        client = Client()
        client.login(os.environ['BLUESKY_HANDLE'], os.environ['BLUESKY_PASSWORD'])

        # --- UPDATED: List of RSS feed URLs ---
        rss_urls = [
            "https://www.theguardian.com/environment/climate-crisis/rss",
            "https://www.nature.com/nclimate.rss" # Added Nature Climate Change feed
            # Add more URLs as needed
        ]

        posted_entries = load_posted_entries()

        for rss_url in rss_urls:
            print(f"\n--- Processing feed: {rss_url} ---")
            try:
                feed = feedparser.parse(rss_url)
                if feed.bozo:
                    print(f"Warning: Feed may be ill-formed. Error: {feed.bozo_exception}")

                if not feed.entries:
                    print("No entries found in this feed.")
                    continue

                for entry in feed.entries:
                    entry_title = entry.get('title', 'No Title Provided')
                    entry_link = entry.get('link')
                    # Try getting description, fallback to summary, then empty string
                    entry_desc = entry.get('description', entry.get('summary', ''))

                    if not entry_link:
                        print(f"Skipping entry with no link: '{entry_title}'")
                        continue

                    entry_id = hashlib.md5(entry_link.encode()).hexdigest()

                    if entry_id in posted_entries:
                        continue

                    # --- Use the new keyword hashtag generator ---
                    hashtags_keywords = generate_keyword_hashtags(
                        entry_title,
                        entry_desc # Pass description for better keyword context
                    )

                    if not hashtags_keywords:
                         print(f"Warning: No suitable keywords found for hashtags for entry: '{entry_title}'")
                         # Optionally skip posting if no hashtags, or post without them
                         # continue

                    # Create post content
                    # Pass the generated keywords (without #) to create_bluesky_post
                    content = create_bluesky_post(entry, hashtags_keywords)

                    try:
                        # Pass the generated keywords (without #) to post_to_bluesky
                        post_to_bluesky(client, content, entry_link, hashtags_keywords)

                        posted_entries[entry_id] = {
                            'title': entry_title,
                            'link': entry_link,
                            'date_posted': datetime.now(timezone.utc).isoformat(),
                            'hashtags': [f"#{tag}" for tag in hashtags_keywords] # Store with #
                        }

                        print(f"Successfully posted: {entry_title}")
                        print(f"Generated hashtags: {' '.join([f'#{tag}' for tag in hashtags_keywords])}")

                        time.sleep(3) # Wait between posts

                    except Exception as post_error:
                        print(f"Error posting '{entry_title}' from {rss_url}: {str(post_error)}")

            except Exception as feed_error:
                print(f"Error processing feed {rss_url}: {str(feed_error)}")
                continue # Move to the next feed URL

        save_posted_entries(posted_entries)
        print("\n--- Feed processing complete ---")

    except Exception as e:
        # Catch login errors or other fatal issues
        print(f"Fatal error during script execution: {str(e)}")
        raise

if __name__ == "__main__":
    main()
