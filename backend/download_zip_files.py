#!/usr/bin/env python3
"""
Download ZIP files from extracted download URLs and populate data_files table.
"""

import sqlite3
import requests
import hashlib
import os
from datetime import datetime
import uuid
from pathlib import Path

def download_zip_files(limit=20):
    """Download ZIP files from metadata download URLs."""

    # Create supporting_docs directory if it doesn't exist
    docs_dir = Path('supporting_docs')
    docs_dir.mkdir(exist_ok=True)

    conn = sqlite3.connect('datasets.db')
    cursor = conn.cursor()

    # Get datasets with ZIP URLs
    cursor.execute('''
        SELECT dataset_id, download_url, title
        FROM metadata
        WHERE download_url LIKE '%.zip'
        LIMIT ?
    ''', (limit,))

    rows = cursor.fetchall()

    print(f'Found {len(rows)} datasets with ZIP URLs')
    print('=' * 60)

    stats = {
        'attempted': 0,
        'success': 0,
        'failed': 0,
        'total_bytes': 0
    }

    for dataset_id, download_url, title in rows:
        stats['attempted'] += 1
        print(f'\n[{stats["attempted"]}/{len(rows)}] Downloading: {title[:50]}...')
        print(f'URL: {download_url}')

        try:
            # Download with timeout
            response = requests.get(download_url, timeout=30, stream=True)

            if response.status_code != 200:
                print(f'  ✗ HTTP {response.status_code}')
                stats['failed'] += 1
                continue

            # Get filename from URL
            filename = download_url.split('/')[-1]
            if not filename.endswith('.zip'):
                filename += '.zip'

            # Save to supporting_docs
            file_path = docs_dir / filename

            # Download content
            content = response.content
            file_size = len(content)

            # Calculate checksum
            checksum = hashlib.sha256(content).hexdigest()

            # Write file
            with open(file_path, 'wb') as f:
                f.write(content)

            stats['total_bytes'] += file_size

            # Insert into data_files table
            file_id = str(uuid.uuid4())
            cursor.execute('''
                INSERT INTO data_files
                (id, dataset_id, filename, file_path, file_size, file_format, checksum, description, downloaded_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                file_id,
                dataset_id,
                filename,
                str(file_path),
                file_size,
                'zip',
                checksum,
                f'Downloaded from {download_url}',
                datetime.utcnow(),
                datetime.utcnow()
            ))

            conn.commit()

            print(f'  ✓ Downloaded: {file_size/1024:.1f} KB')
            print(f'  ✓ Saved to: {file_path}')
            stats['success'] += 1

        except requests.exceptions.Timeout:
            print(f'  ✗ Timeout (>30s)')
            stats['failed'] += 1
        except requests.exceptions.RequestException as e:
            print(f'  ✗ Network error: {e}')
            stats['failed'] += 1
        except Exception as e:
            print(f'  ✗ Error: {e}')
            stats['failed'] += 1

    conn.close()

    print('\n' + '=' * 60)
    print('Download Complete')
    print('=' * 60)
    print(f'Attempted: {stats["attempted"]}')
    print(f'Success: {stats["success"]}')
    print(f'Failed: {stats["failed"]}')
    print(f'Total downloaded: {stats["total_bytes"]/1024/1024:.2f} MB')
    print(f'Success rate: {stats["success"]/stats["attempted"]*100:.1f}%')
    print('=' * 60)

if __name__ == '__main__':
    download_zip_files(limit=20)  # Try 20 ZIP files
