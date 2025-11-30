#!/usr/bin/env python3
"""
This is a script to update repository data using the GitHub API.
"""

import json
import os
import time
from datetime import datetime, timedelta
import requests
from typing import List, Dict, Optional

GITHUB_API_URL = "https://api.github.com"

# Output file paths
ASSETS_DIR = "assets"
POPULAR_FILE = f"{ASSETS_DIR}/popular.json"
NEW_FILE = f"{ASSETS_DIR}/new.json"
CATEGORIES_FILE = f"{ASSETS_DIR}/categories.json"

# Search keywords by category (focusing on LLM/AI/ML/NLP)
CATEGORIES = {
    "LLM and Generative AI": ["llm", "large language model", "gpt", "chatbot", "generative-ai"],
    "Machine Learning": ["machine learning", "deep learning", "tensorflow", "pytorch"],
    "Natural Language Processing": ["nlp", "natural language processing", "transformers", "bert"],
    "AI Tools": ["ai tools", "copilot", "ai assistant", "ai agent"],
    "Data Science": ["data science", "jupyter", "pandas", "data analysis"],
    "Computer Vision": ["computer vision", "opencv", "image recognition", "yolo"],
    "MLOps": ["mlops", "ml infrastructure", "model deployment", "mlflow"],
}


def get_headers() -> Dict[str, str]:
    """Get headers for GitHub API requests"""
    headers = {
        "Accept": "application/vnd.github.v3+json",
    }
    return headers


def check_rate_limit() -> Dict:
    """Check GitHub API rate limit"""
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
    """Search GitHub repositories based on a query"""
    url = f"{GITHUB_API_URL}/search/repositories"
    params = {
        "q": query,
        "sort": sort,
        "order": "desc",
        "per_page": per_page,
    }
    
    try:
        response = requests.get(url, headers=get_headers(), params=params)
        
        # Check rate limit
        remaining = response.headers.get('X-RateLimit-Remaining')
        if remaining:
            print(f"  API calls remaining: {remaining}")
        
        response.raise_for_status()
        data = response.json()
        
        if remaining and int(remaining) < 10:
            print(f"⚠️ WARNING: Only {remaining} API calls remaining!")

        # Wait a bit to avoid hitting rate limits
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
    """Format repository data to include only necessary information"""
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
    
    if affiliate_link:
        data["affiliate_link"] = affiliate_link
    
    return data


def get_popular_repos() -> List[Dict]:
    print("Fetching popular repositories (LLM/AI/ML/NLP focus)...")
    # LLM、AI、ML、NLPに関連するトピックでフィルタ（OR演算子なしで複数トピック）
    query = "stars:>5000 topic:machine-learning"
    repos = search_repositories(query, sort="stars", per_page=50)
    return [format_repo_data(repo) for repo in repos]


def get_trending_repos() -> List[Dict]:
    """Get trending repositories (sorted by stars gained in the last week)"""
    print("Fetching trending repositories (last 7 days)...")
    date_7_days_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    # Repositories updated in the last week with a certain number of stars
    query = f"pushed:>{date_7_days_ago} stars:>1000 topic:ai"
    repos = search_repositories(query, sort="stars", per_page=50)
    return [format_repo_data(repo) for repo in repos]


def get_new_repos() -> List[Dict]:
    """Get new repositories (sorted by creation date, last 30 days, AI/ML focus)"""
    print("Fetching new repositories (last 30 days, AI/ML focus)...")
    date_30_days_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    query = f"created:>{date_30_days_ago} stars:>50"
    repos = search_repositories(query, sort="stars", per_page=50)
    return [format_repo_data(repo) for repo in repos]


def get_category_repos() -> Dict[str, List[Dict]]:
    """Get repositories by category"""
    print("Fetching repositories by category...")
    category_repos = {}
    
    for category, keywords in CATEGORIES.items():
        print(f"  - {category}")
        # Search using the first keyword of the category
        query = f"{keywords[0]} stars:>1000"
        repos = search_repositories(query, sort="stars", per_page=20)
        category_repos[category] = [format_repo_data(repo) for repo in repos]
    
    return category_repos


def save_json(data: any, filepath: str, metadata: Optional[Dict] = None):
    """Save data as a JSON file (with metadata)"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    # Create JSON structure with metadata
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
    print("=" * 60)
    print("Starting repository data update...")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 60)

    print("\nChecking API rate limit...")
    check_rate_limit()
    
    try:
        # Create metadata
        update_time = datetime.now().isoformat()

        # Fetch and save popular repositories
        print("\n" + "-" * 60)
        popular_repos = get_popular_repos()
        save_json(popular_repos, POPULAR_FILE, {
            "updated_at": update_time,
            "source": "GitHub API",
            "api_url": "https://api.github.com/search/repositories",
            "description": "Popular repositories with LLM/AI/ML/NLP focus",
            "count": len(popular_repos),
        })
        
        # Fetch and save trending repositories (newly added)
        print("\n" + "-" * 60)
        trending_repos = get_trending_repos()
        save_json(trending_repos, f"{ASSETS_DIR}/trending.json", {
            "updated_at": update_time,
            "source": "GitHub API",
            "api_url": "https://api.github.com/search/repositories",
            "description": "Trending repositories in the last 7 days",
            "count": len(trending_repos),
        })

        # Fetch and save new repositories
        print("\n" + "-" * 60)
        new_repos = get_new_repos()
        save_json(new_repos, NEW_FILE, {
            "updated_at": update_time,
            "source": "GitHub API",
            "api_url": "https://api.github.com/search/repositories",
            "description": "Recently created repositories (last 30 days)",
            "count": len(new_repos),
        })
        
        # Fetch and save repositories by category
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
