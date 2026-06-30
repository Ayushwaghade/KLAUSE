import os
import requests
from typing import List, Dict, Any

class GitHubClient:
    """
    REST API client for retrieving repository data (issues, PRs, commits) from GitHub.
    Uses 'requests' with pagination, limits, and explicit error handlers.
    """

    def __init__(self, token: str = None):
        self.token = token or os.environ.get("GITHUB_TOKEN")
        self.base_url = "https://api.github.com"
        
    def _get_headers(self) -> dict:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _request(self, endpoint: str, params: dict = None) -> list:
        url = f"{self.base_url}/{endpoint}"
        headers = self._get_headers()
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 401:
                raise ValueError("GitHub API Error (401): Unauthorized. Please check if your GITHUB_TOKEN is valid.")
            elif response.status_code == 403:
                # Rate limit check
                rate_limit_remaining = response.headers.get("X-RateLimit-Remaining")
                if rate_limit_remaining == "0":
                    raise ValueError("GitHub API Error (403): Rate Limit Exceeded. Try setting a GITHUB_TOKEN or waiting.")
                raise ValueError(f"GitHub API Error (403): Forbidden. You might not have permission to view this resource. Info: {response.json().get('message','')}")
            elif response.status_code == 404:
                raise ValueError(f"GitHub API Error (404): Repository or resource not found. Check repository path (format: 'owner/repo').")
            elif response.status_code != 200:
                raise ValueError(f"GitHub API Error ({response.status_code}): {response.text}")
                
            return response.json()
        except requests.exceptions.Timeout:
            raise TimeoutError("GitHub API request timed out.")
        except requests.exceptions.RequestException as re:
            raise ConnectionError(f"GitHub API connection failure: {re}")

    def get_issues(self, repo: str, state: str = "open", limit: int = 30) -> List[Dict[str, Any]]:
        """Retrieves issues for a repository (excluding PRs). Handles pagination."""
        endpoint = f"repos/{repo}/issues"
        accumulated = []
        page = 1
        
        while len(accumulated) < limit:
            per_page = min(100, limit - len(accumulated))
            params = {
                "state": state,
                "per_page": per_page,
                "page": page
            }
            
            results = self._request(endpoint, params=params)
            if not isinstance(results, list) or not results:
                break
                
            # GitHub's issues endpoint returns both issues and Pull Requests.
            # PRs have a 'pull_request' key in the issue object.
            for item in results:
                if "pull_request" not in item:
                    accumulated.append({
                        "number": item.get("number"),
                        "title": item.get("title"),
                        "state": item.get("state"),
                        "user": item.get("user", {}).get("login"),
                        "created_at": item.get("created_at"),
                        "html_url": item.get("html_url")
                    })
                    if len(accumulated) >= limit:
                        break
            
            # Stop if we fetched fewer items than per_page (means no more pages)
            if len(results) < per_page or page >= 3:
                break
            page += 1
            
        return accumulated[:limit]

    def get_prs(self, repo: str, state: str = "open", limit: int = 30) -> List[Dict[str, Any]]:
        """Retrieves Pull Requests for a repository. Handles pagination."""
        endpoint = f"repos/{repo}/pulls"
        accumulated = []
        page = 1
        
        while len(accumulated) < limit:
            per_page = min(100, limit - len(accumulated))
            params = {
                "state": state,
                "per_page": per_page,
                "page": page
            }
            
            results = self._request(endpoint, params=params)
            if not isinstance(results, list) or not results:
                break
                
            for item in results:
                accumulated.append({
                    "number": item.get("number"),
                    "title": item.get("title"),
                    "state": item.get("state"),
                    "user": item.get("user", {}).get("login"),
                    "created_at": item.get("created_at"),
                    "html_url": item.get("html_url")
                })
                if len(accumulated) >= limit:
                    break
                    
            if len(results) < per_page or page >= 3:
                break
            page += 1
            
        return accumulated[:limit]

    def get_commits(self, repo: str, limit: int = 30) -> List[Dict[str, Any]]:
        """Retrieves commits for a repository. Handles pagination."""
        endpoint = f"repos/{repo}/commits"
        accumulated = []
        page = 1
        
        while len(accumulated) < limit:
            per_page = min(100, limit - len(accumulated))
            params = {
                "per_page": per_page,
                "page": page
            }
            
            results = self._request(endpoint, params=params)
            if not isinstance(results, list) or not results:
                break
                
            for item in results:
                commit = item.get("commit", {})
                accumulated.append({
                    "sha": item.get("sha")[:7] if item.get("sha") else None,
                    "author": commit.get("author", {}).get("name"),
                    "message": commit.get("message", "").split("\n")[0],
                    "date": commit.get("author", {}).get("date"),
                    "html_url": item.get("html_url")
                })
                if len(accumulated) >= limit:
                    break
                    
            if len(results) < per_page or page >= 3:
                break
            page += 1
            
        return accumulated[:limit]
