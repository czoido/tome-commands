import os
import json
import re
import requests
from datetime import datetime
from urllib.parse import urlparse

from tome.command import tome_command
from tome.api.output import TomeOutput
from tome.errors import TomeException

def parse_github_pr_url(url):
    """
    Parses a GitHub PR URL to extract owner, repo, and PR number.
    """
    parsed_url = urlparse(url)
    if parsed_url.netloc.lower() != 'github.com':
        raise ValueError(f"URL must be from github.com, but received: '{parsed_url.netloc}'")
    
    match = re.match(r'/([^/]+)/([^/]+)/pull/(\d+)/?$', parsed_url.path)
    if not match:
        raise ValueError("Invalid PR URL format. Expected '/<owner>/<repo>/pull/<pr_number>'.")
    
    owner, repo, pr_number_str = match.groups()
    return {"owner": owner, "repo": repo, "pr_number": int(pr_number_str)}

def format_github_timestamp(timestamp_str):
    """Converts GitHub ISO 8601 timestamp to a readable format."""
    if not timestamp_str: return "N/A"
    try:
        dt_object = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        return dt_object.strftime('%Y-%m-%d %H:%M:%S UTC')
    except ValueError:
        return timestamp_str

def _fetch_github_api(url, headers, params=None, accept_header=None):
    """Helper function for GET requests to GitHub API."""
    request_headers = headers.copy()
    if accept_header:
        request_headers["Accept"] = accept_header
    
    try:
        response = requests.get(url, headers=request_headers, params=params)
        response.raise_for_status() 
        return response
    except requests.exceptions.HTTPError as http_err:
        error_message = f"HTTP error occurred while fetching {url}: {http_err}"
        if http_err.response is not None:
            try:
                gh_error = http_err.response.json()
                error_message = f"GitHub API Error ({http_err.response.status_code}) for {url}: {gh_error.get('message', http_err.response.text)}"
            except json.JSONDecodeError:
                error_message = f"GitHub API Error ({http_err.response.status_code}) for {url}: {http_err.response.text}"
        raise TomeException(error_message) from http_err
    except requests.exceptions.RequestException as req_err:
        raise TomeException(f"Request error occurred while fetching {url}: {req_err}") from req_err

