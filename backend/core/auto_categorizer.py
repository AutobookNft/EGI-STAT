#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auto-Categorization Engine
Author: Fabio Cherici & Padmin D. Curtis (AI Partner OS3.0)
License: MIT
Version: 1.0.0
Date: 2026-01-20

Automatically categorize untagged commits using:
- Rule-based keyword/file/diff analysis
- Optional LLM fallback for low-confidence cases
"""

from __future__ import annotations

import os
import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

# Import TAG system
from tag_system_v2 import TagSystem

# Optional LLM support
HAVE_ANTHROPIC = False
try:
    import anthropic
    HAVE_ANTHROPIC = True
except ImportError:
    pass


@dataclass
class CategorizationResult:
    """Result of commit categorization."""
    tag: str
    confidence: float
    method: str  # 'explicit', 'keyword', 'file_path', 'diff', 'llm'
    reasoning: str


class CommitCategorizer:
    """Auto-categorize commits using hybrid approach."""
    
    # Keyword patterns for each tag
    KEYWORD_RULES = {
        'FIX': [
            r'\b(fix|bug|crash|error|resolve|patch|hotfix)\b',
            r'\b(null\s+pointer|memory\s+leak|race\s+condition)\b',
            r'\b(broken|failing|failed)\b',
        ],
        'FEAT': [
            r'\b(add|implement|create|new|feature)\b',
            r'\b(introduce|support\s+for)\b',
        ],
        'REFACTOR': [
            r'\b(refactor|reorganize|restructure|simplify|cleanup|clean\s+up)\b',
            r'\b(improve\s+code|code\s+quality)\b',
        ],
        'DOC': [
            r'\b(doc|documentation|readme|comment|javadoc)\b',
            r'\b(update\s+docs|add\s+docs)\b',
        ],
        'TEST': [
            r'\b(test|spec|coverage|unit\s+test|integration\s+test)\b',
        ],
        'CONFIG': [
            r'\b(config|configuration|env|environment|settings)\b',
            r'\b(webpack|babel|eslint|prettierrc)\b',
        ],
        'I18N': [
            r'\b(translation|locale|i18n|internationalization)\b',
            r'\b(language\s+file|localization)\b',
        ],
        'PERF': [
            r'\b(performance|optimize|optimization|speed|cache|caching)\b',
            r'\b(faster|improve\s+performance)\b',
        ],
        'SECURITY': [
            r'\b(security|vulnerability|xss|csrf|sql\s+injection)\b',
            r'\b(auth|authentication|authorization|permission)\b',
            r'\b(sanitize|escape|validate\s+input)\b',
        ],
        'CHORE': [
            r'\b(chore|maintenance|housekeeping|dependencies|deps)\b',
            r'\b(update\s+packages|bump\s+version)\b',
        ],
        'DEPLOY': [
            r'\b(deploy|deployment|release|publish)\b',
            r'\b(production|staging)\b',
        ],
        'WIP': [
            r'\bWIP\b',
            r'\b(work\s+in\s+progress|incomplete|ongoing)\b',
        ],
        'REVERT': [
            r'\b(revert|rollback|undo)\b',
        ],
    }
    
    # File path patterns
    FILE_PATH_RULES = {
        'TEST': [r'tests?/', r'spec/', r'\.test\.(js|ts|py)$', r'\.spec\.(js|ts)$'],
        'DOC': [r'docs?/', r'README', r'\.md$', r'CHANGELOG'],
        'CONFIG': [r'config/', r'\.env', r'webpack\.config', r'\.yml$', r'\.yaml$'],
        'I18N': [r'lang/', r'locale/', r'translations?/', r'i18n/'],
        'DEPLOY': [r'deploy/', r'\.github/workflows/', r'Dockerfile', r'docker-compose'],
    }
    
    # Diff pattern hints
    DIFF_RULES = {
        'REFACTOR': lambda diff: 'class' in diff and 'def' in diff and diff.count('\n') > 50,
        'PERF': lambda diff: 'cache' in diff.lower() or 'optimize' in diff.lower(),
        'SECURITY': lambda diff: 'password' in diff or 'token' in diff or 'secret' in diff,
    }
    
    def __init__(self, llm_api_key: Optional[str] = None, llm_model: str = "claude-3-5-sonnet-20241022"):
        """
        Initialize categorizer.
        
        Args:
            llm_api_key: Anthropic API key for LLM fallback (optional)
            llm_model: Claude model to use
        """
        self.llm_client = None
        self.llm_model = llm_model
        
        if llm_api_key and HAVE_ANTHROPIC:
            self.llm_client = anthropic.Anthropic(api_key=llm_api_key)
    
    def categorize(
        self,
        message: str,
        files: List[str] = None,
        diff: str = "",
        use_llm: bool = False
    ) -> CategorizationResult:
        """
        Categorize a commit.
        
        Args:
            message: Commit message
            files: List of changed file paths
            diff: Diff content (optional)
            use_llm: Enable LLM fallback for low-confidence
            
        Returns:
            CategorizationResult with tag and confidence
        """
        files = files or []
        
        # Step 1: Check explicit tag
        explicit_tag, confidence = TagSystem.parse_tag(message)
        if explicit_tag:
            return CategorizationResult(
                tag=explicit_tag,
                confidence=confidence,
                method='explicit',
                reasoning=f'Explicit tag found in message'
            )
        
        # Step 2: Keyword matching
        keyword_result = self._match_keywords(message)
        if keyword_result and keyword_result.confidence >= 0.7:
            return keyword_result
        
        # Step 3: File path analysis
        file_result = self._match_file_paths(files)
        if file_result and file_result.confidence >= 0.8:
            return file_result
        
        # Step 4: Diff analysis
        if diff:
            diff_result = self._match_diff_patterns(diff)
            if diff_result and diff_result.confidence >= 0.75:
                return diff_result
        
        # Step 5: Combine heuristics
        combined = self._combine_signals(keyword_result, file_result, diff_result if diff else None)
        if combined and combined.confidence >= 0.65:
            return combined
        
        # Step 6: LLM fallback (if enabled and low confidence)
        if use_llm and self.llm_client:
            llm_result = self._categorize_with_llm(message, files, diff)
            if llm_result:
                return llm_result
        
        # Fallback: UNTAGGED
        return CategorizationResult(
            tag='UNTAGGED',
            confidence=0.0,
            method='fallback',
            reasoning='No clear category detected'
        )
    
    def _match_keywords(self, message: str) -> Optional[CategorizationResult]:
        """Match commit message against keyword patterns."""
        message_lower = message.lower()
        
        scores = {}
        for tag, patterns in self.KEYWORD_RULES.items():
            score = 0
            matches = []
            
            for pattern in patterns:
                if re.search(pattern, message_lower, re.IGNORECASE):
                    score += 1
                    matches.append(pattern)
            
            if score > 0:
                scores[tag] = (score, matches)
        
        if not scores:
            return None
        
        # Get best match
        best_tag = max(scores, key=lambda t: scores[t][0])
        best_score, matches = scores[best_tag]
        
        # Calculate confidence (higher if multiple patterns match)
        confidence = min(0.6 + (best_score * 0.15), 0.95)
        
        return CategorizationResult(
            tag=best_tag,
            confidence=confidence,
            method='keyword',
            reasoning=f'Keywords matched: {", ".join(matches[:2])}'
        )
    
    def _match_file_paths(self, files: List[str]) -> Optional[CategorizationResult]:
        """Match file paths against patterns."""
        if not files:
            return None
        
        scores = {}
        for tag, patterns in self.FILE_PATH_RULES.items():
            matches = 0
            for file_path in files:
                for pattern in patterns:
                    if re.search(pattern, file_path):
                        matches += 1
                        break
            
            if matches > 0:
                scores[tag] = matches
        
        if not scores:
            return None
        
        best_tag = max(scores, key=scores.get)
        match_ratio = scores[best_tag] / len(files)
        
        # High confidence if >50% of files match
        confidence = min(0.7 + (match_ratio * 0.25), 0.95)
        
        return CategorizationResult(
            tag=best_tag,
            confidence=confidence,
            method='file_path',
            reasoning=f'{scores[best_tag]}/{len(files)} files match pattern'
        )
    
    def _match_diff_patterns(self, diff: str) -> Optional[CategorizationResult]:
        """Match diff content against patterns."""
        for tag, matcher in self.DIFF_RULES.items():
            if callable(matcher) and matcher(diff):
                return CategorizationResult(
                    tag=tag,
                    confidence=0.75,
                    method='diff',
                    reasoning='Diff pattern suggests this category'
                )
        return None
    
    def _combine_signals(
        self,
        keyword_result: Optional[CategorizationResult],
        file_result: Optional[CategorizationResult],
        diff_result: Optional[CategorizationResult]
    ) -> Optional[CategorizationResult]:
        """Combine multiple weak signals into stronger result."""
        results = [r for r in [keyword_result, file_result, diff_result] if r]
        
        if not results:
            return None
        
        # If multiple signals agree, boost confidence
        tag_votes = {}
        for r in results:
            tag_votes[r.tag] = tag_votes.get(r.tag, 0) + r.confidence
        
        best_tag = max(tag_votes, key=tag_votes.get)
        combined_confidence = tag_votes[best_tag] / len(results)
        
        # Boost if multiple methods agree
        methods = [r.method for r in results if r.tag == best_tag]
        if len(methods) > 1:
            combined_confidence = min(combined_confidence + 0.15, 0.95)
        
        return CategorizationResult(
            tag=best_tag,
            confidence=combined_confidence,
            method='combined',
            reasoning=f'Combined signals: {", ".join(methods)}'
        )
    
    def _categorize_with_llm(
        self,
        message: str,
        files: List[str],
        diff: str
    ) -> Optional[CategorizationResult]:
        """Use LLM for categorization (expensive, use sparingly)."""
        if not self.llm_client:
            return None
        
        # Build prompt
        valid_tags = ', '.join(TagSystem.get_all_tags())
        files_str = ', '.join(files[:10]) if files else 'No files provided'
        diff_snippet = diff[:300] + '...' if len(diff) > 300 else diff
        
        prompt = f"""Categorize this git commit into ONE of these tags:
{valid_tags}

