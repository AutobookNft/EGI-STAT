"""
Mission Client — reads MISSION_REGISTRY.json and mission reports.

Extracts structured data from closed missions for statistics enrichment.
Part of the Oracode mission-based statistics pipeline.

@author Padmin D. Curtis (AI Partner OS3.0) for Fabio Cherici
@version 1.0.0 (FlorenceEGI — EGI-STAT)
@date 2026-04-08
@purpose Parse mission registry and reports into structured stats data
"""

import json
import os
import re
from datetime import datetime, date
from pathlib import Path
from dataclasses import dataclass, field


# Mapping from organi_coinvolti names to GitHub repo names
ORGAN_TO_REPO = {
    "EGI": "EGI",
    "EGI-HUB": "EGI-HUB",
    "EGI-HUB-HOME": "EGI-HUB-HOME-REACT",
    "EGI-SIGILLO": "EGI-SIGILLO",
    "EGI-Credential": "egi-credential",
    "NATAN_LOC": "NATAN_LOC",
    "EGI-INFO": "EGI-INFO",
    "EGI-DOC": "EGI-DOC",
    "EGI-STAT": "EGI-STAT",
    "ecosistema": None,  # cross-organ, no single repo
}

# Mission type to tag weight (aligned with tag_system_v2 weights)
MISSION_TYPE_WEIGHTS = {
    "feature": 1.0,
    "bugfix": 1.5,
    "refactor": 2.0,
    "docsync": 0.8,
    "audit": 1.2,
    "lso-evolution": 1.8,
}


@dataclass
class MissionStats:
    """Structured stats extracted from a single mission."""
    mission_id: str
    title: str
    date_opened: date
    date_closed: date | None
    status: str
    mission_type: str
    organs: list[str]
    repos: list[str]
    cross_organ: bool
    files_modified: list[str]
    files_count: int
    doc_sync_executed: bool
    doc_verified: bool
    duration_days: int
    type_weight: float
    # Derived from report (if available)
    files_created: int = 0
    lines_estimate: int = 0


class MissionClient:
    """Reads and parses mission data from MISSION_REGISTRY.json."""

    def __init__(self, registry_path: str = None, docs_path: str = None):
        self.registry_path = registry_path or os.getenv(
            "MISSION_REGISTRY_PATH",
            "/home/fabio/EGI-DOC/docs/missions/MISSION_REGISTRY.json"
        )
        self.docs_path = docs_path or os.getenv(
            "MISSION_DOCS_PATH",
            "/home/fabio/EGI-DOC/docs/missions"
        )

    def load_registry(self) -> dict:
        """Load the mission registry JSON."""
        with open(self.registry_path, "r") as f:
            return json.load(f)

    def get_completed_missions(self) -> list[MissionStats]:
        """Get all completed missions as structured stats."""
        registry = self.load_registry()
        missions = []

        for entry in registry.get("missions", []):
            if entry.get("stato") != "completed":
                continue
            if not entry.get("titolo"):
                continue

            stats = self._parse_mission(entry)
            if stats:
                missions.append(stats)

        return missions

    def get_missions_since(self, since_date: date) -> list[MissionStats]:
        """Get completed missions closed on or after a given date."""
        all_missions = self.get_completed_missions()
        return [m for m in all_missions if m.date_closed and m.date_closed >= since_date]

    def get_missions_for_date(self, target_date: date) -> list[MissionStats]:
        """Get missions that were active on a specific date."""
        all_missions = self.get_completed_missions()
        return [
            m for m in all_missions
            if m.date_opened <= target_date and
               m.date_closed and m.date_closed >= target_date
        ]

    def _parse_mission(self, entry: dict) -> MissionStats | None:
        """Parse a single mission entry into MissionStats."""
        try:
            mission_id = entry["mission_id"]
            title = entry.get("titolo", "")

            date_opened = self._parse_date(entry.get("data_apertura"))
            date_closed = self._parse_date(entry.get("data_chiusura"))
            if not date_opened or not date_closed:
                return None

            organs = entry.get("organi_coinvolti", [])
            repos = self._organs_to_repos(organs)

            files_modified = entry.get("files_modified", [])
            mission_type = entry.get("tipo_missione", "feature")

            duration = (date_closed - date_opened).days + 1  # at least 1 day

            # Try to extract more data from report
            files_created = 0
            report_path = entry.get("report_tecnico")
            if report_path:
                files_created = self._count_created_files_from_report(report_path)

            return MissionStats(
                mission_id=mission_id,
                title=title,
                date_opened=date_opened,
                date_closed=date_closed,
                status=entry.get("stato", "completed"),
                mission_type=mission_type,
                organs=organs,
                repos=repos,
                cross_organ=entry.get("cross_organo", False),
                files_modified=files_modified,
                files_count=len(files_modified),
                doc_sync_executed=entry.get("doc_sync_executed", False),
                doc_verified=entry.get("doc_verified", False),
                duration_days=duration,
                type_weight=MISSION_TYPE_WEIGHTS.get(mission_type, 1.0),
                files_created=files_created,
            )
        except Exception as e:
            print(f"  Warning: could not parse {entry.get('mission_id', '?')}: {e}")
            return None

    def _parse_date(self, date_str) -> date | None:
        """Parse date string, handling 'pending' and None."""
        if not date_str or date_str == "pending":
            return None
        try:
            return datetime.strptime(date_str[:10], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None

    def _organs_to_repos(self, organs: list[str]) -> list[str]:
        """Map organ names to GitHub repo names."""
        repos = []
        for organ in organs:
            repo = ORGAN_TO_REPO.get(organ)
            if repo and repo not in repos:
                repos.append(repo)
        return repos

    def _count_created_files_from_report(self, report_relative_path: str) -> int:
        """Try to extract 'files created' count from mission report."""
        report_path = os.path.join(self.docs_path, os.path.basename(report_relative_path))
        if not os.path.exists(report_path):
            return 0
        try:
            content = Path(report_path).read_text(encoding="utf-8")
            # Look for patterns like "File toccati | 12 file (5 creati, 7 modificati)"
            match = re.search(r'(\d+)\s*creat[io]', content)
            if match:
                return int(match.group(1))
            # Or "FILE CREATI:" section
            match = re.search(r'FILE CREAT[IO].*?:\s*\n((?:- .+\n)+)', content)
            if match:
                return len(match.group(1).strip().split('\n'))
        except Exception:
            pass
        return 0
