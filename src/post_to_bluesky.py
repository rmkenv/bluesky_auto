# --- Main Function ---
def main():
    try:
        # Initialize Bluesky client
        client = Client()
        client.login(os.environ['BLUESKY_HANDLE'], os.environ['BLUESKY_PASSWORD'])

        # --- UPDATED: List of RSS feed URLs ---
        rss_urls = [
            "https://www.theguardian.com/environment/climate-crisis/rss",
            "https://feeds.bbci.co.uk/news/technology/rss.xml",
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