Commit message: {message}
Files changed: {files_str}
Diff snippet: {diff_snippet}

Response format:
TAG_NAME | confidence (0.0-1.0) | brief reasoning

Example: FIX | 0.95 | Resolves null pointer exception in payment service
"""
        
        try:
            response = self.llm_client.messages.create(
                model=self.llm_model,
                max_tokens=100,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parse response
            content = response.content[0].text.strip()
            parts = content.split('|')
            
            if len(parts) >= 3:
                tag = parts[0].strip()
                confidence = float(parts[1].strip())
                reasoning = parts[2].strip()
                
                # Validate tag
                if tag in TagSystem.get_all_tags():
                    return CategorizationResult(
                        tag=tag,
                        confidence=confidence,
                        method='llm',
                        reasoning=reasoning
                    )
        
        except Exception as e:
            print(f"⚠️  LLM categorization failed: {e}")
        
        return None


# ============== CLI for testing ==============

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Auto-Categorize Commits')
    parser.add_argument('--message', required=True, help='Commit message')
    parser.add_argument('--files', nargs='*', help='Changed files')
    parser.add_argument('--llm', action='store_true', help='Enable LLM fallback')
    parser.add_argument('--api-key', help='Anthropic API key (or use ANTHROPIC_API_KEY env)')
    
    args = parser.parse_args()
    
    api_key = args.api_key or os.getenv('ANTHROPIC_API_KEY')
    categorizer = CommitCategorizer(llm_api_key=api_key if args.llm else None)
    
    result = categorizer.categorize(
        message=args.message,
        files=args.files or [],
        use_llm=args.llm
    )
    
    print("\n" + "="*70)
    print("🔍 Categorization Result")
    print("="*70)
    print(f"Message: {args.message}")
    print(f"Tag: {result.tag}")
    print(f"Confidence: {result.confidence:.2f}")
    print(f"Method: {result.method}")
    print(f"Reasoning: {result.reasoning}")
    print("="*70)
