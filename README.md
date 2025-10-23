# GitHub PR Metrics Reporter

GitHub PR Metrics Reporter tool that generates comprehensive pull request (PR) metrics reports for GitHub users in the josys-src organization. The tool reads usernames from CSV files and produces detailed analytics about PR creation, merge rates, abandonment rates, merge times, and code change metrics.

## Features

- **Comprehensive PR Analysis**: Tracks created, merged, open, and abandoned PRs
- **Time-based Analysis**: Configurable week range (default: last 1 complete week)
- **Detailed Metrics**: 
  - Total PRs created, merged, open, and abandoned
  - Merge rate and abandonment rate percentages (rounded to 2 decimal places)
  - Average merge time in hours (rounded to 2 decimal places)
  - **Code Change Analytics**: Average lines changed per PR, total lines added/deleted
  - **Coding Days Analytics**: Count of unique days with at least one commit
  - **P90/P95 Percentile Analytics**: 90th and 95th percentile values for PR merge time and coding days
  - **CursorAI Metrics**: Track AI-assisted coding activity (chat suggestions, completions, edits)
  - Total commit count per user
  - Individual PR details with timestamps and line counts
- **Multiple Output Formats**: Console report + CSV exports with enhanced line count data
- **Batch Processing**: Process multiple users from CSV input
- **Error Handling**: Graceful handling of API errors and missing data
- **Performance Optimized**: Efficient API calls with individual PR line count fetching
- **Precise Float Formatting**: All aggregate float values rounded to 2 decimal places for consistency

## Prerequisites

1. **GitHub CLI**: Install and authenticate with GitHub CLI
   ```bash
   # Install GitHub CLI (macOS)
   brew install gh
   
   # Authenticate
   gh auth login
   ```

2. **Python 3.6+**: Ensure Python 3.6 or higher is installed

3. **CursorAI API Key** (Optional): For tracking AI-assisted coding metrics
   ```bash
   # Set environment variable (macOS/Linux)
   export CURSOR_API_KEY="your-api-key-here"
   export CURSOR_TEAM_ID="your-team-id-here"
   
   # Add to ~/.zshrc or ~/.bashrc for persistence
   echo 'export CURSOR_API_KEY="your-api-key-here"' >> ~/.zshrc
   echo 'export CURSOR_TEAM_ID="your-team-id-here"' >> ~/.zshrc
   ```
   
   **Note**: The tool will work without CursorAI API key - it will simply skip CursorAI metrics collection. To obtain your API key, contact your CursorAI administrator or check your CursorAI account settings.

## Installation

1. Clone or download this repository
2. No additional Python packages required (uses only standard library)

## Usage

### Basic Usage
```bash
python3 gm.py <csv_file>
```

### Advanced Usage
```bash
# Analyze last 2 weeks instead of default 1
python3 gm.py usernames.csv --weeks 2

# Specify custom output directory
python3 gm.py usernames.csv --output ./reports/

# Combine options
python3 gm.py usernames.csv --weeks 4 --output ./monthly_reports/
```

### CSV Input Format

The tool accepts CSV files with usernames in one of these formats:

####With header column named "username"
```csv
username
SuperStar1212
Trish0405
Nolan3007
Samantha2804
```


## Output Files

The tool generates three types of output:

### 1. Console Report
Displays formatted metrics for each user and overall statistics:
```
PR METRICS REPORT - josys-src Organization (Last 1 week)
Date Range: 2025-08-31 (Sunday) to 2025-09-06 (Saturday)
===============================================================================

👤 SuperStar1212
   📝 PRs Created: 30
   ✅ PRs Merged: 29
   🔄 PRs Open: 1
   ❌ PRs Abandoned: 0
   📊 Merge Rate: 96.7%
   📉 Abandonment Rate: 0.0%
   ⏱️  Average Merge Time: 0.1 hours
   📏 Average Lines Changed: 106.5
   ➕ Total Lines Added: 2903
   ➖ Total Lines Deleted: 717
   📅 Coding Days: 5
   💾 Total Commits: 42

📈 OVERALL STATISTICS
   Users Processed: 6
   Total PRs Created: 54
   Total PRs Merged: 45
   Overall Merge Rate: 83.3%
   Overall Abandonment Rate: 5.6%
   Overall Average Merge Time: 3.7 hours
   P90 Merge Time: 19.5 hours
   P95 Merge Time: 21.3 hours
   Overall Average Lines Changed: 615.8
   Total Lines Added (All Users): 27897
   Total Lines Deleted (All Users): 7203
   Total Coding Days (All Users): 35
   Total Commits (All Users): 133
   Average Coding Days per User: 5.8
   P90 Coding Days: 6.4 days
   P95 Coding Days: 6.7 days
   ...
```

