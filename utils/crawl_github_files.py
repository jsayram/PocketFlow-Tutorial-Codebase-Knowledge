import requests
import base64
import os
import tempfile
import git
import time
import fnmatch
import sys
from typing import Union, Set, List, Dict, Tuple, Any
from urllib.parse import urlparse
import logging
from dotenv import load_dotenv
logger = logging.getLogger(__name__)


def preview_file(files):
    """
    Allows selecting and previewing a specific file from the repository.
    
    Args:
        files (dict): Dictionary mapping file paths to file contents
        
    Returns:
        None: Displays file information to the console
    """
    if not files:
        print("No files available to preview.")
        return
    
    # Sort files alphabetically for easier navigation
    sorted_files = sorted(files.keys())
    
    # Show file list with numbers for selection
    print("\nAvailable files:")
    for i, file_path in enumerate(sorted_files, 1):
        print(f"[{i}] {file_path}")
    
    # Get user selection
    while True:
        try:
            choice = input("\nEnter file number to preview (or 'q' to quit): ")
            
            if choice.lower() == 'q':
                return
                
            file_index = int(choice) - 1
            if 0 <= file_index < len(sorted_files):
                selected_file = sorted_files[file_index]
                break
            else:
                print(f"Invalid selection. Please enter a number between 1 and {len(sorted_files)}.")
        except ValueError:
            print("Please enter a valid number or 'q' to quit.")
    
    # Get file content
    file_content = files[selected_file]
    file_size = len(file_content)
    
    # Show file information
    print("\n" + "="*50)
    print(f"File: {selected_file}")
    print(f"Size: {file_size} characters")
    
    # Determine file type for better explanation
    file_extension = selected_file.split('.')[-1] if '.' in selected_file else 'unknown'
    file_type_descriptions = {
        'py': 'Python source code',
        'md': 'Markdown document',
        'txt': 'Text file',
        'json': 'JSON data file',
        'yml': 'YAML configuration file',
        'yaml': 'YAML configuration file',
        'js': 'JavaScript source code',
        'html': 'HTML document',
        'css': 'CSS stylesheet',
        'gitignore': 'Git ignore rules',
        'env': 'Environment variables file',
        'c': 'C source code',
        'cpp': 'C++ source code',
        'cs': 'C# source code',
        'java': 'Java source code',
        'go': 'Go source code',
        'rb': 'Ruby source code',
        'php': 'PHP source code',
        'swift': 'Swift source code',
        'rs': 'Rust source code',
        'kt': 'Kotlin source code', 
        'html': 'HTML document',
        'xml': 'XML document',
        'sql': 'SQL database file',
        'csv': 'Comma-separated values file',
        'log': 'Log file',
        'sh': 'Shell script',
        'bash': 'Bash script',
        'ps1': 'PowerShell script',
        'pl': 'Perl script',
        'r': 'R script',
        'dart': 'Dart source code',
        'ts': 'TypeScript source code',
        'vue': 'Vue.js component',
        'jsx': 'React JSX file',
        'tsx': 'React TSX file',
        'less': 'Less CSS file',
        'scss': 'Sass CSS file',
        'dockerfile': 'Dockerfile',
        'makefile': 'Makefile',
        'properties': 'Java properties file',
    }
    
    file_type = file_type_descriptions.get(file_extension, f"File with .{file_extension} extension")
    print(f"Type: {file_type}")
    print("="*50)
    
    # Ask for preview length
    preview_lines = 10
    try:
        preview_input = input(f"\nHow many lines to preview? (default: {preview_lines}): ")
        if preview_input.strip():
            preview_lines = int(preview_input)
    except ValueError:
        print(f"Using default preview length of {preview_lines} lines.")
    
    # Show content preview with line numbers
    print("\nContent preview:")
    print("-"*50)
    
    lines = file_content.split('\n')
    for i, line in enumerate(lines[:preview_lines], 1):
        print(f"{i:3d} | {line}")
    
    if len(lines) > preview_lines:
        print(f"\n... and {len(lines) - preview_lines} more lines")
    
    # Offer to see more of the file
    while True:
        action = input("\nOptions: [m]ore lines, [a]ll content, [f]ind text, [b]ack to file list, [q]uit: ").lower()
        
        if action == 'm':
            try:
                more_lines = int(input("How many more lines? "))
                print("\nContent continued:")
                print("-"*50)
                for i, line in enumerate(lines[preview_lines:preview_lines+more_lines], preview_lines+1):
                    print(f"{i:3d} | {line}")
                preview_lines += more_lines
            except ValueError:
                print("Please enter a valid number.")
                
        elif action == 'a':
            print("\nFull content:")
            print("-"*50)
            for i, line in enumerate(lines, 1):
                print(f"{i:3d} | {line}")
                
        elif action == 'f':
            search_term = input("Enter text to find: ")
            if search_term:
                print(f"\nLines containing '{search_term}':")
                print("-"*50)
                found = False
                for i, line in enumerate(lines, 1):
                    if search_term.lower() in line.lower():
                        print(f"{i:3d} | {line}")
                        found = True
                if not found:
                    print(f"No matches found for '{search_term}'")
            
        elif action == 'b':
            preview_file(files)  # Recursive call to restart the preview process
            return
            
        elif action == 'q':
            return
            
        else:
            print("Invalid option.")


