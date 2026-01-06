#!/usr/bin/env python3
"""
Extract download URLs and landing page URLs from existing XML documents
and update the database.
"""

import sqlite3
from lxml import etree
import sys

def extract_urls():
    """Extract URLs from all metadata XML documents."""
    conn = sqlite3.connect('datasets.db')
    cursor = conn.cursor()

    # Get all datasets with XML
    cursor.execute('SELECT id, dataset_id, raw_document_xml FROM metadata WHERE raw_document_xml IS NOT NULL')
    rows = cursor.fetchall()

    print(f'Processing {len(rows)} datasets to extract URLs...')
    print('=' * 60)

    stats = {
        'total': len(rows),
        'with_download': 0,
        'with_landing': 0,
        'with_both': 0,
        'errors': 0
    }

    ns = {
        'gmd': 'http://www.isotc211.org/2005/gmd',
        'gco': 'http://www.isotc211.org/2005/gco'
    }

    for idx, row in enumerate(rows, 1):
        metadata_id, dataset_id, raw_xml = row

        if not raw_xml:
            continue

        try:
            root = etree.fromstring(raw_xml.encode('utf-8'))

            # Extract online resources
            xpath = './/gmd:distributionInfo//gmd:onLine//gmd:CI_OnlineResource'
            resources = root.xpath(xpath, namespaces=ns)

            download_url = ''
            landing_url = ''

            # Categorize URLs by function code
            for resource in resources:
                url_elem = resource.xpath('.//gmd:linkage//gmd:URL', namespaces=ns)
                function_elem = resource.xpath('.//gmd:function//gmd:CI_OnLineFunctionCode', namespaces=ns)

                if url_elem and len(url_elem) > 0:
                    url = url_elem[0].text
                    if not url:
                        continue

                    function_code = ''
                    if function_elem and len(function_elem) > 0:
                        function_code = function_elem[0].get('codeListValue', '').lower()

                    # Prioritize download URLs
                    if 'download' in function_code or url.endswith('.zip'):
                        if not download_url:  # Use first download URL found
                            download_url = url
                    elif 'information' in function_code:
                        if not landing_url:
                            landing_url = url
                    elif not landing_url and url.startswith('http'):
                        # Fallback: any HTTP URL can be landing page
                        landing_url = url

            # Update statistics
            if download_url:
                stats['with_download'] += 1
            if landing_url:
                stats['with_landing'] += 1
            if download_url and landing_url:
                stats['with_both'] += 1

            # Update database
            cursor.execute(
                'UPDATE metadata SET download_url = ?, landing_page_url = ? WHERE id = ?',
                (download_url or None, landing_url or None, metadata_id)
            )

            if idx % 50 == 0:
                print(f'Processed {idx}/{stats["total"]} datasets...')

        except Exception as e:
            print(f'Error processing dataset {dataset_id}: {e}')
            stats['errors'] += 1
            continue

    conn.commit()
    conn.close()

    print('=' * 60)
    print('URL Extraction Complete')
    print('=' * 60)
    print(f'Total datasets: {stats["total"]}')
    print(f'With download URL: {stats["with_download"]} ({stats["with_download"]/stats["total"]*100:.1f}%)')
    print(f'With landing page URL: {stats["with_landing"]} ({stats["with_landing"]/stats["total"]*100:.1f}%)')
    print(f'With both URLs: {stats["with_both"]} ({stats["with_both"]/stats["total"]*100:.1f}%)')
    print(f'Errors: {stats["errors"]}')
    print('=' * 60)

if __name__ == '__main__':
    extract_urls()
