#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EGI TAG System v2.0 - Expanded Hierarchy
Author: Fabio Cherici & Padmin D. Curtis (AI Partner OS3.0)
License: MIT
Version: 2.0.0
Date: 2026-01-20

Expanded TAG system from 7 to 16 tags with:
- Alias support (emoji, conventional commits, typos)
- Backward compatibility
- Enhanced categorization
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import re


# ============== Day Type Classification (from v6) ==============

DAY_TYPES = {
    'REFACTORING': {
        'description': 'Debt Repayment Day',
        'criteria': lambda stats: stats.get('REFACTOR', 0) > 20 or stats.get('FIX', 0) > 50,
        'multiplier': 1.5,
        'icon': '🔧'
    },
    'BUG_FIXING': {
        'description': 'Bug Extermination Day',
        'criteria': lambda stats: stats.get('FIX', 0) > 40 and stats.get('FIX', 0) <= 50,
        'multiplier': 1.3,
        'icon': '🐛'
    },
    'FEATURE_DEV': {
        'description': 'Feature Building Day',
        'criteria': lambda stats: stats.get('FEAT', 0) > 50,
        'multiplier': 1.0,
        'icon': '✨'
    },
    'TESTING': {
        'description': 'Quality Assurance Day',
        'criteria': lambda stats: stats.get('TEST', 0) > 40,
        'multiplier': 1.1,
        'icon': '🧪'
    },
    'MAINTENANCE': {
        'description': 'Maintenance Day',
        'criteria': lambda stats: stats.get('CHORE', 0) > 40,
        'multiplier': 0.8,
        'icon': '🔨'
    },
    'MIXED': {
        'description': 'Mixed Activities',
        'criteria': lambda stats: True,  # Default fallback
        'multiplier': 1.0,
        'icon': '��'
    }
}


# ============== Day Type Classification (from v6) ==============\n\nDAY_TYPES = {\n    'REFACTORING': {\n        'description': 'Debt Repayment Day',\n        'criteria': lambda stats: stats.get('REFACTOR', 0) > 20 or stats.get('FIX', 0) > 50,\n        'multiplier': 1.5,\n        'icon': '🔧'\n    },\n    'BUG_FIXING': {\n        'description': 'Bug Extermination Day',\n        'criteria': lambda stats: stats.get('FIX', 0) > 40 and stats.get('FIX', 0) <= 50,\n        'multiplier': 1.3,\n        'icon': '🐛'\n    },\n    'FEATURE_DEV': {\n        'description': 'Feature Building Day',\n        'criteria': lambda stats: stats.get('FEAT', 0) > 50,\n        'multiplier': 1.0,\n        'icon': '✨'\n    },\n    'TESTING': {\n        'description': 'Quality Assurance Day',\n        'criteria': lambda stats: stats.get('TEST', 0) > 40,\n        'multiplier': 1.1,\n        'icon': '🧪'\n    },\n    'MAINTENANCE': {\n        'description': 'Maintenance Day',\n        'criteria': lambda stats: stats.get('CHORE', 0) > 40,\n        'multiplier': 0.8,\n        'icon': '🔨'\n    },\n    'MIXED': {\n        'description': 'Mixed Activities',\n        'criteria': lambda stats: True,\n        'multiplier': 1.0,\n        'icon': '📦'\n    }\n}\n

@dataclass
class TagConfig:
    """Configuration for a single tag."""
    name: str
    weight: float
    aliases: List[str]
    description: str
    color: str  # For future UI/Excel formatting
    icon: str