def ensure_github_url():
    """
    Ensures the GITHUB_URL environment variable is available.
    Loads from .env file if present and checks for the URL.
    
    Returns:
        str: The GitHub URL if found
        
    Raises:
        Exception: If GitHub URL is not found after attempting to load it
    """
    # First, try to find and load the .env file from multiple possible locations
    # This is shared with ensure_api_key to maintain consistency
    env_locations = [
        '.env',                                  # Current directory
        '../.env',                               # Parent directory
        os.path.join(os.path.dirname(__file__), '../.env'),  # Project root relative to this script
        os.path.expanduser('~/.env')             # Home directory
    ]
    
    # Try each location if environment isn't already loaded
    if not os.environ.get("GITHUB_URL") and not os.environ.get("GITHUB_TOKEN"):
        env_loaded = False
        for env_path in env_locations:
            if os.path.exists(env_path):
                logger.info(f"Found .env file at {env_path}")
                load_dotenv(env_path)
                env_loaded = True
                break
        
        # If no .env file was found, try to find one automatically
        if not env_loaded:
            logger.info("No .env file found in standard locations, searching...")
            env_path = find_dotenv(usecwd=True)
            if env_path:
                logger.info(f"Found .env file at {env_path}")
                load_dotenv(env_path)
                env_loaded = True
            else:
                logger.warning("No .env file found")
    
    # Check if the GitHub URL exists in environment variables
    github_url = os.environ.get("GITHUB_URL")
    if not github_url:
        # Check common variants of the variable name
        for var_name in ["REPO_URL", "REPOSITORY_URL", "GIT_REPO"]:
            logger.info(f"GITHUB_URL not found, checking {var_name}...")
            github_url = os.environ.get(var_name)
            if github_url:
                logger.info(f"Using {var_name} instead of GITHUB_URL")
                os.environ["GITHUB_URL"] = github_url
                break
    
    # Also check for GitHub token as it's often needed together
    github_token = os.environ.get("GITHUB_TOKEN")
    if github_token:
        logger.info("GITHUB_TOKEN found in environment variables")
    else:
        logger.warning("GITHUB_TOKEN not found in environment variables - may have limited API access")
    
    # If still no GitHub URL, provide help
    if not github_url:
        logger.error("No GitHub URL found in environment variables")
        print("\n" + "="*50)
        print("GITHUB URL CONFIGURATION ERROR")
        print("="*50)
        print("\nYour .env file should contain:")
        print("\nGITHUB_URL=https://github.com/username/repository")
        print("\nAnd optionally:")
        print("GITHUB_TOKEN=your-github-token")
        print("\nLocation of .env file should be in the project root directory")
        print("\nCurrent working directory:", os.getcwd())
        print("\nThe following .env file locations were checked:")
        for path in env_locations:
            if os.path.exists(path):
                print(f" - {path} (EXISTS)")
            else:
                print(f" - {path} (not found)")
        
        print("\nEnvironment variables currently set:")
        for key in sorted(os.environ.keys()):
            if "URL" in key or "GITHUB" in key or "REPO" in key or "GIT" in key:
                value = os.environ[key]
                # Don't mask URLs as they're generally not sensitive
                print(f" - {key}: {value}")
        
        raise Exception("GITHUB_URL not set in environment variables after loading .env file")
    
    # Validate URL format
    if not github_url.startswith(("http://github.com/", "https://github.com/")):
        logger.warning(f"GitHub URL format may be invalid: {github_url}")
        print("WARNING: GitHub URL should be in the format https://github.com/username/repository")
    
    return github_url




