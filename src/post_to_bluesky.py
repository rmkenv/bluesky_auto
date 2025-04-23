import os
import feedparser
import time
from atproto import Client
from datetime import datetime, timezone
import json
import hashlib
import re
from collections import Counter # Import Counter for frequency counting

# --- Expanded Stopword List ---
# Added more common verbs, prepositions, conjunctions, articles, pronouns, etc.
COMMON_WORDS = {
    'a', 'about', 'above', 'after', 'again', 'against', 'all', 'also', 'am', 'an', 'and', 'any', 'are', 'aren',
    'as', 'at', 'be', 'because', 'been', 'before', 'being', 'below', 'between', 'both', 'but', 'by', 'can',
    'cannot', 'could', 'couldn', 'did', 'didn', 'do', 'does', 'doesn', 'doing', 'don', 'down', 'during', 'each',
    'few', 'for', 'from', 'further', 'had', 'hadn', 'has', 'hasn', 'have', 'haven', 'having', 'he', 'her', 'here',
    'hers', 'herself', 'him', 'himself', 'his', 'how', 'i', 'if', 'in', 'into', 'is', 'isn', 'it', 'its', 'itself',
    'just', 'like', 'made', 'make', 'many', 'may', 'me', 'might', 'more', 'most', 'must', 'my', 'myself', 'new',
    'no', 'nor', 'not', 'now', 'of', 'off', 'on', 'once', 'only', 'or', 'other', 'our', 'ours', 'ourselves',
    'out', 'over', 'own', 'people', 'per', 'put', 're', 'report', 'reports', 'reported', 'said', 'same', 'say',
    'says', 'see', 'seen', 'shan', 'she', 'should', 'shouldn', 'since', 'so', 'some', 'such', 'than', 'that',
    'the', 'their', 'theirs', 'them', 'themselves', 'then', 'there', 'these', 'they', 'this', 'those', 'through',
    'time', 'to', 'too', 'told', 'under', 'until', 'up', 'upon', 'us', 'use', 'used', 'uses', 'very', 'via',
    'want', 'was', 'wasn', 'we', 'well', 'were', 'weren', 'what', 'when', 'where', 'which', 'while', 'who', 'whom',
    'why', 'will', 'with', 'won', 'would', 'wouldn', 'year', 'years', 'yes', 'yet', 'you', 'your', 'yours',
    'yourself', 'yourselves', 'according', 'get', 'one', 'two', 'three', 'day', 'days', 'week', 'weeks', 'month',
    'months', 'today', 'tomorrow', 'yesterday', 'man', 'woman', 'men', 'women', 'first', 'last', 'next', 'back',
    'even', 'found', 'give', 'go', 'going', 'got', 'high', 'key', 'know', 'latest', 'less', 'long', 'look', 'low',
    'news', 'part', 'post', 'public', 'read', 'set', 'show', 'still', 'take', 'think', 'top', 'update', 'way',
    'work'
}

# --- Improved Hashtag Generation ---
def generate_keyword_hashtags(title, description, num_hashtags=5):
    """Generates hashtags based on keyword frequency and title priority."""
    if not description:
        description = "" # Ensure description is a string

    full_text = f"{title} {description}"
    title_text = title

    # 1. Clean and tokenize text
    # Remove punctuation (except internal hyphens/apostrophes if needed, here simplified)
    # Keep alphanumeric and spaces
    clean_text = re.sub(r'[^\w\s]', '', full_text.lower())
    words = clean_text.split()

    clean_title = re.sub(r'[^\w\s]', '', title_text.lower())
    title_words = set(clean_title.split()) # Use set for quick lookup

    # 2. Filter words
    filtered_words = []
    for word in words:
        if len(word) > 3 and word not in COMMON_WORDS and not word.isdigit():
            filtered_words.append(word)

    if not filtered_words:
        # Fallback 1: Try extracting from title only if main text yields nothing
        title_filtered = [w for w in title_words if len(w) > 3 and w not in COMMON_WORDS and not w.isdigit()]
        if title_filtered:
            # Return the longest words from the title as hashtags
            title_filtered.sort(key=len, reverse=True)
            return [w.capitalize() for w in title_filtered[:num_hashtags]] # Capitalize for better look
        else:
            return [] # No usable words found

    # 3. Calculate Term Frequency and boost title words
    word_counts = Counter(filtered_words)
    boosted_counts = Counter()
    for word, count in word_counts.items():
        boost = 2 if word in title_words else 1 # Give double weight if word is in title
        boosted_counts[word] += count * boost

    # 4. Get top N keywords based on boosted frequency
    # Sort by frequency (desc), then alphabetically for tie-breaking
    sorted_keywords = sorted(boosted_counts.items(), key=lambda item: (-item[1], item[0]))

    # 5. Format as hashtags (CamelCase or just Capitalize)
    top_hashtags = []
    for word, count in sorted_keywords:
        # Simple capitalization, could implement CamelCase if needed
        top_hashtags.append(word.capitalize())
        if len(top_hashtags) >= num_hashtags:
            break

    # Fallback 2: If still too few hashtags, add longest title words
    if len(top_hashtags) < 2:
         title_filtered = [w for w in title_words if len(w) > 3 and w not in COMMON_WORDS and not w.isdigit()]
         title_filtered.sort(key=len, reverse=True)
         for word in title_filtered:
             cap_word = word.capitalize()
             if cap_word not in top_hashtags:
                 top_hashtags.append(cap_word)
             if len(top_hashtags) >= num_hashtags:
                 break

    return top_hashtags[:num_hashtags]


