
import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import json
import google.generativeai as genai
from main import *  # Import all helper functions

load_dotenv()
SECRET_KEY = os.getenv('secretkey')

app = Flask(__name__)

@app.route('/task', methods=['POST'])
def handle_task():
    data = request.get_json(silent=True)
    print('Received JSON at /task:', data)
    if not data:
        return jsonify({'error': 'Invalid JSON'}), 400
    if 'secret' in data and data['secret'] == SECRET_KEY:
        print('Secret verified, saving JSON...')
        with open('receivedjson.json', 'w') as f:
            json.dump(data, f, indent=2)
        print('JSON saved. Asking AI agent to generate files...')
        try:
            # Import required modules at the beginning
            import re
            from pydantic import BaseModel, Field
            import requests
            import base64
            import shutil
            
            # Check round parameter for repo logic
            round_num = data.get('round', 1)
            task_name = data.get('task', 'default-task')
            print(f'Round: {round_num}, Task: {task_name}')
            
            # Setup worker directory and handle repo creation/update based on round
            worker_dir = os.path.abspath(os.path.join(os.getcwd(), '../theworker'))
            os.makedirs(worker_dir, exist_ok=True)
            
            github_token = os.getenv('GITHUB_TOKEN')
            github_username = 'samarthnaikk'  # constant username
            
            if round_num == 1:
                print('Round 1: Creating new repository...')
                # Delete existing .git if it exists
                git_dir = os.path.join(worker_dir, '.git')
                if os.path.exists(git_dir):
                    shutil.rmtree(git_dir)
                    print('Deleted existing .git directory')
                
                # Create new GitHub repository using GitHub API
                repo_create_url = 'https://api.github.com/user/repos'
                headers = {
                    'Authorization': f'token {github_token}',
                    'Accept': 'application/vnd.github.v3+json'
                }
                repo_data = {
                    'name': task_name,
                    'description': f'Generated project: {task_name}',
                    'public': True,
                    'auto_init': False
                }
                repo_resp = requests.post(repo_create_url, headers=headers, json=repo_data)
                print(f'GitHub repo creation response: {repo_resp.status_code} {repo_resp.text}')
                
                if repo_resp.status_code == 201:
                    repo_full_name = f'{github_username}/{task_name}'
                    print(f'Successfully created repository: {repo_full_name}')
                else:
                    repo_full_name = f'{github_username}/{task_name}'
                    print(f'Repository creation failed. Status: {repo_resp.status_code}')
                    if repo_resp.status_code == 403:
                        print('ERROR: GitHub token lacks repository creation permissions.')
                        print('Please ensure your token has "repo" scope and create the repository manually:')
                        print(f'1. Go to https://github.com/new')
                        print(f'2. Create a public repository named: {task_name}')
                        print(f'3. Enable GitHub Pages in repository settings')
                        print(f'Or update your token with "repo" scope at: https://github.com/settings/tokens')
                        return jsonify({'error': 'Repository creation failed - insufficient token permissions', 
                                      'action_required': f'Create repository manually: {repo_full_name}'}), 403
                    elif repo_resp.status_code == 422:
                        print(f'Repository {repo_full_name} already exists, proceeding with updates...')
                    else:
                        print(f'Unexpected error creating repository: {repo_resp.text}')
                        return jsonify({'error': 'Repository creation failed', 'details': repo_resp.text}), 500
            else:
                print('Round 2: Updating existing repository...')
                repo_full_name = data.get('repo_full_name', f'{github_username}/{task_name}')
                print(f'Using existing repository: {repo_full_name}')
            
            api_key = os.getenv('GEMINI_API_KEY')
            brief = data.get('brief', '')
            print(f'Calling Gemini API with google-generativeai, brief: {brief}')
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            response = model.generate_content(brief)
            print(f'Gemini API response: {response.text}')
            # Use Pydantic to parse markdown/code block for file content

            class GeminiFile(BaseModel):
                filename: str = Field(...)
                content: str = Field(...)

            # Use the determined repo_full_name for file operations
            checks = data.get('checks', [])
            created_files = set()
            # Try to create files mentioned in checks
            for check in checks:
                print(f'Processing check: {check}')
                
                # Enhanced file detection - look for common file patterns or treat check as filename
                filename = None
                
                # Try to match common file patterns first
                file_patterns = {
                    r'index\.html': 'index.html',
                    r'README\.md': 'README.md', 
                    r'LICENSE': 'LICENSE',
                    r'style\.css': 'style.css',
                    r'script\.js': 'script.js',
                    r'main\.js': 'main.js',
                    r'app\.js': 'app.js',
                    r'package\.json': 'package.json'
                }
                
                for pattern, file_name in file_patterns.items():
                    if re.search(pattern, check, re.IGNORECASE):
                        filename = file_name
                        break
                
                # If no pattern matched, try to extract filename from the check string
                if not filename:
                    # Look for file extensions
                    ext_match = re.search(r'(\w+\.(html|css|js|md|json|txt|py))', check, re.IGNORECASE)
                    if ext_match:
                        filename = ext_match.group(1)
                    else:
                        # Default to treating the whole check as a filename requirement
                        if '.' in check and len(check.split()) == 1:
                            filename = check.strip()
                        else:
                            # Generate a relevant filename based on the check description
                            print(f'No specific filename found in check: {check}, skipping...')
                            continue
                
                if filename:
                    print(f'Creating file: {filename} for check: {check}')
                    
                    # Special handling for README to make it professional
                    if filename.lower() == 'readme.md':
                        file_prompt = f"""Create a professional README.md file for this project with the following requirements:
                        
Project: {brief}

Include these sections:
1. Project title and brief description
2. Features/Overview
3. Installation instructions 
4. Usage guide
5. Technologies used
6. Contributing guidelines
7. License information

Make it well-structured, professional, and include proper markdown formatting. Focus on clarity and completeness."""
                    else:
                        file_prompt = f"Generate professional, well-structured content for {filename} based on this project requirement: {brief}. Check requirement: {check}"
                    
                    file_response = model.generate_content(file_prompt)
                    code_block_match = re.search(r'`{3}[a-zA-Z]*\n([\s\S]*?)`{3}', file_response.text)
                    file_content = code_block_match.group(1).strip() if code_block_match else file_response.text
                    file_path = os.path.join(worker_dir, filename)
                    print(f'Creating file: {file_path}')
                    with open(file_path, 'w') as f:
                        f.write(file_content)
                    print(f'File {file_path} created.')
                    created_files.add(filename)
                    # Add, commit, and push using GitHub API
                    commit_message = f"Update {filename} via AI task"
                    branch = 'main'
                    with open(file_path, 'rb') as f:
                        content_b64 = base64.b64encode(f.read()).decode('utf-8')
                    file_url = f'https://api.github.com/repos/{repo_full_name}/contents/{filename}'
                    headers = {
                        'Authorization': f'token {github_token}',
                        'Accept': 'application/vnd.github.v3+json'
                    }
                    data_payload = {
                        'message': commit_message,
                        'content': content_b64,
                        'branch': branch
                    }
                    # Check if file exists to get sha
                    sha = None
                    sha_resp = requests.get(file_url, headers=headers)
                    if sha_resp.status_code == 200:
                        sha = sha_resp.json().get('sha')
                        print(f'Existing file sha: {sha}')
                    if sha:
                        data_payload['sha'] = sha
                    resp = requests.put(file_url, headers=headers, json=data_payload)
                    print(f'GitHub API file update response: {resp.status_code} {resp.text}')
            # Also create index.html if found in Gemini response and not already created
            code_block_match = re.search(r'`{3}html\n([\s\S]*?)`{3}', response.text)
            if code_block_match and 'index.html' not in created_files:
                file_content = code_block_match.group(1).strip()
                filename = 'index.html'
                file_path = os.path.join(worker_dir, filename)
                print(f'Creating file: {file_path}')
                with open(file_path, 'w') as f:
                    f.write(file_content)
                print(f'File {file_path} created.')
                # Add, commit, and push using GitHub API
                commit_message = f"Update {filename} via AI task"
                branch = 'main'
                with open(file_path, 'rb') as f:
                    content_b64 = base64.b64encode(f.read()).decode('utf-8')
                file_url = f'https://api.github.com/repos/{repo_full_name}/contents/{filename}'
                headers = {
                    'Authorization': f'token {github_token}',
                    'Accept': 'application/vnd.github.v3+json'
                }
                data_payload = {
                    'message': commit_message,
                    'content': content_b64,
                    'branch': branch
                }
                # Check if file exists to get sha
                sha = None
                sha_resp = requests.get(file_url, headers=headers)
                if sha_resp.status_code == 200:
                    sha = sha_resp.json().get('sha')
                    print(f'Existing file sha: {sha}')
                if sha:
                    data_payload['sha'] = sha
                resp = requests.put(file_url, headers=headers, json=data_payload)
                print(f'GitHub API file update response: {resp.status_code} {resp.text}')
            else:
                print('Gemini API did not return a code block. No file created.')
        
            # Enable GitHub Pages after files are pushed (if not already enabled)
            try:
                print('Checking/enabling GitHub Pages...')
                pages_enable_url = f'https://api.github.com/repos/{repo_full_name}/pages'
                headers = {
                    'Authorization': f'token {github_token}',
                    'Accept': 'application/vnd.github.v3+json'
                }
                
                # Check if Pages is already enabled
                pages_check_resp = requests.get(pages_enable_url, headers=headers)
                
                if pages_check_resp.status_code == 404:
                    print('GitHub Pages not enabled, enabling now...')
                    # Enable GitHub Pages
                    pages_data = {
                        'source': {
                            'branch': 'main',
                            'path': '/'
                        }
                    }
                    pages_enable_resp = requests.post(pages_enable_url, headers=headers, json=pages_data)
                    print(f'GitHub Pages enable response: {pages_enable_resp.status_code} {pages_enable_resp.text}')
                else:
                    print(f'GitHub Pages already enabled: {pages_check_resp.status_code}')
                    
            except Exception as e:
                print(f'Error enabling GitHub Pages: {e}')
        
            # Trigger GitHub Pages build after all files are pushed
            try:
                pages_url = f'https://api.github.com/repos/{repo_full_name}/pages/builds'
                headers = {
                    'Authorization': f'token {github_token}',
                    'Accept': 'application/vnd.github.v3+json'
                }
                pages_resp = requests.post(pages_url, headers=headers)
                print(f'GitHub Pages build trigger response: {pages_resp.status_code} {pages_resp.text}')
            except Exception as e:
                print(f'Error triggering GitHub Pages build: {e}')
                
        except Exception as e:
            print(f'Error generating files: {e}')
            return jsonify({'status': 'error', 'details': str(e)}), 500
        
        # Prepare response with repository links
        repo_url = f'https://github.com/{repo_full_name}'
        pages_url = f'https://{github_username}.github.io/{task_name}'
        
        print('All tasks completed.')
        print(f'Repository: {repo_url}')
        print(f'GitHub Pages: {pages_url}')
        
        return jsonify({
            'status': 'OK',
            'repository': {
                'name': task_name,
                'full_name': repo_full_name,
                'url': repo_url,
                'pages_url': pages_url
            },
            'round': round_num,
            'files_created': list(created_files)
        }), 200
    else:
        print('Unauthorized: secret mismatch.')
        return jsonify({'error': 'Unauthorized'}), 403

@app.route('/')
def health():
    return 'API is running!'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7860)
