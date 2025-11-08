#!/usr/bin/env python3
"""
JIRA Metrics Summary Script
Analyzes release versions and ticket metrics for specified JIRA boards
Uses environment variables for configuration
"""

import os
import sys
import argparse
from datetime import datetime, timedelta
from atlassian import Jira
from collections import defaultdict

def get_jira_config():
    """Get JIRA configuration from environment variables"""
    config = {
        'url': os.getenv('JIRA_URL'),
        'email': os.getenv('JIRA_EMAIL'),
        'api_token': os.getenv('JIRA_API_TOKEN')
    }
    
    # Check for missing variables
    missing_vars = []
    for key, value in config.items():
        if not value:
            env_var_name = f"JIRA_{key.upper()}"
            missing_vars.append(env_var_name)
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   {var}")
        
        print("\n🔧 Please set the following environment variables:")
        print('   export JIRA_URL="https://josysglobal.atlassian.net"')
        print('   export JIRA_EMAIL="your-email@josys.com"')
        print('   export JIRA_API_TOKEN="your-api-token"')
        print("\n💡 Get API token from: https://id.atlassian.com/manage-profile/security/api-tokens")
        return None
    
    return config

def calculate_date_range(weeks):
    """Calculate date range for the specified number of weeks (Sunday to Saturday)"""
    today = datetime.now().date()
    
    # Find the most recent Saturday (end of previous complete week)
    if today.weekday() == 6:  # If today is Sunday
        end_date = today - timedelta(days=1)
    else:
        days_since_last_saturday = today.weekday() + 2
        end_date = today - timedelta(days=days_since_last_saturday)
    
    # Calculate start date: go back 'weeks' complete weeks to the Sunday
    start_date = end_date - timedelta(days=(weeks * 7 - 1))
    
    return start_date, end_date

def get_release_versions(jira, project_key, start_date, end_date):
    """Get release versions for a project created within the date range"""
    try:
        # Get all versions for the project
        versions = jira.get_project_versions(project_key)
        
        # Filter versions created within the date range
        filtered_versions = []
        for version in versions:
            version_id = version.get('id')
            
            # Try to get detailed version information to check creation date
            try:
                # Get version details which may include creation date
                import requests
                import base64
                import os
                
                # Get credentials from environment
                email = os.getenv('JIRA_EMAIL')
                api_token = os.getenv('JIRA_API_TOKEN')
                base_url = os.getenv('JIRA_URL')
                
                if all([email, api_token, base_url]):
                    # Create auth header
                    credentials = f"{email}:{api_token}"
                    encoded_credentials = base64.b64encode(credentials.encode()).decode()
                    headers = {
                        'Authorization': f'Basic {encoded_credentials}',
                        'Content-Type': 'application/json'
                    }
                    
                    # Get version details
                    version_url = f"{base_url}/rest/api/3/version/{version_id}"
                    response = requests.get(version_url, headers=headers)
                    
                    if response.status_code == 200:
                        version_details = response.json()
                        
                        # Check if version was created within our time window
                        # Try different date fields that might indicate creation
                        creation_date = None
                        
                        # Check for startDate (project start date)
                        start_date_str = version_details.get('startDate')
                        if start_date_str:
                            try:
                                creation_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                            except ValueError:
                                pass
                        
                        # If no startDate, check releaseDate as fallback
                        if not creation_date:
                            release_date_str = version_details.get('releaseDate')
                            if release_date_str:
                                try:
                                    creation_date = datetime.strptime(release_date_str, '%Y-%m-%d').date()
                                except ValueError:
                                    pass
                        
                        # Filter based on creation/start date within time window
                        if creation_date and start_date <= creation_date <= end_date:
                            filtered_versions.append(version)
                        elif not creation_date:
                            # If we can't determine creation date, include it
                            # This ensures we don't miss versions due to API limitations
                            filtered_versions.append(version)
                    else:
                        # If we can't get version details, include the version
                        filtered_versions.append(version)
                else:
                    # If credentials not available, include all versions
                    filtered_versions.append(version)
                    
            except Exception:
                # If any error occurs getting version details, include the version
                filtered_versions.append(version)
        
        return filtered_versions
    except Exception as e:
        print(f"⚠️  Error getting versions for {project_key}: {e}")
        return []

