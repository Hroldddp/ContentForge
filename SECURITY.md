# Security

If you find a security issue, don't open a public issue. Report it privately:

- GitHub Security Advisories preferred: https://github.com/Hroldddp/ContentForge/security/advisories
- Or open a draft issue with the `security` label

We'll acknowledge within 48 hours and give a timeline for the fix.

## Things to watch

- **`.env` files** — don't commit API keys
- **Dependencies** — keep them updated
- **yt-dlp** — only downloads from YouTube, URLs aren't user-supplied

## Best practices

- `.env` is in `.gitignore` but double-check
- `sudo pacman -Syu` regularly
- Review Dependabot PRs when they come in
- Run `bash setup.sh` after pulling updates
