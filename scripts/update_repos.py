#!/usr/bin/env python3
"""
GitHub APIを使用してリポジトリ情報を取得し、JSONファイルを更新するスクリプト
"""

import json
import os
import time
from datetime import datetime, timedelta
import requests
from typing import List, Dict, Optional

# GitHub API設定
GITHUB_API_URL = "https://api.github.com"

# 出力ファイルパス
ASSETS_DIR = "assets"
POPULAR_FILE = f"{ASSETS_DIR}/popular.json"
NEW_FILE = f"{ASSETS_DIR}/new.json"
CATEGORIES_FILE = f"{ASSETS_DIR}/categories.json"

# カテゴリー別の検索キーワード（LLM/AI/ML/NLPに焦点を当てる）
CATEGORIES = {
    "LLM & 生成AI": ["llm", "large language model", "gpt", "chatbot", "generative-ai"],
    "機械学習": ["machine learning", "deep learning", "tensorflow", "pytorch"],
    "自然言語処理": ["nlp", "natural language processing", "transformers", "bert"],
    "AIツール": ["ai tools", "copilot", "ai assistant", "ai agent"],
    "データサイエンス": ["data science", "jupyter", "pandas", "data analysis"],
    "コンピュータビジョン": ["computer vision", "opencv", "image recognition", "yolo"],
    "MLOps": ["mlops", "ml infrastructure", "model deployment", "mlflow"],
}


def get_headers() -> Dict[str, str]:
    """GitHub API用のヘッダーを取得"""
    headers = {
        "Accept": "application/vnd.github.v3+json",
    }
    return headers


def check_rate_limit() -> Dict:
    """GitHub APIのレート制限を確認"""
    url = f"{GITHUB_API_URL}/rate_limit"
    try:
        response = requests.get(url, headers=get_headers())
        response.raise_for_status()
        rate_data = response.json()
        core = rate_data.get("rate", {})
        print(f"Rate Limit: {core.get('remaining')}/{core.get('limit')} remaining")
        print(f"Reset at: {datetime.fromtimestamp(core.get('reset', 0)).strftime('%Y-%m-%d %H:%M:%S')}")
        return core
    except requests.exceptions.RequestException as e:
        print(f"Error checking rate limit: {e}")
        return {}


def search_repositories(query: str, sort: str = "stars", per_page: int = 30) -> List[Dict]:
    """GitHubでリポジトリを検索"""
    url = f"{GITHUB_API_URL}/search/repositories"
    params = {
        "q": query,
        "sort": sort,
        "order": "desc",
        "per_page": per_page,
    }
    
    try:
        response = requests.get(url, headers=get_headers(), params=params)
        
        # レート制限のチェック
        remaining = response.headers.get('X-RateLimit-Remaining')
        if remaining:
            print(f"  API calls remaining: {remaining}")
        
        response.raise_for_status()
        data = response.json()
        
        # API制限に近づいたら警告
        if remaining and int(remaining) < 10:
            print(f"⚠️ WARNING: Only {remaining} API calls remaining!")
        
        # レート制限を超えないよう少し待機
        time.sleep(0.5)
        
        return data.get("items", [])
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            print(f"❌ Rate limit exceeded! Please wait and try again later.")
            print(f"Response: {e.response.text}")
        else:
            print(f"Error searching repositories: {e}")
        return []
    except requests.exceptions.RequestException as e:
        print(f"Error searching repositories: {e}")
        return []


def format_repo_data(repo: Dict, affiliate_link: Optional[str] = None) -> Dict:
    """リポジトリデータを必要な情報のみに整形"""
    data = {
        "name": repo.get("full_name", ""),
        "html_url": repo.get("html_url", ""),
        "description": repo.get("description", ""),
        "stargazers_count": repo.get("stargazers_count", 0),
        "forks_count": repo.get("forks_count", 0),
        "language": repo.get("language", ""),
        "updated_at": repo.get("updated_at", ""),
        "created_at": repo.get("created_at", ""),
        "topics": repo.get("topics", []),
    }
    
    # アフィリエイトリンクがある場合は追加
    if affiliate_link:
        data["affiliate_link"] = affiliate_link
    
    return data


def get_popular_repos() -> List[Dict]:
    """人気のリポジトリを取得（スター数順、LLM/AI/ML/NLPにフォーカス）"""
    print("Fetching popular repositories (LLM/AI/ML/NLP focus)...")
    # LLM、AI、ML、NLPに関連するトピックでフィルタ（OR演算子なしで複数トピック）
    query = "stars:>5000 topic:machine-learning"
    repos = search_repositories(query, sort="stars", per_page=50)
    return [format_repo_data(repo) for repo in repos]


