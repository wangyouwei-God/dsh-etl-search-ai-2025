#!/usr/bin/env python3
"""
Extract supporting documents (PDFs, CSVs, etc.) from downloaded ZIP files
and populate the supporting_documents table.
"""

import sqlite3
import zipfile
import hashlib
import uuid
from datetime import datetime
from pathlib import Path

def extract_supporting_documents():
    """Extract supporting documents from ZIP files."""

    conn = sqlite3.connect('datasets.db')
    cursor = conn.cursor()

    # Get all downloaded ZIP files
    cursor.execute('''
        SELECT id, dataset_id, filename, file_path
        FROM data_files
        WHERE file_format = 'zip'
    ''')

    zip_files = cursor.fetchall()

    print(f'Found {len(zip_files)} ZIP files to extract')
    print('=' * 60)

    stats = {
        'zips_processed': 0,
        'docs_extracted': 0,
        'total_bytes': 0,
        'errors': 0
    }

    # Document types we're interested in
    doc_extensions = {'.pdf', '.doc', '.docx', '.txt', '.csv', '.xlsx', '.readme', '.md'}

    for data_file_id, dataset_id, filename, file_path in zip_files:
        stats['zips_processed'] += 1
        print(f'\n[{stats["zips_processed"]}/{len(zip_files)}] Extracting: {filename}')

        try:
            with zipfile.ZipFile(file_path, 'r') as zf:
                # List all files in ZIP
                file_list = zf.namelist()
                doc_files = [f for f in file_list if Path(f).suffix.lower() in doc_extensions]

                print(f'  Found {len(doc_files)} document(s) in ZIP')

                for doc_file in doc_files[:10]:  # Extract up to 10 docs per ZIP
                    try:
                        # Read document content
                        content = zf.read(doc_file)
                        file_size = len(content)

                        # Calculate checksum
                        checksum = hashlib.sha256(content).hexdigest()

                        # Determine file type
                        file_ext = Path(doc_file).suffix.lower()
                        file_type = file_ext[1:] if file_ext else 'unknown'

                        # Generate unique filename
                        doc_filename = Path(doc_file).name

                        # Save to supporting_docs directory
                        output_path = Path('supporting_docs') / dataset_id[:8] / doc_filename
                        output_path.parent.mkdir(parents=True, exist_ok=True)

                        with open(output_path, 'wb') as f:
                            f.write(content)

                        # Insert into supporting_documents table
                        doc_id = str(uuid.uuid4())
                        cursor.execute('''
                            INSERT INTO supporting_documents
                            (id, dataset_id, title, document_type, filename, file_path, file_size,
                             file_type, checksum, extracted_from_zip, is_processed, downloaded_at, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            doc_id,
                            dataset_id,
                            doc_filename,  # title
                            file_type,  # document_type
                            doc_filename,
                            str(output_path),
                            file_size,
                            file_type,
                            checksum,
                            data_file_id,  # extracted_from_zip
                            0,  # is_processed
                            datetime.utcnow(),  # downloaded_at
                            datetime.utcnow()  # created_at
                        ))

                        stats['docs_extracted'] += 1
                        stats['total_bytes'] += file_size

                        print(f'    ✓ {doc_filename} ({file_size/1024:.1f} KB, {file_type})')

                    except Exception as e:
                        print(f'    ✗ Error extracting {doc_file}: {e}')
                        continue

                conn.commit()

        except zipfile.BadZipFile:
            print(f'  ✗ Bad ZIP file')
            stats['errors'] += 1
        except Exception as e:
            print(f'  ✗ Error: {e}')
            stats['errors'] += 1

    conn.close()

    print('\n' + '=' * 60)
    print('Extraction Complete')
    print('=' * 60)
    print(f'ZIP files processed: {stats["zips_processed"]}')
    print(f'Documents extracted: {stats["docs_extracted"]}')
    print(f'Total size: {stats["total_bytes"]/1024/1024:.2f} MB')
    print(f'Errors: {stats["errors"]}')
    print('=' * 60)

if __name__ == '__main__':
    extract_supporting_documents()
