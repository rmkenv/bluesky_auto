import os
import feedparser  # You'll need to install this: pip install feedparser
import time
from atproto import Client  # You'll need to install this: pip install atproto
from datetime import datetime, timezone
import json
import hashlib
import google.generativeai as genai  # You'll need to install this: pip install google-generativeai
import re
import nltk  # You'll need to install this: pip install nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

def setup_gemini():
    genai.configure(api_key=os.environ['GEMINI_API_KEY'])
    model = genai.GenerativeModel('gemini-pro')
    return model

def load_posted_entries():
    try:
        with open('posted_entries.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_posted_entries(posted):
    with open('posted_entries.json', 'w') as f:
        json.dump(posted, f)

def setup_nltk():
    # Download necessary NLTK data
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt', quiet=True)

    try:
        nltk.data.find('corpora/stopwords')
    except LookupError:
        nltk.download('stopwords', quiet=True)

def extract_relevant_hashtags(text):
    # Tokenize text
    words = word_tokenize(text.lower())

    # Get stopwords
    stop_words = set(stopwords.words('english'))

    # Additional words to filter out (common words, articles, etc.)
    additional_filters = {
        'said', 'says', 'according', 'like', 'just', 'now', 'get', 'one',
        'two', 'three', 'new', 'time', 'year', 'years', 'day', 'days',
        'week', 'weeks', 'month', 'months', 'today', 'tomorrow', 'yesterday',
        'say', 'said', 'says', 'told', 'report', 'reported', 'reports',
        'people', 'person', 'man', 'woman', 'men', 'women'
    }

    # Combine all filters
    all_filters = stop_words.union(additional_filters)

    # Filter words
    relevant_words = [word for word in words if
                     word.isalnum() and  # Only alphanumeric
                     len(word) > 3 and   # Longer than 3 chars
                     word not in all_filters and  # Not in our filter list
                     not word.isdigit()]  # Not just a number

    # Return unique words
    return list(set(relevant_words))

def generate_hashtags_with_gemini(model, title, description):
    # First try with Gemini
    prompt = f"""
    Generate 5 relevant hashtags for a social media post with the following content:
    Title: {title}
    Description: {description}

    Rules for hashtags:
    1. No spaces in hashtags
    2. Use camelCase for multiple words
    3. Keep them relevant to the content
    4. No special characters except numbers
    5. Avoid common words, names, articles, prepositions
    6. Focus on topic-specific terms and keywords
    7. Return only the hashtags, one per line, starting with #
    """

    try:
        response = model.generate_content(prompt)
        hashtags = response.text.strip().split('\n')

        # Clean and validate hashtags
        cleaned_hashtags = []
        for tag in hashtags:
            # Remove any extra # symbols and spaces
            tag = tag.strip().replace(' ', '')
            if not tag.startswith('#'):
                tag = f"#{tag}"
            # Validate hashtag format
            if re.match(r'^#[a-zA-Z0-9]+$', tag):
                cleaned_hashtags.append(tag)

        # If we got good hashtags from Gemini, return them
        if len(cleaned_hashtags) >= 3:
            return cleaned_hashtags[:5]  # Return maximum 5 hashtags

        # Otherwise fall back to our extraction method
        return fallback_hashtag_generation(title, description)

    except Exception as e:
        print(f"Error generating hashtags with Gemini: {str(e)}")
        # Fallback to our extraction method
        return fallback_hashtag_generation(title, description)

def fallback_hashtag_generation(title, description):
    # Combine title and description for better context
    full_text = f"{title} {description}"

    # Extract relevant words
    relevant_words = extract_relevant_hashtags(full_text)

    # Convert to hashtags (take up to 5)
    hashtags = [f"#{word}" for word in relevant_words[:5]]

    # If we don't have enough hashtags, add some generic ones based on the RSS feed topic
    if len(hashtags) < 3:
        generic_tags = ["#ClimateChange", "#Environment", "#ClimateAction"]
        hashtags.extend(generic_tags[:5-len(hashtags)])

    return hashtags

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
        # Setup NLTK
        setup_nltk()

        # Initialize Gemini
        model = setup_gemini()

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

            # Generate hashtags using Gemini with fallback
            hashtags = generate_hashtags_with_gemini(
                model,
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
