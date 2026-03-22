#!/bin/bash
# =============================================================================
# AI Council Release Branch Creator
# =============================================================================
# Creates a release branch from develop with dev-only files removed
#
# Usage:
#   ./scripts/create-release.sh              # Interactive version selection
#   ./scripts/create-release.sh patch        # Auto-increment patch (x.y.Z)
#   ./scripts/create-release.sh minor        # Auto-increment minor (x.Y.0)
#   ./scripts/create-release.sh major        # Auto-increment major (X.0.0)
#   ./scripts/create-release.sh v1.2.0       # Explicit version
#   ./scripts/create-release.sh --dry-run    # Simulate without making changes
#   ./scripts/create-release.sh patch --dry-run
#
# Safety Features:
#   - Auto-commits uncommitted tracked changes before proceeding
#   - Backs up untracked local files to backup directory
#   - Restores missing untracked files after completion
#   - Maintains version log in scripts/production-release-log.md
#
# Flow:
#   develop → release/vX.Y.Z → PR to main → tag on merge
#
# Deployment:
#   - Install via: uvx --from git+https://github.com/tondinugraha/aicouncil aicouncil
#   - Or: pip install git+https://github.com/tondinugraha/aicouncil@main
#
# =============================================================================

set -e  # Exit on error

# -----------------------------------------------------------------------------
# Dry Run Mode
# -----------------------------------------------------------------------------
DRY_RUN=false
VERSION_ARG=""

# Parse arguments
for arg in "$@"; do
    case $arg in
        --dry-run)
            DRY_RUN=true
            ;;
        *)
            VERSION_ARG="$arg"
            ;;
    esac
done

dry_run() {
    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}[DRY-RUN]${NC} $*"
        return 0
    else
        "$@"
    fi
}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

# Project name
PROJECT_NAME="aicouncil"

# Backup configuration
BACKUP_DIR="${HOME}/Dev/backup/${PROJECT_NAME}-develop"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
RELEASE_LOG="${SCRIPT_DIR}/production-release-log.md"

# Cache the absolute script path before anything gets deleted
SELF_SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"

# Untracked files to protect (git-ignored but needed locally)
UNTRACKED_FILES=(
    ".mcp.json"
    "CLAUDE.md"
    ".gitignore"
)

# Local-only directories to protect (git-ignored but needed locally)
LOCAL_ONLY_DIRS=(
    "_bmad/"
    ".aicouncil/"
    ".claude/"
    ".claude-work/"
    ".pytest_cache/"
    ".ruff_cache/"
    ".venv/"
)

# Dev-only directories to remove from release (ONLY git-tracked directories!)
# NOTE: Do NOT add gitignored directories here - they won't be in release anyway
#
# Gitignored (DO NOT ADD): _bmad, .claude, .claude-work, .aicouncil, .venv,
#                          .pytest_cache, .ruff_cache
#
# TRACKED (must be here): _bmad-output, docs, tests, scripts
DEV_DIRECTORIES=(
    "_bmad-output/"
    "docs/"
    "tests/"
    "scripts/"
)

# Dev-only files to remove from release (ONLY tracked files)
DEV_FILES=(
    "CLAUDE.md"
)

# -----------------------------------------------------------------------------
# Output Functions
# -----------------------------------------------------------------------------

print_header() {
    echo ""
    echo -e "${CYAN}=============================================="
    echo -e "  $1"
    echo -e "==============================================${NC}"
    echo ""
}

print_step() {
    echo -e "${BLUE}==>${NC} $1"
}

print_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# -----------------------------------------------------------------------------
# Version Management Functions
# -----------------------------------------------------------------------------

# Parse last version from log
get_last_version() {
    if [ ! -f "$RELEASE_LOG" ]; then
        echo "0.0.0"
        return
    fi
    local version=$(grep -E '^\| v[0-9]+\.[0-9]+\.[0-9]+' "$RELEASE_LOG" | head -1 | awk -F'|' '{print $2}' | tr -d ' v')
    if [ -z "$version" ]; then
        echo "0.0.0"
    else
        echo "$version"
    fi
}

