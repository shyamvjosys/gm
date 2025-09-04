# GitHub PR Metrics Reporter

GitHub PR Metrics Reporter tool that generates comprehensive pull request (PR) metrics reports for GitHub users in the josys-src organization. The tool reads usernames from CSV files and produces detailed analytics about PR creation, merge rates, abandonment rates, and merge times.

## Features

- **Comprehensive PR Analysis**: Tracks created, merged, open, and abandoned PRs
- **Time-based Analysis**: Configurable date range (default: last 7 days)
- **Detailed Metrics**: 
  - Total PRs created, merged, open, and abandoned
  - Merge rate and abandonment rate percentages
  - Average merge time in hours
  - Individual PR details with timestamps
- **Multiple Output Formats**: Console report + CSV exports
- **Batch Processing**: Process multiple users from CSV input
- **Error Handling**: Graceful handling of API errors and missing data

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

📈 OVERALL STATISTICS
   Users Processed: 6
   Total PRs Created: 54
   Total PRs Merged: 45
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

## License
This project is for internal use within the josys-src organization.
