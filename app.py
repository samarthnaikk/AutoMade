
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
            api_key = os.getenv('GEMINI_API_KEY')
            brief = data.get('brief', '')
            print(f'Calling Gemini API with google-generativeai, brief: {brief}')
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            response = model.generate_content(brief)
            print(f'Gemini API response: {response.text}')
            # Use Pydantic to parse markdown/code block for file content
            import re
            from pydantic import BaseModel, Field
            import requests
            import base64

            class GeminiFile(BaseModel):
                filename: str = Field(...)
                content: str = Field(...)

            # Look for markdown code blocks with filenames
            worker_dir = os.path.abspath(os.path.join(os.getcwd(), '../theworker'))
            os.makedirs(worker_dir, exist_ok=True)
            checks = data.get('checks', [])
            created_files = set()
            # Try to create files mentioned in checks
            for check in checks:
                # Simple heuristic: look for file names in check string
                import re
                match = re.search(r'(index\.html|README\.md|LICENSE|style\.css|script\.js)', check, re.IGNORECASE)
                if match:
                    filename = match.group(1)
                    # Ask Gemini for content for each file
                    file_prompt = f"Generate the content for {filename} as required for this app: {brief}"
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
                    github_token = os.getenv('GITHUB_TOKEN')
                    repo_full_name = data.get('repo_full_name')
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
                github_token = os.getenv('GITHUB_TOKEN')
                repo_full_name = data.get('repo_full_name')
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
        except Exception as e:
            print(f'Error generating files: {e}')
            return jsonify({'status': 'error', 'details': str(e)}), 500
        print('All tasks completed.')
        return jsonify({'status': 'OK'}), 200
    else:
        print('Unauthorized: secret mismatch.')
        return jsonify({'error': 'Unauthorized'}), 403

@app.route('/')
def health():
    return 'API is running!'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7860)