def fetch_formatted_pr_data(owner, repo, pr_number, token):
    """
    Fetches and formats GitHub PR details, comments, and diff.
    Returns a dictionary.
    """
    base_url = "https://api.github.com"
    std_headers = {
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    json_accept_header = "application/vnd.github.v3+json" 
    diff_accept_header = "application/vnd.github.v3.diff"

    pr_data = {}
    pr_comments_data = []
    review_comments_data = []
    diff_text = ""
    warnings = []

    pr_api_url = f"{base_url}/repos/{owner}/{repo}/pulls/{pr_number}"
    try:
        response_pr = _fetch_github_api(pr_api_url, std_headers, accept_header=json_accept_header)
        pr_data = response_pr.json()
    except TomeException as e:
        return {"action": "get_pr", "status": "error", "error": f"Failed to fetch PR details: {str(e)}"}

    issue_comments_api_url = f"{base_url}/repos/{owner}/{repo}/issues/{pr_number}/comments"
    try:
        response_issue_comments = _fetch_github_api(issue_comments_api_url, std_headers, params={'per_page': 100}, accept_header=json_accept_header)
        pr_comments_data = response_issue_comments.json()
        if 'next' in response_issue_comments.links:
            warnings.append("WARNING: More general PR comments exist than retrieved (pagination not fully implemented).")
    except TomeException as e:
        warnings.append(f"WARNING: Could not retrieve general PR comments: {str(e)}")

    review_comments_api_url = f"{base_url}/repos/{owner}/{repo}/pulls/{pr_number}/comments"
    try:
        response_review_comments = _fetch_github_api(review_comments_api_url, std_headers, params={'per_page': 100}, accept_header=json_accept_header)
        review_comments_data = response_review_comments.json()
        if 'next' in response_review_comments.links:
            warnings.append("WARNING: More review comments exist than retrieved (pagination not fully implemented).")
    except TomeException as e:
        warnings.append(f"WARNING: Could not retrieve review comments: {str(e)}")

    try:
        response_diff = _fetch_github_api(pr_api_url, std_headers, accept_header=diff_accept_header)
        diff_text = response_diff.text
    except TomeException as e:
        warnings.append(f"WARNING: Could not retrieve PR diff: {str(e)}")
        diff_text = "Error retrieving diff."

    return {
        "action": "get_pr",
        "status": "success",
        "pr_details": {
            "url": pr_data.get('html_url', f"https://github.com/{owner}/{repo}/pull/{pr_number}"),
            "title": pr_data.get('title', 'N/A'),
            "state": pr_data.get('state', 'N/A'),
            "author": pr_data.get('user', {}).get('login', 'N/A'),
            "created_at": format_github_timestamp(pr_data.get('created_at', '')),
            "updated_at": format_github_timestamp(pr_data.get('updated_at', '')),
            "merged_at": format_github_timestamp(pr_data.get('merged_at', '')),
            "body": pr_data.get('body') or "No description provided.",
            "base_ref": pr_data.get('base', {}).get('ref', 'N/A'),
            "head_ref": pr_data.get('head', {}).get('ref', 'N/A'),
        },
        "pr_comments": [
            {
                "author": c.get('user', {}).get('login', 'N/A'),
                "created_at": format_github_timestamp(c.get('created_at', '')),
                "body": c.get('body') or "No comment body."
            } for c in pr_comments_data
        ],
        "review_comments": [
            {
                "author": rc.get('user', {}).get('login', 'N/A'),
                "path": rc.get('path', 'N/A'),
                "line": rc.get('line') or rc.get('original_line'),
                "created_at": format_github_timestamp(rc.get('created_at', '')),
                "body": rc.get('body') or "No comment body."
            } for rc in review_comments_data
        ],
        "diff": diff_text,
        "warnings": warnings
    }

def gpr_text_formatter(data):
    """Text formatter for get_pr command."""
    output = TomeOutput(stdout=True)
    error_output = TomeOutput() 

    if data.get("status") == "error":
        raise TomeException(data.get("error", "Unknown error fetching PR data."))
    
    for warning_msg in data.get("warnings", []):
        error_output.warning(warning_msg)
    
    details = data.get("pr_details", {})
    output.print(f"GitHub Pull Request: {details.get('url', 'N/A')}")
    output.print(f"Title: {details.get('title', 'N/A')}")
    output.print(f"Author: @{details.get('author', 'N/A')}")
    output.print(f"State: {details.get('state', 'N/A')}")
    output.print(f"Created: {details.get('created_at', 'N/A')}")
    if details.get('merged_at') and details.get('merged_at') != "N/A":
        output.print(f"Merged: {details.get('merged_at')}")
    output.print(f"Base: {details.get('base_ref', 'N/A')} <- Head: {details.get('head_ref', 'N/A')}")
    output.print("-" * 40)
    output.print("PR DESCRIPTION:")
    output.print(details.get('body', "No description provided."))
    output.print("=" * 40)

    pr_comments = data.get("pr_comments", [])
    if pr_comments:
        output.print("\nGENERAL PR COMMENTS:\n")
        for comment in pr_comments:
            output.print("-" * 40)
            output.print(f"Comment by @{comment['author']} on {comment['created_at']}")
            output.print("-" * 40)
            output.print(comment['body'])
            output.print("-" * 40)
    else:
        output.print("\nNo general PR comments found.")
    output.print("=" * 40)

    review_comments = data.get("review_comments", [])
    if review_comments:
        output.print("\nREVIEW COMMENTS (ON DIFF):\n")
        for r_comment in review_comments:
            output.print("-" * 40)
            output.print(f"Comment by @{r_comment['author']} on {r_comment['created_at']}")
            output.print(f"File: {r_comment['path']}, Line: {r_comment['line']}")
            output.print("-" * 40)
            output.print(r_comment['body'])
            output.print("-" * 40)
    else:
        output.print("\nNo review comments found on the diff.")
    output.print("=" * 40)

    output.print("\nCODE DIFF:\n")
    output.print(data.get("diff", "No diff available or error retrieving diff."))


def gpr_json_formatter(data):
    """JSON formatter for get_pr command."""
    output = TomeOutput(stdout=True)
    output.print_json(json.dumps(data, indent=2))
    if data.get("status") == "error": 
        raise TomeException(data.get("error", "Unknown error fetching PR data."))

@tome_command(formatters={"text": gpr_text_formatter, "json": gpr_json_formatter})
def get_pr(tome_api, parser, *args):
    """Fetches GitHub PR details, comments, and diff; requires GH_TOKEN env var."""
    parser.add_argument(
        "url", 
        help="Full URL of the GitHub PR (e.g., https://github.com/owner/repo/pull/123)."
    )
    parsed_args = parser.parse_args(*args)
    
    github_token = os.environ.get('GH_TOKEN')
    if not github_token:
        return {
            "action": "get_pr", 
            "status": "error", 
            "error": "GH_TOKEN environment variable not set. Please set it with your GitHub personal access token."
        }
    
    try:
        pr_details_from_url = parse_github_pr_url(parsed_args.url)
    except ValueError as ve:
        return {"action": "get_pr", "status": "error", "error": f"URL Parsing Error: {str(ve)}"}

    try:
        result_data = fetch_formatted_pr_data(
            pr_details_from_url["owner"],
            pr_details_from_url["repo"],
            pr_details_from_url["pr_number"],
            github_token
        )
        return result_data
    except TomeException as e: 
         return {"action": "get_pr", "status": "error", "error": str(e)}
