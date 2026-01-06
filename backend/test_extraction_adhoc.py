
import unittest
import json
import os
import sys
from pathlib import Path

# Clean up debug prints and path hacks
# The script is now in backend/, so 'src' is directly importable if backend/ is in path (which it is by default)

from infrastructure.etl.extractors.json_extractor import JSONExtractor
from domain.entities.resource import RemoteFileResource, WebFolderResource, APIDataResource

class TestResourceExtraction(unittest.TestCase):

    def setUp(self):
        self.extractor = JSONExtractor()
        self.test_file = "test_metadata_temp.json"
        
    def tearDown(self):
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    def test_extract_resources_from_online_resources(self):
        # Mock data mimicking UKCEH structure
        data = {
            "title": "Test Dataset",
            "abstract": "Abstract",
            "onlineResources": [
                {
                    "url": "https://data-package.ceh.ac.uk/data/123.zip",
                    "name": "Data Download",
                    "function": "download"
                },
                {
                    "url": "https://catalogue.ceh.ac.uk/datastore/eidchub/123",
                    "name": "Supporting Docs",
                    "function": "information"
                }
            ]
        }
        
        with open(self.test_file, 'w') as f:
            json.dump(data, f)
            
        resources = self.extractor.extract_resources(self.test_file)
        
        self.assertEqual(len(resources), 2)
        
        # Check first resource (ZIP)
        self.assertIsInstance(resources[0], RemoteFileResource)
        self.assertEqual(resources[0].url, "https://data-package.ceh.ac.uk/data/123.zip")
        self.assertEqual(resources[0].resource_type, "file")
        
        # Check second resource (Folder)
        self.assertIsInstance(resources[1], WebFolderResource)
        self.assertEqual(resources[1].url, "https://catalogue.ceh.ac.uk/datastore/eidchub/123")
        self.assertEqual(resources[1].resource_type, "folder")
        
    def test_extract_resources_fallback_download_url(self):
        # Mock data with legacy downloadUrl
        data = {
            "title": "Legacy Dataset",
            "abstract": "Abstract",
            "downloadUrl": "https://example.com/legacy.zip"
        }
        
        with open(self.test_file, 'w') as f:
            json.dump(data, f)
            
        resources = self.extractor.extract_resources(self.test_file)
        
        self.assertEqual(len(resources), 1)
        self.assertIsInstance(resources[0], RemoteFileResource)
        self.assertEqual(resources[0].url, "https://example.com/legacy.zip")

if __name__ == '__main__':
    unittest.main()