### 2. Summary CSV (`pr_summary.csv`)
Contains aggregated metrics per user:
- `username`: GitHub username
- `total_created`: Total PRs created
- `total_merged`: Total PRs merged
- `total_open`: Total PRs still open
- `total_abandoned`: Total PRs closed without merge
- `merge_rate`: Percentage of PRs that were merged (rounded to 2 decimal places)
- `abandonment_rate`: Percentage of PRs that were abandoned (rounded to 2 decimal places)
- `average_merge_time_hours`: Average time from creation to merge (rounded to 2 decimal places)
- `average_lines_changed`: Average lines changed per PR (rounded to 2 decimal places)
- `total_lines_added`: Total lines added across all PRs
- `total_lines_deleted`: Total lines deleted across all PRs
- `coding_days`: Total count of unique calendar days with commits (calculated per week Monday-Sunday)
- `total_commits`: Total number of commits made by the user
- `error`: Any error encountered for this user

### 3. Detailed CSV (`pr_details.csv`)
Contains individual PR records with:
- `username`: GitHub username
- `title`: PR title
- `state`: PR state (open, merged, closed)
- `created_at`: Creation timestamp
- `closed_at`: Close/merge timestamp
- `merge_time_hours`: Time to merge in hours (rounded to 2 decimal places)
- `lines_added`: Lines of code added in this PR
- `lines_deleted`: Lines of code deleted in this PR
- `lines_changed`: Total lines changed (added + deleted)
- `repository`: Repository name
- `url`: PR URL

**Note**: The `pr_number` column has been removed from the detailed CSV output for cleaner data presentation.


## Command Line Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--weeks` | `-w` | Number of weeks to analyze | 1 |
| `--output` | `-o` | Output directory for CSV files | Current directory |
| `--help` | `-h` | Show help message | - |

## Examples

```bash
# Analyze last week for Arvind's team
python3 gm.py org1.csv

# Monthly analysis for teams (4 weeks)
python3 gm.py EM-1.csv --weeks 4

# Generate reports in specific directory
python3 gm.py team.csv --output ./team_reports/
```

## Metrics Definitions

### Core PR Metrics
- **Created**: PRs authored by the user in the specified time range
- **Merged**: PRs that were successfully merged
- **Open**: PRs still awaiting review/merge
- **Abandoned**: PRs that were closed without merging
- **Merge Rate**: `(Merged PRs / Total PRs) × 100`
- **Abandonment Rate**: `(Abandoned PRs / Total PRs) × 100`
- **Merge Time**: Time from PR creation to merge completion

### Code Change Metrics
- **Lines Added**: Total lines of code added across all PRs
- **Lines Deleted**: Total lines of code removed across all PRs
- **Lines Changed**: Total lines modified (additions + deletions)
- **Average Lines Changed**: Mean lines changed per PR for the user
- **Overall Average**: Team-wide average lines changed per PR

### Coding Activity Metrics
- **Coding Days**: Total count of unique calendar days with commits, calculated per week (Monday-Sunday) across all weeks in the date range
- **Total Commits**: Total number of commits made by the user in the time period
- **Average Coding Days**: Team-wide average of coding days per user

### P90/P95 Percentile Metrics
- **P90 Merge Time**: The 90th percentile of PR merge times across all PRs - 90% of PRs are merged within this time
- **P95 Merge Time**: The 95th percentile of PR merge times across all PRs - 95% of PRs are merged within this time
- **P90 Coding Days**: The 90th percentile of coding days across all users - 90% of users have this many or fewer coding days
- **P95 Coding Days**: The 95th percentile of coding days across all users - 95% of users have this many or fewer coding days
- These metrics help identify performance benchmarks and outliers in team productivity

### CursorAI Metrics (Optional)
**Per User Metrics:**
- **Chat Suggested Lines**: Number of lines of code suggested by CursorAI chat
- **Chat Accepted Lines**: Number of suggested lines that were accepted by the developer
- **Chat Acceptance Rate**: Percentage of suggested lines that were accepted (Accepted / Suggested × 100)
- **AI Completions**: Number of AI-powered code completions used
- **AI Edits**: Number of AI-assisted code edits performed
- **Sessions**: Total number of coding sessions tracked
- **Session Duration**: Total time spent coding with CursorAI (in minutes)
- **Files Edited**: Number of unique files edited with CursorAI assistance

**Aggregate Metrics (in Summary CSV):**
- **Total Cursor Chat Suggested Lines**: Sum of all chat suggested lines across all users
- **Total Cursor Chat Accepted Lines**: Sum of all chat accepted lines across all users
- **Overall Cursor Acceptance Rate**: Team-wide acceptance rate of AI suggestions
- **Total Cursor AI Completions**: Sum of all AI completions across all users
- **Total Cursor AI Edits**: Sum of all AI edits across all users
- **Total Cursor Sessions**: Sum of all coding sessions across all users
- **Total Cursor Session Duration**: Sum of all session durations (in minutes)
- **Total Cursor Files Edited**: Sum of all files edited with AI assistance
- **Cursor Users with Data**: Number of users who have CursorAI activity data

