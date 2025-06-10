import requests
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

from tome.command import tome_command
from tome.api.output import TomeOutput
from tome.errors import TomeException
from rich.console import Console
from rich.progress import Progress

# --- Helper Functions ---

def fetch_item(item_id):
    """Fetches details for a single Hacker News item."""
    try:
        url = f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        # Return an error structure for this specific item
        return {"id": item_id, "error": str(e)}

def get_domain(url_string):
    """Extracts the domain from a URL."""
    if not url_string:
        return "self.hackernews"
    try:
        return urlparse(url_string).netloc.replace("www.", "")
    except:
        return "N/A"

# --- Tome Command Formatters ---

def hn_top_text_formatter(data):
    """Text formatter for Hacker News top stories."""
    output = TomeOutput(stdout=True)
    error_output = TomeOutput() # For warnings/errors to stderr

    if data.get("status") == "error":
        raise TomeException(data.get("error", "An unknown error occurred."))
    
    stories = data.get("stories", [])
    if not stories:
        output.info("No stories found.")
        return

    output.info(f"[bold magenta]Top {len(stories)} Hacker News Stories:[/bold magenta]")
    for i, story in enumerate(stories, 1):
        if story.get("error"):
            error_output.warning(f"{i}. [Skipped] Could not fetch story ID {story.get('id')}: {story.get('error')}")
            continue

        score = story.get('score', 0)
        title = story.get('title', 'No Title')
        author = story.get('by', 'N/A')
        comments = story.get('descendants', 0)
        domain = get_domain(story.get('url'))
        
        # Color coding based on score
        score_color = "green" if score > 200 else "yellow" if score > 50 else "default"
        
        output.print(f"\n[bold]{i}. {title}[/bold] [dim]({domain})[/dim]")
        output.print(f"   [{score_color}]{score} points[/] by [cyan]{author}[/cyan] | [blue]{comments} comments[/]")
        output.print(f"   [dim]HN Link: https://news.ycombinator.com/item?id={story.get('id')}[/dim]")
        if story.get('url'):
            output.print(f"   [dim]URL: {story.get('url')}[/dim]")


def hn_top_json_formatter(data):
    """JSON formatter for Hacker News top stories."""
    output = TomeOutput(stdout=True)
    output.print_json(json.dumps(data, indent=2))
    if data.get("status") == "error": 
        raise TomeException(data.get("error", "An unknown error occurred."))

# --- Tome Command Definition ---

@tome_command(formatters={"text": hn_top_text_formatter, "json": hn_top_json_formatter})
def hn_top(tome_api, parser, *args):
    """
    Fetches the top stories from Hacker News.
    Requires the 'requests' library to be installed.
    """
    parser.add_argument(
        '-l', '--limit',
        type=int,
        default=10,
        help="Number of top stories to display (default: 10)."
    )
    parsed_args = parser.parse_args(*args)

    if parsed_args.limit <= 0:
        return {"status": "success", "stories": []} # Return empty list if limit is zero or less

    try:
        # 1. Fetch top story IDs
        top_stories_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
        response = requests.get(top_stories_url, timeout=10)
        response.raise_for_status()
        top_story_ids = response.json()

        # 2. Fetch story details concurrently for speed
        story_ids_to_fetch = top_story_ids[:parsed_args.limit]
        stories_details = []

        with Progress(console=Console(stderr=True)) as progress:
            task = progress.add_task("[cyan]Fetching stories...", total=len(story_ids_to_fetch))
            with ThreadPoolExecutor(max_workers=10) as executor:
                future_to_id = {executor.submit(fetch_item, story_id): story_id for story_id in story_ids_to_fetch}
                for future in as_completed(future_to_id):
                    stories_details.append(future.result())
                    progress.update(task, advance=1)
        
        # Sort results by original ranking because concurrency makes order unpredictable
        id_map = {story['id']: story for story in stories_details}
        sorted_stories = [id_map[story_id] for story_id in story_ids_to_fetch if story_id in id_map]

        return {"status": "success", "stories": sorted_stories}

    except requests.exceptions.RequestException as e:
        return {"status": "error", "error": f"Failed to connect to Hacker News API: {e}"}