class TagSystem:
    """Expanded TAG system with 16 categories."""
    
    # Core tag hierarchy
    TAGS: Dict[str, TagConfig] = {
        # ============== Development (Primary) ==============
        'FEAT': TagConfig(
            name='FEAT',
            weight=1.0,
            aliases=['FEATURE', '✨', 'feat', 'feat:', 'feature:'],
            description='New feature implementation',
            color='#10B981',  # Green
            icon='✨'
        ),
        'FIX': TagConfig(
            name='FIX',
            weight=1.5,
            aliases=['fix', 'fix:', 'FIX:', '🐛', 'bugfix'],
            description='Bug fix',
            color='#EF4444',  # Red
            icon='🐛'
        ),
        'REFACTOR': TagConfig(
            name='REFACTOR',
            weight=2.0,
            aliases=['RAFACTOR', '♻️', 'refactor', 'refactor:', 'refactoring'],
            description='Code refactoring (debt repayment)',
            color='#8B5CF6',  # Purple
            icon='♻️'
        ),
        
        # ============== Quality & Testing ==============
        'TEST': TagConfig(
            name='TEST',
            weight=1.2,
            aliases=['test', 'test:', 'tests', '🧪', 'testing'],
            description='Testing code',
            color='#06B6D4',  # Cyan
            icon='🧪'
        ),
        'DEBUG': TagConfig(
            name='DEBUG',
            weight=1.3,
            aliases=['debug', 'debug:', 'debugging'],
            description='Debugging session',
            color='#F59E0B',  # Amber
            icon='🔍'
        ),
        
        # ============== Documentation & Config ==============
        'DOC': TagConfig(
            name='DOC',
            weight=0.8,
            aliases=['docs', 'DOCS', 'doc:', 'docs:', '📚', 'documentation'],
            description='Documentation',
            color='#3B82F6',  # Blue
            icon='📚'
        ),
        'CONFIG': TagConfig(
            name='CONFIG',
            weight=0.7,
            aliases=['config', 'config:', 'configuration', '🔧'],
            description='Configuration changes',
            color='#6B7280',  # Gray
            icon='🔧'
        ),
        
        # ============== Maintenance ==============
        'CHORE': TagConfig(
            name='CHORE',
            weight=0.6,
            aliases=['chore', 'chore:', '🔨', 'maintenance'],
            description='Maintenance tasks',
            color='#9CA3AF',  # Light gray
            icon='🔨'
        ),
        'I18N': TagConfig(
            name='I18N',
            weight=0.7,
            aliases=['i18n', 'I18N', 'i18n:', '🌍', 'translation', 'locale'],
            description='Internationalization',
            color='#14B8A6',  # Teal
            icon='🌍'
        ),
        
        # ============== Special Categories ==============
        'PERF': TagConfig(
            name='PERF',
            weight=1.4,
            aliases=['perf', 'PERF', 'perf:', 'performance', '⚡'],
            description='Performance optimization',
            color='#FBBF24',  # Yellow
            icon='⚡'
        ),
        'SECURITY': TagConfig(
            name='SECURITY',
            weight=1.8,
            aliases=['security', 'SECURITY', 'security:', '🔒', 'sec:'],
            description='Security fix/enhancement',
            color='#DC2626',  # Dark red
            icon='🔒'
        ),
        'WIP': TagConfig(
            name='WIP',
            weight=0.3,
            aliases=['wip', 'WIP', 'wip:', '🚧', 'work in progress'],
            description='Work in progress',
            color='#F97316',  # Orange
            icon='🚧'
        ),
        'REVERT': TagConfig(
            name='REVERT',
            weight=0.5,
            aliases=['revert', 'REVERT', 'revert:', '⏪'],
            description='Revert previous commit',
            color='#EF4444',  # Red
            icon='⏪'
        ),
        'MERGE': TagConfig(
            name='MERGE',
            weight=0.4,
            aliases=['merge', 'MERGE', 'Merge branch', 'Merge pull request'],
            description='Merge commit',
            color='#8B5CF6',  # Purple
            icon='🔀'
        ),
        'DEPLOY': TagConfig(
            name='DEPLOY',
            weight=0.8,
            aliases=['deploy', 'DEPLOY', 'deployment', '🚀'],
            description='Deployment',
            color='#10B981',  # Green
            icon='🚀'
        ),
        'UPDATE': TagConfig(
            name='UPDATE',
            weight=0.6,
            aliases=['update', 'UPDATE', 'updates'],
            description='Generic update (needs recategorization)',
            color='#6B7280',  # Gray
            icon='📦'
        ),
    }
    
    # Build reverse lookup: alias -> canonical tag
    _ALIAS_MAP: Dict[str, str] = {}
    
    @classmethod
    def _build_alias_map(cls) -> None:
        """Build reverse lookup map from aliases to canonical tags."""
        if cls._ALIAS_MAP:
            return  # Already built
        
        for tag_name, config in cls.TAGS.items():
            # Add canonical name
            cls._ALIAS_MAP[tag_name] = tag_name
            cls._ALIAS_MAP[tag_name.lower()] = tag_name
            
            # Add all aliases
            for alias in config.aliases:
                cls._ALIAS_MAP[alias] = tag_name
                cls._ALIAS_MAP[alias.lower()] = tag_name
    
    @classmethod
    def parse_tag(cls, commit_message: str) -> Tuple[Optional[str], float]:
        """
        Parse tag from commit message.
        
        Args:
            commit_message: Git commit message
            
        Returns:
            (tag_name, confidence_score)
            - tag_name: Canonical tag name or None if not found
            - confidence: 1.0 for explicit tags, lower for inferred
        """
        cls._build_alias_map()
        
        # Strategy 1: Bracket tags [TAG]
        bracket_match = re.search(r'\[([^\]]+)\]', commit_message)
        if bracket_match:
            potential_tag = bracket_match.group(1).strip()
            canonical = cls._ALIAS_MAP.get(potential_tag)
            if canonical:
                return canonical, 1.0
        
        # Strategy 2: Conventional commits (tag: message)
        conventional_match = re.match(r'^([a-zA-Z0-9_-]+):', commit_message)
        if conventional_match:
            potential_tag = conventional_match.group(1).strip()
            canonical = cls._ALIAS_MAP.get(potential_tag)
            if canonical:
                return canonical, 1.0
        
        # Strategy 3: Emoji at start
        emoji_match = re.match(r'^([\U0001F300-\U0001F9FF])', commit_message)
        if emoji_match:
            emoji = emoji_match.group(1)
            canonical = cls._ALIAS_MAP.get(emoji)
            if canonical:
                return canonical, 0.95  # Slightly lower confidence
        
        # Strategy 4: Merge commits (special case)
        if commit_message.startswith('Merge '):
            return 'MERGE', 1.0
        
        # Strategy 5: WIP detection (anywhere in message)
        if re.search(r'\bWIP\b', commit_message, re.IGNORECASE):
            return 'WIP', 0.9
        
        # Not found
        return None, 0.0
    
    @classmethod
    def get_weight(cls, tag_name: str) -> float:
        """Get weight for a tag."""
        config = cls.TAGS.get(tag_name)
        return config.weight if config else 0.5  # Default for unknown
    
    @classmethod
    def get_all_tags(cls) -> List[str]:
        """Get list of all canonical tag names."""
        return list(cls.TAGS.keys())
    
    @classmethod
    def get_config(cls, tag_name: str) -> Optional[TagConfig]:
        """Get configuration for a tag."""
        return cls.TAGS.get(tag_name)


