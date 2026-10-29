#!/bin/bash

# PostToolUse hook: run Prettier on client files Claude just wrote or edited.
# Claude Code passes the tool call as JSON on stdin; the path is at .tool_input.file_path.

FILE=$(jq -r '.tool_input.file_path // empty')

# Only client source files; Prettier is installed in client/
case "$FILE" in
  *client*.js|*client*.vue|*client*.css|*client*.json)
    cd "${CLAUDE_PROJECT_DIR}/client" && npx --no-install prettier --write "$FILE" >/dev/null 2>&1
    ;;
esac

# Never block the tool call
exit 0
