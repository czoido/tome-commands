# My Tome Utilities 🛠️

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
$ tome install https://github.com/czoido/tome-commands.git
```

After installation, the commands will be available under their respective
namespaces (e.g., `utils`). You can see all installed commands from this Tome by
running `tome list`.

[utils:get-folder-contents](./utils/get-folder-contents.py)

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
