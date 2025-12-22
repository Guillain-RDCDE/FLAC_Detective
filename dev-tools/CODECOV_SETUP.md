# Codecov Setup Instructions

The Codecov badge in README.md currently shows "unknown" because coverage data hasn't been uploaded yet or the Codecov integration isn't fully configured.

## Option 1: Using Codecov GitHub App (Recommended for Public Repos)

1. Go to https://github.com/apps/codecov
2. Click "Configure" or "Install"
3. Select your GitHub account/organization
4. Grant access to the FLAC_Detective repository
5. The next CI run will automatically upload coverage without needing a token

## Option 2: Using CODECOV_TOKEN Secret

1. Go to https://codecov.io and sign in with GitHub
2. Add your repository: https://github.com/GuillainM/FLAC_Detective
3. Copy the repository upload token from Codecov dashboard
4. Add it as a GitHub secret:
   - Go to: https://github.com/GuillainM/FLAC_Detective/settings/secrets/actions
   - Click "New repository secret"
   - Name: `CODECOV_TOKEN`
   - Value: (paste your token from Codecov)
5. The CI workflow will now use this token to upload coverage

## Verifying Coverage Upload

After configuration, the next push to `main` or PR will:
1. Run tests with coverage on Ubuntu Python 3.11
2. Generate `coverage.xml`
3. Upload to Codecov
4. Update the badge in README.md

## Troubleshooting

- **Badge still shows "unknown"**: Wait for the next CI run after configuration
- **Upload fails**: Check the CI logs in the "Upload coverage to Codecov" step
- **Low coverage warning**: Current threshold is 80% (configurable in `.github/codecov.yml`)

## Current Configuration

- Coverage is collected only on: **Ubuntu + Python 3.11**
- Minimum coverage: **80%**
- Configuration file: `.github/codecov.yml`
- Workflow file: `.github/workflows/ci.yml` (lines 72-88)