# Increment version based on type
increment_version() {
    local version=$1
    local type=$2

    IFS='.' read -r major minor patch <<< "$version"

    case $type in
        major) echo "$((major + 1)).0.0" ;;
        minor) echo "${major}.$((minor + 1)).0" ;;
        patch) echo "${major}.${minor}.$((patch + 1))" ;;
    esac
}

# Validate semantic version format
validate_version() {
    local version=$1
    if [[ ! "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        print_error "Invalid version format: $version"
        print_error "Expected: X.Y.Z (e.g., 1.2.3)"
        exit 1
    fi
}

# Determine version from argument
resolve_version() {
    local arg=$1
    local last_version=$(get_last_version)

    case $arg in
        major|minor|patch)
            increment_version "$last_version" "$arg"
            ;;
        v[0-9]*.[0-9]*.[0-9]*)
            local ver="${arg#v}"
            validate_version "$ver"
            echo "$ver"
            ;;
        [0-9]*.[0-9]*.[0-9]*)
            validate_version "$arg"
            echo "$arg"
            ;;
        "")
            echo ""
            print_step "Last release: v${last_version}"
            echo ""
            echo "Select version increment type:"
            echo "  [1] patch  -> v$(increment_version "$last_version" "patch")"
            echo "  [2] minor  -> v$(increment_version "$last_version" "minor")"
            echo "  [3] major  -> v$(increment_version "$last_version" "major")"
            echo ""
            read -p "Choice [1/2/3]: " choice
            case $choice in
                1) increment_version "$last_version" "patch" ;;
                2) increment_version "$last_version" "minor" ;;
                3) increment_version "$last_version" "major" ;;
                *) print_error "Invalid choice"; exit 1 ;;
            esac
            ;;
        *)
            print_error "Invalid version argument: $arg"
            echo ""
            echo "Usage:"
            echo "  $0              # Interactive version selection"
            echo "  $0 patch        # Auto-increment patch (x.y.Z)"
            echo "  $0 minor        # Auto-increment minor (x.Y.0)"
            echo "  $0 major        # Auto-increment major (X.0.0)"
            echo "  $0 v1.2.0       # Explicit version"
            exit 1
            ;;
    esac
}

# Update release log after successful PR creation
update_release_log() {
    local version=$1
    local branch=$2
    local pr_number=$3
    local date=$(date +%Y-%m-%d)
    local log_file=$4

    # Ensure directory exists (scripts/ may have been deleted during release)
    mkdir -p "$(dirname "$log_file")"

    # Initialize log file if doesn't exist
    if [ ! -f "$log_file" ]; then
        cat > "$log_file" << 'EOF'
# AI Council Production Release Log

> **Auto-generated by `create-release.sh`**
> Do not edit manually unless correcting errors.
>
> **Status values:** `pending` (PR created) -> `merged` (PR merged) -> `deployed` (in production)
>
> **Deployment:**
> - Install: `uvx --from git+https://github.com/tondinugraha/aicouncil aicouncil`
> - Or: `pip install git+https://github.com/tondinugraha/aicouncil@main`

| Version | Date | Branch | PR | Status | Notes |
|---------|------|--------|-----|--------|-------|
EOF
    fi

    # Create new entry
    local new_entry="| v${version} | ${date} | ${branch} | #${pr_number} | pending | |"

    # Insert new entry after the header line
    local temp_file=$(mktemp)
    head -n 11 "$log_file" > "$temp_file"
    echo "$new_entry" >> "$temp_file"
    tail -n +12 "$log_file" >> "$temp_file"
    mv "$temp_file" "$log_file"

    print_success "Release log updated: v${version}"
}

# -----------------------------------------------------------------------------
# Safety Functions
# -----------------------------------------------------------------------------

