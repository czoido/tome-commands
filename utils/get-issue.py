import os
import fnmatch 
import json
import re
import requests 
from datetime import datetime
from urllib.parse import urlparse

from tome.command import tome_command
from tome.api.output import TomeOutput
from tome.errors import TomeException


def parse_github_issue_url(url):
    """
    Parses a GitHub issue URL to extract owner, repo, and issue number.
    """
    parsed_url = urlparse(url)
    if parsed_url.netloc.lower() != 'github.com':
        raise ValueError(f"URL must be from github.com, but received: '{parsed_url.netloc}'")
    
    match = re.match(r'/([^/]+)/([^/]+)/issues/(\d+)/?$', parsed_url.path)
    if not match:
        raise ValueError("Invalid URL format. Expected '/<owner>/<repo>/issues/<issue_number>'.")
    
    owner, repo, issue_number_str = match.groups()
    return {"owner": owner, "repo": repo, "issue_number": int(issue_number_str)}

def format_github_timestamp(timestamp_str):
    """Converts GitHub ISO 8601 timestamp to a readable format."""
    try:
        dt_object = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        return dt_object.strftime('%Y-%m-%d %H:%M:%S UTC')
    except ValueError:
        return timestamp_str 

def _fetch_github_api(url, headers, params=None):
    """Helper function for GET requests to GitHub API."""
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status() 
        return response
    except requests.exceptions.HTTPError as http_err:
        error_message = f"HTTP error occurred: {http_err}"
        if http_err.response is not None:
            try:
                gh_error = http_err.response.json()
                error_message = f"GitHub API Error ({http_err.response.status_code}): {gh_error.get('message', http_err.response.text)}"
            except json.JSONDecodeError:
                error_message = f"GitHub API Error ({http_err.response.status_code}): {http_err.response.text}"
        raise TomeException(error_message) from http_err
    except requests.exceptions.RequestException as req_err:
        raise TomeException(f"Request error occurred: {req_err}") from req_err


def fetch_formatted_issue_conversation(owner, repo, issue_number, token):
    """
    Fetches and formats a GitHub issue conversation.
    Returns a dictionary with 'status' and 'data' or 'error'.
    """
    base_url = "https://api.github.com"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    output_lines = []
    warnings = []

    issue_url_api = f"{base_url}/repos/{owner}/{repo}/issues/{issue_number}"
    try:
        response_issue = _fetch_github_api(issue_url_api, headers)
        issue_data = response_issue.json()
    except TomeException as e:
        return {"status": "error", "error": f"Failed to fetch issue details: {str(e)}"}

    output_lines.append(f"GitHub Issue Conversation: {owner}/{repo} #{issue_number}")
    output_lines.append(f"URL: https://github.com/{owner}/{repo}/issues/{issue_number}")
    output_lines.append(f"Title: {issue_data.get('title', 'N/A')}")
    output_lines.append(f"Status: {issue_data.get('state', 'N/A')}")
    output_lines.append("-" * 40)

    author = issue_data.get('user', {}).get('login', 'N/A')
    created_at = format_github_timestamp(issue_data.get('created_at', ''))
    output_lines.append(f"Opened by: @{author} on {created_at}")
    output_lines.append("-" * 40)
    output_lines.append("ISSUE DESCRIPTION:")
    output_lines.append(issue_data.get('body') or "No description provided.")
    output_lines.append("=" * 40)

    comments_url_api = issue_data.get('comments_url')
    if comments_url_api:
        try:
            response_comments = _fetch_github_api(comments_url_api, headers, params={'per_page': 100})
            comments_data = response_comments.json()
            if 'next' in response_comments.links:
                warnings.append("WARNING: More comments exist than retrieved (pagination not fully implemented for >100 comments).")

            if comments_data:
                output_lines.append("\nCOMMENTS:\n")
                for comment in comments_data:
                    comment_author = comment.get('user', {}).get('login', 'N/A')
                    comment_created_at = format_github_timestamp(comment.get('created_at', ''))
                    output_lines.append("-" * 40)
                    output_lines.append(f"Comment by @{comment_author} on {comment_created_at}")
                    output_lines.append("-" * 40)
                    output_lines.append(comment.get('body') or "No comment body.")
                    output_lines.append("-" * 40)
            elif response_comments.ok :
                 output_lines.append("\nNo comments found for this issue.")
        except TomeException as e:
            warnings.append(f"WARNING: Could not retrieve comments: {str(e)}")
            output_lines.append("\nCould not retrieve comments.")
    else:
        output_lines.append("\nNo comments URL found in issue data.")
        
    return {
        "status": "success",
        "conversation_text": "\n".join(output_lines),
        "warnings": warnings,
        "url": f"https://github.com/{owner}/{repo}/issues/{issue_number}",
        "title": issue_data.get('title', 'N/A')
    }

def gic_text_formatter(data):
    """
    Text formatter for get_issue_conversation.
    Prints the path and content of each found file or errors.
    """
    output = TomeOutput(stdout=True)
    error_output = TomeOutput() 

    if data.get("status") == "error":
        raise TomeException(data.get("error", "Unknown error fetching issue conversation."))
    
    for warning_msg in data.get("warnings", []):
        error_output.warning(warning_msg)
    
    if "conversation_text" in data:
        output.print(data["conversation_text"])
    else:
        output.info("No conversation data to display.")


def gic_json_formatter(data):
    """
    JSON formatter for get_issue_conversation.
    Prints the list of file data (or errors) as JSON.
    """
    output = TomeOutput(stdout=True)
    output.print_json(json.dumps(data, indent=2))
    if data.get("status") == "error": 
        raise TomeException(data.get("error", "Unknown error fetching issue conversation."))

@tome_command(formatters={"text": gic_text_formatter, "json": gic_json_formatter})
def get_issue(tome_api, parser, *args):
    """
    Fetches a GitHub issue conversation; requires GH_TOKEN env var.
    """
    parser.add_argument(
        "url", 
        help="Full URL of the GitHub issue (e.g., https://github.com/owner/repo/issues/123)."
    )
    parsed_args = parser.parse_args(*args)
    
    github_token = os.environ.get('GH_TOKEN')
    if not github_token:
        return {
            "action": "get_issue", 
            "status": "error", 
            "error": "GH_TOKEN environment variable not set. Please set it with your GitHub personal access token."
        }
    
    try:
        issue_details = parse_github_issue_url(parsed_args.url)
    except ValueError as ve:
        return {"action": "get_issue", "status": "error", "error": f"URL Parsing Error: {str(ve)}"}

    try:
        result_data = fetch_formatted_issue_conversation(
            issue_details["owner"],
            issue_details["repo"],
            issue_details["issue_number"],
            github_token
        )
        result_data["action"] = "get_issue" 
        return result_data
    except TomeException as e: 
         return {"action": "get_issue", "status": "error", "error": str(e)}
