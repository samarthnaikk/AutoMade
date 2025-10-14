import os
import subprocess
import shutil
import sys

FILES_TO_PUBLISH = ['index.html', 'style.css', 'script.js']
BRANCH = 'gh-pages'
WORKER_DIR = '../theworker'


def publish_to_github_pages(repo_url):
    # Remove theworker directory if it exists
    if os.path.exists(WORKER_DIR):
        shutil.rmtree(WORKER_DIR)

    # Clone the GitHub repo into theworker
    subprocess.run(['git', 'clone', repo_url, WORKER_DIR], check=True)
    os.chdir(WORKER_DIR)

    # Create gh-pages branch (orphan)
    subprocess.run(['git', 'checkout', '--orphan', BRANCH])
    subprocess.run(['git', 'rm', '-rf', '.'], check=False)

    # Copy required files from original project
    project_dir = os.path.abspath(os.path.join(os.getcwd(), '../AutoMade'))
    for file in FILES_TO_PUBLISH:
        src = os.path.join(project_dir, file)
        dst = os.path.join(os.getcwd(), file)
        if os.path.exists(src):
            shutil.copy(src, dst)

    subprocess.run(['git', 'add'] + FILES_TO_PUBLISH)
    subprocess.run(['git', 'commit', '-m', 'Publish to GitHub Pages'], check=False)
    subprocess.run(['git', 'push', '-f', 'origin', BRANCH])

    print('Published to GitHub Pages!')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: python helper.py <github_repo_url>')
        sys.exit(1)
    publish_to_github_pages(sys.argv[1])