def crawl_github_files(
    repo_url, 
    token=None, 
    max_file_size: int = 1 * 1024 * 1024,  # 1 MB
    use_relative_paths: bool = False,
    include_patterns: Union[str, Set[str]] = None,
    exclude_patterns: Union[str, Set[str]] = None
):
    """
    Crawl files from a specific path in a GitHub repository at a specific commit.

    Args:
        repo_url (str): URL of the GitHub repository with specific path and commit
                        (e.g., 'https://github.com/microsoft/autogen/tree/e45a15766746d95f8cfaaa705b0371267bec812e/python/packages/autogen-core/src/autogen_core')
        token (str, optional): **GitHub personal access token.**
            - **Required for private repositories.**
            - **Recommended for public repos to avoid rate limits.**
            - Can be passed explicitly or set via the `GITHUB_TOKEN` environment variable.
        max_file_size (int, optional): Maximum file size in bytes to download (default: 1 MB)
        use_relative_paths (bool, optional): If True, file paths will be relative to the specified subdirectory
        include_patterns (str or set of str, optional): Pattern or set of patterns specifying which files to include (e.g., "*.py", {"*.md", "*.txt"}).
                                                       If None, all files are included.
        exclude_patterns (str or set of str, optional): Pattern or set of patterns specifying which files to exclude.
                                                       If None, no files are excluded.

    Returns:
        dict: Dictionary with files and statistics
    """
    # Convert single pattern to set
    if include_patterns and isinstance(include_patterns, str):
        include_patterns = {include_patterns}
    if exclude_patterns and isinstance(exclude_patterns, str):
        exclude_patterns = {exclude_patterns}

    def should_include_file(file_path: str, file_name: str) -> bool:
        """Determine if a file should be included based on patterns"""
        # If no include patterns are specified, include all files
        if not include_patterns:
            include_file = True
        else:
            # Check if file matches any include pattern
            include_file = any(fnmatch.fnmatch(file_name, pattern) for pattern in include_patterns)

        # If exclude patterns are specified, check if file should be excluded
        if exclude_patterns and include_file:
            # Exclude if file matches any exclude pattern
            exclude_file = any(fnmatch.fnmatch(file_path, pattern) for pattern in exclude_patterns)
            return not exclude_file

        return include_file

    # Detect SSH URL (git@ or .git suffix)
    is_ssh_url = repo_url.startswith("git@") or repo_url.endswith(".git")

    if is_ssh_url:
        # Clone repo via SSH to temp dir
        with tempfile.TemporaryDirectory() as tmpdirname:
            print(f"Cloning SSH repo {repo_url} to temp dir {tmpdirname} ...")
            try:
                repo = git.Repo.clone_from(repo_url, tmpdirname)
            except Exception as e:
                print(f"Error cloning repo: {e}")
                return {"files": {}, "stats": {"error": str(e)}}

            # Attempt to checkout specific commit/branch if in URL
            # Parse ref and subdir from SSH URL? SSH URLs don't have branch info embedded
            # So rely on default branch, or user can checkout manually later
            # Optionally, user can pass ref explicitly in future API

            # Walk directory
            files = {}
            skipped_files = []

            for root, dirs, filenames in os.walk(tmpdirname):
                for filename in filenames:
                    abs_path = os.path.join(root, filename)
                    rel_path = os.path.relpath(abs_path, tmpdirname)

                    # Check file size
                    try:
                        file_size = os.path.getsize(abs_path)
                    except OSError:
                        continue

                    if file_size > max_file_size:
                        skipped_files.append((rel_path, file_size))
                        print(f"Skipping {rel_path}: size {file_size} exceeds limit {max_file_size}")
                        continue

                    # Check include/exclude patterns
                    if not should_include_file(rel_path, filename):
                        print(f"Skipping {rel_path}: does not match include/exclude patterns")
                        continue

                    # Read content
                    try:
                        with open(abs_path, "r", encoding="utf-8-sig") as f:
                            content = f.read()
                        files[rel_path] = content
                        print(f"Added {rel_path} ({file_size} bytes)")
                    except Exception as e:
                        print(f"Failed to read {rel_path}: {e}")

            return {
                "files": files,
                "stats": {
                    "downloaded_count": len(files),
                    "skipped_count": len(skipped_files),
                    "skipped_files": skipped_files,
                    "base_path": None,
                    "include_patterns": include_patterns,
                    "exclude_patterns": exclude_patterns,
                    "source": "ssh_clone"
                }
            }

    # Parse GitHub URL to extract owner, repo, commit/branch, and path
    parsed_url = urlparse(repo_url)
    path_parts = parsed_url.path.strip('/').split('/')
    
    if len(path_parts) < 2:
        raise ValueError(f"Invalid GitHub URL: {repo_url}")
    
    # Extract the basic components
    owner = path_parts[0]
    repo = path_parts[1]
    
    # Setup for GitHub API
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"

    def fetch_branches(owner: str, repo: str):
        """Get brancshes of the repository"""

        url = f"https://api.github.com/repos/{owner}/{repo}/branches"
        response = requests.get(url, headers=headers, timeout=(30, 30))

        if response.status_code == 404:
            if not token:
                print(f"Error 404: Repository not found or is private.\n"
                      f"If this is a private repository, please provide a valid GitHub token via the 'token' argument or set the GITHUB_TOKEN environment variable.")
            else:
                print(f"Error 404: Repository not found or insufficient permissions with the provided token.\n"
                      f"Please verify the repository exists and the token has access to this repository.")
            return []
            
        if response.status_code != 200:
            print(f"Error fetching the branches of {owner}/{repo}: {response.status_code} - {response.text}")
            return []

        return response.json()

    def check_tree(owner: str, repo: str, tree: str):
        """Check the repository has the given tree"""

        url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{tree}"
        response = requests.get(url, headers=headers, timeout=(30, 30))

        return True if response.status_code == 200 else False 

    # Check if URL contains a specific branch/commit
    if len(path_parts) > 2 and 'tree' == path_parts[2]:
        join_parts = lambda i: '/'.join(path_parts[i:])

        branches = fetch_branches(owner, repo)
        branch_names = map(lambda branch: branch.get("name"), branches)

        # Fetching branches is not successfully
        if len(branches) == 0:
            return

        # To check branch name
        relevant_path = join_parts(3)

        # Find a match with relevant path and get the branch name
        filter_gen = (name for name in branch_names if relevant_path.startswith(name))
        ref = next(filter_gen, None)

        # If match is not found, check for is it a tree
        if ref == None:
            tree = path_parts[3]
            ref = tree if check_tree(owner, repo, tree) else None

        # If it is neither a tree nor a branch name
        if ref == None:
            print(f"The given path does not match with any branch and any tree in the repository.\n"
                  f"Please verify the path is exists.")
            return

        # Combine all parts after the ref as the path
        part_index = 5 if '/' in ref else 4
        specific_path = join_parts(part_index) if part_index < len(path_parts) else ""
    else:
        # Dont put the ref param to quiery
        # and let Github decide default branch
        ref = None
        specific_path = ""
    
    # Dictionary to store path -> content mapping
    files = {}
    skipped_files = []
    
    def fetch_contents(path):
        """Fetch contents of the repository at a specific path and commit"""
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
        params = {"ref": ref} if ref != None else {}
        
        response = requests.get(url, headers=headers, params=params, timeout=(30, 30))
        
        if response.status_code == 403 and 'rate limit exceeded' in response.text.lower():
            reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
            wait_time = max(reset_time - time.time(), 0) + 1
            print(f"Rate limit exceeded. Waiting for {wait_time:.0f} seconds...")
            time.sleep(wait_time)
            return fetch_contents(path)
            
        if response.status_code == 404:
            if not token:
                print(f"Error 404: Repository not found or is private.\n"
                      f"If this is a private repository, please provide a valid GitHub token via the 'token' argument or set the GITHUB_TOKEN environment variable.")
            elif not path and ref == 'main':
                print(f"Error 404: Repository not found. Check if the default branch is not 'main'\n"
                      f"Try adding branch name to the request i.e. python main.py --repo https://github.com/username/repo/tree/master")
            else:
                print(f"Error 404: Path '{path}' not found in repository or insufficient permissions with the provided token.\n"
                      f"Please verify the token has access to this repository and the path exists.")
            return
            
        if response.status_code != 200:
            print(f"Error fetching {path}: {response.status_code} - {response.text}")
            return
        
        contents = response.json()
        
        # Handle both single file and directory responses
        if not isinstance(contents, list):
            contents = [contents]
        
        for item in contents:
            item_path = item["path"]
            
            # Calculate relative path if requested
            if use_relative_paths and specific_path:
                # Make sure the path is relative to the specified subdirectory
                if item_path.startswith(specific_path):
                    rel_path = item_path[len(specific_path):].lstrip('/')
                else:
                    rel_path = item_path
            else:
                rel_path = item_path
            
            if item["type"] == "file":
                # Check if file should be included based on patterns
                if not should_include_file(rel_path, item["name"]):
                    print(f"Skipping {rel_path}: Does not match include/exclude patterns")
                    continue
                
                # Check file size if available
                file_size = item.get("size", 0)
                if file_size > max_file_size:
                    skipped_files.append((item_path, file_size))
                    print(f"Skipping {rel_path}: File size ({file_size} bytes) exceeds limit ({max_file_size} bytes)")
                    continue
                
                # For files, get raw content
                if "download_url" in item and item["download_url"]:
                    file_url = item["download_url"]
                    file_response = requests.get(file_url, headers=headers, timeout=(30, 30))
                    
                    # Final size check in case content-length header is available but differs from metadata
                    content_length = int(file_response.headers.get('content-length', 0))
                    if content_length > max_file_size:
                        skipped_files.append((item_path, content_length))
                        print(f"Skipping {rel_path}: Content length ({content_length} bytes) exceeds limit ({max_file_size} bytes)")
                        continue
                        
                    if file_response.status_code == 200:
                        files[rel_path] = file_response.text
                        print(f"Downloaded: {rel_path} ({file_size} bytes) ")
                    else:
                        print(f"Failed to download {rel_path}: {file_response.status_code}")
                else:
                    # Alternative method if download_url is not available
                    content_response = requests.get(item["url"], headers=headers, timeout=(30, 30))
                    if content_response.status_code == 200:
                        content_data = content_response.json()
                        if content_data.get("encoding") == "base64" and "content" in content_data:
                            # Check size of base64 content before decoding
                            if len(content_data["content"]) * 0.75 > max_file_size:  # Approximate size calculation
                                estimated_size = int(len(content_data["content"]) * 0.75)
                                skipped_files.append((item_path, estimated_size))
                                print(f"Skipping {rel_path}: Encoded content exceeds size limit")
                                continue
                                
                            file_content = base64.b64decode(content_data["content"]).decode('utf-8')
                            files[rel_path] = file_content
                            print(f"Downloaded: {rel_path} ({file_size} bytes)")
                        else:
                            print(f"Unexpected content format for {rel_path}")
                    else:
                        print(f"Failed to get content for {rel_path}: {content_response.status_code}")
            
            elif item["type"] == "dir":
                # OLD IMPLEMENTATION (comment this block to test new implementation)
                # Always recurse into directories without checking exclusions first
                # fetch_contents(item_path)

                # NEW IMPLEMENTATION (uncomment this block to test optimized version)
                # # Check if directory should be excluded before recursing
                if exclude_patterns:
                    dir_excluded = any(fnmatch.fnmatch(item_path, pattern) or
                                    fnmatch.fnmatch(rel_path, pattern) for pattern in exclude_patterns)
                    if dir_excluded:
                        continue
                
                # # Only recurse if directory is not excluded
                fetch_contents(item_path)
    
    # Start crawling from the specified path
    fetch_contents(specific_path)
    
    return {
        "files": files,
        "stats": {
            "downloaded_count": len(files),
            "skipped_count": len(skipped_files),
            "skipped_files": skipped_files,
            "base_path": specific_path if use_relative_paths else None,
            "include_patterns": include_patterns,
            "exclude_patterns": exclude_patterns
        }
    }