# --- Other functions (load_posted_entries, save_posted_entries, create_bluesky_post, create_facets, post_to_bluesky) remain largely the same ---
# Minor adjustments might be needed if capitalization changes affect facet finding, but current logic should handle it.

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
    title = entry.get('title', 'No Title') # Provide default title
    link = entry.get('link', '')

    # Format hashtags with # for display
    formatted_hashtags = [f"#{tag}" for tag in hashtags]

    # Create post content with title, link and hashtags
    content = f"{title}\n\n{link}\n\n{' '.join(formatted_hashtags)}"

    # Ensure content doesn't exceed Bluesky's character limit (300)
    # Using byte length for more accuracy with facets
    content_bytes = content.encode('utf-8')
    if len(content_bytes) > 300:
        # Calculate available space more carefully
        link_len = len(link.encode('utf-8')) if link else 0
        hashtags_len = len(' '.join(formatted_hashtags).encode('utf-8'))
        # Account for newlines (approx 1 byte each) and spacing
        overhead = link_len + hashtags_len + 4
        available_title_bytes = 300 - overhead

        # Truncate title carefully by bytes
        title_bytes = title.encode('utf-8')
        if len(title_bytes) > available_title_bytes:
            # Find the closest byte boundary without cutting a multi-byte character
            limit = available_title_bytes
            while limit > 0 and (title_bytes[limit] & 0xC0) == 0x80: # Check if it's a continuation byte
                limit -= 1
            truncated_title_bytes = title_bytes[:limit]

            try:
                # Decode the truncated bytes safely
                title = truncated_title_bytes.decode('utf-8', errors='ignore') + '...'
            except Exception:
                 # Fallback if decoding fails badly
                 title = title[:max(10, available_title_bytes // 3)] + '...' # Rough estimate

        content = f"{title}\n\n{link}\n\n{' '.join(formatted_hashtags)}"

    return content

def create_facets(content, link, hashtags):
    facets = []
    # Encode content once to work with byte indices consistently
    try:
        content_bytes = content.encode('utf-8')
        content_len_bytes = len(content_bytes)
    except Exception as e:
        print(f"Error encoding content for facet creation: {e}")
        return [] # Cannot create facets without encoded content

    # Add URL facet
    if link: # Only add if link exists
        try:
            link_bytes = link.encode('utf-8')
            # Find link bytes within content bytes
            link_start_byte = -1
            try:
                link_start_byte = content_bytes.find(link_bytes)
            except Exception as find_err:
                 print(f"Error finding link bytes: {find_err}")


            if link_start_byte != -1:
                byte_end = link_start_byte + len(link_bytes)
                # Ensure byteEnd does not exceed content length
                if byte_end <= content_len_bytes:
                    facets.append({
                        "index": {
                            "byteStart": link_start_byte,
                            "byteEnd": byte_end
                        },
                        "features": [
                            {
                                "$type": "app.bsky.richtext.facet#link",
                                "uri": link
                            }
                        ]
                    })
                else:
                    print(f"Warning: Calculated byteEnd for link {link} exceeds content length.")
            # else: # Optional: Warn if link text not found in final content
            #     print(f"Warning: Link text '{link}' not found in post content for facet creation.")

        except Exception as e:
             print(f"Warning: Could not create facet for link {link}: {e}")


    # Add hashtag facets
    for tag in hashtags: # tag is now expected without '#'
        try:
            hashtag_text = f"#{tag}" # Add '#' for searching in content
            hashtag_bytes = hashtag_text.encode('utf-8')
            current_pos = 0
            while current_pos < content_len_bytes:
                # Find next occurrence from current position
                start_byte = content_bytes.find(hashtag_bytes, current_pos)

                if start_byte == -1:
                    break # No more occurrences

                byte_end = start_byte + len(hashtag_bytes)
                # Ensure byteEnd does not exceed content length
                if byte_end <= content_len_bytes:
                    facets.append({
                        "index": {
                            "byteStart": start_byte,
                            "byteEnd": byte_end
                        },
                        "features": [
                            {
                                "$type": "app.bsky.richtext.facet#tag",
                                "tag": tag # Tag value should NOT have '#'
                            }
                        ]
                    })
                else:
                     print(f"Warning: Calculated byteEnd for tag {hashtag_text} exceeds content length.")

                # Move position past the current find to avoid overlap/infinite loop
                current_pos = start_byte + 1 # Check from next byte

        except Exception as e:
            print(f"Warning: Could not create facet for tag #{tag}: {e}")


    return facets

def post_to_bluesky(client, content, link, hashtags):
    # Create facets for both the URL and hashtags
    facets = create_facets(content, link, hashtags) # Pass hashtags without '#'

    # Post with the facets to create hyperlinks
    return client.send_post(text=content, facets=facets)


# --- Main Function ---
def main():
    try:
        # Initialize Bluesky client
        client = Client()
        client.login(os.environ['BLUESKY_HANDLE'], os.environ['BLUESKY_PASSWORD'])

        # List of RSS feed URLs
        rss_urls = [
            "https://www.theguardian.com/environment/climate-crisis/rss",
            "https://feeds.bbci.co.uk/news/technology/rss.xml",
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
                    entry_desc = entry.get('description', entry.get('summary', '')) # Use description or summary

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

                        time.sleep(3)

                    except Exception as post_error:
                        print(f"Error posting '{entry_title}' from {rss_url}: {str(post_error)}")

            except Exception as feed_error:
                print(f"Error processing feed {rss_url}: {str(feed_error)}")
                continue

        save_posted_entries(posted_entries)
        print("\n--- Feed processing complete ---")

    except Exception as e:
        print(f"Fatal error during script execution: {str(e)}")
        raise

if __name__ == "__main__":
    main()
