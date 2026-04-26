#!/bin/bash
echo "Building frontend..."
npm run build
if [ $? -eq 0 ]; then
    echo "✅ Frontend build success!"
else
    echo "❌ Frontend build failed!"
    exit 1
fi