# Auto-commit all uncommitted tracked changes
auto_commit_changes() {
    local modified=$(git diff --name-only | wc -l | tr -d ' ')
    local staged=$(git diff --cached --name-only | wc -l | tr -d ' ')

    if [ "$modified" -gt 0 ] || [ "$staged" -gt 0 ]; then
        if [ "$DRY_RUN" = true ]; then
            print_step "Auto-committing working changes..."
            echo -e "${YELLOW}[DRY-RUN]${NC} Would auto-commit ${modified} modified, ${staged} staged files"
            print_success "Would commit changes automatically"
        else
            print_step "Auto-committing working changes..."
            git add -u
            git commit -m "chore(release): auto-save working changes before v${VERSION}

Files: ${modified} modified, ${staged} staged
Triggered by: create-release.sh"
            print_success "Changes committed automatically"
        fi
    else
        print_success "No uncommitted changes to save"
    fi
}

# Backup untracked local files
backup_untracked_files() {
    print_step "Backing up untracked local files..."

    rm -rf "$BACKUP_DIR"
    mkdir -p "$BACKUP_DIR"

    local backed_up=0
    for dir in "${LOCAL_ONLY_DIRS[@]}"; do
        if [ -d "$PROJECT_ROOT/$dir" ]; then
            mkdir -p "$BACKUP_DIR/$(dirname "$dir")"
            cp -R "$PROJECT_ROOT/$dir" "$BACKUP_DIR/$dir"
            echo "  + $dir"
            backed_up=$((backed_up + 1))
        fi
    done
    for file in "${UNTRACKED_FILES[@]}"; do
        if [ -f "$PROJECT_ROOT/$file" ]; then
            mkdir -p "$BACKUP_DIR/$(dirname "$file")"
            cp "$PROJECT_ROOT/$file" "$BACKUP_DIR/$file"
            echo "  + $file"
            backed_up=$((backed_up + 1))
        fi
    done

    if [ $backed_up -gt 0 ]; then
        print_success "Backed up $backed_up item(s) to $BACKUP_DIR"
    else
        print_warning "No untracked files found to backup"
    fi
}

# Restore all untracked files from backup
restore_untracked_files() {
    print_step "Restoring local files from backup..."

    local restored=0
    for dir in "${LOCAL_ONLY_DIRS[@]}"; do
        if [ -d "$BACKUP_DIR/$dir" ]; then
            rm -rf "$PROJECT_ROOT/$dir"
            mkdir -p "$PROJECT_ROOT/$(dirname "$dir")"
            cp -R "$BACKUP_DIR/$dir" "$PROJECT_ROOT/$dir"
            echo "  + Restored: $dir"
            restored=$((restored + 1))
        fi
    done
    for file in "${UNTRACKED_FILES[@]}"; do
        if [ -f "$BACKUP_DIR/$file" ]; then
            mkdir -p "$PROJECT_ROOT/$(dirname "$file")"
            cp "$BACKUP_DIR/$file" "$PROJECT_ROOT/$file"
            echo "  + Restored: $file"
            restored=$((restored + 1))
        fi
    done

    if [ $restored -gt 0 ]; then
        print_success "Restored $restored item(s) from backup"
    else
        print_warning "No backup files found to restore"
    fi
}

# -----------------------------------------------------------------------------
# Main Script
# -----------------------------------------------------------------------------

print_header "AI Council Release Creator"

# Change to project root
cd "$PROJECT_ROOT"

# Check if we're in the repo root
if [ ! -d ".git" ]; then
    print_error "Must run from repository root"
    exit 1
fi

# Verify we're on develop branch
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "develop" ]; then
    print_error "Release script must be run from 'develop' branch"
    print_error "Current branch: $CURRENT_BRANCH"
    echo ""
    echo "Switch to develop first:"
    echo "  git checkout develop"
    exit 1
fi

# Check if gh CLI is available
if ! command -v gh &> /dev/null; then
    print_error "GitHub CLI (gh) is required but not installed"
    echo "Install with: brew install gh (macOS)"
    exit 1
fi

# Check if authenticated with gh
if ! gh auth status &> /dev/null; then
    print_error "Not authenticated with GitHub CLI"
    echo "Run: gh auth login"
    exit 1
fi

# Resolve version from argument
VERSION=$(resolve_version "$VERSION_ARG")
BRANCH_NAME="release/v${VERSION}"

