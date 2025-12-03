import requests
import base64
import os
import tempfile
import git
import time
import fnmatch
import sys
from typing import Union, Set
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

def crawl_github_files(
    repo_url, 
    token=None, 
    max_file_size=1048576,
    use_relative_paths=False,
    include_patterns=None,
    exclude_patterns=None
):
    """
    Minimal GitHub repo crawler that fetches files based on patterns.
    
    Args:
        repo_url: GitHub repository URL
        token: GitHub access token
        max_file_size: Maximum file size to download in bytes
        use_relative_paths: Whether to use paths relative to the specified subdirectory
        include_patterns: Patterns of files to include
        exclude_patterns: Patterns of files to exclude
        
    Returns:
        Dictionary containing files and stats
    """
    # Normalize patterns to sets
    if include_patterns and isinstance(include_patterns, str):
        include_patterns = {include_patterns}
    if exclude_patterns and isinstance(exclude_patterns, str):
        exclude_patterns = {exclude_patterns}
        
    # File selection helper
    def should_include_file(file_path, file_name):
        if not include_patterns:
            return True
        include_file = any(fnmatch.fnmatch(file_name, pattern) for pattern in include_patterns)
        if exclude_patterns and include_file:
            exclude_file = any(fnmatch.fnmatch(file_path, pattern) for pattern in exclude_patterns)
            return not exclude_file
        return include_file

    # Handle SSH URLs with direct git clone
    if repo_url.startswith("git@") or repo_url.endswith(".git"):
        with tempfile.TemporaryDirectory() as tmpdirname:
            git.Repo.clone_from(repo_url, tmpdirname)
            files = {}
            skipped_files = []

            for root, _, filenames in os.walk(tmpdirname):
                for filename in filenames:
                    abs_path = os.path.join(root, filename)
                    rel_path = os.path.relpath(abs_path, tmpdirname)
                    
                    file_size = os.path.getsize(abs_path)
                    if file_size > max_file_size:
                        skipped_files.append((rel_path, file_size))
                        continue

                    if not should_include_file(rel_path, filename):
                        continue

                    try:
                        with open(abs_path, "r", encoding="utf-8") as f:
                            content = f.read()
                        files[rel_path] = content
                    except Exception:
                        pass

            return {
                "files": files,
                "stats": {
                    "downloaded_count": len(files),
                    "skipped_count": len(skipped_files),
                    "skipped_files": skipped_files,
                    "base_path": None,
                    "include_patterns": include_patterns,
                    "exclude_patterns": exclude_patterns
                }
            }

    # Parse HTTP GitHub URL
    print(f"Parsing URL: {repo_url}")
    parsed_url = urlparse(repo_url)
    path_parts = parsed_url.path.strip('/').split('/')
    
    owner = path_parts[0]
    repo = path_parts[1]
    
    # Setup API access
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"

    # Extract branch/commit ref and specific path
    ref = None
    specific_path = ""
    
    if len(path_parts) > 2 and path_parts[2] == 'tree':
        ref = path_parts[3]
        specific_path = '/'.join(path_parts[4:]) if len(path_parts) > 4 else ""
    
    # Storage for results
    files = {}
    skipped_files = []
    
    # Recursive file fetcher
    def fetch_contents(path):
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
        params = {"ref": ref} if ref else {}
        
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            return
        
        contents = response.json()
        contents = [contents] if not isinstance(contents, list) else contents
        
        for item in contents:
            item_path = item["path"]
            
            # Calculate relative path if needed
            rel_path = item_path
            if use_relative_paths and specific_path and item_path.startswith(specific_path):
                rel_path = item_path[len(specific_path):].lstrip('/')
            
            if item["type"] == "file":
                if not should_include_file(rel_path, item["name"]):
                    continue
                
                file_size = item.get("size", 0)
                if file_size > max_file_size:
                    skipped_files.append((item_path, file_size))
                    continue
                
                # Get file content - prefer direct download URL if available
                if "download_url" in item and item["download_url"]:
                    file_response = requests.get(item["download_url"], headers=headers)
                    if file_response.status_code == 200:
                        files[rel_path] = file_response.text
                else:
                    # Fall back to API content endpoint
                    content_data = requests.get(item["url"], headers=headers).json()
                    if content_data.get("encoding") == "base64" and "content" in content_data:
                        file_content = base64.b64decode(content_data["content"]).decode('utf-8')
                        files[rel_path] = file_content
            
            elif item["type"] == "dir":
                fetch_contents(item_path)
    
    # Start crawling
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

if __name__ == "__main__":
    try:
        github_token = os.environ.get("GITHUB_TOKEN")
        repo_url = os.environ.get("GITHUB_URL")
        print(f"Token: {github_token}")
        print(f"Repo URL: {repo_url}")
        
        
        result = crawl_github_files(
            repo_url, 
            token=github_token,
            use_relative_paths=True,
            include_patterns={"*.py", "*.md", "src/**/*.js","*.cs"},
            exclude_patterns={ 
                "tests/*", "**/node_modules/**", "**/.vscode/**", 
                "**/.venv/**", "**/__pycache__/**"
            },
            max_file_size=500000
        )
        
        files = result["files"]
        
        if files:
            print(f"Repository crawled successfully! Found {len(files)} files.")
    except Exception as e:
        sys.exit(1)