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

# def preview_file(files):
#     if not files:
#         return
    
#     sorted_files = sorted(files.keys())
#     print("\nAvailable files:")
#     for i, file_path in enumerate(sorted_files, 1):
#         print(f"[{i}] {file_path}")
    
#     while True:
#         choice = input("\nEnter file number to preview (or 'q' to quit): ")
        
#         if choice.lower() == 'q':
#             return
                
#         try:
#             file_index = int(choice) - 1
#             if 0 <= file_index < len(sorted_files):
#                 selected_file = sorted_files[file_index]
#                 break
#             else:
#                 print(f"Invalid selection. Please enter a number between 1 and {len(sorted_files)}.")
#         except ValueError:
#             print("Please enter a valid number or 'q' to quit.")
    
#     file_content = files[selected_file]
#     file_size = len(file_content)
    
#     print("\n" + "="*50)
#     print(f"File: {selected_file}")
#     print(f"Size: {file_size} characters")
    
#     file_extension = selected_file.split('.')[-1] if '.' in selected_file else 'unknown'
#     file_type_descriptions = {
#         'py': 'Python source code', 'md': 'Markdown document', 'txt': 'Text file',
#         'json': 'JSON data file', 'yml': 'YAML configuration file', 
#         'yaml': 'YAML configuration file', 'js': 'JavaScript source code',
#         'html': 'HTML document', 'css': 'CSS stylesheet',
#         'gitignore': 'Git ignore rules', 'env': 'Environment variables file'
#     }
    
#     file_type = file_type_descriptions.get(file_extension, f"File with .{file_extension} extension")
#     print(f"Type: {file_type}")
#     print("="*50)
    
#     preview_lines = 10
#     try:
#         preview_input = input(f"\nHow many lines to preview? (default: {preview_lines}): ")
#         if preview_input.strip():
#             preview_lines = int(preview_input)
#     except ValueError:
#         pass
    
#     lines = file_content.split('\n')
#     print("\nContent preview:")
#     print("-"*50)
    
#     for i, line in enumerate(lines[:preview_lines], 1):
#         print(f"{i:3d} | {line}")
    
#     if len(lines) > preview_lines:
#         print(f"\n... and {len(lines) - preview_lines} more lines")
    
#     while True:
#         action = input("\nOptions: [m]ore lines, [a]ll content, [f]ind text, [b]ack to file list, [q]uit: ").lower()
        
#         if action == 'm':
#             try:
#                 more_lines = int(input("How many more lines? "))
#                 print("\nContent continued:")
#                 print("-"*50)
#                 for i, line in enumerate(lines[preview_lines:preview_lines+more_lines], preview_lines+1):
#                     print(f"{i:3d} | {line}")
#                 preview_lines += more_lines
#             except ValueError:
#                 print("Please enter a valid number.")
                
#         elif action == 'a':
#             print("\nFull content:")
#             print("-"*50)
#             for i, line in enumerate(lines, 1):
#                 print(f"{i:3d} | {line}")
                
#         elif action == 'f':
#             search_term = input("Enter text to find: ")
#             if search_term:
#                 print(f"\nLines containing '{search_term}':")
#                 print("-"*50)
#                 found = False
#                 for i, line in enumerate(lines, 1):
#                     if search_term.lower() in line.lower():
#                         print(f"{i:3d} | {line}")
#                         found = True
#                 if not found:
#                     print(f"No matches found for '{search_term}'")
            
#         elif action == 'b':
#             preview_file(files)
#             return
            
#         elif action == 'q':
#             return

# def ensure_github_url():
#     env_locations = [
#         '.env', '../.env',
#         os.path.join(os.path.dirname(__file__), '../.env'),
#         os.path.expanduser('~/.env')
#     ]
    
#     if not os.environ.get("GITHUB_URL") and not os.environ.get("GITHUB_TOKEN"):
#         for env_path in env_locations:
#             if os.path.exists(env_path):
#                 load_dotenv(env_path)
#                 break
    
#     github_url = os.environ.get("GITHUB_URL")
#     if not github_url:
#         for var_name in ["REPO_URL", "REPOSITORY_URL", "GIT_REPO"]:
#             github_url = os.environ.get(var_name)
#             if github_url:
#                 os.environ["GITHUB_URL"] = github_url
#                 break
    
#     if not github_url:
#         raise Exception("GITHUB_URL not set in environment variables")
    
#     return github_url