def get_version_tickets(jira, project_key, version_id):
    """Get tickets associated with a specific version"""
    try:
        # JQL to find tickets with specific fix version
        jql = f'project = {project_key} AND fixVersion = {version_id}'
        
        # Use requests directly to call the v3 API
        import requests
        import urllib.parse
        import base64
        
        try:
            # Get credentials from environment
            import os
            email = os.getenv('JIRA_EMAIL')
            api_token = os.getenv('JIRA_API_TOKEN')
            base_url = os.getenv('JIRA_URL')
            
            if not all([email, api_token, base_url]):
                print(f"⚠️  Missing credentials for API call")
                return 0, 0
            
            # Create basic auth header
            credentials = f"{email}:{api_token}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            headers = {
                'Authorization': f'Basic {encoded_credentials}',
                'Content-Type': 'application/json'
            }
            
            # Prepare the API call using the correct endpoint
            url = f"{base_url}/rest/api/3/search/jql"
            
            # Prepare the request payload
            payload = {
                'jql': jql,
                'maxResults': 1000,
                'fields': ['status', 'summary']
            }
            
            # Make direct HTTP request using POST
            import json
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            
            if response.status_code == 200:
                data = response.json()
                total_tickets = data.get('total', 0)
                issues = data.get('issues', [])
                
                # Count DONE tickets
                done_statuses = ['DONE', 'DEPLOYMENT READY', 'DEPLOYED TO PROD']
                done_tickets = 0
                
                for issue in issues:
                    status = issue.get('fields', {}).get('status', {}).get('name', '')
                    if status.upper() in [s.upper() for s in done_statuses]:
                        done_tickets += 1
                
                return total_tickets, done_tickets
            else:
                print(f"   ⚠️  API call failed with status {response.status_code}: {response.text[:200]}")
                return 0, 0
                
        except ImportError:
            # requests not available, fall back to the library method
            print(f"⚠️  Could not use direct API call for version {version_id}")
            return 0, 0
        except Exception as api_error:
            print(f"   ⚠️  API error for version {version_id}: {api_error}")
            return 0, 0
                
    except Exception as e:
        print(f"⚠️  Error getting tickets for version {version_id}: {e}")
        return 0, 0

def analyze_board_metrics(jira, project_key, start_date, end_date, extended=False):
    """Analyze metrics for a specific board/project"""
    print(f"\n📋 Analyzing {project_key} project...")
    
    # Get release versions
    versions = get_release_versions(jira, project_key, start_date, end_date)
    
    if not versions:
        print(f"   ❌ No release versions found for {project_key}")
        return None
    
    # Initialize counters
    total_versions = len(versions)
    released_count = 0
    unreleased_count = 0
    version_details = []
    
    # Analyze each version
    for version in versions:
        name = version.get('name', 'Unnamed Version')
        version_id = version.get('id')
        release_date = version.get('releaseDate', 'No release date')
        released = version.get('released', False)
        
        if released:
            released_count += 1
        else:
            unreleased_count += 1
        
        # Get ticket metrics only if extended mode is enabled
        total_tickets = 0
        done_tickets = 0
        if extended:
            total_tickets, done_tickets = get_version_tickets(jira, project_key, version_id)
        
        version_details.append({
            'name': name,
            'version_id': version_id,
            'release_date': release_date,
            'released': released,
            'total_tickets': total_tickets,
            'done_tickets': done_tickets
        })
    
    return {
        'project_key': project_key,
        'total_versions': total_versions,
        'released_count': released_count,
        'unreleased_count': unreleased_count,
        'version_details': version_details
    }