def get_trending_repos() -> List[Dict]:
    """トレンドリポジトリを取得（最近1週間でスターが増えた順）"""
    print("Fetching trending repositories (last 7 days)...")
    date_7_days_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    # 過去1週間で更新され、一定以上のスターを持つリポジトリ
    query = f"pushed:>{date_7_days_ago} stars:>1000 topic:ai"
    repos = search_repositories(query, sort="stars", per_page=50)
    return [format_repo_data(repo) for repo in repos]


def get_new_repos() -> List[Dict]:
    """新着リポジトリを取得（作成日順、過去30日間、AI/ML関連）"""
    print("Fetching new repositories (last 30 days, AI/ML focus)...")
    date_30_days_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    query = f"created:>{date_30_days_ago} stars:>50"
    repos = search_repositories(query, sort="stars", per_page=50)
    return [format_repo_data(repo) for repo in repos]


def get_category_repos() -> Dict[str, List[Dict]]:
    """カテゴリー別にリポジトリを取得"""
    print("Fetching repositories by category...")
    category_repos = {}
    
    for category, keywords in CATEGORIES.items():
        print(f"  - {category}")
        # カテゴリーの最初のキーワードで検索
        query = f"{keywords[0]} stars:>1000"
        repos = search_repositories(query, sort="stars", per_page=20)
        category_repos[category] = [format_repo_data(repo) for repo in repos]
    
    return category_repos


def save_json(data: any, filepath: str, metadata: Optional[Dict] = None):
    """データをJSONファイルとして保存（メタデータ付き）"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    # メタデータを含むJSON構造を作成
    output = {
        "metadata": metadata or {
            "updated_at": datetime.now().isoformat(),
            "source": "GitHub API",
            "api_url": "https://api.github.com/search/repositories",
        },
        "repositories": data if isinstance(data, list) else data,
    }
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"✓ Saved: {filepath}")


def main():
    """メイン処理"""
    print("=" * 60)
    print("Starting repository data update...")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 60)
    
    # レート制限を確認
    print("\nChecking API rate limit...")
    check_rate_limit()
    
    try:
        # メタデータの作成
        update_time = datetime.now().isoformat()
        
        # 人気順のリポジトリを取得・保存
        print("\n" + "-" * 60)
        popular_repos = get_popular_repos()
        save_json(popular_repos, POPULAR_FILE, {
            "updated_at": update_time,
            "source": "GitHub API",
            "api_url": "https://api.github.com/search/repositories",
            "description": "Popular repositories with LLM/AI/ML/NLP focus",
            "count": len(popular_repos),
        })
        
        # トレンドリポジトリを取得・保存（新規追加）
        print("\n" + "-" * 60)
        trending_repos = get_trending_repos()
        save_json(trending_repos, f"{ASSETS_DIR}/trending.json", {
            "updated_at": update_time,
            "source": "GitHub API",
            "api_url": "https://api.github.com/search/repositories",
            "description": "Trending repositories in the last 7 days",
            "count": len(trending_repos),
        })
        
        # 新着リポジトリを取得・保存
        print("\n" + "-" * 60)
        new_repos = get_new_repos()
        save_json(new_repos, NEW_FILE, {
            "updated_at": update_time,
            "source": "GitHub API",
            "api_url": "https://api.github.com/search/repositories",
            "description": "Recently created repositories (last 30 days)",
            "count": len(new_repos),
        })
        
        # カテゴリー別リポジトリを取得・保存
        print("\n" + "-" * 60)
        category_repos = get_category_repos()
        save_json(category_repos, CATEGORIES_FILE, {
            "updated_at": update_time,
            "source": "GitHub API",
            "api_url": "https://api.github.com/search/repositories",
            "description": "Repositories organized by AI/ML categories",
            "categories": list(category_repos.keys()),
            "count": sum(len(repos) for repos in category_repos.values()),
        })
        
        print("\n" + "=" * 60)
        print("✓ Update completed successfully!")
        print(f"  Popular repos: {len(popular_repos)}")
        print(f"  Trending repos: {len(trending_repos)}")
        print(f"  New repos: {len(new_repos)}")
        print(f"  Categories: {len(category_repos)}")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error during update: {e}")
        raise


if __name__ == "__main__":
    main()