def crawl_github_files(
    repo_url, 
    token=None, 
    max_file_size=1048576,
    use_relative_paths=False,
    include_patterns=None,
    exclude_patterns=None
):
    if include_patterns and isinstance(include_patterns, str):
        include_patterns = {include_patterns}
    if exclude_patterns and isinstance(exclude_patterns, str):
        exclude_patterns = {exclude_patterns}

    def should_include_file(file_path, file_name):
        if not include_patterns:
            include_file = True
        else:
            include_file = any(fnmatch.fnmatch(file_name, pattern) for pattern in include_patterns)

        if exclude_patterns and include_file:
            exclude_file = any(fnmatch.fnmatch(file_path, pattern) for pattern in exclude_patterns)
            return not exclude_file

        return include_file

    is_ssh_url = repo_url.startswith("git@") or repo_url.endswith(".git")

    if is_ssh_url:
        with tempfile.TemporaryDirectory() as tmpdirname:
            try:
                git.Repo.clone_from(repo_url, tmpdirname)
            except Exception as e:
                return {"files": {}, "stats": {"error": str(e)}}

            files = {}
            skipped_files = []

            for root, _, filenames in os.walk(tmpdirname):
                for filename in filenames:
                    abs_path = os.path.join(root, filename)
                    rel_path = os.path.relpath(abs_path, tmpdirname)

                    try:
                        file_size = os.path.getsize(abs_path)
                    except OSError:
                        continue

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
                    "exclude_patterns": exclude_patterns,
                    "source": "ssh_clone"
                }
            }

    parsed_url = urlparse(repo_url)
    path_parts = parsed_url.path.strip('/').split('/')
    
    if len(path_parts) < 2:
        raise ValueError(f"Invalid GitHub URL: {repo_url}")
    
    owner = path_parts[0]
    repo = path_parts[1]
    
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"

    def fetch_branches(owner, repo):
        url = f"https://api.github.com/repos/{owner}/{repo}/branches"
        response = requests.get(url, headers=headers)
        return response.json() if response.status_code == 200 else []

    def check_tree(owner, repo, tree):
        url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{tree}"
        response = requests.get(url, headers=headers)
        return response.status_code == 200

    if len(path_parts) > 2 and 'tree' == path_parts[2]:
        join_parts = lambda i: '/'.join(path_parts[i:])

        branches = fetch_branches(owner, repo)
        branch_names = map(lambda branch: branch.get("name"), branches)

        if len(branches) == 0:
            return

        relevant_path = join_parts(3)
        filter_gen = (name for name in branch_names if relevant_path.startswith(name))
        ref = next(filter_gen, None)

        if ref == None:
            tree = path_parts[3]
            ref = tree if check_tree(owner, repo, tree) else None

        if ref == None:
            return

        part_index = 5 if '/' in ref else 4
        specific_path = join_parts(part_index) if part_index < len(path_parts) else ""
    else:
        ref = None
        specific_path = ""
    
    files = {}
    skipped_files = []
    
    def fetch_contents(path):
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
        params = {"ref": ref} if ref != None else {}
        
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 403 and 'rate limit exceeded' in response.text.lower():
            reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
            wait_time = max(reset_time - time.time(), 0) + 1
            time.sleep(wait_time)
            return fetch_contents(path)
            
        if response.status_code != 200:
            return
        
        contents = response.json()
        
        if not isinstance(contents, list):
            contents = [contents]
        
        for item in contents:
            item_path = item["path"]
            
            if use_relative_paths and specific_path:
                if item_path.startswith(specific_path):
                    rel_path = item_path[len(specific_path):].lstrip('/')
                else:
                    rel_path = item_path
            else:
                rel_path = item_path
            
            if item["type"] == "file":
                if not should_include_file(rel_path, item["name"]):
                    continue
                
                file_size = item.get("size", 0)
                if file_size > max_file_size:
                    skipped_files.append((item_path, file_size))
                    continue
                
                if "download_url" in item and item["download_url"]:
                    file_url = item["download_url"]
                    file_response = requests.get(file_url, headers=headers)
                    
                    content_length = int(file_response.headers.get('content-length', 0))
                    if content_length > max_file_size:
                        skipped_files.append((item_path, content_length))
                        continue
                        
                    if file_response.status_code == 200:
                        files[rel_path] = file_response.text
                else:
                    content_response = requests.get(item["url"], headers=headers)
                    if content_response.status_code == 200:
                        content_data = content_response.json()
                        if content_data.get("encoding") == "base64" and "content" in content_data:
                            if len(content_data["content"]) * 0.75 > max_file_size:
                                estimated_size = int(len(content_data["content"]) * 0.75)
                                skipped_files.append((item_path, estimated_size))
                                continue
                                
                            file_content = base64.b64decode(content_data["content"]).decode('utf-8')
                            files[rel_path] = file_content
            
            elif item["type"] == "dir":
                fetch_contents(item_path)
    
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
        # git_url = ensure_github_url()
        github_token = os.environ.get("GITHUB_TOKEN")
        repo_url = os.environ.get("GITHUB_URL")
        
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
            # preview_file(files)
    except Exception as e:
        sys.exit(1)