# Example usage
if __name__ == "__main__":
    try:
        # Try to load API key from .env file
        git_url = ensure_github_url()
        
        # If we get here, the key was found
        print("Github URL loaded successfully!")
        git_url_preview = git_url  # Get the last part of the URL
        print(f"using repo giturl: {git_url_preview}")
        
        # Get token from environment variable (recommended for private repos)
        github_token = os.environ.get("GITHUB_TOKEN")
        if not github_token:
            print("Warning: No GitHub token found in environment variable 'GITHUB_TOKEN'.\n"
                "Private repositories will not be accessible without a token.\n"
                "To access private repos, set the environment variable or pass the token explicitly.")
        
        repo_url = os.environ.get("GITHUB_URL")  # Replace with your GitHub repo URL
        
        # Example: Get Python and Markdown files, but exclude test files
        result = crawl_github_files(
            repo_url, 
            token=github_token,
            #max_file_size=1 * 1024 * 1024,  # 1 MB in bytes
            use_relative_paths=True,  # Enable relative paths
            # include_patterns={"*.py", "*.md", "src/**/*.js", "*.cs"},  # Only include these patterns
            # exclude_patterns= { "tests/*", 
            #     "docs/*", 
            #     "**/node_modules/**", 
            #     "**/.vscode/**", 
            #     "**/.venv/**", 
            #     "**/__pycache__/**",
            #     "**/.vscode/**", 
            #     "**/.venv/**", 
            #     "**/__pycache__/**",
            #     "**/.git/**"
            # },  
            # Exclude these patterns
            include_patterns={"*.py", "*.md", "src/**/*.js","*.cs"},  # Only include these patterns
            exclude_patterns= { "tests/*",
                "**/node_modules/**", 
                "**/.vscode/**", 
                "**/.venv/**", 
                "**/__pycache__/**",
                "**/.vscode/**", 
                "**/.venv/**", 
                "**/__pycache__/**",
            }, 
                               
            max_file_size=500000  # Skip files larger than 500KB
        )
        
        files = result["files"]
        stats = result["stats"]
        
        print(f"\nDownloaded {stats['downloaded_count']} files.")
        print(f"Skipped {stats['skipped_count']} files due to size limits or patterns.")
        print(f"Base path for relative paths: {stats['base_path']}")
        print(f"Include patterns: {stats['include_patterns']}")
        print(f"Exclude patterns: {stats['exclude_patterns']}")
        
        # Display all file paths in the dictionary
        print("\nFiles in dictionary:")
        for file_path in sorted(files.keys()):
            print(f"  {file_path}")
        
        # Example: accessing content of a specific file
        if files:
            sample_file = next(iter(files))
            print(f"Repository crawled successfully! Found {len(files)} files.")
            preview_file(files)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)