# ============== Backward Compatibility ==============

# Legacy v6 TAG_WEIGHTS dict (for existing code compatibility)
TAG_WEIGHTS = {tag: config.weight for tag, config in TagSystem.TAGS.items()}

# Legacy TAG_REGEX (still works but limited)
TAG_REGEX = re.compile(r'\[(FEAT|FIX|DOC|CHORE|REFACTOR|TEST|DEBUG|PERF|SECURITY|WIP|REVERT|MERGE|DEPLOY|CONFIG|I18N|UPDATE)\]')


# ============== Usage Examples ==============

if __name__ == "__main__":
    # Test cases
    test_messages = [
        "[FEAT] Add payment system",
        "feat: Implement user authentication",
        "fix: Resolve memory leak",
        "🐛 Fix null pointer exception",
        "[RAFACTOR] Reorganize services",  # Typo handling
        "WIP on main: da1f6769",
        "Merge branch 'develop' into main",
        "✨ New dashboard component",
        "[UPDATE] Various fixes",
        "FEATURE: Add export functionality",
        "Random commit without tag",
    ]
    
    print("=" * 70)
    print("TAG System v2.0 - Test Results")
    print("=" * 70)
    
    for msg in test_messages:
        tag, confidence = TagSystem.parse_tag(msg)
        if tag:
            config = TagSystem.get_config(tag)
            print(f"\n✅ '{msg[:50]}'")
            print(f"   → Tag: {config.icon} {tag}")
            print(f"   → Weight: {config.weight}x")
            print(f"   → Confidence: {confidence:.2f}")
        else:
            print(f"\n❌ '{msg[:50]}'")
            print(f"   → UNTAGGED")
    
    print("\n" + "=" * 70)
    print(f"Total tags supported: {len(TagSystem.get_all_tags())}")
    print(f"Total aliases: {len(TagSystem._ALIAS_MAP)}")
