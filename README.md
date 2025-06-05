# tome-commands

This repository contains a collection of **tome** commands designed to assist
with various development and utility tasks. These scripts are managed and run
using the [tome script management tool](https://jfrog.github.io/tome/).

## Installation

To use these commands, you first need to have **tome** installed. If you haven't
already, please follow the instructions on the [official tome documentation
site](https://jfrog.github.io/tome/).

Once **tome** is installed, you can install this entire collection of utility
commands by pointing `tome install` to this repository:

```bash
# create a new virtual environment and activate it
$ python -m venv .venv
$ source .venv/bin/activate

# install tome
$ pip install tomescripts

# install this Tome of commands
$ tome install https://github.com/czoido/tome-commands.git

# check installation
$ tome list
```

After installation, the commands will be available under their respective
namespaces (e.g., `utils`). You can see all installed commands from this Tome by
running `tome list`.

## `tome utils:get-folder-contents` ([source code](./utils/get-folder-contents.py))

This command recursively searches a directory, finds files matching specified
patterns, and concatenates their contents into a single output. This is
extremely helpful for preparing codebases or sets of documents to be fed into
Large Language Models (LLMs) for analysis, summarization, or other tasks.

**Basic Usage:** To get the content of all Python files in the current directory
and its subdirectories:

```bash
$ tome utils:get-folder-contents "*.py"
```

**Specifying Multiple Patterns:** To include Python and Markdown files:

```bash
$ tome utils:get-folder-contents "*.py" "*.md"
```

**Ignoring Files and Directories:** To get all Python files but ignore the
`venv` directory, `__pycache__` directories, and any `setup.py` files:

```bash
$ tome utils:get-folder-contents "*.py" -i "venv/*" "__pycache__/*" "setup.py"
```

**Searching in a Specific Base Directory:**
```bash
$ tome utils:get-folder-contents "*.java" --base-dir ./my-java-project/src
```

**Output Formats:** The command supports different output formats using the
global `--format` option provided by **tome**:

* **Text (default):** Outputs the content of each file, prefixed by its path and
  separators.

```bash
$ tome utils:get-folder-contents "src/*.py"
--------------
path: src/main.py
--------------
# Contents of main.py
print("Hello")
--------------
path: src/utils.py
--------------
# Contents of utils.py
def helper():
    return True
--------------
```

* **JSON:** Outputs a JSON array where each object contains the path, content,
  and status for a file.

```bash
$ tome utils:get-folder-contents "src/*.py" --format json
[
{
    "path": "src/main.py",
    "content": "# Contents of main.py\nprint(\"Hello\")",
    "status": "success"
},
{
    "path": "src/utils.py",
    "content": "# Contents of utils.py\ndef helper():\n    return True",
    "status": "success"
}
]
```

## `tome utils:get-issue` ([source code](./utils/get-issue.py))

This command fetches the full conversation (initial post and all comments) from
a public GitHub issue URL and formats it for easy reading or for input into a
Large Language Model (LLM).

**Prerequisites:**
* Requires the `GH_TOKEN` environment variable to be set with a GitHub Personal
  Access Token. This token is used for authenticated read-only access to the
  GitHub API to avoid rate limiting.

**Basic Usage:** To fetch the conversation for a specific GitHub issue:

```
$ tome utils:get-issue "https://github.com/owner/repo/issues/123"
```

**Output Formats:** The command supports different output formats using the
global `--format` option provided by **tome**:

* **Text (default):** Outputs the formatted issue title, body, and comments in a
  human-readable plain text format. Warnings (e.g., if pagination limits comment
  retrieval) are printed to stderr.

```
$ tome utils:get-issue "https://github.com/octocat/Spoon-Knife/issues/1"
GitHub Issue Conversation: octocat/Spoon-Knife #1
URL: [https://github.com/octocat/Spoon-Knife/issues/1](https://github.com/octocat/Spoon-Knife/issues/1)
Title: Test issue
Status: open
----------------------------------------
Opened by: @octocat on 2011-04-10 20:09:31 UTC
----------------------------------------
ISSUE DESCRIPTION:
This is a test issue
========================================

COMMENTS:

----------------------------------------
Comment by @octocat on 2011-04-10 20:19:31 UTC
----------------------------------------
This is a comment
----------------------------------------
```

* **JSON (`--format json`):** Outputs a JSON object containing the action,
  status, URL, title, any warnings, and the full `conversation_text`.

```
$ tome utils:get-issue "https://github.com/octocat/Spoon-Knife/issues/1" --format json
{
    "status": "success",
    "conversation_text": "GitHub Issue Conversation: octocat/Spoon-Knife #1\nURL: [https://github.com/octocat/Spoon-Knife/issues/1](https://github.com/octocat/Spoon-Knife/issues/1)...",
    "warnings": [],
    "url": "[https://github.com/octocat/Spoon-Knife/issues/1](https://github.com/octocat/Spoon-Knife/issues/1)",
    "title": "Test issue",
    "action": "get_issue"
}
```

## `tome utils:get-pr` ([source code](./utils/get-pr.py))

Fetches GitHub Pull Request (PR) details, including its description, general
comments, review comments on the diff, and the code diff itself. This is useful
for summarizing PRs or providing context to LLMs.

**Basic Usage:** To fetch the details, comments, and diff for a specific GitHub
PR:

```bash
$ tome utils:get-pr "[https://github.com/owner/repo/pull/456](https://github.com/owner/repo/pull/456)"
```

**Output Formats:**

* **Text (default):** Provides a human-readable output of the PR details,
  description, comments, and diff.

* **JSON (`--format json`):** Outputs a structured JSON object containing all
  fetched PR data.