**Understanding CursorAI Metrics:**
- High acceptance rates (>50%) indicate effective AI suggestions and good code quality
- High completion counts suggest heavy reliance on AI assistance for productivity
- Session duration helps track active coding time vs. total work time
- These metrics help measure AI adoption and effectiveness across the team

### Understanding the Data
- **Large Line Changes**: May indicate feature development or major refactoring
- **Small Frequent Changes**: Often suggests bug fixes or incremental improvements
- **High Merge Rates**: Indicates good code quality and review processes
- **Fast Merge Times**: Shows efficient review and CI/CD processes
- **High Coding Days**: Indicates consistent daily development activity
- **Regular Commits**: Shows steady development progress and good version control practices
- **P90/P95 Metrics**: Use these for setting realistic SLAs and identifying outliers that need attention

## Error Handling

The tool handles various error scenarios:
- **Missing GitHub CLI**: Shows installation instructions
- **Authentication issues**: Prompts to run `gh auth login`
- **Invalid usernames**: Reports errors in output without stopping
- **API rate limits**: Gracefully handles GitHub API limitations
- **Network issues**: Reports connection errors per user
- **Permission errors**: Handles repositories the user cannot access

## Troubleshooting

### GitHub CLI Issues
```bash
# Check if GitHub CLI is installed
gh --version

# Re-authenticate if needed
gh auth logout
gh auth login
```

### Permission Issues
Ensure your GitHub account has access to the josys-src organization repositories.

### CSV Format Issues
- Ensure CSV files are UTF-8 encoded
- Check for extra whitespace in usernames
- Verify column headers match expected format

### CursorAI Metrics Showing as 0

If all CursorAI metrics are showing as 0, check the following:

1. **API Key Not Set**:
   ```bash
   # Check if environment variable is set
   echo $CURSOR_API_KEY
   
   # If empty, set it:
   export CURSOR_API_KEY="your-api-key-here"
   export CURSOR_TEAM_ID="your-team-id-here"
   ```

2. **API Key Invalid or Expired**:
   - Verify your API key with your CursorAI administrator
   - Check if your API key has the correct permissions
   - The script will show "Authentication failed" error if the key is invalid

3. **Users Not in CursorAI System**:
   - The script expects users with the email format `email@josys.com`
   - If a user doesn't have a CursorAI account, their metrics will be 0
   - Check the console output for "User not available in Cursor" messages

4. **No Activity in Date Range**:
   - CursorAI metrics are only collected for the specified date range
   - Try extending the date range: `python3 gm.py users.csv --weeks 2`
   - Check if users were actually using CursorAI during that period

5. **API Response Issues**:
   - Look for debug output in the console showing API response status
   - Status 200 with 0 events means no activity was recorded
   - Status 400 typically means user not found in CursorAI system
   - Status 401/403 means authentication/permission issues

6. **Debug Mode**:
   - The script now includes detailed debug output showing:
     - API request details (email, date range, timestamps)
     - Response status codes
     - Number of usage events retrieved
     - Parsed metrics for each user
   - Review this output to identify the specific issue

**Common Scenarios:**
- ✅ API Key set + Users exist + Activity present = Metrics show correctly
- ⚠️ No API Key = All metrics show 0, message: "No API key configured"
- ⚠️ User not in Cursor = Metrics show 0, message: "User not available in Cursor"
- ⚠️ No activity = Metrics show 0, but API call succeeds (0 events retrieved)

## Changelog

### Latest Updates (October 2025)
- **CursorAI Aggregate Metrics**: Added comprehensive aggregate CursorAI metrics in overall statistics
  - Total chat suggested/accepted lines across all users
  - Overall chat acceptance rate
  - Total AI completions, edits, sessions, and session duration
  - Per-user averages for active CursorAI users
  - All metrics included in CSV summary output
- **Enhanced Debug Output**: Added detailed API response logging for troubleshooting CursorAI integration
- **Improved Documentation**: Comprehensive troubleshooting guide for CursorAI metrics showing as 0
- **CSV Format Support**: Confirmed support for email,github_username format in input CSV files

### Previous Updates (September 2025)
- **Added P90/P95 Percentile Analytics**: New percentile calculations for PR merge time and coding days
- **Enhanced Overall Statistics**: P90 and P95 values now displayed in console output for better performance insights
- **Improved Coding Days Calculation**: Fixed issue where coding days were showing as 0 despite commit activity
- **Better Data Collection**: Enhanced data structures to support percentile calculations across all users

### Previous Updates
- **Enhanced Code Change Analytics**: Added detailed line count tracking per PR
- **Coding Days Feature**: Implemented unique coding days calculation based on commit activity
- **CSV Export Improvements**: Enhanced detailed PR exports with line count data
- **Performance Optimizations**: Improved API call efficiency for large datasets

## License
This project is for internal use within the josys-src organization.
