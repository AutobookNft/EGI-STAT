#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EGI Productivity Analytics v7.1.0 - Complete GitHub Edition
Author: Fabio Cherici & Padmin D. Curtis (AI Partner OS3.0)
License: MIT
Version: 7.1.0
Date: 2026-01-20

Complete v6 metrics + v7 GitHub API multi-repo.
"""

from __future__ import annotations

import argparse
import datetime as dt
import math
import os
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple
import yaml

# Import v7 components
try:
    from tag_system_v2 import TagSystem, TAG_WEIGHTS, DAY_TYPES
    from github_client import GitHubMultiRepoClient, CommitData
    from auto_categorizer import CommitCategorizer
except ImportError as e:
    print(f"❌ Missing component: {e}")
    sys.exit(1)

# Excel support
HAVE_PANDAS = False
try:
    import pandas as pd
    import openpyxl
    HAVE_PANDAS = True
except ImportError:
    pass


# ═══════════════════════════════════════════════════════════════
# DATACLASSES (from v6, adapted for multi-repo)
# ═══════════════════════════════════════════════════════════════

@dataclass
class DayStats:
    date: dt.date
    # Per-repository breakdown (dynamic, adapts to number of repos)
    repos_commits: Dict[str, int]  # repo -> commit_count
    repos_lines_net: Dict[str, int]  # repo -> net_lines
    # Combined stats (same as v6)
    commits: int
    commits_weighted: float
    files_modified: int
    lines_added: int
    lines_removed: int
    lines_touched: int
    lines_net: int
    tags: Dict[str, int]
    day_type: str
    day_type_icon: str
    cognitive_load: float
    productivity_index: float


@dataclass
class WeekStats:
    week_number: int
    period: str
    description: str
    start_date: dt.date
    end_date: dt.date
    # Per-repository breakdown
    repos_commits: Dict[str, int]
    repos_lines_net: Dict[str, int]
    # Combined stats (same as v6)
    commits: int
    commits_weighted: float
    files_modified: int
    lines_touched: int
    lines_net: int
    tag_coverage_pct: float
    avg_cognitive_load: float
    avg_productivity: float
    testing_minutes: float
    coding_minutes: float


# ═══════════════════════════════════════════════════════════════
# HELPER FUNCTIONS (from v6)
# ═══════════════════════════════════════════════════════════════

def classify_day_type(tag_percentages: Dict[str, float]) -> Tuple[str, str]:
    """Classify day based on tag distribution."""
    for day_type, config in DAY_TYPES.items():
        if config['criteria'](tag_percentages):
            return day_type, config['icon']
    return 'MIXED', '📦'


def calculate_cognitive_load(commits: int, files: int, lines_touched: int) -> float:
    """Calculate cognitive load using log-scaled formula."""
    if commits == 0:
        return 1.0
    
    li = math.log(lines_touched + 1)
    fm = math.log(files + 1)
    dp = math.log(commits + 1)
    
    cl = (li + fm + dp) / 3.0
    cl_normalized = 1.0 + (cl / 2.0)
    return max(1.0, min(3.5, cl_normalized))


def calculate_productivity_index(
    commits_weighted: float,
    lines_net: int,
    cognitive_load: float,
    day_type_multiplier: float
) -> float:
    """Calculate productivity index.
    
    Uses abs(lines_net) because removing code is productive too!
    """
    if cognitive_load == 0:
        cognitive_load = 1.0
    
    # Use absolute value - both adding AND removing code is productive work
    base_score = (commits_weighted * 10.0) + (abs(lines_net) / 10.0)
    return (base_score * day_type_multiplier) / cognitive_load


# ═══════════════════════════════════════════════════════════════
# ANALYSIS ENGINE (v6 logic + v7 GitHub data)
# ═══════════════════════════════════════════════════════════════

class ProductivityAnalyzer:
    """Complete analytics engine."""
    
    def __init__(self, github_client: GitHubMultiRepoClient, categorizer: CommitCategorizer):
        self.github = github_client
        self.categorizer = categorizer
        self.all_repos = set()
    
    def analyze_day(self, date: dt.date, all_commits: List[CommitData]) -> DayStats:
        """Analyze single day."""
        day_commits = [c for c in all_commits if c.date.date() == date]
        
        # Track all repos encountered
        for c in day_commits:
            self.all_repos.add(c.repository)
        
        if not day_commits:
            return DayStats(
                date=date,
                repos_commits={},
                repos_lines_net={},
                commits=0,
                commits_weighted=0.0,
                files_modified=0,
                lines_added=0,
                lines_removed=0,
                lines_touched=0,
                lines_net=0,
                tags={},
                day_type='MIXED',
                day_type_icon='📦',
                cognitive_load=1.0,
                productivity_index=0.0
            )
        
        # Count tags
        tag_counter = Counter()
        commits_weighted = 0.0
        
        for commit in day_commits:
            tag, confidence = TagSystem.parse_tag(commit.message)
            if not tag:
                result = self.categorizer.categorize(commit.message, commit.files_changed)
                tag = result.tag
            
            tag_counter[tag] += 1
            weight = TagSystem.get_weight(tag)
            commits_weighted += weight
        
        # Tag percentages
        tag_percentages = {tag: (count / len(day_commits)) * 100 for tag, count in tag_counter.items()}
        
        # Repository breakdown
        repos_commits = Counter()
        repos_lines_net = Counter()
        
        for commit in day_commits:
            repos_commits[commit.repository] += 1
            repos_lines_net[commit.repository] += (commit.additions - commit.deletions)
        
        # File statistics
        all_files = set()
        lines_added = sum(c.additions for c in day_commits)
        lines_removed = sum(c.deletions for c in day_commits)
        
        for commit in day_commits:
            all_files.update(commit.files_changed)
        
        lines_touched = lines_added + lines_removed
        lines_net = lines_added - lines_removed
        
        # Day type
        day_type, day_icon = classify_day_type(tag_percentages)
        day_type_multiplier = DAY_TYPES[day_type]['multiplier']
        
        # Metrics
        cognitive_load = calculate_cognitive_load(len(day_commits), len(all_files), lines_touched)
        productivity = calculate_productivity_index(commits_weighted, lines_net, cognitive_load, day_type_multiplier)
        
        return DayStats(
            date=date,
            repos_commits=dict(repos_commits),
            repos_lines_net=dict(repos_lines_net),
            commits=len(day_commits),
            commits_weighted=commits_weighted,
            files_modified=len(all_files),
            lines_added=lines_added,
            lines_removed=lines_removed,
            lines_touched=lines_touched,
            lines_net=lines_net,
            tags=dict(tag_counter),
            day_type=day_type,
            day_type_icon=day_icon,
            cognitive_load=cognitive_load,
            productivity_index=productivity
        )
    
    def analyze_week(
        self,
        week_number: int,
        start_date: dt.date,
        end_date: dt.date,
        description: str,
        all_commits: List[CommitData]
    ) -> Tuple[WeekStats, List[DayStats]]:
        """Analyze weekly statistics."""
        daily_stats = []
        current_date = start_date
        
        while current_date <= end_date:
            day_stat = self.analyze_day(current_date, all_commits)
            daily_stats.append(day_stat)
            current_date += dt.timedelta(days=1)
        
        # Aggregate
        repos_commits = Counter()
        repos_lines_net = Counter()
        
        for day in daily_stats:
            for repo, count in day.repos_commits.items():
                repos_commits[repo] += count
            for repo, lines in day.repos_lines_net.items():
                repos_lines_net[repo] += lines
        
        total_commits = sum(d.commits for d in daily_stats)
        total_commits_weighted = sum(d.commits_weighted for d in daily_stats)
        total_files = sum(d.files_modified for d in daily_stats)
        total_lines_touched = sum(d.lines_touched for d in daily_stats)
        total_lines_net = sum(d.lines_net for d in daily_stats)
        
        # TAG coverage
        tagged_commits = sum(
            count for day in daily_stats
            for tag, count in day.tags.items()
            if tag != 'UNTAGGED'
        )
        tag_coverage_pct = (tagged_commits / total_commits * 100) if total_commits > 0 else 0.0
        
        # Averages
        days_with_commits = [d for d in daily_stats if d.commits > 0]
        avg_cognitive = sum(d.cognitive_load for d in days_with_commits) / len(days_with_commits) if days_with_commits else 1.0
        avg_productivity = sum(d.productivity_index for d in days_with_commits) / len(days_with_commits) if days_with_commits else 0.0
        
        # Time estimates
        testing_minutes = total_commits * 22.0
        coding_minutes = total_commits * 22.0
        
        # Format period
        month_names = {
            1: 'Gennaio', 2: 'Febbraio', 3: 'Marzo', 4: 'Aprile', 5: 'Maggio', 6: 'Giugno',
            7: 'Luglio', 8: 'Agosto', 9: 'Settembre', 10: 'Ottobre', 11: 'Novembre', 12: 'Dicembre'
        }
        
        start_month = month_names.get(start_date.month, start_date.strftime('%B'))
        end_month = month_names.get(end_date.month, end_date.strftime('%B'))
        
        if start_date.month == end_date.month:
            period = f"{start_date.day}-{end_date.day} {start_month} 2025"
        else:
            period = f"{start_date.day} {start_month} - {end_date.day} {end_month} 2025"
        
        return WeekStats(
            week_number=week_number,
            period=period,
            description=description,
            start_date=start_date,
            end_date=end_date,
            repos_commits=dict(repos_commits),
            repos_lines_net=dict(repos_lines_net),
            commits=total_commits,
            commits_weighted=total_commits_weighted,
            files_modified=total_files,
            lines_touched=total_lines_touched,
            lines_net=total_lines_net,
            tag_coverage_pct=tag_coverage_pct,
            avg_cognitive_load=avg_cognitive,
            avg_productivity=avg_productivity,
            testing_minutes=testing_minutes,
            coding_minutes=coding_minutes
        ), daily_stats
    
    def generate_full_report(
        self,
        start_date: dt.date,
        end_date: dt.date
    ) -> Tuple[List[WeekStats], List[DayStats]]:
        """Generate complete report."""
        # Fetch commits
        start_dt = dt.datetime.combine(start_date, dt.time.min)
        end_dt = dt.datetime.combine(end_date, dt.time.max)
        
        print("🔍 Fetching commits from GitHub...")
        all_commits = self.github.get_commits(start_dt, end_dt)
        print(f"✅ Fetched {len(all_commits)} commits")
        
        all_weekly_stats = []
        all_daily_stats = []
        
        week_number = 1
        days_since_monday = start_date.weekday()
        current_monday = start_date - dt.timedelta(days=days_since_monday)
        
        week_descriptions = {
            1: 'Introduzione TAG system', 2: 'Stabilizzazione', 3: 'Consolidamento',
            4: 'Sviluppo avanzato', 5: 'Ottimizzazione', 6: 'Completamento features',
            7: 'Testing e refinement', 8: 'Advanced development', 9: 'Production readiness',
            10: 'PA/Enterprise Development', 11: 'Scalability & Performance',
            12: 'Final Polish', 13: 'Quality Assurance', 14: 'Deployment Preparation',
            15: 'User Testing', 16: 'Performance Tuning', 17: 'Security Hardening',
            18: 'Documentation', 19: 'Launch Preparation', 20: 'Post-Launch Support',
            21: 'Iteration & Improvement', 22: 'Feature Expansion',
            23: 'Platform Optimization', 24: 'Enterprise Integration'
        }
        
        while current_monday <= end_date:
            current_sunday = current_monday + dt.timedelta(days=6)
            week_end = min(current_sunday, end_date)
            
            description = week_descriptions.get(week_number, f'Sviluppo settimana {week_number}')
            if week_end == end_date and end_date == dt.date.today():
                description += ' (in corso)'
            
            week_stats, daily_stats = self.analyze_week(
                week_number, current_monday, week_end, description, all_commits
            )
            
            all_weekly_stats.append(week_stats)
            all_daily_stats.extend(daily_stats)
            
            current_monday += dt.timedelta(days=7)
            week_number += 1
        
        return all_weekly_stats, all_daily_stats


# ==== CONTINUA PARTE 2... ====


# ═══════════════════════════════════════════════════════════════
# EXCEL EXPORT (v6-compatible with multi-repo)
# ═══════════════════════════════════════════════════════════════

def create_excel_report(
    weekly_stats: List[WeekStats],
    daily_stats: List[DayStats],
    output_path: Path,
    all_repos: set
) -> None:
    """Create Excel file with comprehensive v6-style metrics."""
    if not HAVE_PANDAS:
        print("⚠️ pandas/openpyxl not available", file=sys.stderr)
        return
    
    # Prepare weekly data
    weekly_data = []
    for week in weekly_stats:
        row = {
            'Settimana': f'Settimana {week.week_number}',
            'Periodo': week.period,
            'Descrizione': week.description,
        }
        
        # Add per-repo columns
        for repo in sorted(all_repos):
            repo_short = repo.split('/')[-1]
            row[f'Commits {repo_short}'] = week.repos_commits.get(repo, 0)
            row[f'Righe Nette {repo_short}'] = week.repos_lines_net.get(repo, 0)
        
        # Combined columns
        row.update({
            'Commits TOTALI': week.commits,
            'Commits Pesati': round(week.commits_weighted, 1),
            'Files Modificati': week.files_modified,
            'Righe Toccate': week.lines_touched,
            'Righe Nette TOTALI': week.lines_net,
            'TAG Coverage %': round(week.tag_coverage_pct, 1),
            'Cognitive Load': round(week.avg_cognitive_load, 2),
            'Productivity Index': round(week.avg_productivity, 2),
            'Testing Time (h)': round(week.testing_minutes / 60, 1),
            'Coding Time (h)': round(week.coding_minutes / 60, 1)
        })
        weekly_data.append(row)
    
    # Prepare daily data
    daily_data = []
    for day in daily_stats:
        if day.commits == 0:
            continue
        
        tags_str = ', '.join(f"{tag}:{count}" for tag, count in day.tags.items())
        
        row = {
            'Data': day.date.isoformat(),
            'Giorno': day.date.strftime('%A'),
        }
        
        # Add per-repo columns
        for repo in sorted(all_repos):
            repo_short = repo.split('/')[-1]
            row[f'Commits {repo_short}'] = day.repos_commits.get(repo, 0)
            row[f'Righe Nette {repo_short}'] = day.repos_lines_net.get(repo, 0)
        
        # Combined columns
        row.update({
            'Commits TOTALI': day.commits,
            'Commits Pesati': round(day.commits_weighted, 1),
            'Files': day.files_modified,
            'Righe +': day.lines_added,
            'Righe -': day.lines_removed,
            'Righe Toccate': day.lines_touched,
            'Righe Nette TOTALI': day.lines_net,
            'TAG Distribution': tags_str,
            'Day Type': f"{day.day_type_icon} {day.day_type}",
            'Cognitive Load': round(day.cognitive_load, 2),
            'Productivity Index': round(day.productivity_index, 2)
        })
        daily_data.append(row)
    
    # Summary data
    total_commits = sum(w.commits for w in weekly_stats)
    total_weighted = sum(w.commits_weighted for w in weekly_stats)
    total_lines_touched = sum(w.lines_touched for w in weekly_stats)
    total_lines_net = sum(w.lines_net for w in weekly_stats)
    total_testing_hours = sum(w.testing_minutes for w in weekly_stats) / 60
    avg_tag_coverage = sum(w.tag_coverage_pct for w in weekly_stats) / len(weekly_stats) if weekly_stats else 0
    avg_productivity = sum(d.productivity_index for d in daily_stats if d.commits > 0) / len([d for d in daily_stats if d.commits > 0]) if any(d.commits > 0 for d in daily_stats) else 0
    
    summary_data = [
        {'Metrica': 'Commit Totali', 'Valore': total_commits, 'Note': 'Tutti i commit nel periodo'},
        {'Metrica': 'Commit Pesati Totali', 'Valore': round(total_weighted, 1), 'Note': 'Basato su TAG weights (REFACTOR=2x, FIX=1.5x)'},
        {'Metrica': 'Copertura TAG Media', 'Valore': f'{round(avg_tag_coverage, 1)}%', 'Note': 'Media delle settimane'},
        {'Metrica': 'Righe Toccate Totali', 'Valore': f'{total_lines_touched:,}', 'Note': 'Added + Removed (real work)'},
        {'Metrica': 'Righe Nette Totali', 'Valore': f'{total_lines_net:,}', 'Note': 'Added - Removed'},
        {'Metrica': 'Testing Time Totale', 'Valore': f'{round(total_testing_hours, 1)}h', 'Note': '22 min per commit estimate'},
        {'Metrica': 'Indice Produttività Medio', 'Valore': round(avg_productivity, 2), 'Note': 'Multi-dimensional scoring'},
    ]
    
    # Create DataFrames
    df_weekly = pd.DataFrame(weekly_data)
    df_daily = pd.DataFrame(daily_data)
    df_summary = pd.DataFrame(summary_data)
    
    # Write Excel
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        df_summary.to_excel(writer, sheet_name='Summary', index=False)
        df_weekly.to_excel(writer, sheet_name='Weekly', index=False)
        df_daily.to_excel(writer, sheet_name='Daily', index=False)
        
        # Auto-adjust column widths
        for sheet_name in ['Summary', 'Weekly', 'Daily']:
            worksheet = writer.sheets[sheet_name]
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
    
    print(f"✅ Excel file created: {output_path}")


# ═══════════════════════════════════════════════════════════════
# TERMINAL OUTPUT (adapted for multi-repo)
# ═══════════════════════════════════════════════════════════════

def print_terminal_summary(weekly_stats: List[WeekStats], daily_stats: List[DayStats], is_single_day: bool = False, requested_date: dt.date = None) -> None:
    """Print summary to terminal."""
    # Find target day
    if is_single_day and daily_stats and requested_date:
        target_day = next((d for d in daily_stats if d.date == requested_date), daily_stats[0])
    else:
        today_list = [d for d in daily_stats if d.date == dt.date.today()]
        if today_list:
            target_day = today_list[0]
        else:
            days_with_commits = [d for d in daily_stats if d.commits > 0]
            target_day = days_with_commits[-1] if days_with_commits else None
    
    if target_day:
        print("\n" + "="*70)
        print("📊 STATISTICHE OGGI" if not is_single_day else "📊 STATISTICHE GIORNO ANALIZZATO")
        print("="*70)
        print(f"📅 Data: {target_day.date.isoformat()}")
        print()
        
        # Per-repo breakdown
        for repo, commits in sorted(target_day.repos_commits.items()):
            repo_short = repo.split('/')[-1]
            lines = target_day.repos_lines_net.get(repo, 0)
            print(f"📊 {repo_short}:")
            print(f"   ✨ Commits: {commits}")
            print(f"   💯 Righe nette: {lines:+,}")
            print()
        
        # Combined totals
        print("📊 TOTALE GIORNALIERO:")
        print(f"   ✨ Commits totali: {target_day.commits} (pesati: {target_day.commits_weighted:.1f})")
        print(f"   📁 Files modificati: {target_day.files_modified}")
        print(f"   📈 Righe aggiunte: +{target_day.lines_added:,}")
        print(f"   📉 Righe rimosse: -{target_day.lines_removed:,}")
        print(f"   🔢 Righe toccate: {target_day.lines_touched:,}")
        print(f"   💯 Righe nette: {target_day.lines_net:+,}")
        print(f"   {target_day.day_type_icon} Tipo giornata: {target_day.day_type}")
        print(f"   🧠 Cognitive Load: {target_day.cognitive_load:.2f}x")
        print(f"   🚀 Productivity Index: {target_day.productivity_index:.2f}")
        
        if target_day.tags:
            print(f"\n🏷️ TAG Distribution:")
            for tag, count in sorted(target_day.tags.items(), key=lambda x: -x[1]):
                weight = TAG_WEIGHTS.get(tag, 0.5)
                print(f"   [{tag}]: {count} commits (weight: {weight}x)")
    
    # Weekly summary
    if not is_single_day and weekly_stats:
        last_week = weekly_stats[-1]
        
        print("\n" + "="*70)
        print("📊 RIEPILOGO ULTIMA SETTIMANA")
        print("="*70)
        print(f"🗓️ Periodo: {last_week.period}")
        print()
        
        # Per-repo breakdown
        for repo, commits in sorted(last_week.repos_commits.items()):
            repo_short = repo.split('/')[-1]
            lines = last_week.repos_lines_net.get(repo, 0)
            print(f"📊 {repo_short}:")
            print(f"   ✨ Commits: {commits}")
            print(f"   💯 Righe nette: {lines:+,}")
            print()
        
        # Combined
        print("�� TOTALE SETTIMANALE:")
        print(f"   ✨ Commit totali: {last_week.commits} (pesati: {last_week.commits_weighted:.1f})")
        print(f"   💯 Righe nette totali: {last_week.lines_net:+,}")
        print(f"   📊 Settimane analizzate: {len(weekly_stats)} (Excel completo)")
        print(f"   🗓️ Periodo completo: {weekly_stats[0].start_date.isoformat()} → {weekly_stats[-1].end_date.isoformat()}")


# ═══════════════════════════════════════════════════════════════
# CLI & MAIN
# ═══════════════════════════════════════════════════════════════

DEFAULT_CONFIG = {
    'github': {
        'repositories': [
            'AutobookNft/EGI',
            'AutobookNft/EGI-HUB',
            'AutobookNft/EGI-HUB-HOME-REACT',
            'AutobookNft/EGI-INFO',
            'AutobookNft/NATAN_LOC',
        ]
    },
    'analysis': {
        'default_start_date': '2025-08-19',
    }
}


def load_config(config_path: Path = None) -> Dict:
    """Load configuration."""
    if config_path and config_path.exists():
        with open(config_path) as f:
            return yaml.safe_load(f)
    return DEFAULT_CONFIG


def parse_args() -> argparse.Namespace:
    """Parse arguments."""
    parser = argparse.ArgumentParser(description='EGI Productivity v7.1 - Complete Edition')
    parser.add_argument('--config', type=Path, default=Path('productivity_config.yaml'))
    parser.add_argument('--since', type=str)
    parser.add_argument('--until', type=str)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--test-github', action='store_true')
    parser.add_argument('--no-cache', action='store_true')
    return parser.parse_args()


def main() -> int:
    """Main execution."""
    print("🚀 EGI Productivity Analytics v7.1.0 COMPLETE")
    print("   GitHub API Multi-Repository Edition")
    print("   v6 Metrics + v7 Features + 16 TAG System")
    print("="*70)
    
    args = parse_args()
    
    # Load config
    config = load_config(args.config if args.config.exists() else None)
    
    # Get GitHub token
    github_token = os.getenv('GITHUB_TOKEN')
    if not github_token:
        print("\n❌ GitHub token required!")
        print("   export GITHUB_TOKEN='your_token_here'")
        return 1
    
    # Initialize clients
    github_client = GitHubMultiRepoClient(
        token=github_token,
        repositories=config['github']['repositories']
    )
    
    # Test mode
    if args.test_github:
        print("\n🔍 Testing GitHub connection...")
        if github_client.test_connection():
            print(f"\n✅ Tracking {len(config['github']['repositories'])} repositories")
            return 0
        return 1
    
    # Initialize components
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    categorizer = CommitCategorizer(llm_api_key=anthropic_key)
    analyzer = ProductivityAnalyzer(github_client, categorizer)
    
    # Parse dates
    if args.since:
        start_date = dt.date.fromisoformat(args.since)
    else:
        start_date = dt.date.fromisoformat(config['analysis']['default_start_date'])
    
    end_date = dt.date.fromisoformat(args.until) if args.until else dt.date.today()
    
    # Output path
    if args.output:
        output_path = args.output
    else:
        filename = f"productivity_v7_{dt.date.today().strftime('%Y%m%d')}.xlsx"
        output_path = Path.cwd() / filename
    
    print(f"\n📊 Period: {start_date} → {end_date}")
    print(f"📁 Repositories: {len(config['github']['repositories'])}")
    print(f"💾 Output: {output_path}")
    print()
    
    # Detect single day
    is_single_day = (start_date == end_date)
    
    # Run analysis
    try:
        weekly_stats, daily_stats = analyzer.generate_full_report(start_date, end_date)
        
        if not is_single_day:
            print(f"\n✅ Analyzed {len(weekly_stats)} weeks, {len([d for d in daily_stats if d.commits > 0])} days with commits")
        
        # Terminal output
        print_terminal_summary(weekly_stats, daily_stats, is_single_day, start_date if is_single_day else None)
        
        # Excel export (only if NOT single day)
        if not is_single_day:
            if HAVE_PANDAS:
                print("\n📊 Creating Excel report...")
                create_excel_report(weekly_stats, daily_stats, output_path, analyzer.all_repos)
                
                if output_path.exists():
                    size = output_path.stat().st_size
                    print(f"📁 File size: {size:,} bytes")
            else:
                print("\n⚠️ pandas not available. Install: pip install pandas openpyxl")
        else:
            print("\n💡 Single day analysis - Excel skipped")
        
        print("\n🎉 Analysis complete!")
        return 0
        
    except Exception as e:
        print(f"\n❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