# Show dry-run banner if enabled
if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}================================================${NC}"
    echo -e "${YELLOW}  DRY-RUN MODE — No changes will be made${NC}"
    echo -e "${YELLOW}================================================${NC}"
    echo ""
fi

print_header "Creating Release: v${VERSION}"

# Safety Step 1: Auto-commit uncommitted changes
auto_commit_changes

# Safety Step 2: Backup untracked files
backup_untracked_files

# Step 1: Pull latest develop
print_step "Pulling latest develop..."
if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}[DRY-RUN]${NC} git pull origin develop"
else
    git pull origin develop
fi
print_success "On latest develop"

# Step 2: Check if release branch already exists
if git show-ref --verify --quiet "refs/heads/${BRANCH_NAME}"; then
    print_error "Branch ${BRANCH_NAME} already exists locally"
    echo "Delete it first with: git branch -D ${BRANCH_NAME}"
    exit 1
fi

if git ls-remote --exit-code --heads origin "${BRANCH_NAME}" &> /dev/null; then
    print_error "Branch ${BRANCH_NAME} already exists on remote"
    echo "Delete it first with: git push origin --delete ${BRANCH_NAME}"
    exit 1
fi

# Step 3: Create release branch
print_step "Creating branch ${BRANCH_NAME}..."
if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}[DRY-RUN]${NC} git checkout -b ${BRANCH_NAME}"
else
    git checkout -b "${BRANCH_NAME}"
fi
print_success "Created ${BRANCH_NAME}"

# Step 4: Remove dev-only directories
print_step "Removing dev-only directories..."
removed_count=0
for dir in "${DEV_DIRECTORIES[@]}"; do
    if [ -d "$dir" ]; then
        if [ "$DRY_RUN" = true ]; then
            file_count=$(find "$dir" -type f 2>/dev/null | wc -l | tr -d ' ')
            echo -e "  ${YELLOW}[DRY-RUN]${NC} Would remove ${dir} ($file_count files)"
        else
            git rm -rf --cached "${dir}" 2>/dev/null || true
            rm -rf "${dir}" 2>/dev/null || true
            echo "  - Removed ${dir}"
        fi
        removed_count=$((removed_count + 1))
    fi
done
print_success "Processed $removed_count directories"

# Step 5: Remove dev-only files
print_step "Removing dev-only files..."
removed_files=0
for file in "${DEV_FILES[@]}"; do
    if [ -f "$file" ]; then
        if [ "$DRY_RUN" = true ]; then
            size=$(ls -lh "$file" 2>/dev/null | awk '{print $5}')
            echo -e "  ${YELLOW}[DRY-RUN]${NC} Would remove ${file} ($size)"
        else
            git rm --cached "${file}" 2>/dev/null || true
            rm -f "${file}" 2>/dev/null || true
            echo "  - Removed ${file}"
        fi
        removed_files=$((removed_files + 1))
    fi
done
print_success "Processed $removed_files files"

# Step 6: Stage all removals
if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}[DRY-RUN]${NC} git add -A"
else
    git add -A
fi

# Step 7: Commit
if [ "$DRY_RUN" = true ]; then
    print_step "Committing changes..."
    echo -e "${YELLOW}[DRY-RUN]${NC} git commit -m 'chore: prepare release v${VERSION}...'"
    print_success "Changes would be committed"
else
    if git diff --cached --quiet; then
        print_warning "No dev files were found to remove"
        git commit --allow-empty -m "chore: prepare release v${VERSION}

Production release from develop branch.
No dev-only files were tracked in this release."
    else
        print_step "Committing changes..."
        git commit -m "chore: prepare release v${VERSION}

Remove development-only files for production release:
- BMAD workflow outputs (_bmad-output/)
- Documentation (docs/)
- Test suite (tests/)
- Release scripts (scripts/)
- Dev configs (CLAUDE.md)

These files remain on develop branch for development use.

Install via:
  uvx --from git+https://github.com/tondinugraha/aicouncil aicouncil

