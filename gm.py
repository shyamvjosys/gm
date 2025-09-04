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
from datetime import datetime, timedelta


def get_pr_metrics(username: str, days: int = 7) -> dict:
    """Get comprehensive PR metrics for username in josys-src org"""
    
    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
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
                'pr_number': pr.get('number', ''),
                'title': pr.get('title', ''),
                'state': pr.get('state', ''),
                'created_at': pr.get('createdAt', ''),
                'closed_at': pr.get('closedAt', ''),
                'merge_time_hours': round(merge_time_hours, 2) if merge_time_hours is not None else None,
                'lines_added': additions,
                'lines_deleted': deletions,
                'lines_changed': lines_changed,
                'repository': pr.get('repository', {}).get('name', '') if pr.get('repository') else '',
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
            metrics['merge_rate'] = (metrics['total_merged'] / metrics['total_created']) * 100
            metrics['abandonment_rate'] = (metrics['total_abandoned'] / metrics['total_created']) * 100
        
        # Calculate average merge time
        if merge_times_hours:
            metrics['average_merge_time_hours'] = round(sum(merge_times_hours) / len(merge_times_hours), 2)
        
        # Calculate average lines changed
        if all_lines_changed:
            metrics['average_lines_changed'] = round(sum(all_lines_changed) / len(all_lines_changed), 2)
        
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


