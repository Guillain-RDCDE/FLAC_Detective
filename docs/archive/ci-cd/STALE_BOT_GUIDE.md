# Stale Bot Management Guide

This guide explains how the FLAC Detective project manages stale issues and pull requests automatically.

## Overview

The Stale Bot is an automated GitHub Action that helps maintain the project by identifying and closing inactive issues and pull requests. This keeps the issue tracker clean and focused on active work.

## How It Works

### 📅 Schedule

The bot runs automatically:
- **Daily** at midnight UTC (00:00)
- Can also be **manually triggered** via GitHub Actions UI

### ⏱️ Timeline

#### Issues
1. After **60 days** of inactivity → Marked as `stale`
2. After **7 more days** (67 total) → Automatically closed

#### Pull Requests
1. After **45 days** of inactivity → Marked as `stale` (faster than issues)
2. After **7 more days** (52 total) → Automatically closed

### 🏷️ Exemption Labels

Issues/PRs with these labels will **never** become stale:

| Label | Description |
|-------|-------------|
| `pinned` | Important items to keep visible |
| `security` | Security-related issues |
| `critical` | Critical bugs or features |
| `roadmap` | Long-term planning items |
| `help wanted` | Issues seeking community help |
| `good first issue` | Beginner-friendly issues |
| `work-in-progress` | PRs actively being worked on |
| `do-not-close` | Items that should remain open |

### 📝 Special Rules

- **Draft PRs**: Never marked as stale
- **Milestones**: Issues with milestones are exempt
- **Assigned**: Assigned items can still become stale (activity expected)

## Messages

### Stale Issue Warning

When an issue becomes stale, the bot posts:

```
👋 This issue has been automatically marked as stale because it has not had recent activity.

It will be closed in **7 days** if no further activity occurs.

If you believe this issue is still relevant:
- Add a comment to remove the stale label
- Provide additional context or updates

Thank you for your contributions to FLAC Detective! 🎵
```

### Stale PR Warning

For pull requests:

```
👋 This pull request has been automatically marked as stale because it has not had recent activity.

It will be closed in **7 days** if no further activity occurs.

If you're still working on this:
- Push new commits or add a comment
- Resolve any conflicts
- Request a review

Thank you for your contribution! 🙏
```

### Closure Messages

If no activity occurs within 7 days, items are closed with a polite message explaining how to reopen.

## Preventing Stale Status

### For Issues

To prevent an issue from becoming stale:

1. **Comment** on the issue to show activity
2. **Add updates** about progress or blockers
3. **Apply an exemption label** (if appropriate)
4. **Assign a milestone** to indicate planned work

### For Pull Requests

To keep a PR active:

1. **Push commits** to show continued work
2. **Comment** with status updates
3. **Request reviews** from maintainers
4. **Mark as draft** if not ready for review
5. **Apply exemption labels** like `work-in-progress`

## Reactivating Stale Items

If an issue/PR is marked stale but shouldn't be:

1. **Add a comment** → The `stale` label is automatically removed
2. **Provide context** about why it's still relevant
3. **Add exemption label** to prevent future stale marking

## For Maintainers

### Manual Control

You can manually manage the stale workflow:

```bash
# Trigger manually from GitHub Actions UI
# Go to: Actions → "Mark stale issues and PRs" → Run workflow
```

### Configuration

Edit [.github/workflows/stale.yml](../.github/workflows/stale.yml) to adjust:

- `days-before-stale`: Days before marking stale
- `days-before-close`: Days after stale before closing
- `exempt-issue-labels`: Labels that prevent stale marking
- `operations-per-run`: Limit to avoid rate limiting

### Testing Changes

To test configuration changes without taking action:

```yaml
# In stale.yml, set:
debug-only: true
```

This will log what would happen without actually marking or closing items.

### Common Adjustments

#### Increase Inactivity Period

```yaml
days-before-stale: 90      # Wait 90 days instead of 60
days-before-pr-stale: 60   # Wait 60 days for PRs
```

#### Add New Exemption Labels

```yaml
exempt-issue-labels: 'pinned,security,critical,roadmap,help wanted,good first issue,your-new-label'
```

#### Change Close Delay

```yaml
days-before-close: 14      # Give 14 days warning instead of 7
```

## Best Practices

### For Contributors

1. **Stay Engaged**: Comment regularly on your issues/PRs
2. **Use Draft PRs**: Mark work-in-progress PRs as drafts
3. **Update Status**: Add progress updates even if code hasn't changed
4. **Be Responsive**: Reply to review comments promptly

### For Maintainers

1. **Review Stale Items**: Check weekly for false positives
2. **Add Exemption Labels**: Proactively label important items
3. **Communicate**: Let contributors know about upcoming closure
4. **Be Flexible**: Manually reopen if there's good reason

## Rationale

### Why Auto-Close Issues?

- **Focus**: Keeps issue tracker focused on active work
- **Clarity**: Makes it easier to see what needs attention
- **Motivation**: Encourages timely responses and updates
- **Maintenance**: Reduces clutter for maintainers

### Why Different Timings?

- **Issues (60 days)**: Longer window as issues may need research
- **PRs (45 days)**: Shorter as they represent ready/active work
- **Close delay (7 days)**: Gives time to respond to stale notice

## Statistics

The bot processes up to **30 operations per run** to respect GitHub's rate limits. This includes:
- Checking items for staleness
- Adding stale labels
- Posting comments
- Closing items

## Troubleshooting

### Issue Closed Too Soon?

1. Comment on the closed issue with updates
2. Ask a maintainer to reopen
3. Reference it in a new issue if needed

### PR Closed But Still Working?

1. Comment explaining continued work
2. Push new commits to trigger reopening consideration
3. Apply `work-in-progress` label

### Bot Not Working?

Check:
1. **Permissions**: Workflow has `issues: write` and `pull-requests: write`
2. **Schedule**: GitHub Actions scheduled workflows can have delays
3. **Rate Limits**: Check if operations-per-run limit was hit
4. **Manual Trigger**: Try running manually to test

## References

- **Workflow File**: [.github/workflows/stale.yml](../.github/workflows/stale.yml)
- **GitHub Action**: [actions/stale@v9](https://github.com/actions/stale)
- **Action Documentation**: [Stale Action Docs](https://github.com/actions/stale#readme)

---

**Questions?** Open an issue or discussion on GitHub!
