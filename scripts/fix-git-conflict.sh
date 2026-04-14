#!/bin/bash
# Fix Git Conflict - ChromaDB Binary File
# Run this when you have merge conflicts with chroma.sqlite3

set -e

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

echo -e "${YELLOW}🔧 Fixing Git Conflict...${NC}\n"

cd "$(dirname "$0")/.."

# 1. Check if we're in a merge conflict state
if [ -f ".git/MERGE_HEAD" ]; then
    echo -e "${YELLOW}📋 Merge in progress detected. Aborting...${NC}"
    git merge --abort
fi

# 2. Clean stash
echo -e "${YELLOW}📋 Cleaning stash...${NC}"
git stash drop 2>/dev/null || true

# 3. Remove unmerged binary files
echo -e "${YELLOW}📋 Removing unmerged binary files...${NC}"
git rm --cached backend/data/chroma_db/chroma.sqlite3 2>/dev/null || true
rm -f backend/data/chroma_db/chroma.sqlite3

# 4. Add to .gitignore if not already there
if ! grep -q "chroma.sqlite3" .gitignore 2>/dev/null; then
    echo -e "${YELLOW}📋 Adding chroma.sqlite3 to .gitignore...${NC}"
    echo "backend/data/chroma_db/chroma.sqlite3" >> .gitignore
    git add .gitignore
    git commit -m "chore: ignore local chroma database" || true
fi

# 5. Clean untracked files (optional)
echo -e "${YELLOW}📋 Cleaning up other untracked files...${NC}"
rm -f backend/hasil_suara.mp3 deploy.sh 2>/dev/null || true
rm -rf scripts/package*.json 2>/dev/null || true

# 6. Try pull again
echo -e "${YELLOW}📋 Pulling latest changes...${NC}"
git pull

echo -e "${GREEN}✅ Git conflict resolved!${NC}"
echo -e "${GREEN}✅ Ready to rebuild and restart${NC}\n"

echo -e "${YELLOW}Next steps:${NC}"
echo "  1. cd frontend && npm install --legacy-peer-deps && npm run build && cd .."
echo "  2. bash scripts/stop.sh"
echo "  3. sleep 2"
echo "  4. bash scripts/start.sh"
