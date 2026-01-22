#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Multi-Repository Client
Author: Fabio Cherici & Padmin D. Curtis (AI Partner OS3.0)
License: MIT
Version: 1.0.0
Date: 2026-01-20

Fetch commits from multiple GitHub repositories with caching.
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import hashlib

try:
    from github import Github, GithubException
    from github.Commit import Commit as GHCommit
    from github.Repository import Repository
    HAVE_PYGITHUB = True
except ImportError:
    HAVE_PYGITHUB = False
    print("⚠️  PyGithub not installed. Run: pip install PyGithub")


@dataclass
class CommitData:
    """Structured commit data."""
    sha: str
    message: str
    author: str
    author_email: str
    date: datetime
    repository: str
    files_changed: List[str]
    additions: int
    deletions: int
    total_changes: int


class CommitCache:
    """SQLite cache for GitHub API responses."""
    
    def __init__(self, cache_path: Path):
        self.cache_path = cache_path
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize cache database."""
        conn = sqlite3.connect(self.cache_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS commits (
                cache_key TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                timestamp INTEGER NOT NULL
            )
        ''')
        conn.commit()
        conn.close()
    
    def _make_key(self, repo: str, since: str, until: str) -> str:
        """Generate cache key."""
        raw = f"{repo}:{since}:{until}"
        return hashlib.sha256(raw.encode()).hexdigest()
    
    def get(self, repo: str, since: str, until: str, max_age_hours: int = 24) -> Optional[List[Dict]]:
        """Get cached commits if still valid."""
        key = self._make_key(repo, since, until)
        
        conn = sqlite3.connect(self.cache_path)
        cursor = conn.cursor()
        cursor.execute('SELECT data, timestamp FROM commits WHERE cache_key = ?', (key,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        data_json, timestamp = row
        
        # Check age
        age_hours = (datetime.now().timestamp() - timestamp) / 3600
        if age_hours > max_age_hours:
            return None
        
        return json.loads(data_json)
    
    def set(self, repo: str, since: str, until: str, data: List[Dict]) -> None:
        """Cache commits."""
        key = self._make_key(repo, since, until)
        timestamp = int(datetime.now().timestamp())
        data_json = json.dumps(data, default=str)
        
        conn = sqlite3.connect(self.cache_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO commits (cache_key, data, timestamp)
            VALUES (?, ?, ?)
        ''', (key, data_json, timestamp))
        conn.commit()
        conn.close()
    
    def clear(self) -> None:
        """Clear all cached data."""
        conn = sqlite3.connect(self.cache_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM commits')
        conn.commit()
        conn.close()


class GitHubMultiRepoClient:
    """Fetch commits from multiple GitHub repositories."""
    
    def __init__(
        self,
        token: Optional[str] = None,
        repositories: Optional[List[str]] = None,
        cache_dir: Optional[Path] = None
    ):
        """
        Initialize GitHub client.
        
        Args:
            token: GitHub personal access token (or use GITHUB_TOKEN env var)
            repositories: List of repos in format "owner/repo"
            cache_dir: Directory for cache database
        """
        if not HAVE_PYGITHUB:
            raise ImportError("PyGithub required. Install with: pip install PyGithub")
        
        # Get token
        self.token = token or os.getenv('GITHUB_TOKEN')
        if not self.token:
            raise ValueError(
                "GitHub token required. Provide via token= or GITHUB_TOKEN env var.\n"
                "Create token: https://github.com/settings/tokens\n"
                "Scopes needed: repo (for private repos) or public_repo (for public only)"
            )
        
        # Initialize GitHub client
        self.client = Github(self.token)
        
        # Store repositories
        self.repositories = repositories or []
        
        # Initialize cache
        cache_path = cache_dir or Path.home() / '.egi_productivity_cache'
        self.cache = CommitCache(cache_path / 'github_commits.db')
    
    def add_repository(self, repo: str) -> None:
        """Add repository to tracked list."""
        if repo not in self.repositories:
            self.repositories.append(repo)
    
    def get_commits(
        self,
        since: datetime,
        until: datetime,
        use_cache: bool = True,
        cache_max_age_hours: int = 24
    ) -> List[CommitData]:
        """
        Fetch commits from all repositories.
        
        Args:
            since: Start date (inclusive)
            until: End date (inclusive)
            use_cache: Use cached data if available
            cache_max_age_hours: Max cache age before refresh
            
        Returns:
            List of CommitData sorted by date
        """
        all_commits = []
        
        for repo_name in self.repositories:
            repo_commits = self._get_repo_commits(
                repo_name,
                since,
                until,
                use_cache,
                cache_max_age_hours
            )
            all_commits.extend(repo_commits)
        
        # Sort by date
        all_commits.sort(key=lambda c: c.date)
        
        return all_commits
    
    def _get_repo_commits(
        self,
        repo_name: str,
        since: datetime,
        until: datetime,
        use_cache: bool,
        cache_max_age_hours: int
    ) -> List[CommitData]:
        """Fetch commits from single repository."""
        since_str = since.isoformat()
        until_str = until.isoformat()
        
        # Try cache first
        if use_cache:
            cached = self.cache.get(repo_name, since_str, until_str, cache_max_age_hours)
            if cached:
                # Reconstruct CommitData objects with proper datetime conversion
                commits_list = []
                for c_dict in cached:
                    # Convert date string to datetime
                    if isinstance(c_dict['date'], str):
                        c_dict['date'] = datetime.fromisoformat(c_dict['date'])
                    commits_list.append(CommitData(**c_dict))
                return commits_list
        
        # Fetch from GitHub API
        try:
            repo = self.client.get_repo(repo_name)
            commits = self._fetch_commits_from_api(repo, since, until, repo_name)
            
            # Cache results
            if use_cache:
                self.cache.set(
                    repo_name,
                    since_str,
                    until_str,
                    [asdict(c) for c in commits]
                )
            
            return commits
            
        except GithubException as e:
            print(f"⚠️  Failed to fetch {repo_name}: {e.status} - {e.data.get('message', 'Unknown error')}")
            return []
    
    def _parse_commit(self, gh_commit, repo_name: str) -> Optional[CommitData]:
        """Parse GitHub commit into CommitData format.
        
        NOTE: Accessing .stats triggers an extra API call per commit. 
        This is slow but necessary for accurate line counts.
        """
        try:
            # Attempt to get stats (triggers extra API call)
            try:
                additions = gh_commit.stats.additions if gh_commit.stats else 0
                deletions = gh_commit.stats.deletions if gh_commit.stats else 0
            except Exception:
                # If stats fail (rate limit, etc), use 0
                additions = 0
                deletions = 0
            
            # Files
            files_list = []
            try:
                # Accessing .files might be safe now if .stats triggered the fetch
                files_list = [f.filename for f in gh_commit.files]
            except Exception:
                pass

            return CommitData(
                sha=gh_commit.sha,
                message=gh_commit.commit.message,
                author=gh_commit.commit.author.name if gh_commit.commit.author else "Unknown",
                author_email=gh_commit.commit.author.email if gh_commit.commit.author else "",
                date=gh_commit.commit.author.date if gh_commit.commit.author else datetime.now(),
                repository=repo_name,
                additions=additions,
                deletions=deletions,
                total_changes=additions + deletions,
                files_changed=files_list
            )
        except Exception as e:
            print(f"⚠️  Error parsing commit {gh_commit.sha[:7]}: {e}")
            return None

    def _fetch_commits_from_api(
        self,
        repo: Repository,
        since: datetime,
        until: datetime,
        repo_name: str
    ) -> List[CommitData]:
        """Fetch commits from GitHub API across ALL branches."""
        commits_by_sha = {}  # Deduplicate by SHA
        
        # Add 1 day to until to make it inclusive
        until_inclusive = until + timedelta(days=1)
        
        try:
            # Get all branches
            branches = list(repo.get_branches())
            print(f"   📁 {repo_name}: scanning {len(branches)} branches...")
            
            # Query commits from each branch
            for branch in branches:
                try:
                    # Get commits in this branch
                    gh_commits = repo.get_commits(sha=branch.name, since=since, until=until_inclusive)
                    
                    for gh_commit in gh_commits:
                        # Deduplicate by SHA (same commit can be in multiple branches)
                        if gh_commit.sha not in commits_by_sha:
                            commit_data = self._parse_commit(gh_commit, repo_name)
                            if commit_data:
                                commits_by_sha[gh_commit.sha] = commit_data
                
                except GithubException as e:
                    # Skip branches that error (e.g., protected, deleted)
                    if e.status != 404:
                        print(f"   ⚠️  Branch {branch.name}: {e.status}")
                    continue
                    
        except GithubException as e:
            # Handle rate limiting
            if e.status == 403 and 'rate limit' in str(e.data).lower():
                rate_limit = self.client.get_rate_limit()
                core = rate_limit.resources.core
                reset_time = core.reset
                wait_minutes = (reset_time - datetime.now()).total_seconds() / 60
                print(f"⚠️  Rate limit exceeded. Resets in {wait_minutes:.1f} minutes.")
                print(f"   Current limit: {core.remaining}/{core.limit}")
            raise
        
        # Return deduplicated commits
        commits = list(commits_by_sha.values())
        print(f"   ✅ {repo_name}: {len(commits)} unique commits (across all branches)")
        return commits

# ============== CLI for testing ==============

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='GitHub Multi-Repo Commit Fetcher')
    parser.add_argument('--token', help='GitHub token (or use GITHUB_TOKEN env)')
    parser.add_argument('--test', action='store_true', help='Test connection')
    parser.add_argument('--repos', nargs='+', help='Repositories (owner/repo format)')
    parser.add_argument('--since', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--until', help='End date (YYYY-MM-DD)')
    parser.add_argument('--no-cache', action='store_true', help='Disable cache')
    parser.add_argument('--clear-cache', action='store_true', help='Clear cache and exit')
    
    args = parser.parse_args()
    
    # Test mode
    if args.test:
        client = GitHubMultiRepoClient(token=args.token)
        client.test_connection()
        exit(0)
    
    # Clear cache mode
    if args.clear_cache:
        cache_path = Path.home() / '.egi_productivity_cache' / 'github_commits.db'
        cache = CommitCache(cache_path)
        cache.clear()
        print("✅ Cache cleared")
        exit(0)
    
    # Fetch commits
    if not args.repos:
        print("❌ --repos required")
        exit(1)
    
    client = GitHubMultiRepoClient(token=args.token, repositories=args.repos)
    
    since = datetime.fromisoformat(args.since) if args.since else datetime.now() - timedelta(days=7)
    until = datetime.fromisoformat(args.until) if args.until else datetime.now()
    
    print(f"📊 Fetching commits from {len(args.repos)} repositories...")
    print(f"   Date range: {since.date()} → {until.date()}")
    print()
    
    commits = client.get_commits(since, until, use_cache=not args.no_cache)
    
    print(f"✅ Found {len(commits)} commits")
    print()
    
    # Group by repository
    by_repo = {}
    for commit in commits:
        if commit.repository not in by_repo:
            by_repo[commit.repository] = []
        by_repo[commit.repository].append(commit)
    
    for repo, repo_commits in by_repo.items():
        print(f"📁 {repo}: {len(repo_commits)} commits")
        for c in repo_commits[:5]:  # Show first 5
            print(f"   - [{c.date.strftime('%Y-%m-%d %H:%M')}] {c.message[:60]}")
        if len(repo_commits) > 5:
            print(f"   ... and {len(repo_commits) - 5} more")
        print()
