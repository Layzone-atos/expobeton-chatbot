#!/usr/bin/env python3
"""Fix Windows CRLF line endings in all text files."""
import os

EXTENSIONS = {'.sh', '.py', '.yml', '.yaml', '.txt', '.md', '.json', '.css', '.js', '.html'}
SKIP_DIRS = {'.git', 'models', '__pycache__', '.rasa', 'node_modules', 'docs', 'pdf_source_2018',
             'pdf_source_2019', 'pdf_source_2021', 'pdf_source_2022', 'pdf_source_2023',
             'pdf_source_2024', 'pdf_source_2025', 'pdf_source_2026'}

fixed = 0
for root, dirs, files in os.walk('.'):
    dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith('.')]
    for f in files:
        if any(f.endswith(ext) for ext in EXTENSIONS):
            path = os.path.join(root, f)
            try:
                with open(path, 'rb') as fp:
                    content = fp.read()
                if b'\r' in content:
                    clean = content.replace(b'\r\n', b'\n').replace(b'\r', b'\n')
                    with open(path, 'wb') as fp:
                        fp.write(clean)
                    print(f'Fixed: {path}')
                    fixed += 1
            except Exception as e:
                print(f'Skip {path}: {e}')

print(f'\nTotal: {fixed} files fixed')
