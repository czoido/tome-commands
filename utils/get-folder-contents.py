import os
import fnmatch
import json
from tome.command import tome_command
from tome.api.output import TomeOutput
from tome.errors import TomeException

def gfc_text_formatter(results_list):
    """
    Text formatter for get_folder_contents.
    Prints the path and content of each found file or errors.
    """
    output = TomeOutput(stdout=True)
    if not results_list:
        output.info("No files found matching the criteria.")
        return

    for item in results_list:
        if item.get("status") == "error":
            TomeOutput().error(f"Error processing {item.get('path', 'Unknown path')}: {item.get('error')}")
        elif "path" in item and "content" in item:
            output.print("--------------")
            output.print(f"path: {item['path']}")
            output.print("--------------")
            output.print(item['content'])
            output.print("--------------\n")

def gfc_json_formatter(results_list):
    """
    JSON formatter for get_folder_contents.
    Prints the list of file data (or errors) as JSON.
    """
    output = TomeOutput(stdout=True)
    output.print_json(json.dumps(results_list, indent=2))

@tome_command(formatters={"text": gfc_text_formatter, "json": gfc_json_formatter})
def get_folder_contents(tome_api, parser, *args):
    """Lists file contents matching patterns, with ignore options."""
    parser.add_argument(
        'patterns', nargs='+', 
        help="File patterns (fnmatch-style) to search for recursively (e.g., '*.py' 'src/**/*.js')."
    )
    parser.add_argument(
        '-i', '--ignore', nargs='*', default=[],
        help="Glob patterns or names of files/directories to ignore (e.g., '*.log' 'node_modules' '.git')."
    )
    parser.add_argument(
        '--base-dir', default='.',
        help="Base directory to start the search from (default: current directory)."
    )
    parsed_args = parser.parse_args(*args)

    output_files_data = []

    def is_ignored(current_path, ignore_patterns):
        # Normalize path for consistent matching
        normalized_path = os.path.normpath(current_path)
        path_parts = normalized_path.split(os.sep)
        
        for pattern in ignore_patterns:
            # Direct name match in any part of the path (for simple names like 'node_modules')
            if not any(c in pattern for c in ['*', '?', '[', ']']): # Not a glob pattern
                if pattern in path_parts:
                    return True
            # Glob pattern matching against the full path or basename
            elif fnmatch.fnmatch(normalized_path, pattern) or \
                 fnmatch.fnmatch(os.path.basename(normalized_path), pattern):
                return True
        return False

    base_search_dir = os.path.abspath(parsed_args.base_dir)
    if not os.path.isdir(base_search_dir):
        raise TomeException(f"Base directory not found or is not a directory: {base_search_dir}")

    for root, dirs, files in os.walk(base_search_dir, topdown=True):
        # Filter out ignored directories before os.walk descends into them
        # os.walk requires modifying dirs[:] in-place
        dirs[:] = [d for d in dirs if not is_ignored(os.path.relpath(os.path.join(root, d), base_search_dir), parsed_args.ignore)]

        for filename in files:
            filepath_abs = os.path.join(root, filename)
            filepath_rel = os.path.relpath(filepath_abs, base_search_dir)

            if is_ignored(filepath_rel, parsed_args.ignore):
                continue

            matched_by_pattern = False
            for pattern in parsed_args.patterns:
                if fnmatch.fnmatch(filepath_rel, pattern) or fnmatch.fnmatch(filename, pattern):
                    matched_by_pattern = True
                    break
            
            if matched_by_pattern:
                try:
                    with open(filepath_abs, 'r', encoding='utf-8', errors='ignore') as f:
                        contents = f.read()
                    output_files_data.append({
                        "path": filepath_rel,
                        "content": contents,
                        "status": "success"
                    })
                except Exception as e:
                    output_files_data.append({
                        "path": filepath_rel,
                        "status": "error",
                        "error": f"Could not read file: {str(e)}"
                    })
    
    if not output_files_data and parsed_args.patterns:
         pass


    return output_files_data
