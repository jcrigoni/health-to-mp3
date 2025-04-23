#!/bin/bash

# This script deletes markdown files with less than 100 words

for file in *.md; do                                                            
  word_count=$(wc -w < "$file")
  if [ "$word_count" -lt 100 ]; then
    echo "Delete $file ($word_count words)"
    rm "$file"