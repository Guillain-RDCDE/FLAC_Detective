# Codecov Configuration Verification Guide

This guide helps you verify that Codecov is properly configured and working.

## ✅ Pre-flight Checklist

### 1. GitHub App Configuration (Completed ✓)
- [x] Codecov GitHub App installed
- [x] Repository access granted to FLAC_Detective
- [x] Workflow file updated with correct parameters

### 2. Workflow Configuration

The CI workflow (`.github/workflows/ci.yml`) should:
- [x] Run tests with coverage on Linux + Python 3.11
- [x] Generate `coverage.xml` file
- [x] Upload to Codecov using `codecov/codecov-action@v4`
- [x] Use `files: ./coverage.xml` parameter
- [x] Have `verbose: true` for debugging

### 3. Codecov Configuration File

The `.github/codecov.yml` file should:
- [x] Set coverage targets (80%)
- [x] Configure ignored paths (tests/, __pycache__, etc.)
- [x] Enable PR comments and annotations

## 🔍 Verification Steps

### Step 1: Check CI Run Status

1. Go to: https://github.com/GuillainM/FLAC_Detective/actions
2. Find the latest "FLAC Detective CI" workflow run
3. Look for the "Test Python 3.11 on ubuntu-latest" job
4. Check these steps:
   - ✅ "Test with coverage (Ubuntu only)" - Should PASS
   - ✅ "Upload coverage to Codecov" - Should complete (even if continue-on-error)

### Step 2: Check Codecov Dashboard

1. Go to: https://app.codecov.io/gh/GuillainM/FLAC_Detective
2. Verify:
   - Repository is listed
   - Latest commit shows up
   - Coverage percentage is displayed
   - Coverage graph shows data

### Step 3: Verify Badge

1. Check the badge in README.md:
   ```markdown
   [![codecov](https://codecov.io/gh/GuillainM/FLAC_Detective/branch/main/graph/badge.svg)](https://codecov.io/gh/GuillainM/FLAC_Detective)
   ```

2. The badge should show:
   - ✅ A percentage (e.g., "85%") instead of "unknown"
   - ✅ A color (green/yellow/red based on coverage)

### Step 4: Check Upload Logs

If the badge still shows "unknown", check the CI logs:

1. Go to the workflow run
2. Expand "Upload coverage to Codecov" step
3. Look for:
   - ✅ "Uploading coverage reports"
   - ✅ "Processing upload"
   - ✅ "View upload at: https://app.codecov.io/..."

## 🐛 Troubleshooting

### Badge Shows "unknown"

**Possible causes:**
1. **No CI run yet** - Wait for the latest commit to finish CI
2. **Upload failed** - Check logs in "Upload coverage to Codecov" step
3. **Wrong branch** - Badge points to `main` branch by default
4. **Codecov processing** - Wait 1-2 minutes after upload

**Solutions:**
```bash
# Trigger a new CI run
git commit --allow-empty -m "ci: trigger coverage update"
git push origin main
```

### Upload Fails with Authentication Error

**If you see:** "Error: Unable to locate build via GitHub Actions API"

**Solution:** Ensure Codecov GitHub App is installed and has access

1. Go to: https://github.com/apps/codecov
2. Click "Configure"
3. Verify "GuillainM/FLAC_Detective" is in the repository list

### Coverage Not Updated

**If coverage data is stale:**

1. Check that tests ran successfully
2. Verify `coverage.xml` was generated
3. Check Codecov dashboard for upload errors
4. Try manual workflow trigger:
   - Go to Actions → "Generate Coverage Report"
   - Click "Run workflow"

## 📊 Expected Coverage

Based on current configuration:
- **Target:** 80% minimum coverage
- **Tests run on:** Ubuntu + Python 3.11
- **Coverage includes:** All files in `src/flac_detective/`
- **Excluded:** `tests/`, `__init__.py`, `__pycache__/`

## 🔗 Useful Links

- **Codecov Dashboard:** https://app.codecov.io/gh/GuillainM/FLAC_Detective
- **GitHub Actions:** https://github.com/GuillainM/FLAC_Detective/actions
- **Codecov Docs:** https://docs.codecov.com/docs
- **GitHub App:** https://github.com/apps/codecov

## ✅ Verification Complete

Once you've confirmed:
- [ ] CI runs successfully
- [ ] Coverage.xml is uploaded to Codecov
- [ ] Codecov dashboard shows coverage data
- [ ] Badge displays percentage instead of "unknown"

The Codecov integration is working correctly! 🎉

---

**Last Updated:** 2025-12-22
**Commit that triggered test:** 19432da