def print_summary_report(project_metrics, start_date, end_date, weeks, extended=False):
    """Print the comprehensive metrics report with table format"""
    print("=" * 120)
    mode_text = " - EXTENDED MODE" if extended else ""
    print(f"JIRA METRICS SUMMARY REPORT{mode_text}")
    print(f"Date Range: {start_date.strftime('%Y-%m-%d')} (Sunday) to {end_date.strftime('%Y-%m-%d')} (Saturday)")
    print(f"Analysis Period: Last {weeks} week{'s' if weeks != 1 else ''}")
    print("=" * 120)
    
    # Project-level tables for each project
    for metrics in project_metrics:
        if metrics and metrics['version_details']:
            project = metrics['project_key']
            print(f"\n📋 {project} PROJECT - RELEASE VERSIONS")
            
            if extended:
                # Extended mode: include ticket information
                print("-" * 100)
                print("Release Name                    | Status    | Release Date | Total Tickets | Done Tickets | Open Tickets")
                print("-" * 100)
                
                for version in metrics['version_details']:
                    name = version['name'][:30]  # Truncate long names
                    status = "Released" if version['released'] else "Unreleased"
                    release_date = version['release_date'] if version['release_date'] != 'No release date' else 'Not Set'
                    total_tickets = version['total_tickets']
                    done_tickets = version['done_tickets']
                    open_tickets = max(0, total_tickets - done_tickets)
                    
                    print(f"{name:30} | {status:9} | {release_date:12} | {total_tickets:13} | {done_tickets:12} | {open_tickets:12}")
            else:
                # Basic mode: only release versions, status, and release date
                print("-" * 80)
                print("Release Name                    | Status      | Release Date")
                print("-" * 80)
                
                for version in metrics['version_details']:
                    name = version['name'][:30]  # Truncate long names
                    status = "Released" if version['released'] else "Unreleased"
                    release_date = version['release_date'] if version['release_date'] != 'No release date' else 'Not Set'
                    print(f"{name:30} | {status:11} | {release_date:12}")
    
    # Overall Statistics
    total_versions_all = sum(m['total_versions'] for m in project_metrics if m)
    total_released_all = sum(m['released_count'] for m in project_metrics if m)
    total_unreleased_all = sum(m['unreleased_count'] for m in project_metrics if m)
    
    print(f"\n🎯 OVERALL SUMMARY")
    print("-" * 60)
    print("Metric                    | Value")
    print("-" * 60)
    print(f"Total Projects Analyzed   | {len([m for m in project_metrics if m])}")
    print(f"Total Release Versions    | {total_versions_all}")
    print(f"Total Releases Completed  | {total_released_all}")
    print(f"Total Unreleased          | {total_unreleased_all}")
    if total_versions_all > 0:
        overall_release_rate = (total_released_all / total_versions_all) * 100
        print(f"Overall Release Rate      | {overall_release_rate:.1f}%")
    
    # Extended statistics only in extended mode
    if extended:
        total_tickets_all = sum(
            sum(v['total_tickets'] for v in m['version_details']) 
            for m in project_metrics if m and m['version_details']
        )
        total_done_all = sum(
            sum(v['done_tickets'] for v in m['version_details']) 
            for m in project_metrics if m and m['version_details']
        )
        total_open_all = max(0, total_tickets_all - total_done_all)
        
        print(f"Total JIRA Tickets        | {total_tickets_all}")
        print(f"Total DONE Tickets        | {total_done_all}")
        print(f"Total Open Tickets        | {total_open_all}")
        if total_tickets_all > 0:
            overall_completion_rate = (total_done_all / total_tickets_all) * 100
            print(f"Overall Completion Rate   | {overall_completion_rate:.1f}%")

