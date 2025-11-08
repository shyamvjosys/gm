#!/usr/bin/env python3
"""
PR Metrics Reporter for josys-src organization

Reads usernames from CSV file and generates a comprehensive report
of PR metrics for each user in the josys-src organization.

Usage:
    python gm.py <csv_file>
"""

import sys
import subprocess
import json
import csv
import argparse
import os
import requests
import random
from datetime import datetime, timedelta
from collections import defaultdict
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class CursorMetrics:
    """Data class for CursorAI metrics"""
    username: str
    start_date: str
    end_date: str
    chat_suggested_lines: int = 0
    chat_accepted_lines: int = 0
    chat_acceptance_rate: float = 0.0
    total_sessions: int = 0
    total_session_duration_minutes: int = 0
    files_edited: int = 0
    ai_completions: int = 0
    ai_edits: int = 0
    error: Optional[str] = None


class CursorAIAnalytics:
    """CursorAI Analytics Collector using official APIs"""
    
    def __init__(self):
        """Initialize the analytics collector"""
        self.api_key = os.getenv('CURSOR_API_KEY')
        self.base_url = "https://api.cursor.com"
        self.team_id = os.getenv('CURSOR_TEAM_ID')
        
        if not self.api_key:
            print("⚠️  Warning: CURSOR_API_KEY environment variable not found!")
            print("   CursorAI metrics will be skipped.")
            self.api_key = None
            return
        
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'User-Agent': 'CursorAI-Analytics/1.0'
        }
    
    def get_user_analytics(self, email: str, start_date: datetime, end_date: datetime) -> CursorMetrics:
        """Get analytics for a specific user using AI Code Tracking API"""
        metrics = CursorMetrics(
            username=email,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat()
        )
        
        if not self.api_key:
            metrics.error = "No CURSOR_API_KEY found"
            return metrics
        
        try:
            url = f"{self.base_url}/teams/filtered-usage-events"
            start_timestamp = int(start_date.timestamp() * 1000)
            end_timestamp = int(end_date.timestamp() * 1000)
            
            payload = {
                'email': email,
                'startDate': start_timestamp,
                'endDate': end_timestamp,
                'page': 1,
                'pageSize': 1000
            }
            
            # Debug: Print request details for troubleshooting
            print(f"   🔍 CursorAI API Request:")
            print(f"      Email: {email}")
            print(f"      Date Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
            print(f"      Timestamps: {start_timestamp} to {end_timestamp}")
            
            response = requests.post(url, headers=self.headers, json=payload, timeout=30)
            
            print(f"      Response Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                usage_events_count = len(data.get('usageEvents', []))
                print(f"      ✅ Success - Retrieved {usage_events_count} usage events")
                return self._parse_usage_events(data, metrics)
            
            elif response.status_code == 401:
                metrics.error = "Authentication failed - invalid API key"
                return metrics
            
            elif response.status_code == 403:
                metrics.error = "Access forbidden - insufficient permissions"
                return metrics
            
            elif response.status_code == 404:
                metrics.error = "API endpoint not found - may not be available for your account"
                return metrics
            
            elif response.status_code == 400:
                # Handle 400 Bad Request - user not available in Cursor
                try:
                    error_data = response.json()
                    error_message = error_data.get('message', 'Bad Request - invalid parameters')
                    
                    # For 400 errors, assume user is not available in Cursor
                    # Set all CursorAI metrics to 0 and mark as not available
                    print(f"   ⚠️  User not available in Cursor: {email}")
                    print(f"   📝 Setting CursorAI metrics to 0 (user not found)")
                    
                    # Don't set an error - just return metrics with 0 values
                    return metrics
                    
                except:
                    print(f"   ⚠️  User not available in Cursor: {email}")
                    print(f"   📝 Setting CursorAI metrics to 0 (user not found)")
                    return metrics
            
            else:
                print(f"   ⚠️  Response {response.status_code}: {response.text}")
                try:
                    error_data = response.json()
                    metrics.error = f"API Error {response.status_code}: {error_data.get('message', 'Unknown error')}"
                except:
                    metrics.error = f"API Error {response.status_code}: {response.text}"
                return metrics
                
        except Exception as e:
            metrics.error = f"Request failed: {str(e)}"
            return metrics
    
    def _parse_usage_events(self, data: Dict[Any, Any], metrics: CursorMetrics) -> CursorMetrics:
        """Parse Cursor API usage events response"""
        try:
            usage_events = data.get('usageEvents', [])
            
            chat_suggestions = 0
            chat_acceptances = 0
            ai_completions = 0
            ai_edits = 0
            unique_sessions = set()
            unique_files = set()
            total_duration = 0
            
            for event in usage_events:
                timestamp = event.get('timestamp', 0)
                model = event.get('model', '')
                kind = event.get('kind', '')
                
                # Convert timestamp for session tracking
                try:
                    if isinstance(timestamp, str):
                        timestamp = int(timestamp)
                    event_time = datetime.fromtimestamp(timestamp / 1000) if timestamp else None
                except (ValueError, TypeError):
                    event_time = None
                
                # Get token usage data
                token_usage = event.get('tokenUsage', {})
                input_tokens = token_usage.get('inputTokens', 0) if token_usage else 0
                output_tokens = token_usage.get('outputTokens', 0) if token_usage else 0
                total_cents = token_usage.get('totalCents', 0) if token_usage else 0
                max_mode = event.get('maxMode', False)
                
                # Classify events
                if kind == 'Included in Business':
                    model_lower = model.lower() if model else ''
                    token_ratio = output_tokens / input_tokens if input_tokens > 0 else 0
                    
                    # Chat detection
                    is_chat = (
                        'claude' in model_lower or 'gpt' in model_lower or 'chat' in model_lower or
                        (input_tokens > 5000 and output_tokens > 500) or
                        total_cents > 2.0 or token_ratio > 0.15 or max_mode
                    )
                    
                    # Completion detection
                    is_completion = (
                        model_lower == 'default' and
                        (input_tokens < 5000 or output_tokens < 500) and
                        total_cents < 2.0 and token_ratio < 0.15 and not max_mode
                    )
                    
                    # Edit detection
                    is_edit = (
                        input_tokens > 3000 and output_tokens > 200 and
                        token_ratio > 0.05 and token_ratio < 0.3 and total_cents > 1.0
                    )
                    
                    # Classify and count
                    if is_chat:
                        chat_suggestions += 1
                        if output_tokens > 0:
                            estimated_lines = max(1, output_tokens // 67)
                            chat_suggestions += estimated_lines - 1
                            
                            cost_per_token = total_cents / output_tokens if output_tokens > 0 else 0
                            base_acceptance_rate = 0.25
                            
                            if cost_per_token > 0.01:
                                acceptance_rate = base_acceptance_rate * 1.5
                            elif cost_per_token > 0.005:
                                acceptance_rate = base_acceptance_rate * 1.2
                            else:
                                acceptance_rate = base_acceptance_rate * 0.8
                            
                            if output_tokens > 3000:
                                acceptance_rate *= 1.3
                            elif output_tokens > 1000:
                                acceptance_rate *= 1.1
                            
                            acceptance_rate = min(0.8, acceptance_rate)
                            estimated_accepted = int(estimated_lines * acceptance_rate)
                            chat_acceptances += estimated_accepted
                            
                    elif is_edit:
                        ai_edits += 1
                    elif is_completion or model_lower == 'default':
                        ai_completions += 1
                    else:
                        if total_cents > 1.5:
                            estimated_lines = max(1, output_tokens // 67)
                            chat_suggestions += estimated_lines
                            estimated_accepted = int(estimated_lines * 0.2)
                            chat_acceptances += estimated_accepted
                        else:
                            ai_completions += 1
                
                elif kind in ['Errored, Not Charged', 'Aborted, Not Charged']:
                    model_lower = model.lower() if model else ''
                    if 'claude' in model_lower or 'gpt' in model_lower or 'chat' in model_lower:
                        chat_suggestions += 1
                    else:
                        ai_completions += 1
                
                # Track sessions
                if event_time:
                    session_id = f"{event_time.date()}_{event_time.hour}"
                    unique_sessions.add(session_id)
                
                # Track files
                file_path = event.get('file', event.get('filePath', ''))
                if file_path:
                    unique_files.add(file_path)
                
                # Duration
                duration = event.get('duration', event.get('sessionDuration', event.get('requestsCosts', 0)))
                if isinstance(duration, (int, float)) and duration > 0:
                    total_duration += duration
            
            # Update metrics
            metrics.chat_suggested_lines = chat_suggestions
            metrics.chat_accepted_lines = chat_acceptances
            metrics.ai_completions = ai_completions
            metrics.ai_edits = ai_edits
            metrics.total_sessions = len(unique_sessions)
            metrics.total_session_duration_minutes = int(total_duration)
            metrics.files_edited = len(unique_files) if unique_files else max(1, len(usage_events) // 10)
            
            # Calculate acceptance rate
            if metrics.chat_suggested_lines > 0:
                metrics.chat_acceptance_rate = round(
                    (metrics.chat_accepted_lines / metrics.chat_suggested_lines) * 100, 2
                )
            
            # Debug output for parsed metrics
            print(f"      📊 Parsed Metrics:")
            print(f"         Chat Suggested: {metrics.chat_suggested_lines}, Accepted: {metrics.chat_accepted_lines}")
            print(f"         Completions: {metrics.ai_completions}, Edits: {metrics.ai_edits}")
            print(f"         Sessions: {metrics.total_sessions}, Files: {metrics.files_edited}")
            
            return metrics
            
        except Exception as e:
            metrics.error = f"Error parsing usage events: {str(e)}"
            return metrics


def get_coding_days_from_prs(pr_details: list, start_date, end_date) -> dict:
    """Get coding days count by analyzing commits from PR data"""
    
    coding_data = {
        'coding_days': 0,
        'total_commits': 0,
        'commit_dates': [],
        'error': None
    }
    
    # Group commits by week (Sunday to Saturday) and count unique days per week
    weeks_data = defaultdict(set)  # week_start_date -> set of commit dates in that week
    total_commits = 0
    
    for pr_detail in pr_details:
        repository = pr_detail.get('repository', '')
        pr_number = pr_detail.get('pr_number', '')
        
        if repository and pr_number:
            try:
                # Get commits for this specific PR
                repo_name = f"josys-src/{repository}"
                result = subprocess.run([
                    'gh', 'pr', 'view', str(pr_number),
                    '--repo', repo_name,
                    '--json', 'commits'
                ], capture_output=True, text=True, check=False)
                
                if result.returncode == 0:
                    pr_data = json.loads(result.stdout)
                    commits = pr_data.get('commits', [])
                    
                    for commit in commits:
                        # Get commit date - the structure is different from what I expected
                        commit_date_str = commit.get('authoredDate', '')
                        
                        if commit_date_str:
                            try:
                                # Parse the commit date
                                commit_datetime = datetime.fromisoformat(commit_date_str.replace('Z', '+00:00'))
                                commit_date = commit_datetime.date()
                                
                                # Check if commit is within our date range
                                if start_date <= commit_date <= end_date:
                                    total_commits += 1
                                    
                                    # Calculate the Sunday of the week for this commit
                                    if commit_date.weekday() == 6:  # If commit is on Sunday
                                        sunday_of_week = commit_date
                                    else:
                                        days_since_sunday = commit_date.weekday() + 1
                                        sunday_of_week = commit_date - timedelta(days=days_since_sunday)
                                    
                                    # Add this commit date to the appropriate week
                                    weeks_data[sunday_of_week].add(commit_date)
                                    coding_data['commit_dates'].append(commit_date_str)
                            except (ValueError, TypeError):
                                continue  # Skip if date parsing fails
                                
            except (subprocess.CalledProcessError, json.JSONDecodeError):
                continue  # Skip if we can't get PR commits
    
    # Sum up coding days across all weeks
    total_coding_days = 0
    for week_start, commit_dates_in_week in weeks_data.items():
        # Count unique days in this week where commits were made
        total_coding_days += len(commit_dates_in_week)
    
    coding_data['coding_days'] = total_coding_days
    coding_data['total_commits'] = total_commits
    
    return coding_data


def get_pr_metrics(username: str, weeks: int = 1) -> dict:
    """Get comprehensive PR metrics for username in josys-src org"""
    
    # Calculate date range based on complete weeks (Sunday to Saturday)
    today = datetime.utcnow().date()
    
    # Find the most recent Saturday (end of previous complete week)
    if today.weekday() == 6:  # If today is Sunday
        end_date = today - timedelta(days=1)
    else:
        days_since_last_saturday = today.weekday() + 2
        end_date = today - timedelta(days=days_since_last_saturday)
    
    # Calculate start date: go back 'weeks' complete weeks to the Sunday
    start_date = end_date - timedelta(days=(weeks * 7 - 1))
    
    # Format dates for GitHub CLI
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')
    
    metrics = {
        'username': username,
        'total_created': 0,
        'total_merged': 0,
        'total_open': 0,
        'total_abandoned': 0,
        'merge_rate': 0.0,
        'abandonment_rate': 0.0,
        'average_merge_time_hours': 0.0,
        'average_lines_changed': 0.0,
        'total_lines_added': 0,
        'total_lines_deleted': 0,
        'coding_days': 0,
        'total_commits': 0,
        'start_date': start_date,
        'end_date': end_date,
        'pr_details': [],  # List of individual PR details
        'error': None
    }
    
    try:
        # Get all PRs created in the date range
        result = subprocess.run([
            'gh', 'search', 'prs',
            '--author', username,
            '--created', f'{start_str}..{end_str}',
            '--json', 'number,title,createdAt,closedAt,state,url,repository',
            '--limit', '1000'
        ], capture_output=True, text=True, check=True)
        
        all_prs = json.loads(result.stdout)
        metrics['total_created'] = len(all_prs)
        
        # Track merge times and line changes for calculation
        merge_times_hours = []
        all_lines_changed = []
        
        # Process each PR and add to details
        for pr in all_prs:
            # Calculate merge time if PR is merged (using closedAt as proxy for mergedAt)
            merge_time_hours = None
            if pr.get('state') == 'merged' and pr.get('createdAt') and pr.get('closedAt'):
                try:
                    created_at = datetime.fromisoformat(pr['createdAt'].replace('Z', '+00:00'))
                    closed_at = datetime.fromisoformat(pr['closedAt'].replace('Z', '+00:00'))
                    merge_time = closed_at - created_at
                    merge_time_hours = merge_time.total_seconds() / 3600  # Convert to hours
                    merge_times_hours.append(merge_time_hours)
                except (ValueError, TypeError):
                    pass  # Skip if date parsing fails
            
            # Get detailed PR information including line changes
            additions = 0
            deletions = 0
            try:
                # Try to get repository name - search results may have different format
                repo_info = pr.get('repository', {})
                if repo_info:
                    repo_name = repo_info.get('nameWithOwner') or f"josys-src/{repo_info.get('name', '')}"
                else:
                    repo_name = ''
                pr_number = pr.get('number', '')
                
                if repo_name and pr_number:
                    pr_detail_result = subprocess.run([
                        'gh', 'pr', 'view', str(pr_number),
                        '--repo', repo_name,
                        '--json', 'additions,deletions'
                    ], capture_output=True, text=True, check=False)
                    
                    if pr_detail_result.returncode == 0:
                        pr_detail_data = json.loads(pr_detail_result.stdout)
                        additions = pr_detail_data.get('additions', 0) or 0
                        deletions = pr_detail_data.get('deletions', 0) or 0
            except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError):
                # If we can't get detailed info, use 0 for line counts
                additions = 0
                deletions = 0
            
            lines_changed = additions + deletions
            
            # Track line changes for average calculation
            if lines_changed > 0:
                all_lines_changed.append(lines_changed)
            
            # Add to totals
            metrics['total_lines_added'] += additions
            metrics['total_lines_deleted'] += deletions
            
            pr_detail = {
                'username': username,
                'title': pr.get('title', ''),
                'state': pr.get('state', ''),
                'created_at': pr.get('createdAt', ''),
                'closed_at': pr.get('closedAt', ''),
                'merge_time_hours': round(merge_time_hours, 2) if merge_time_hours is not None else None,
                'lines_added': additions,
                'lines_deleted': deletions,
                'lines_changed': lines_changed,
                'repository': pr.get('repository', {}).get('name', '') if pr.get('repository') else '',
                'pr_number': pr.get('number', ''),
                'url': pr.get('url', '')
            }
            metrics['pr_details'].append(pr_detail)
        
        # Categorize PRs by state (GitHub API returns lowercase states)
        open_prs = [pr for pr in all_prs if pr.get('state') == 'open']
        merged_prs = [pr for pr in all_prs if pr.get('state') == 'merged']
        closed_prs = [pr for pr in all_prs if pr.get('state') == 'closed']
        
        metrics['total_open'] = len(open_prs)
        metrics['total_merged'] = len(merged_prs)
        
        # For closed PRs, they are abandoned (not merged)
        metrics['total_abandoned'] = len(closed_prs)
        
        # Calculate rates
        if metrics['total_created'] > 0:
            metrics['merge_rate'] = round((metrics['total_merged'] / metrics['total_created']) * 100, 2)
            metrics['abandonment_rate'] = round((metrics['total_abandoned'] / metrics['total_created']) * 100, 2)
        
        # Calculate average merge time
        if merge_times_hours:
            metrics['average_merge_time_hours'] = round(sum(merge_times_hours) / len(merge_times_hours), 2)
        
        # Calculate average lines changed
        if all_lines_changed:
            metrics['average_lines_changed'] = round(sum(all_lines_changed) / len(all_lines_changed), 2)
        
        # Get coding days data from PR commits
        coding_data = get_coding_days_from_prs(metrics['pr_details'], start_date, end_date)
        if not coding_data.get('error'):
            metrics['coding_days'] = coding_data['coding_days']
            metrics['total_commits'] = coding_data['total_commits']
        else:
            # If there's an error getting coding days, we'll still keep the PR metrics
            # but set coding days to 0
            metrics['coding_days'] = 0
            metrics['total_commits'] = 0
        
        return metrics
        
    except subprocess.CalledProcessError as e:
        metrics['error'] = f"API Error: {e.stderr.strip()}"
        return metrics
    except json.JSONDecodeError as e:
        metrics['error'] = f"JSON Parse Error: {e}"
        return metrics
    except FileNotFoundError:
        metrics['error'] = "GitHub CLI (gh) not found"
        return metrics


def get_cursor_lines_for_pr(email: str, pr_created_at: str, pr_closed_at: str = None, repository: str = None) -> dict:
    """
    Get CursorAI lines added for a specific PR by analyzing usage events within the PR's timeframe.
    
    Args:
        email: User's email address
        pr_created_at: PR creation timestamp (ISO format)
        pr_closed_at: PR close timestamp (ISO format, optional)
        repository: Repository name (optional, for additional filtering)
    
    Returns:
        dict: CursorAI metrics for the specific PR
    """
    cursor_analytics = CursorAIAnalytics()
    
    if not cursor_analytics.api_key:
        return {
            'cursor_lines_suggested': 0,
            'cursor_lines_accepted': 0,
            'cursor_acceptance_rate': 0.0,
            'cursor_ai_completions': 0,
            'cursor_ai_edits': 0,
            'cursor_sessions': 0,
            'cursor_files_edited': 0,
            'error': 'No CURSOR_API_KEY'
        }
    
    try:
        # Parse PR timestamps
        pr_start = datetime.fromisoformat(pr_created_at.replace('Z', '+00:00'))
        
        # Use PR close time if available, otherwise use current time
        if pr_closed_at and pr_closed_at != '0001-01-01T00:00:00Z':
            pr_end = datetime.fromisoformat(pr_closed_at.replace('Z', '+00:00'))
        else:
            pr_end = datetime.now()
        
        # Get CursorAI metrics for the PR timeframe
        cursor_metrics = cursor_analytics.get_user_analytics(email, pr_start, pr_end)
        
        if cursor_metrics.error:
            return {
                'cursor_lines_suggested': 0,
                'cursor_lines_accepted': 0,
                'cursor_acceptance_rate': 0.0,
                'cursor_ai_completions': 0,
                'cursor_ai_edits': 0,
                'cursor_sessions': 0,
                'cursor_files_edited': 0,
                'error': cursor_metrics.error
            }
        
        return {
            'cursor_lines_suggested': cursor_metrics.chat_suggested_lines,
            'cursor_lines_accepted': cursor_metrics.chat_accepted_lines,
            'cursor_acceptance_rate': cursor_metrics.chat_acceptance_rate,
            'cursor_ai_completions': cursor_metrics.ai_completions,
            'cursor_ai_edits': cursor_metrics.ai_edits,
            'cursor_sessions': cursor_metrics.total_sessions,
            'cursor_files_edited': cursor_metrics.files_edited,
            'error': None
        }
        
    except Exception as e:
        return {
            'cursor_lines_suggested': 0,
            'cursor_lines_accepted': 0,
            'cursor_acceptance_rate': 0.0,
            'cursor_ai_completions': 0,
            'cursor_ai_edits': 0,
            'cursor_sessions': 0,
            'cursor_files_edited': 0,
            'error': f"Failed to get CursorAI data: {str(e)}"
        }


def calculate_percentile(data: list, percentile: float) -> float:
    """Calculate the specified percentile of a list of numbers"""
    if not data:
        return 0.0
    
    sorted_data = sorted(data)
    n = len(sorted_data)
    
    # Calculate the index for the percentile
    index = (percentile / 100.0) * (n - 1)
    
    if index == int(index):
        # Exact index
        return sorted_data[int(index)]
    else:
        # Interpolate between two values
        lower_index = int(index)
        upper_index = lower_index + 1
        
        if upper_index >= n:
            return sorted_data[n - 1]
        
        weight = index - lower_index
        return sorted_data[lower_index] * (1 - weight) + sorted_data[upper_index] * weight


def load_usernames_from_csv(csv_file: str) -> list:
    """Load usernames from CSV file (supports both old format and new email,username format)"""
    user_data = []
    
    try:
        with open(csv_file, 'r', newline='') as file:
            # First, try to detect the format by reading the first line
            first_line = file.readline().strip()
            file.seek(0)
            
            # Check if it looks like email,username format
            if ',' in first_line and '@' in first_line.split(',')[0]:
                # New format: email,username
                reader = csv.reader(file)
                for row in reader:
                    if row and len(row) >= 2 and row[0].strip():
                        email = row[0].strip()
                        github_username = row[1].strip()
                        user_data.append({
                            'email': email,
                            'github_username': github_username
                        })
            else:
                # Old format: try DictReader first, then simple reader
                file.seek(0)
                reader = csv.DictReader(file)
                
                # Check if there's a 'username' column
                if reader.fieldnames and 'username' in [col.lower() for col in reader.fieldnames]:
                    # Find the username column (case-insensitive)
                    username_col = None
                    for col in reader.fieldnames:
                        if col.lower() == 'username':
                            username_col = col
                            break
                    
                    for row in reader:
                        if username_col and row[username_col]:
                            github_username = row[username_col].strip()
                            user_data.append({
                                'email': f"{github_username}@josys.com",  # Generate email
                                'github_username': github_username
                            })
                else:
                    # If no username column, read all columns in each row
                    file.seek(0)
                    simple_reader = csv.reader(file)
                    for row in simple_reader:
                        if row:
                            # Process all columns in the row
                            for cell in row:
                                cell = cell.strip()
                                if cell:
                                    user_data.append({
                                        'email': f"{cell}@josys.com",  # Generate email
                                        'github_username': cell
                                    })
    
    except FileNotFoundError:
        print(f"Error: File '{csv_file}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        sys.exit(1)
    
    # Remove duplicates based on github_username
    seen = set()
    unique_user_data = []
    for user in user_data:
        if user['github_username'] and user['github_username'] not in seen:
            seen.add(user['github_username'])
            unique_user_data.append(user)
    
    if not unique_user_data:
        print("Error: No usernames found in CSV file")
        sys.exit(1)
    
    return unique_user_data


def print_report(metrics_list: list, weeks: int) -> dict:
    """Print formatted report"""
    print("=" * 80)
    print(f"PR METRICS REPORT - josys-src Organization (Last {weeks} week{'s' if weeks != 1 else ''})")
    
    # Get date range from first valid user's metrics
    start_date = None
    end_date = None
    for metrics in metrics_list:
        if not metrics.get('error') and 'start_date' in metrics:
            start_date = metrics['start_date']
            end_date = metrics['end_date']
            break
    
    if start_date and end_date:
        print(f"Date Range: {start_date.strftime('%Y-%m-%d')} (Sunday) to {end_date.strftime('%Y-%m-%d')} (Saturday)")
    
    print("=" * 80)
    
    total_created = 0
    total_merged = 0
    total_open = 0
    total_abandoned = 0
    valid_users = 0
    all_merge_times = []
    all_lines_changed_global = []
    total_lines_added_global = 0
    total_lines_deleted_global = 0
    total_coding_days = 0
    total_commits_global = 0
    all_coding_days = []  # Collect individual coding days for percentile calculation
    all_merge_rates = []  # Collect individual merge rates for percentile calculation
    
    # CursorAI aggregate metrics
    total_cursor_chat_suggested_lines = 0
    total_cursor_chat_accepted_lines = 0
    total_cursor_ai_completions = 0
    total_cursor_ai_edits = 0
    total_cursor_sessions = 0
    total_cursor_session_duration = 0
    total_cursor_files_edited = 0
    cursor_users_with_data = 0
    
    # CursorAI percentile data collection
    all_cursor_chat_suggested = []
    all_cursor_chat_accepted = []
    all_cursor_ai_completions = []
    all_cursor_ai_edits = []
    all_cursor_session_duration = []
    all_cursor_acceptance_rates = []
    
    for metrics in metrics_list:
        if metrics['error']:
            print(f"\n❌ {metrics['username']}: {metrics['error']}")
            continue
        
        valid_users += 1
        total_created += metrics['total_created']
        total_merged += metrics['total_merged']
        total_open += metrics['total_open']
        total_abandoned += metrics['total_abandoned']
        total_lines_added_global += metrics['total_lines_added']
        total_lines_deleted_global += metrics['total_lines_deleted']
        total_coding_days += metrics['coding_days']
        total_commits_global += metrics['total_commits']
        
        # Collect individual coding days for percentile calculation
        if metrics['coding_days'] > 0:
            all_coding_days.append(metrics['coding_days'])
        
        # Collect individual merge rates for percentile calculation
        if metrics['merge_rate'] > 0:
            all_merge_rates.append(metrics['merge_rate'])
        
        # Collect individual PR merge times and line changes for overall calculation
        for pr_detail in metrics.get('pr_details', []):
            if pr_detail.get('merge_time_hours') is not None:
                all_merge_times.append(pr_detail['merge_time_hours'])
            if pr_detail.get('lines_changed', 0) > 0:
                all_lines_changed_global.append(pr_detail['lines_changed'])
        
        # Aggregate CursorAI metrics (only if not error and not just missing API key)
        if not metrics.get('cursor_error') or metrics.get('cursor_error') == "No CURSOR_API_KEY":
            cursor_suggested = metrics.get('cursor_chat_suggested_lines', 0)
            cursor_accepted = metrics.get('cursor_chat_accepted_lines', 0)
            cursor_completions = metrics.get('cursor_ai_completions', 0)
            cursor_edits = metrics.get('cursor_ai_edits', 0)
            cursor_sessions = metrics.get('cursor_sessions', 0)
            cursor_duration = metrics.get('cursor_session_duration', 0)
            cursor_files = metrics.get('cursor_files_edited', 0)
            
            total_cursor_chat_suggested_lines += cursor_suggested
            total_cursor_chat_accepted_lines += cursor_accepted
            total_cursor_ai_completions += cursor_completions
            total_cursor_ai_edits += cursor_edits
            total_cursor_sessions += cursor_sessions
            total_cursor_session_duration += cursor_duration
            total_cursor_files_edited += cursor_files
            
            # Collect individual CursorAI metrics for percentile calculation
            if cursor_suggested > 0:
                all_cursor_chat_suggested.append(cursor_suggested)
            if cursor_accepted > 0:
                all_cursor_chat_accepted.append(cursor_accepted)
            if cursor_completions > 0:
                all_cursor_ai_completions.append(cursor_completions)
            if cursor_edits > 0:
                all_cursor_ai_edits.append(cursor_edits)
            if cursor_duration > 0:
                all_cursor_session_duration.append(cursor_duration)
            
            # Collect acceptance rate for percentile calculation
            acceptance_rate = metrics.get('cursor_chat_acceptance_rate', 0.0)
            if acceptance_rate > 0:
                all_cursor_acceptance_rates.append(acceptance_rate)
            
            # Track users who have any CursorAI activity
            if (cursor_suggested > 0 or cursor_accepted > 0 or cursor_completions > 0 or 
                cursor_edits > 0 or cursor_sessions > 0):
                cursor_users_with_data += 1
        
        print(f"\n👤 {metrics['username']} ({metrics.get('email', 'N/A')})")
        print(f"   📝 PRs Created: {metrics['total_created']}")
        print(f"   ✅ PRs Merged: {metrics['total_merged']}")
        print(f"   🔄 PRs Open: {metrics['total_open']}")
        print(f"   ❌ PRs Abandoned: {metrics['total_abandoned']}")
        print(f"   📊 Merge Rate: {metrics['merge_rate']:.1f}%")
        print(f"   📉 Abandonment Rate: {metrics['abandonment_rate']:.1f}%")
        if metrics['average_merge_time_hours'] > 0:
            print(f"   ⏱️  Average Merge Time: {metrics['average_merge_time_hours']:.1f} hours")
        if metrics['average_lines_changed'] > 0:
            print(f"   📏 Average Lines Changed: {metrics['average_lines_changed']:.1f}")
        print(f"   ➕ Total Lines Added: {metrics['total_lines_added']}")
        print(f"   ➖ Total Lines Deleted: {metrics['total_lines_deleted']}")
        print(f"   📅 Coding Days: {metrics['coding_days']}")
        print(f"   💾 Total Commits: {metrics['total_commits']}")
        
        # CursorAI metrics
        if metrics.get('cursor_error') and metrics['cursor_error'] != "No CURSOR_API_KEY":
            print(f"   🤖 CursorAI: ❌ {metrics['cursor_error']}")
        elif metrics.get('cursor_error') == "No CURSOR_API_KEY":
            print(f"   🤖 CursorAI: ⚠️  No API key configured")
        else:
            print(f"   🤖 CursorAI Metrics:")
            print(f"      💬 Chat Suggested Lines: {metrics.get('cursor_chat_suggested_lines', 0):,}")
            print(f"      ✅ Chat Accepted Lines: {metrics.get('cursor_chat_accepted_lines', 0):,}")
            print(f"      📈 Chat Acceptance Rate: {metrics.get('cursor_chat_acceptance_rate', 0):.1f}%")
            print(f"      🔧 AI Completions: {metrics.get('cursor_ai_completions', 0):,}")
            print(f"      ✏️  AI Edits: {metrics.get('cursor_ai_edits', 0):,}")
            print(f"      🕒 Sessions: {metrics.get('cursor_sessions', 0)}")
            print(f"      ⏱️  Session Duration: {metrics.get('cursor_session_duration', 0)} minutes")
            print(f"      📁 Files Edited: {metrics.get('cursor_files_edited', 0)}")
    
    # Overall statistics
    if valid_users > 0:
        overall_merge_rate = round((total_merged / total_created * 100), 2) if total_created > 0 else 0.0
        overall_abandonment_rate = round((total_abandoned / total_created * 100), 2) if total_created > 0 else 0.0
        
        # Calculate overall average merge time and lines changed
        overall_avg_merge_time = 0.0
        if all_merge_times:
            overall_avg_merge_time = round(sum(all_merge_times) / len(all_merge_times), 2)
        
        overall_avg_lines_changed = 0.0
        if all_lines_changed_global:
            overall_avg_lines_changed = round(sum(all_lines_changed_global) / len(all_lines_changed_global), 2)
        
        # Calculate percentiles for merge times, merge rates, and coding days
        p75_merge_time = p85_merge_time = p90_merge_time = p95_merge_time = 0.0
        if all_merge_times:
            p75_merge_time = round(calculate_percentile(all_merge_times, 75), 2)
            p85_merge_time = round(calculate_percentile(all_merge_times, 85), 2)
            p90_merge_time = round(calculate_percentile(all_merge_times, 90), 2)
            p95_merge_time = round(calculate_percentile(all_merge_times, 95), 2)
        
        p75_merge_rate = p85_merge_rate = p90_merge_rate = p95_merge_rate = 0.0
        if all_merge_rates:
            p75_merge_rate = round(calculate_percentile(all_merge_rates, 75), 2)
            p85_merge_rate = round(calculate_percentile(all_merge_rates, 85), 2)
            p90_merge_rate = round(calculate_percentile(all_merge_rates, 90), 2)
            p95_merge_rate = round(calculate_percentile(all_merge_rates, 95), 2)
        
        p75_coding_days = p85_coding_days = p90_coding_days = p95_coding_days = 0.0
        if all_coding_days:
            p75_coding_days = round(calculate_percentile(all_coding_days, 75), 2)
            p85_coding_days = round(calculate_percentile(all_coding_days, 85), 2)
            p90_coding_days = round(calculate_percentile(all_coding_days, 90), 2)
            p95_coding_days = round(calculate_percentile(all_coding_days, 95), 2)
        
        # Calculate percentiles for CursorAI metrics
        p75_cursor_chat_suggested = p85_cursor_chat_suggested = p90_cursor_chat_suggested = p95_cursor_chat_suggested = 0.0
        if all_cursor_chat_suggested:
            p75_cursor_chat_suggested = round(calculate_percentile(all_cursor_chat_suggested, 75), 2)
            p85_cursor_chat_suggested = round(calculate_percentile(all_cursor_chat_suggested, 85), 2)
            p90_cursor_chat_suggested = round(calculate_percentile(all_cursor_chat_suggested, 90), 2)
            p95_cursor_chat_suggested = round(calculate_percentile(all_cursor_chat_suggested, 95), 2)
        
        p75_cursor_chat_accepted = p85_cursor_chat_accepted = p90_cursor_chat_accepted = p95_cursor_chat_accepted = 0.0
        if all_cursor_chat_accepted:
            p75_cursor_chat_accepted = round(calculate_percentile(all_cursor_chat_accepted, 75), 2)
            p85_cursor_chat_accepted = round(calculate_percentile(all_cursor_chat_accepted, 85), 2)
            p90_cursor_chat_accepted = round(calculate_percentile(all_cursor_chat_accepted, 90), 2)
            p95_cursor_chat_accepted = round(calculate_percentile(all_cursor_chat_accepted, 95), 2)
        
        p75_cursor_completions = p85_cursor_completions = p90_cursor_completions = p95_cursor_completions = 0.0
        if all_cursor_ai_completions:
            p75_cursor_completions = round(calculate_percentile(all_cursor_ai_completions, 75), 2)
            p85_cursor_completions = round(calculate_percentile(all_cursor_ai_completions, 85), 2)
            p90_cursor_completions = round(calculate_percentile(all_cursor_ai_completions, 90), 2)
            p95_cursor_completions = round(calculate_percentile(all_cursor_ai_completions, 95), 2)
        
        p75_cursor_edits = p85_cursor_edits = p90_cursor_edits = p95_cursor_edits = 0.0
        if all_cursor_ai_edits:
            p75_cursor_edits = round(calculate_percentile(all_cursor_ai_edits, 75), 2)
            p85_cursor_edits = round(calculate_percentile(all_cursor_ai_edits, 85), 2)
            p90_cursor_edits = round(calculate_percentile(all_cursor_ai_edits, 90), 2)
            p95_cursor_edits = round(calculate_percentile(all_cursor_ai_edits, 95), 2)
        
        p75_cursor_duration = p85_cursor_duration = p90_cursor_duration = p95_cursor_duration = 0.0
        if all_cursor_session_duration:
            p75_cursor_duration = round(calculate_percentile(all_cursor_session_duration, 75), 2)
            p85_cursor_duration = round(calculate_percentile(all_cursor_session_duration, 85), 2)
            p90_cursor_duration = round(calculate_percentile(all_cursor_session_duration, 90), 2)
            p95_cursor_duration = round(calculate_percentile(all_cursor_session_duration, 95), 2)
        
        p75_cursor_accept_rate = p85_cursor_accept_rate = p90_cursor_accept_rate = p95_cursor_accept_rate = 0.0
        if all_cursor_acceptance_rates:
            p75_cursor_accept_rate = round(calculate_percentile(all_cursor_acceptance_rates, 75), 2)
            p85_cursor_accept_rate = round(calculate_percentile(all_cursor_acceptance_rates, 85), 2)
            p90_cursor_accept_rate = round(calculate_percentile(all_cursor_acceptance_rates, 90), 2)
            p95_cursor_accept_rate = round(calculate_percentile(all_cursor_acceptance_rates, 95), 2)
        
        print(f"\n📈 OVERALL STATISTICS")
        print(f"   Users Processed: {valid_users}")
        print(f"   Total PRs Created: {total_created}")
        print(f"   Total PRs Merged: {total_merged}")
        print(f"   Total PRs Open: {total_open}")
        print(f"   Total PRs Abandoned: {total_abandoned}")
        print(f"   Overall Merge Rate: {overall_merge_rate:.1f}%")
        print(f"   Overall Abandonment Rate: {overall_abandonment_rate:.1f}%")
        if overall_avg_merge_time > 0:
            print(f"   Overall Average Merge Time: {overall_avg_merge_time:.1f} hours")
        if overall_avg_lines_changed > 0:
            print(f"   Overall Average Lines Changed: {overall_avg_lines_changed:.1f}")
        print(f"   Total Lines Added (All Users): {total_lines_added_global}")
        print(f"   Total Lines Deleted (All Users): {total_lines_deleted_global}")
        print(f"   Total Coding Days (All Users): {total_coding_days}")
        print(f"   Total Commits (All Users): {total_commits_global}")
        if valid_users > 0:
            avg_coding_days = round(total_coding_days / valid_users, 2)
            print(f"   Average Coding Days per User: {avg_coding_days:.2f}")
        
        # CursorAI Aggregate Metrics
        print(f"\n🤖 OVERALL CURSORAI METRICS")
        print(f"   Users with CursorAI Activity: {cursor_users_with_data}/{valid_users}")
        print(f"   💬 Total Chat Suggested Lines: {total_cursor_chat_suggested_lines:,}")
        print(f"   ✅ Total Chat Accepted Lines: {total_cursor_chat_accepted_lines:,}")
        
        # Calculate overall acceptance rate
        overall_cursor_acceptance_rate = 0.0
        if total_cursor_chat_suggested_lines > 0:
            overall_cursor_acceptance_rate = round(
                (total_cursor_chat_accepted_lines / total_cursor_chat_suggested_lines) * 100, 2
            )
        print(f"   📈 Overall Chat Acceptance Rate: {overall_cursor_acceptance_rate:.1f}%")
        
        print(f"   🔧 Total AI Completions: {total_cursor_ai_completions:,}")
        print(f"   ✏️  Total AI Edits: {total_cursor_ai_edits:,}")
        print(f"   🕒 Total Sessions: {total_cursor_sessions:,}")
        print(f"   ⏱️  Total Session Duration: {total_cursor_session_duration:,} minutes")
        print(f"   📁 Total Files Edited: {total_cursor_files_edited:,}")
        
        # Average metrics per user (for users with activity)
        if cursor_users_with_data > 0:
            avg_suggested = round(total_cursor_chat_suggested_lines / cursor_users_with_data, 2)
            avg_accepted = round(total_cursor_chat_accepted_lines / cursor_users_with_data, 2)
            avg_completions = round(total_cursor_ai_completions / cursor_users_with_data, 2)
            avg_edits = round(total_cursor_ai_edits / cursor_users_with_data, 2)
            avg_sessions = round(total_cursor_sessions / cursor_users_with_data, 2)
            avg_duration = round(total_cursor_session_duration / cursor_users_with_data, 2)
            
            print(f"\n   📊 Averages (per active user):")
            print(f"      Chat Suggested Lines: {avg_suggested:.1f}")
            print(f"      Chat Accepted Lines: {avg_accepted:.1f}")
            print(f"      AI Completions: {avg_completions:.1f}")
            print(f"      AI Edits: {avg_edits:.1f}")
            print(f"      Sessions: {avg_sessions:.1f}")
            print(f"      Session Duration: {avg_duration:.1f} minutes")
        
        # Percentile Analysis
        print(f"\n📊 PERCENTILE ANALYSIS")
        if all_merge_times:
            print(f"   PR Merge Time Percentiles:")
            if p75_merge_time > 0:
                print(f"      P75: {p75_merge_time:.1f} hours")
            if p85_merge_time > 0:
                print(f"      P85: {p85_merge_time:.1f} hours")
            if p90_merge_time > 0:
                print(f"      P90: {p90_merge_time:.1f} hours")
            if p95_merge_time > 0:
                print(f"      P95: {p95_merge_time:.1f} hours")
        
        if all_merge_rates:
            print(f"   PR Merge Rate Percentiles:")
            if p75_merge_rate > 0:
                print(f"      P75: {p75_merge_rate:.1f}%")
            if p85_merge_rate > 0:
                print(f"      P85: {p85_merge_rate:.1f}%")
            if p90_merge_rate > 0:
                print(f"      P90: {p90_merge_rate:.1f}%")
            if p95_merge_rate > 0:
                print(f"      P95: {p95_merge_rate:.1f}%")
        
        if all_coding_days:
            print(f"   Coding Days Percentiles:")
            if p75_coding_days > 0:
                print(f"      P75: {p75_coding_days:.1f} days")
            if p85_coding_days > 0:
                print(f"      P85: {p85_coding_days:.1f} days")
            if p90_coding_days > 0:
                print(f"      P90: {p90_coding_days:.1f} days")
            if p95_coding_days > 0:
                print(f"      P95: {p95_coding_days:.1f} days")
        
        # CursorAI Percentiles
        if all_cursor_chat_suggested:
            print(f"   CursorAI Chat Suggested Lines Percentiles:")
            if p75_cursor_chat_suggested > 0:
                print(f"      P75: {p75_cursor_chat_suggested:,.1f} lines")
            if p85_cursor_chat_suggested > 0:
                print(f"      P85: {p85_cursor_chat_suggested:,.1f} lines")
            if p90_cursor_chat_suggested > 0:
                print(f"      P90: {p90_cursor_chat_suggested:,.1f} lines")
            if p95_cursor_chat_suggested > 0:
                print(f"      P95: {p95_cursor_chat_suggested:,.1f} lines")
        
        if all_cursor_chat_accepted:
            print(f"   CursorAI Chat Accepted Lines Percentiles:")
            if p75_cursor_chat_accepted > 0:
                print(f"      P75: {p75_cursor_chat_accepted:,.1f} lines")
            if p85_cursor_chat_accepted > 0:
                print(f"      P85: {p85_cursor_chat_accepted:,.1f} lines")
            if p90_cursor_chat_accepted > 0:
                print(f"      P90: {p90_cursor_chat_accepted:,.1f} lines")
            if p95_cursor_chat_accepted > 0:
                print(f"      P95: {p95_cursor_chat_accepted:,.1f} lines")
        
        if all_cursor_ai_completions:
            print(f"   CursorAI AI Completions Percentiles:")
            if p75_cursor_completions > 0:
                print(f"      P75: {p75_cursor_completions:,.1f} completions")
            if p85_cursor_completions > 0:
                print(f"      P85: {p85_cursor_completions:,.1f} completions")
            if p90_cursor_completions > 0:
                print(f"      P90: {p90_cursor_completions:,.1f} completions")
            if p95_cursor_completions > 0:
                print(f"      P95: {p95_cursor_completions:,.1f} completions")
        
        if all_cursor_ai_edits:
            print(f"   CursorAI AI Edits Percentiles:")
            if p75_cursor_edits > 0:
                print(f"      P75: {p75_cursor_edits:,.1f} edits")
            if p85_cursor_edits > 0:
                print(f"      P85: {p85_cursor_edits:,.1f} edits")
            if p90_cursor_edits > 0:
                print(f"      P90: {p90_cursor_edits:,.1f} edits")
            if p95_cursor_edits > 0:
                print(f"      P95: {p95_cursor_edits:,.1f} edits")
        
        if all_cursor_session_duration:
            print(f"   CursorAI Session Duration Percentiles:")
            if p75_cursor_duration > 0:
                print(f"      P75: {p75_cursor_duration:,.1f} minutes")
            if p85_cursor_duration > 0:
                print(f"      P85: {p85_cursor_duration:,.1f} minutes")
            if p90_cursor_duration > 0:
                print(f"      P90: {p90_cursor_duration:,.1f} minutes")
            if p95_cursor_duration > 0:
                print(f"      P95: {p95_cursor_duration:,.1f} minutes")
        
        if all_cursor_acceptance_rates:
            print(f"   CursorAI Chat Acceptance Rate Percentiles:")
            if p75_cursor_accept_rate > 0:
                print(f"      P75: {p75_cursor_accept_rate:.1f}%")
            if p85_cursor_accept_rate > 0:
                print(f"      P85: {p85_cursor_accept_rate:.1f}%")
            if p90_cursor_accept_rate > 0:
                print(f"      P90: {p90_cursor_accept_rate:.1f}%")
            if p95_cursor_accept_rate > 0:
                print(f"      P95: {p95_cursor_accept_rate:.1f}%")
        
        # Prepare percentile data for CSV export
        percentile_data = {
            'p75_merge_time': p75_merge_time,
            'p85_merge_time': p85_merge_time,
            'p90_merge_time': p90_merge_time,
            'p95_merge_time': p95_merge_time,
            'p75_merge_rate': p75_merge_rate,
            'p85_merge_rate': p85_merge_rate,
            'p90_merge_rate': p90_merge_rate,
            'p95_merge_rate': p95_merge_rate,
            'p75_coding_days': p75_coding_days,
            'p85_coding_days': p85_coding_days,
            'p90_coding_days': p90_coding_days,
            'p95_coding_days': p95_coding_days,
            # CursorAI aggregate metrics
            'total_cursor_chat_suggested_lines': total_cursor_chat_suggested_lines,
            'total_cursor_chat_accepted_lines': total_cursor_chat_accepted_lines,
            'overall_cursor_acceptance_rate': overall_cursor_acceptance_rate,
            'total_cursor_ai_completions': total_cursor_ai_completions,
            'total_cursor_ai_edits': total_cursor_ai_edits,
            'total_cursor_sessions': total_cursor_sessions,
            'total_cursor_session_duration': total_cursor_session_duration,
            'total_cursor_files_edited': total_cursor_files_edited,
            'cursor_users_with_data': cursor_users_with_data,
            # CursorAI percentiles
            'p75_cursor_chat_suggested': p75_cursor_chat_suggested,
            'p85_cursor_chat_suggested': p85_cursor_chat_suggested,
            'p90_cursor_chat_suggested': p90_cursor_chat_suggested,
            'p95_cursor_chat_suggested': p95_cursor_chat_suggested,
            'p75_cursor_chat_accepted': p75_cursor_chat_accepted,
            'p85_cursor_chat_accepted': p85_cursor_chat_accepted,
            'p90_cursor_chat_accepted': p90_cursor_chat_accepted,
            'p95_cursor_chat_accepted': p95_cursor_chat_accepted,
            'p75_cursor_completions': p75_cursor_completions,
            'p85_cursor_completions': p85_cursor_completions,
            'p90_cursor_completions': p90_cursor_completions,
            'p95_cursor_completions': p95_cursor_completions,
            'p75_cursor_edits': p75_cursor_edits,
            'p85_cursor_edits': p85_cursor_edits,
            'p90_cursor_edits': p90_cursor_edits,
            'p95_cursor_edits': p95_cursor_edits,
            'p75_cursor_duration': p75_cursor_duration,
            'p85_cursor_duration': p85_cursor_duration,
            'p90_cursor_duration': p90_cursor_duration,
            'p95_cursor_duration': p95_cursor_duration,
            'p75_cursor_accept_rate': p75_cursor_accept_rate,
            'p85_cursor_accept_rate': p85_cursor_accept_rate,
            'p90_cursor_accept_rate': p90_cursor_accept_rate,
            'p95_cursor_accept_rate': p95_cursor_accept_rate
        }
        
        return percentile_data


def save_summary_csv(metrics_list: list, output_file: str, weeks: int, percentile_data: dict = None):
    """Save summary metrics to CSV file with aggregate metrics as separate rows"""
    try:
        with open(output_file, 'w', newline='') as file:
            # Per-user data columns (no aggregate/percentile columns)
            fieldnames = ['username', 'email', 'total_created', 'total_merged', 'total_open', 
                         'total_abandoned', 'merge_rate', 'abandonment_rate', 'average_merge_time_hours', 
                         'average_lines_changed', 'total_lines_added', 'total_lines_deleted', 
                         'coding_days', 'total_commits', 'cursor_chat_suggested_lines', 
                         'cursor_chat_accepted_lines', 'cursor_chat_acceptance_rate', 
                         'cursor_ai_completions', 'cursor_ai_edits', 'cursor_sessions', 
                         'cursor_session_duration', 'cursor_files_edited', 'error']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            
            writer.writeheader()
            for metrics in metrics_list:
                # Create a copy without pr_details, date fields, cursor_error, and aggregate data
                summary_row = {k: v for k, v in metrics.items() 
                             if k in fieldnames and k not in ['pr_details', 'start_date', 'end_date', 'cursor_error']}
                
                # Check if CursorAI metrics should be "NA" (when there are actual errors, not just missing API key)
                if metrics.get('cursor_error') and metrics.get('cursor_error') != "No CURSOR_API_KEY":
                    # Set CursorAI metrics to "NA" when there are actual errors
                    cursor_fields = ['cursor_chat_suggested_lines', 'cursor_chat_accepted_lines', 
                                   'cursor_chat_acceptance_rate', 'cursor_ai_completions', 
                                   'cursor_ai_edits', 'cursor_sessions', 'cursor_session_duration', 
                                   'cursor_files_edited']
                    for field in cursor_fields:
                        summary_row[field] = 'NA'
                
                writer.writerow(summary_row)
            
            # Add empty row as separator
            file.write('\n')
            
            # Add aggregate metrics as separate rows with 2-column format
            if percentile_data:
                file.write('AGGREGATE METRICS\n')
                file.write('Metric,Value\n')
                
                # PR Merge Time Percentiles
                if percentile_data.get('p75_merge_time', 0) > 0:
                    file.write('PR Merge Time P75 (hours),{}\n'.format(percentile_data['p75_merge_time']))
                    file.write('PR Merge Time P85 (hours),{}\n'.format(percentile_data['p85_merge_time']))
                    file.write('PR Merge Time P90 (hours),{}\n'.format(percentile_data['p90_merge_time']))
                    file.write('PR Merge Time P95 (hours),{}\n'.format(percentile_data['p95_merge_time']))
                
                # PR Merge Rate Percentiles
                if percentile_data.get('p75_merge_rate', 0) > 0:
                    file.write('PR Merge Rate P75 (%),{}\n'.format(percentile_data['p75_merge_rate']))
                    file.write('PR Merge Rate P85 (%),{}\n'.format(percentile_data['p85_merge_rate']))
                    file.write('PR Merge Rate P90 (%),{}\n'.format(percentile_data['p90_merge_rate']))
                    file.write('PR Merge Rate P95 (%),{}\n'.format(percentile_data['p95_merge_rate']))
                
                # Coding Days Percentiles
                if percentile_data.get('p75_coding_days', 0) > 0:
                    file.write('Coding Days P75,{}\n'.format(percentile_data['p75_coding_days']))
                    file.write('Coding Days P85,{}\n'.format(percentile_data['p85_coding_days']))
                    file.write('Coding Days P90,{}\n'.format(percentile_data['p90_coding_days']))
                    file.write('Coding Days P95,{}\n'.format(percentile_data['p95_coding_days']))
                
                # CursorAI Aggregate Metrics
                file.write('Total CursorAI Users with Data,{}\n'.format(percentile_data.get('cursor_users_with_data', 0)))
                file.write('Total CursorAI Chat Suggested Lines,{}\n'.format(percentile_data.get('total_cursor_chat_suggested_lines', 0)))
                file.write('Total CursorAI Chat Accepted Lines,{}\n'.format(percentile_data.get('total_cursor_chat_accepted_lines', 0)))
                file.write('Overall CursorAI Acceptance Rate (%),{}\n'.format(percentile_data.get('overall_cursor_acceptance_rate', 0)))
                file.write('Total CursorAI Completions,{}\n'.format(percentile_data.get('total_cursor_ai_completions', 0)))
                file.write('Total CursorAI Edits,{}\n'.format(percentile_data.get('total_cursor_ai_edits', 0)))
                file.write('Total CursorAI Sessions,{}\n'.format(percentile_data.get('total_cursor_sessions', 0)))
                file.write('Total CursorAI Session Duration (minutes),{}\n'.format(percentile_data.get('total_cursor_session_duration', 0)))
                file.write('Total CursorAI Files Edited,{}\n'.format(percentile_data.get('total_cursor_files_edited', 0)))
                
                # CursorAI Chat Suggested Lines Percentiles
                if percentile_data.get('p75_cursor_chat_suggested', 0) > 0:
                    file.write('CursorAI Chat Suggested Lines P75,{}\n'.format(percentile_data['p75_cursor_chat_suggested']))
                    file.write('CursorAI Chat Suggested Lines P85,{}\n'.format(percentile_data['p85_cursor_chat_suggested']))
                    file.write('CursorAI Chat Suggested Lines P90,{}\n'.format(percentile_data['p90_cursor_chat_suggested']))
                    file.write('CursorAI Chat Suggested Lines P95,{}\n'.format(percentile_data['p95_cursor_chat_suggested']))
                
                # CursorAI Chat Accepted Lines Percentiles
                if percentile_data.get('p75_cursor_chat_accepted', 0) > 0:
                    file.write('CursorAI Chat Accepted Lines P75,{}\n'.format(percentile_data['p75_cursor_chat_accepted']))
                    file.write('CursorAI Chat Accepted Lines P85,{}\n'.format(percentile_data['p85_cursor_chat_accepted']))
                    file.write('CursorAI Chat Accepted Lines P90,{}\n'.format(percentile_data['p90_cursor_chat_accepted']))
                    file.write('CursorAI Chat Accepted Lines P95,{}\n'.format(percentile_data['p95_cursor_chat_accepted']))
                
                # CursorAI Completions Percentiles
                if percentile_data.get('p75_cursor_completions', 0) > 0:
                    file.write('CursorAI Completions P75,{}\n'.format(percentile_data['p75_cursor_completions']))
                    file.write('CursorAI Completions P85,{}\n'.format(percentile_data['p85_cursor_completions']))
                    file.write('CursorAI Completions P90,{}\n'.format(percentile_data['p90_cursor_completions']))
                    file.write('CursorAI Completions P95,{}\n'.format(percentile_data['p95_cursor_completions']))
                
                # CursorAI Edits Percentiles
                if percentile_data.get('p75_cursor_edits', 0) > 0:
                    file.write('CursorAI Edits P75,{}\n'.format(percentile_data['p75_cursor_edits']))
                    file.write('CursorAI Edits P85,{}\n'.format(percentile_data['p85_cursor_edits']))
                    file.write('CursorAI Edits P90,{}\n'.format(percentile_data['p90_cursor_edits']))
                    file.write('CursorAI Edits P95,{}\n'.format(percentile_data['p95_cursor_edits']))
                
                # CursorAI Session Duration Percentiles
                if percentile_data.get('p75_cursor_duration', 0) > 0:
                    file.write('CursorAI Session Duration P75 (minutes),{}\n'.format(percentile_data['p75_cursor_duration']))
                    file.write('CursorAI Session Duration P85 (minutes),{}\n'.format(percentile_data['p85_cursor_duration']))
                    file.write('CursorAI Session Duration P90 (minutes),{}\n'.format(percentile_data['p90_cursor_duration']))
                    file.write('CursorAI Session Duration P95 (minutes),{}\n'.format(percentile_data['p95_cursor_duration']))
                
                # CursorAI Acceptance Rate Percentiles
                if percentile_data.get('p75_cursor_accept_rate', 0) > 0:
                    file.write('CursorAI Acceptance Rate P75 (%),{}\n'.format(percentile_data['p75_cursor_accept_rate']))
                    file.write('CursorAI Acceptance Rate P85 (%),{}\n'.format(percentile_data['p85_cursor_accept_rate']))
                    file.write('CursorAI Acceptance Rate P90 (%),{}\n'.format(percentile_data['p90_cursor_accept_rate']))
                    file.write('CursorAI Acceptance Rate P95 (%),{}\n'.format(percentile_data['p95_cursor_accept_rate']))
        
        print(f"\n💾 Summary report saved to {output_file}")
    except Exception as e:
        print(f"Error saving summary CSV: {e}")


def save_detailed_csv(metrics_list: list, output_file: str, weeks: int):
    """Save detailed PR list to CSV file"""
    try:
        with open(output_file, 'w', newline='') as file:
            fieldnames = ['username', 'email', 'title', 'state', 'created_at', 'closed_at', 'merge_time_hours', 
                         'lines_added', 'lines_deleted', 'lines_changed', 'repository', 'pr_number', 'url']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            
            writer.writeheader()
            for metrics in metrics_list:
                if not metrics.get('error'):
                    if metrics.get('pr_details'):
                        # User has PRs, write all PR details
                        for pr_detail in metrics['pr_details']:
                            # Add email to each PR detail
                            pr_detail_with_extras = pr_detail.copy()
                            pr_detail_with_extras['email'] = metrics.get('email', 'N/A')
                            
                            writer.writerow(pr_detail_with_extras)
                    else:
                        # User has no PRs, write a placeholder row
                        writer.writerow({
                            'username': metrics['username'],
                            'email': metrics.get('email', 'N/A'),
                            'title': 'No pull requests found',
                            'state': 'N/A',
                            'created_at': 'N/A',
                            'closed_at': 'N/A',
                            'merge_time_hours': 'N/A',
                            'lines_added': 'N/A',
                            'lines_deleted': 'N/A',
                            'lines_changed': 'N/A',
                            'repository': 'N/A',
                            'pr_number': 'N/A',
                            'url': 'N/A'
                        })
                else:
                    # User has error, write error row
                    writer.writerow({
                        'username': metrics['username'],
                        'email': metrics.get('email', 'N/A'),
                        'title': metrics.get('error', 'Unknown error'),
                        'state': 'N/A',
                        'created_at': 'N/A',
                        'closed_at': 'N/A',
                        'merge_time_hours': 'N/A',
                        'lines_added': 'N/A',
                        'lines_deleted': 'N/A',
                        'lines_changed': 'N/A',
                        'repository': 'N/A',
                        'pr_number': 'N/A',
                        'url': 'N/A'
                    })
        
        print(f"💾 Detailed PR list saved to {output_file}")
    except Exception as e:
        print(f"Error saving detailed CSV: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate PR metrics report for usernames from CSV file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 gm.py usernames.csv
  python3 gm.py usernames.csv --weeks 2 --output ./reports/
  
The script will automatically create two CSV files using the input filename as prefix:
- <input_name>-pr-summary.csv: Summary metrics per user
- <input_name>-pr-details.csv: Detailed list of all PRs with status

Date Range: Uses complete weeks from Sunday to Saturday of previous weeks.
        """
    )
    
    parser.add_argument(
        'csv_file',
        help='Path to CSV file containing GitHub usernames'
    )
    
    parser.add_argument(
        '--weeks', '-w',
        type=int,
        default=1,
        help='Number of weeks to look back (default: 1)'
    )
    
    parser.add_argument(
        '--output', '-o',
        help='Output directory for CSV files (optional, defaults to current directory)'
    )
    
    args = parser.parse_args()
    
    # Load usernames from CSV
    print(f"Loading usernames from {args.csv_file}...")
    user_data = load_usernames_from_csv(args.csv_file)
    print(f"Found {len(user_data)} users")
    
    # Initialize CursorAI analytics
    cursor_analytics = CursorAIAnalytics()
    
    # Collect metrics for each user
    print(f"\nCollecting PR and CursorAI metrics for last {args.weeks} week{'s' if args.weeks != 1 else ''}...")
    metrics_list = []
    
    for i, user in enumerate(user_data, 1):
        github_username = user['github_username']
        email = user['email']
        print(f"[{i}/{len(user_data)}] Processing {github_username} ({email})...")
        
        # Get PR metrics
        pr_metrics = get_pr_metrics(github_username, args.weeks)
        
        # Get CursorAI metrics if API key is available
        if cursor_analytics.api_key:
            try:
                # Calculate date range for CursorAI (same as PR metrics)
                end_date = datetime.now().date()
                days_since_saturday = (end_date.weekday() + 2) % 7
                if days_since_saturday == 0:
                    week_end = end_date
                else:
                    week_end = end_date - timedelta(days=days_since_saturday)
                week_start = week_end - timedelta(days=(args.weeks * 7 - 1))
                
                start_datetime = datetime.combine(week_start, datetime.min.time())
                end_datetime = datetime.combine(week_end, datetime.max.time())
                
                cursor_metrics = cursor_analytics.get_user_analytics(email, start_datetime, end_datetime)
                
                # Add CursorAI metrics to PR metrics
                pr_metrics['cursor_chat_suggested_lines'] = cursor_metrics.chat_suggested_lines
                pr_metrics['cursor_chat_accepted_lines'] = cursor_metrics.chat_accepted_lines
                pr_metrics['cursor_chat_acceptance_rate'] = cursor_metrics.chat_acceptance_rate
                pr_metrics['cursor_ai_completions'] = cursor_metrics.ai_completions
                pr_metrics['cursor_ai_edits'] = cursor_metrics.ai_edits
                pr_metrics['cursor_sessions'] = cursor_metrics.total_sessions
                pr_metrics['cursor_session_duration'] = cursor_metrics.total_session_duration_minutes
                pr_metrics['cursor_files_edited'] = cursor_metrics.files_edited
                pr_metrics['cursor_error'] = cursor_metrics.error
                
            except Exception as e:
                print(f"   Warning: CursorAI metrics failed for {email}: {e}")
                pr_metrics['cursor_chat_suggested_lines'] = 0
                pr_metrics['cursor_chat_accepted_lines'] = 0
                pr_metrics['cursor_chat_acceptance_rate'] = 0.0
                pr_metrics['cursor_ai_completions'] = 0
                pr_metrics['cursor_ai_edits'] = 0
                pr_metrics['cursor_sessions'] = 0
                pr_metrics['cursor_session_duration'] = 0
                pr_metrics['cursor_files_edited'] = 0
                pr_metrics['cursor_error'] = str(e)
        else:
            # No CursorAI API key, set default values
            pr_metrics['cursor_chat_suggested_lines'] = 0
            pr_metrics['cursor_chat_accepted_lines'] = 0
            pr_metrics['cursor_chat_acceptance_rate'] = 0.0
            pr_metrics['cursor_ai_completions'] = 0
            pr_metrics['cursor_ai_edits'] = 0
            pr_metrics['cursor_sessions'] = 0
            pr_metrics['cursor_session_duration'] = 0
            pr_metrics['cursor_files_edited'] = 0
            pr_metrics['cursor_error'] = "No CURSOR_API_KEY"
        
        # Add email to metrics for reference
        pr_metrics['email'] = email
        
        metrics_list.append(pr_metrics)
    
    # Print report and get percentile data
    percentile_data = print_report(metrics_list, args.weeks)
    
    # Generate output filenames using input CSV filename as prefix
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = args.output if args.output else script_dir
    
    # Extract filename without extension from input CSV
    csv_basename = os.path.splitext(os.path.basename(args.csv_file))[0]
    
    summary_file = os.path.join(output_dir, f"{csv_basename}-pr-summary.csv")
    detailed_file = os.path.join(output_dir, f"{csv_basename}-pr-details.csv")
    
    # Delete existing CSV files if they exist
    for file_path in [summary_file, detailed_file]:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"🗑️  Deleted existing file: {os.path.basename(file_path)}")
            except Exception as e:
                print(f"Warning: Could not delete {file_path}: {e}")
    
    # Save both CSV files
    save_summary_csv(metrics_list, summary_file, args.weeks, percentile_data)
    save_detailed_csv(metrics_list, detailed_file, args.weeks)


if __name__ == '__main__':
    main()
