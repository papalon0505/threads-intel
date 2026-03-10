"""Example: Scrape a Threads profile and print posts."""

from threads_intel import scrape_threads

result = scrape_threads("https://www.threads.net/@zuck", delay=False)

print(f"Profile: {result['profile_summary']}")
print(f"Posts found: {result['posts_found']}\n")

for post in result["posts"][:5]:
    print(f"@{post.get('username', '?')}: {post['text'][:100]}")
    print(f"  Likes: {post.get('like_count', '?')} | {post.get('published_on', '')}")
    if post.get("url"):
        print(f"  Link: {post['url']}")
    print()
