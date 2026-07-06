# Push to All Remotes

Transparently push the current branch to all configured remotes (origin + pictet).

## Usage

```bash
# Push current branch
./scripts/git-push-all

# Push specific branch
./scripts/git-push-all main
```

## How it works

The script reads all git remotes with both fetch and push URLs,
and pushes the given branch to each one. For the `pictet` remote,
it uses `GH_TOKEN` from the `eguenichon_pictet` account.

## Git alias (optional)

```bash
git config --global alias.push-all '!f() { BRANCH=${1:-$(git branch --show-current)}; GIT_REMOTE_URLS=($(git remote -v | grep "(push)" | awk "{print \$2}")); for url in "${GIT_REMOTE_URLS[@]}"; do git push "$url" "$BRANCH"; done; }; f'
```
