import requests
import sys
import time
from urllib.parse import urlparse
import re
# 替换为你的GitHub个人访问令牌
GITHUB_TOKEN = ''

# 输入文件和输出文件
INPUT_FILE = 'input.txt'
OUTPUT_FILE = 'output.txt'

headers = {
    'Authorization': f'token {GITHUB_TOKEN}',
    'Accept': 'application/vnd.github.v3+json'
}

def get_repo_owner_and_name(repo_url):
    """
    从仓库URL中提取所有者和仓库名
    """
    parsed_url = urlparse(repo_url)
    path_parts = parsed_url.path.strip('/').split('/')
    if len(path_parts) >= 2:
        owner, repo = path_parts[0], path_parts[1]
        return owner, repo
    else:
        return None, None

def get_commit_count(owner, repo):
    """
    获取仓库的总提交数
    """
    url = f'https://api.github.com/repos/{owner}/{repo}/contributors?per_page=100&anon=1'
    commit_count = 0
    page = 1
    while True:
        response = requests.get(url, headers=headers, params={'page': page})
        if response.status_code == 200:
            contributors = response.json()
            if not contributors:
                break
            for contributor in contributors:
                commit_count += contributor.get('contributions', 0)
            if 'next' in response.links:
                page += 1
            else:
                break
        elif response.status_code == 202:
            # GitHub 在后台生成统计数据，稍后重试
            print(f"Commit count data for {owner}/{repo} is being generated. Waiting...")
            time.sleep(3)
            continue
        else:
            print(f"Failed to fetch contributors for {owner}/{repo}: {response.status_code}")
            break
    return commit_count

def get_languages(owner, repo):
    """
    获取仓库的语言构成
    """
    url = f'https://api.github.com/repos/{owner}/{repo}/languages'
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        languages = response.json()
        return languages
    else:
        print(f"Failed to fetch languages for {owner}/{repo}: {response.status_code}")
        return {}

def get_repo_info(owner, repo):
    """
    获取仓库的详细信息，包括 Star 数和主要语言。
    """
    api_url = f'https://api.github.com/repos/{owner}/{repo}'
    response = requests.get(api_url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"无法获取仓库信息: {owner}/{repo} (状态码: {response.status_code})")
        return None
def main():
    try:
        with open(INPUT_FILE, 'r') as infile:
            repo_urls = [line.strip() for line in infile if line.strip()]
    except FileNotFoundError:
        print(f"输入文件 {INPUT_FILE} 未找到。")
        sys.exit(1)

    qualified_repos = []

    for repo_url in repo_urls:
        owner, repo = get_repo_owner_and_name(repo_url)
        if not owner or not repo:
            print(f"无法解析仓库URL: {repo_url}")
            continue

        print(f"正在处理仓库: {owner}/{repo}")

        # 获取提交数量
        commit_count = get_commit_count(owner, repo)
        print(f"提交数量: {commit_count}")

        repo_info = get_repo_info(owner, repo)
        if not repo_info:
            continue

        stars = repo_info.get('stargazers_count', 0)
        if stars < 10:
            print(f"跳过 {owner}/{repo}，Star 数不足: {stars}")
            continue
        print(f"{owner}/{repo} 满足的 Star 数: {stars}")
        if commit_count <= 50:
            print(f"提交数量不满足 >50 的条件，跳过。")
            continue

        # 获取语言构成
        languages = get_languages(owner, repo)
        if not languages:
            print(f"无法获取语言信息，跳过。")
            continue

        total_bytes = sum(languages.values())
        if total_bytes == 0:
            print(f"仓库没有代码文件，跳过。")
            continue

        java_bytes = languages.get('Java', 0)
        java_percentage = (java_bytes / total_bytes) * 100
        print(f"Java占比: {java_percentage:.2f}%")

        if java_percentage > 50:
            print(f"符合条件，添加到结果中。")
            qualified_repos.append(repo_url)
            # 将符合条件的仓库写入输出文件
            with open(OUTPUT_FILE, 'a') as outfile:
                outfile.write(repo_url + '\n')
        else:
            print(f"Java占比不满足 >50%，跳过。")

        # 为避免触发速率限制，稍作延迟
        # time.sleep(1)



    print(f"过滤完成，共找到 {len(qualified_repos)} 个符合条件的仓库。结果已保存到 {OUTPUT_FILE}。")

    deduplicate_github_urls(OUTPUT_FILE, OUTPUT_FILE)


def extract_repo_name(url):
    """
    从GitHub仓库URL中提取仓库名称。
    例如:
    输入: https://github.com/username/repo-name
    输出: repo-name
    """
    pattern = r'^https?://github\.com/[^/]+/([^/]+)(?:\.git)?/?$'
    match = re.match(pattern, url.strip())
    if match:
        return match.group(1)
    else:
        return None

def deduplicate_github_urls(input_file, output_file):
    seen_repos = set()
    with open(input_file, 'r', encoding='utf-8') as infile, \
         open(output_file, 'w', encoding='utf-8') as outfile:
        for line in infile:
            repo_url = line.strip()
            if not repo_url:
                continue  # 跳过空行
            repo_name = extract_repo_name(repo_url)
            if repo_name is None:
                print(f"警告: 无法解析URL: {repo_url}", file=sys.stderr)
                continue
            if repo_name not in seen_repos:
                seen_repos.add(repo_name)
                outfile.write(repo_url + '\n')
if __name__ == '__main__':
    main()