def main():
    parser = argparse.ArgumentParser(
        description="Generate JIRA metrics summary for release versions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 jira_metrics_summary.py
  python3 jira_metrics_summary.py --weeks 2
  python3 jira_metrics_summary.py --extended
  python3 jira_metrics_summary.py -w 4 -e

The script analyzes active JIRA projects for release metrics.
Use --extended for detailed ticket analysis.
        """
    )
    
    parser.add_argument(
        '--weeks', '-w',
        type=int,
        default=1,
        help='Number of weeks to analyze (default: 1)'
    )
    
    parser.add_argument(
        '--extended', '-e',
        action='store_true',
        help='Include detailed ticket analysis for each release (default: false)'
    )
    
    args = parser.parse_args()
    
    # Project exclusion list - projects that should not be tracked
    EXCLUDED_PROJECTS = ['QRS', 'UEN', 'DEP', 'CAO_APP', 'JAMF', 'GDD', 'CAOAP', 'SE', 'GTM', 'JDP', 'TDB', 'MTM', 'SEN', 'MFA']
    
    # Get all active JIRA projects dynamically
    def get_active_projects(jira):
        """Get all active (non-archived, non-closed) JIRA projects, excluding specified projects"""
        try:
            all_projects = jira.projects()
            active_projects = []
            
            for project in all_projects:
                # Check if project is not archived
                project_key = project.get('key', '')
                project_name = project.get('name', '')
                
                # Skip excluded projects
                if project_key in EXCLUDED_PROJECTS:
                    print(f"   ⏭️  {project_key}: {project_name} (excluded)")
                    continue
                
                # Get detailed project info to check status
                try:
                    project_details = jira.project(project_key)
                    # Check if project is archived or has versions
                    if not project_details.get('archived', False):
                        # Try to get versions to see if it's an active project
                        versions = jira.get_project_versions(project_key)
                        if len(versions) > 0:  # Only include projects with versions
                            active_projects.append(project_key)
                            print(f"   ✅ {project_key}: {project_name} ({len(versions)} versions)")
                except Exception:
                    # Skip projects we can't access
                    continue
                    
            return active_projects
        except Exception as e:
            print(f"⚠️  Error getting projects: {e}")
            # Fallback to original list (excluding the excluded projects)
            fallback_projects = ['LO', 'RPB', 'WOR', 'JEP', 'JAP', 'SC']
            return [p for p in fallback_projects if p not in EXCLUDED_PROJECTS]
    
    print(f"🎯 JIRA Metrics Summary")
    print(f"📅 Analysis Period: Last {args.weeks} week{'s' if args.weeks != 1 else ''}")
    print("=" * 60)
    
    # Get configuration
    config = get_jira_config()
    if not config:
        return
    
    # Calculate date range
    start_date, end_date = calculate_date_range(args.weeks)
    
    print(f"🔗 Connecting to: {config['url']}")
    print(f"👤 Using account: {config['email']}")
    
    try:
        # Connect to JIRA
        print("\n⏳ Establishing connection...")
        jira = Jira(
            url=config['url'], 
            username=config['email'], 
            password=config['api_token']
        )
        
        # Test connection
        try:
            current_user = jira.myself()
            print(f"✅ Connected as: {current_user.get('displayName', 'User')}")
        except Exception:
            print("✅ Connected to JIRA")
        
        # Get active projects
        print(f"\n🔍 Discovering active JIRA projects...")
        TARGET_PROJECTS = get_active_projects(jira)
        print(f"\n📋 Found {len(TARGET_PROJECTS)} active projects: {', '.join(TARGET_PROJECTS)}")
        
        # Analyze each project
        project_metrics = []
        
        for project in TARGET_PROJECTS:
            try:
                metrics = analyze_board_metrics(jira, project, start_date, end_date, args.extended)
                project_metrics.append(metrics)
            except Exception as e:
                print(f"❌ Error analyzing {project}: {e}")
                project_metrics.append(None)
        
        # Print comprehensive report
        print_summary_report(project_metrics, start_date, end_date, args.weeks, args.extended)
        
    except Exception as e:
        error_msg = str(e).lower()
        print(f"\n❌ Error: {str(e)}")
        
        print("\n🔧 Troubleshooting:")
        if "401" in error_msg or "unauthorized" in error_msg:
            print("• Check your JIRA_EMAIL and JIRA_API_TOKEN")
            print("• Verify your API token is correct and not expired")
        elif "403" in error_msg or "forbidden" in error_msg:
            print("• You may not have permission to access the projects")
            print("• Contact your JIRA administrator for project access")
        elif "404" in error_msg or "not found" in error_msg:
            print("• One or more projects may not exist or you don't have access")
            print("• Check if the project keys 'WOR', 'LO', 'RPB' are correct")
        else:
            print("• Verify your JIRA_URL is correct")
            print("• Check your internet connection")
            print("• Ensure you have proper permissions for the projects")

if __name__ == "__main__":
    main()