def load_usernames_from_csv(csv_file: str) -> list:
    """Load usernames from CSV file"""
    usernames = []
    
    try:
        with open(csv_file, 'r', newline='') as file:
            reader = csv.DictReader(file)
            
            # Check if there's a 'username' column
            if 'username' in [col.lower() for col in reader.fieldnames or []]:
                # Find the username column (case-insensitive)
                username_col = None
                for col in reader.fieldnames:
                    if col.lower() == 'username':
                        username_col = col
                        break
                
                for row in reader:
                    if username_col and row[username_col]:
                        usernames.append(row[username_col].strip())
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
                                usernames.append(cell)
    
    except FileNotFoundError:
        print(f"Error: File '{csv_file}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        sys.exit(1)
    
    # Remove duplicates and empty strings
    usernames = list(set([u for u in usernames if u]))
    
    if not usernames:
        print("Error: No usernames found in CSV file")
        sys.exit(1)
    
    return usernames


def print_report(metrics_list: list, days: int):
    """Print formatted report"""
    print("=" * 80)
    print(f"PR METRICS REPORT - josys-src Organization (Last {days} days)")
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
        
        # Collect individual PR merge times and line changes for overall calculation
        for pr_detail in metrics.get('pr_details', []):
            if pr_detail.get('merge_time_hours') is not None:
                all_merge_times.append(pr_detail['merge_time_hours'])
            if pr_detail.get('lines_changed', 0) > 0:
                all_lines_changed_global.append(pr_detail['lines_changed'])
        
        print(f"\n👤 {metrics['username']}")
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
    
    # Overall statistics
    if valid_users > 0:
        overall_merge_rate = (total_merged / total_created * 100) if total_created > 0 else 0
        overall_abandonment_rate = (total_abandoned / total_created * 100) if total_created > 0 else 0
        
        # Calculate overall average merge time and lines changed
        overall_avg_merge_time = 0.0
        if all_merge_times:
            overall_avg_merge_time = sum(all_merge_times) / len(all_merge_times)
        
        overall_avg_lines_changed = 0.0
        if all_lines_changed_global:
            overall_avg_lines_changed = sum(all_lines_changed_global) / len(all_lines_changed_global)
        
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


def save_summary_csv(metrics_list: list, output_file: str, days: int):
    """Save summary metrics to CSV file"""
    try:
        with open(output_file, 'w', newline='') as file:
            fieldnames = ['username', 'total_created', 'total_merged', 'total_open', 
                         'total_abandoned', 'merge_rate', 'abandonment_rate', 'average_merge_time_hours', 
                         'average_lines_changed', 'total_lines_added', 'total_lines_deleted', 'error']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            
            writer.writeheader()
            for metrics in metrics_list:
                # Create a copy without pr_details for summary
                summary_row = {k: v for k, v in metrics.items() if k != 'pr_details'}
                writer.writerow(summary_row)
        
        print(f"\n💾 Summary report saved to {output_file}")
    except Exception as e:
        print(f"Error saving summary CSV: {e}")


def save_detailed_csv(metrics_list: list, output_file: str, days: int):
    """Save detailed PR list to CSV file"""
    try:
        with open(output_file, 'w', newline='') as file:
            fieldnames = ['username', 'pr_number', 'title', 'state', 'created_at', 'closed_at', 'merge_time_hours', 
                         'lines_added', 'lines_deleted', 'lines_changed', 'repository', 'url']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            
            writer.writeheader()
            for metrics in metrics_list:
                if not metrics.get('error'):
                    if metrics.get('pr_details'):
                        # User has PRs, write all PR details
                        for pr_detail in metrics['pr_details']:
                            writer.writerow(pr_detail)
                    else:
                        # User has no PRs, write a placeholder row
                        writer.writerow({
                            'username': metrics['username'],
                            'pr_number': 'No PRs',
                            'title': 'No pull requests found',
                            'state': 'N/A',
                            'created_at': 'N/A',
                            'closed_at': 'N/A',
                            'merge_time_hours': 'N/A',
                            'lines_added': 'N/A',
                            'lines_deleted': 'N/A',
                            'lines_changed': 'N/A',
                            'repository': 'N/A',
                            'url': 'N/A'
                        })
                else:
                    # User has error, write error row
                    writer.writerow({
                        'username': metrics['username'],
                        'pr_number': 'Error',
                        'title': metrics.get('error', 'Unknown error'),
                        'state': 'N/A',
                        'created_at': 'N/A',
                        'closed_at': 'N/A',
                        'merge_time_hours': 'N/A',
                        'lines_added': 'N/A',
                        'lines_deleted': 'N/A',
                        'lines_changed': 'N/A',
                        'repository': 'N/A',
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
  python3 gm.py usernames.csv --days 14 --output ./reports/
  
The script will automatically create two CSV files in the script's directory:
- pr_summary_TIMESTAMP.csv: Summary metrics per user
- pr_details_TIMESTAMP.csv: Detailed list of all PRs with status
        """
    )
    
    parser.add_argument(
        'csv_file',
        help='Path to CSV file containing GitHub usernames'
    )
    
    parser.add_argument(
        '--days', '-d',
        type=int,
        default=7,
        help='Number of days to look back (default: 7)'
    )
    
    parser.add_argument(
        '--output', '-o',
        help='Output directory for CSV files (optional, defaults to current directory)'
    )
    
    args = parser.parse_args()
    
    # Load usernames from CSV
    print(f"Loading usernames from {args.csv_file}...")
    usernames = load_usernames_from_csv(args.csv_file)
    print(f"Found {len(usernames)} usernames")
    
    # Collect metrics for each username
    print(f"\nCollecting PR metrics for last {args.days} days...")
    metrics_list = []
    
    for i, username in enumerate(usernames, 1):
        print(f"[{i}/{len(usernames)}] Processing {username}...")
        metrics = get_pr_metrics(username, args.days)
        metrics_list.append(metrics)
    
    # Print report
    print_report(metrics_list, args.days)
    
    # Generate output filenames in the script's directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = args.output if args.output else script_dir
    summary_file = os.path.join(output_dir, "pr_summary.csv")
    detailed_file = os.path.join(output_dir, "pr_details.csv")
    
    # Delete existing CSV files if they exist
    for file_path in [summary_file, detailed_file]:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"🗑️  Deleted existing file: {os.path.basename(file_path)}")
            except Exception as e:
                print(f"Warning: Could not delete {file_path}: {e}")
    
    # Save both CSV files
    save_summary_csv(metrics_list, summary_file, args.days)
    save_detailed_csv(metrics_list, detailed_file, args.days)


if __name__ == '__main__':
    main()
