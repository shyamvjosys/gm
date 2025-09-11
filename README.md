# GitHub PR Metrics Reporter

GitHub PR Metrics Reporter tool that generates comprehensive pull request (PR) metrics reports for GitHub users in the josys-src organization. The tool reads usernames from CSV files and produces detailed analytics about PR creation, merge rates, abandonment rates, merge times, and code change metrics.

## Features

- **Comprehensive PR Analysis**: Tracks created, merged, open, and abandoned PRs
- **Time-based Analysis**: Configurable date range (default: last 7 days)
- **Detailed Metrics**: 
  - Total PRs created, merged, open, and abandoned
  - Merge rate and abandonment rate percentages
  - Average merge time in hours
  - **Code Change Analytics**: Average lines changed per PR, total lines added/deleted
  - **Coding Days Analytics**: Count of unique days with at least one commit
  - Total commit count per user
  - Individual PR details with timestamps and line counts
- **Multiple Output Formats**: Console report + CSV exports with enhanced line count data
- **Batch Processing**: Process multiple users from CSV input
- **Error Handling**: Graceful handling of API errors and missing data
- **Performance Optimized**: Efficient API calls with individual PR line count fetching

## Prerequisites

1. **GitHub CLI**: Install and authenticate with GitHub CLI
   ```bash
   # Install GitHub CLI (macOS)
   brew install gh
   
   # Authenticate
   gh auth login
   ```

2. **Python 3.6+**: Ensure Python 3.6 or higher is installed

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
# Analyze last 14 days instead of default 7
python3 gm.py usernames.csv --days 14

# Specify custom output directory
python3 gm.py usernames.csv --output ./reports/

# Combine options
python3 gm.py usernames.csv --days 30 --output ./monthly_reports/
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
PR METRICS REPORT - josys-src Organization (Last 7 days)
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
   Overall Average Lines Changed: 615.8
   Total Lines Added (All Users): 27897
   Total Lines Deleted (All Users): 7203
   Total Coding Days (All Users): 35
   Total Commits (All Users): 133
   Average Coding Days per User: 5.8
   ...
```

### 2. Summary CSV (`pr_summary.csv`)
Contains aggregated metrics per user:
- `username`: GitHub username
- `total_created`: Total PRs created
- `total_merged`: Total PRs merged
- `total_open`: Total PRs still open
- `total_abandoned`: Total PRs closed without merge
- `merge_rate`: Percentage of PRs that were merged
- `abandonment_rate`: Percentage of PRs that were abandoned
- `average_merge_time_hours`: Average time from creation to merge
- `average_lines_changed`: Average lines changed per PR
- `total_lines_added`: Total lines added across all PRs
- `total_lines_deleted`: Total lines deleted across all PRs
- `coding_days`: Total count of unique calendar days with commits (calculated per week Monday-Sunday)
- `total_commits`: Total number of commits made by the user
- `error`: Any error encountered for this user

### 3. Detailed CSV (`pr_details.csv`)
Contains individual PR records with:
- `username`: GitHub username
- `pr_number`: PR number
- `title`: PR title
- `state`: PR state (open, merged, closed)
- `created_at`: Creation timestamp
- `closed_at`: Close/merge timestamp
- `merge_time_hours`: Time to merge in hours
- `lines_added`: Lines of code added in this PR
- `lines_deleted`: Lines of code deleted in this PR
- `lines_changed`: Total lines changed (added + deleted)
- `repository`: Repository name
- `url`: PR URL


## Command Line Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--days` | `-d` | Number of days to analyze | 7 |
| `--output` | `-o` | Output directory for CSV files | Current directory |
| `--help` | `-h` | Show help message | - |

## Examples

```bash
# Analyze last week for Arvind's team
python3 gm.py org1.csv

# Monthly analysis for teams
python3 gm.py EM-1.csv --days 30

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

### Understanding the Data
- **Large Line Changes**: May indicate feature development or major refactoring
- **Small Frequent Changes**: Often suggests bug fixes or incremental improvements
- **High Merge Rates**: Indicates good code quality and review processes
- **Fast Merge Times**: Shows efficient review and CI/CD processes
- **High Coding Days**: Indicates consistent daily development activity
- **Regular Commits**: Shows steady development progress and good version control practices

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

## License
This project is for internal use within the josys-src organization.
