"""Shared Claude Code environment policy for FCC client surfaces."""
"""Custom: CLAUDE_CODE_AUTO_COMPACT_WINDOW changed from 190000 -> 180000
   to match Ornith's 200K context limit (with 20K headroom)."""

CLAUDE_CODE_AUTO_COMPACT_WINDOW = "180000"
CLAUDE_BINARY_NAME = "claude"
CLAUDE_NO_AUTH_SENTINEL = "fcc-no-auth"


def claude_auth_token(auth_token: str) -> str:
    """Return the Claude Code auth marker for proxy-auth or no-auth sessions."""

    return auth_token.strip() or CLAUDE_NO_AUTH_SENTINEL