Removed directories: ${DEV_DIRECTORIES[*]}
Removed files: ${DEV_FILES[*]}"
        print_success "Changes committed"
    fi
fi

# Step 8: Push branch
print_step "Pushing ${BRANCH_NAME} to origin..."
if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}[DRY-RUN]${NC} git push -u origin ${BRANCH_NAME}"
    print_success "Would push to origin"
else
    git push -u origin "${BRANCH_NAME}"
    print_success "Pushed to origin"
fi

# Step 9: Create PR
print_step "Creating Pull Request to main..."
if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}[DRY-RUN]${NC} gh pr create --base main --head ${BRANCH_NAME} --title 'Release v${VERSION}'"
    PR_URL="https://github.com/tondinugraha/aicouncil/pull/999"
    PR_NUMBER="999"
    print_success "Would create PR: $PR_URL (simulated)"
else
    PR_OUTPUT=$(gh pr create \
        --base main \
        --head "${BRANCH_NAME}" \
        --title "Release v${VERSION}" \
        --body "$(cat <<EOF
## Release v${VERSION}

### Summary
Production release from \`develop\` branch with development-only files removed.

### What's Included
- AI Council MCP server (\`src/aicouncil/\`)
- Agent roster and personas (\`src/aicouncil/agents/\`)
- Prompt templates (\`src/aicouncil/prompts/\`)
- Council assembly and deliberation logic
- Memory/knowledge persistence system
- Codebase scanning tools
- Package config (\`pyproject.toml\`, \`uv.lock\`)

### What's Excluded (Dev-Only)
- BMAD workflow outputs (\`_bmad-output/\`)
- Documentation (\`docs/\`)
- Test suite (\`tests/\`)
- Release scripts (\`scripts/\`)
- AI agent configs (\`.claude/\`, \`.aicouncil/\`, \`.mcp.json\`)
- Dev configs (\`CLAUDE.md\`)

### Pre-merge Checklist
- [ ] All council tools working (ai_council, brainstorm, critique, etc.)
- [ ] Agent loader resolves personas correctly
- [ ] Config scaffold works on fresh install
- [ ] No development-only files included

### Installation
\`\`\`bash
# After merge to main:
uvx --from git+https://github.com/tondinugraha/aicouncil aicouncil

# Or pip:
pip install git+https://github.com/tondinugraha/aicouncil@main
\`\`\`

---
*Generated with [create-release.sh](./scripts/create-release.sh)*
EOF
)")
    PR_URL="$PR_OUTPUT"
    PR_NUMBER=$(echo "$PR_URL" | grep -oE '[0-9]+$')
    print_success "PR created: $PR_URL"
fi

# Step 10: Switch back to develop and update release log
print_step "Updating release log..."
if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}[DRY-RUN]${NC} git checkout develop"
    echo -e "${YELLOW}[DRY-RUN]${NC} Would update ${RELEASE_LOG}"
    echo -e "${YELLOW}[DRY-RUN]${NC} git commit & push release log"
    print_success "Would update release log"
else
    git checkout develop

    # Recalculate RELEASE_LOG path using PROJECT_ROOT (scripts/ is back on develop)
    RELEASE_LOG="${PROJECT_ROOT}/scripts/production-release-log.md"

    update_release_log "$VERSION" "$BRANCH_NAME" "$PR_NUMBER" "$RELEASE_LOG"
    git add "$RELEASE_LOG"
    git commit -m "chore(release): log v${VERSION} release (#${PR_NUMBER})"
    git push origin develop
    print_success "Release log committed and pushed"
fi

# Safety Step 3: Restore any missing untracked files
restore_untracked_files

print_header "Release v${VERSION} Created Successfully!"

echo "Branch:  ${BRANCH_NAME}"
echo "PR URL:  ${PR_URL}"
echo "Log:     ${RELEASE_LOG}"
echo ""
echo -e "${CYAN}Next steps:${NC}"
echo "  1. Review the PR on GitHub"
echo "  2. Merge PR to main"
echo "  3. Tag the release: git tag v${VERSION} && git push origin v${VERSION}"
echo "  4. Update release log status to 'merged'"
echo ""
