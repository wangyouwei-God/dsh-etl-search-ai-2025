"""
Infrastructure: JSONExtractor

This module implements the metadata extraction strategy for JSON-formatted metadata files.
This is part of the Infrastructure layer and handles the technical details of
parsing JSON files and mapping them to domain entities.

Design Pattern: Strategy Pattern (Concrete Strategy)

Author: University of Manchester RSE Team
"""

import json
import os
import re
from datetime import datetime
from typing import Dict, Any, Optional, List
import sys

# Add the parent directory to the path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../../')))

from application.interfaces.metadata_extractor import (
    IMetadataExtractor,
    MetadataExtractionError,
    UnsupportedFormatError
)
from domain.entities.metadata import Metadata, BoundingBox, MetadataRelationship
from domain.entities.resource import Resource, RemoteFileResource, WebFolderResource, APIDataResource


class JSONExtractor(IMetadataExtractor):
    """
    Concrete implementation of IMetadataExtractor for JSON-formatted metadata.
    ...
    """

    def __init__(self, strict_mode: bool = False):
        """
        Initialize the JSON extractor.

        Args:
            strict_mode: If True, require all fields to be present.
                        If False, use defaults for missing optional fields.
        """
        self.strict_mode = strict_mode

    def extract_resources(self, source_path: str) -> List[Resource]:
        """
        Extract distribution resources from the JSON metadata.
        
        This implements the polymorphic resource extraction required by the task.
        """
        resources: List[Resource] = []
        
        try:
            with open(source_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check onlineResources (UKCEH specific)
            online_resources = data.get('onlineResources', [])
            if not online_resources:
                # Fallback: check 'distribution' or 'downloadUrl'
                if 'downloadUrl' in data:
                    online_resources.append({'url': data['downloadUrl'], 'name': 'Direct Download', 'function': 'download'})
            
            for res in online_resources:
                url = res.get('url', '')
                if not url:
                    continue
                    
                name = res.get('name', 'Untitled Resource')
                desc = res.get('description', '')
                
                # Polymorphic creation logic
                # 1. Zip files -> RemoteFileResource
                if url.endswith('.zip') or res.get('function') == 'download':
                    resources.append(RemoteFileResource(url=url, title=name, description=desc))
                
                # 2. Datastore/Folders -> WebFolderResource
                elif '/datastore/' in url or url.endswith('/'):
                    resources.append(WebFolderResource(url=url, title=name, description=desc))
                
                # 3. API endpoints -> APIDataResource
                elif '/api/' in url or 'json' in url:
                    resources.append(APIDataResource(url=url, title=name, description=desc))
                
                # Default to RemoteFile for unknown types if likely a file
                else:
                    # Heuristic: assume it's a file if it has an extension
                    if '.' in url.split('/')[-1]:
                        resources.append(RemoteFileResource(url=url, title=name, description=desc))
        
        except Exception as e:
            # Log error but return what we found so far
            # In a real system, we might want to raise, but here we prioritize resilience
            print(f"Error extracting resources from {source_path}: {e}")
            
        return resources

    def extract(self, source_path: str) -> Metadata:
        """
        Extract metadata from a JSON file.

        Args:
            source_path: Path to the JSON metadata file

        Returns:
            Metadata: Validated metadata entity

        Raises:
            FileNotFoundError: If the source file doesn't exist
            MetadataExtractionError: If parsing or extraction fails
            ValueError: If metadata validation fails
        """
        # Validate file exists
        if not os.path.exists(source_path):
            raise FileNotFoundError(f"Metadata file not found: {source_path}")

        # Check if we can handle this file
        if not self.can_extract(source_path):
            raise UnsupportedFormatError(source_path, ["JSON"])

        try:
            # Read and parse JSON file
            with open(source_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Transform JSON data to Metadata entity
            metadata = self._transform_to_metadata(data)

            return metadata

        except json.JSONDecodeError as e:
            raise MetadataExtractionError(
                source_path,
                f"Invalid JSON format: {str(e)}"
            )
        except ValueError as e:
            # Re-raise validation errors from Metadata entity
            raise MetadataExtractionError(
                source_path,
                f"Metadata validation failed: {str(e)}"
            )
        except Exception as e:
            raise MetadataExtractionError(
                source_path,
                f"Unexpected error during extraction: {str(e)}"
            )

    def can_extract(self, source_path: str) -> bool:
        """
        Check if this extractor can handle the given file.

        Args:
            source_path: Path to the file to check

        Returns:
            bool: True if file has .json extension, False otherwise
        """
        return source_path.lower().endswith('.json')

    def get_supported_format(self) -> str:
        """
        Get the format name this extractor supports.

        Returns:
            str: 'JSON'
        """
        return 'JSON'

    def _transform_to_metadata(self, data: Dict[str, Any]) -> Metadata:
        """
        Transform raw JSON data into a Metadata domain entity.

        This is the core transformation logic that maps JSON structure to
        the domain model. It handles nested objects and optional fields.

        Args:
            data: Dictionary containing parsed JSON data

        Returns:
            Metadata: Validated metadata entity

        Raises:
            ValueError: If required fields are missing in strict mode
        """
        # Extract mandatory fields (CEH JSON uses 'description' for abstract)
        title = self._get_required_field(data, 'title')
        abstract = data.get('abstract') or data.get('description')
        if not abstract or (isinstance(abstract, str) and not abstract.strip()):
            abstract = self._get_required_field(data, 'abstract')

        # Extract optional fields with defaults
        keywords = self._extract_keywords(data)

        # Extract bounding box if present (CEH JSON uses boundingBoxes)
        bounding_box = self._extract_bounding_box(
            data.get('bounding_box') or data.get('boundingBoxes')
        )

        # Extract temporal extent
        temporal_start, temporal_end = self._extract_temporal_extent(data)

        # Extract contact information
        contact_organization, contact_email = self._extract_contact(data)

        # Extract metadata date
        metadata_date = self._parse_datetime(
            data.get('metadata_date') or data.get('metadataDate')
        )
        if metadata_date is None:
            metadata_date = datetime.utcnow()

        # Extract language (ISO 639-2 code)
        dataset_language = data.get('language', 'eng')

        # Extract topic category
        topic_category = self._extract_topic_category(data)

        # Extract distribution information
        download_url, landing_page_url, access_type = self._extract_distribution_info(data)

        # Extract relationships between metadata documents (JSON-specific)
        relationships = self._extract_relationships(data)

        # Create and return Metadata entity
        # The Metadata constructor will validate invariants
        return Metadata(
            title=title,
            abstract=abstract,
            keywords=keywords,
            bounding_box=bounding_box,
            temporal_extent_start=temporal_start,
            temporal_extent_end=temporal_end,
            contact_organization=contact_organization,
            contact_email=contact_email,
            metadata_date=metadata_date,
            dataset_language=dataset_language,
            topic_category=topic_category,
            download_url=download_url,
            landing_page_url=landing_page_url,
            access_type=access_type,
            relationships=relationships
        )

    def _get_required_field(self, data: Dict[str, Any], field_name: str) -> str:
        """
        Extract a required field from the data dictionary.

        Args:
            data: Source dictionary
            field_name: Name of the required field

        Returns:
            str: Field value

        Raises:
            ValueError: If field is missing and strict_mode is True
        """
        value = data.get(field_name)

        if value is None or (isinstance(value, str) and not value.strip()):
            if self.strict_mode:
                raise ValueError(f"Required field '{field_name}' is missing or empty")
            else:
                # Return a placeholder value in non-strict mode
                return f"[Missing {field_name}]"

        return str(value)

    def _extract_keywords(self, data: Dict[str, Any]) -> List[str]:
        """Extract keywords from CEH JSON or generic JSON."""
        keywords: List[str] = []

        # Generic keywords field
        raw = data.get('keywords')
        if isinstance(raw, list):
            keywords.extend([str(k) for k in raw if k])

        # CEH keyword lists
        for key in ('keywordsTheme', 'keywordsPlace', 'keywordsOther'):
            items = data.get(key, [])
            if not isinstance(items, list):
                continue
            for item in items:
                if isinstance(item, dict):
                    value = item.get('value') or item.get('label')
                    if value:
                        keywords.append(str(value))
                elif item:
                    keywords.append(str(item))

        # De-duplicate while preserving order
        seen = set()
        deduped: List[str] = []
        for kw in keywords:
            if kw not in seen:
                deduped.append(kw)
                seen.add(kw)
        return deduped

    def _extract_temporal_extent(self, data: Dict[str, Any]) -> tuple[Optional[datetime], Optional[datetime]]:
        """Extract temporal extent from CEH JSON or generic JSON."""
        temporal = data.get('temporal_extent', {})
        if isinstance(temporal, dict):
            start = self._parse_datetime(temporal.get('start'))
            end = self._parse_datetime(temporal.get('end'))
            if start or end:
                return start, end

        extents = data.get('temporalExtents', [])
        if isinstance(extents, list) and extents:
            first = extents[0]
            if isinstance(first, dict):
                start = self._parse_datetime(first.get('begin'))
                end = self._parse_datetime(first.get('end'))
                return start, end

        return None, None

    def _extract_contact(self, data: Dict[str, Any]) -> tuple[str, str]:
        """Extract contact organization/email from CEH JSON or generic JSON."""
        contact = data.get('contact', {})
        if isinstance(contact, dict):
            org = contact.get('organization', '') or contact.get('organisation', '')
            email = contact.get('email', '')
            if org or email:
                return org, email

        for key in ('pointsOfContact', 'distributorContacts'):
            contacts = data.get(key, [])
            if isinstance(contacts, list) and contacts:
                first = contacts[0]
                if isinstance(first, dict):
                    org = first.get('organisationName', '') or first.get('organizationName', '')
                    email = first.get('email', '')
                    return org, email

        return "", ""

    def _extract_distribution_info(self, data: Dict[str, Any]) -> tuple[str, str, str]:
        """
        Extract download URL, landing page URL, and access type from CEH JSON.

        Returns:
            Tuple of (download_url, landing_page_url, access_type)
        """
        download_url = ""
        landing_page_url = ""
        access_type = "download"

        download_candidates = []
        detected_access_types = []

        def is_supporting_resource(url: str, name: str, func: str) -> bool:
            name_l = (name or "").lower()
            func_l = (func or "").lower()
            if "support" in name_l or "supporting" in name_l:
                return True
            if "/sd/" in url:
                return True
            if func_l == "information" and url.endswith(".zip"):
                return True
            return False

        def add_download_candidate(url: str, func: str, name: str) -> None:
            if not url:
                return
            func_l = (func or "").lower()
            name_l = (name or "").lower()

            if func_l == "fileaccess":
                detected_access_types.append("fileAccess")
            elif func_l == "download":
                detected_access_types.append("download")

            if is_supporting_resource(url, name, func):
                return

            is_datastore = "datastore/eidchub" in url
            is_data_package = "data-package.ceh.ac.uk/data" in url
            is_zip = url.endswith(".zip")
            is_download = "download" in func_l or "download" in name_l
            is_file_access = func_l == "fileaccess"

            priority = 0
            if (is_download or is_file_access) and (is_datastore or is_data_package):
                priority = 3
            elif is_datastore or is_data_package:
                priority = 2
            elif is_download or is_file_access:
                priority = 1
            elif is_zip:
                priority = 1

            if priority > 0:
                download_candidates.append((priority, url, func_l))

        online_resources = data.get("onlineResources") or []
        info_links = data.get("infoLinks") or []

        for res in online_resources:
            if not isinstance(res, dict):
                continue
            url = (res.get("url") or "").strip()
            add_download_candidate(url, res.get("function", ""), res.get("name", ""))

        direct_download = data.get("downloadUrl") or data.get("downloadURL") or data.get("download_url")
        if isinstance(direct_download, str):
            add_download_candidate(direct_download.strip(), "download", "download")

        if download_candidates:
            download_candidates.sort(key=lambda x: x[0], reverse=True)
            download_url = download_candidates[0][1]

        if "fileAccess" in detected_access_types:
            access_type = "fileAccess"

        landing_page_url = data.get("uri") or data.get("landing_page_url") or ""
        if not landing_page_url:
            for res in info_links + online_resources:
                if not isinstance(res, dict):
                    continue
                url = (res.get("url") or "").strip()
                if not url:
                    continue
                func_l = (res.get("function") or "").lower()
                name_l = (res.get("name") or "").lower()
                if func_l == "information" or "information" in name_l:
                    if not url.endswith(".zip"):
                        landing_page_url = url
                        break
                if "catalogue.ceh.ac.uk" in url and not url.endswith(".zip"):
                    landing_page_url = url
                    break

        return download_url, landing_page_url, access_type

    def _extract_relationships(self, data: Dict[str, Any]) -> List[MetadataRelationship]:
        """
        Extract metadata relationships from CEH JSON.

        Expected structure:
            "relationships": [{"relation": "<uri>", "target": "<uuid|url>"}]
        """
        relationships: List[MetadataRelationship] = []
        raw_relationships = data.get("relationships") or []
        if not isinstance(raw_relationships, list):
            return relationships

        for item in raw_relationships:
            if not isinstance(item, dict):
                continue
            relation = (item.get("relation") or item.get("predicate") or "").strip()
            if not relation:
                continue

            target = item.get("target") or item.get("object") or item.get("identifier")
            targets = target if isinstance(target, list) else [target]

            for target_item in targets:
                target_value = self._normalize_target(target_item)
                if not target_value:
                    continue
                target_id = self._extract_target_id(target_value)
                target_url = target_value if target_value.startswith(("http://", "https://")) else ""
                relationships.append(
                    MetadataRelationship(
                        relation=relation,
                        target=target_value,
                        target_id=target_id,
                        target_url=target_url
                    )
                )

        return relationships

    def _normalize_target(self, target: Any) -> str:
        """Normalize relationship target into a string identifier or URL."""
        if target is None:
            return ""
        if isinstance(target, dict):
            for key in ("id", "uuid", "identifier", "uri", "url", "href"):
                value = target.get(key)
                if value:
                    return str(value).strip()
            return ""
        return str(target).strip()

    def _extract_target_id(self, target: str) -> str:
        """Extract UUID from a target string or URL if present."""
        if self._looks_like_uuid(target):
            return target
        if target.startswith(("http://", "https://")):
            parts = target.rstrip("/").split("/")
            if parts:
                candidate = parts[-1]
                if self._looks_like_uuid(candidate):
                    return candidate
        return ""

    def _looks_like_uuid(self, value: str) -> bool:
        """Check if value matches UUID format."""
        return bool(re.fullmatch(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", value))

    def _extract_topic_category(self, data: Dict[str, Any]) -> str:
        """Extract topic category from CEH JSON or generic JSON."""
        if 'topic_category' in data:
            return data.get('topic_category', '')

        topics = data.get('topicCategories', [])
        if isinstance(topics, list) and topics:
            first = topics[0]
            if isinstance(first, dict):
                return first.get('value', '') or first.get('label', '')
            return str(first)

        return ""

    def _extract_bounding_box(self, bbox_data: Optional[Any]) -> Optional[BoundingBox]:
        """
        Extract and validate a bounding box from JSON data.

        Args:
            bbox_data: Dictionary or list containing bounding box coordinates

        Returns:
            BoundingBox or None if data is not provided

        Raises:
            ValueError: If bounding box data is invalid
        """
        if bbox_data is None:
            return None

        try:
            if isinstance(bbox_data, list) and bbox_data:
                bbox_data = bbox_data[0]

            if not isinstance(bbox_data, dict):
                return None

            # Support both verbose and short field names
            west = bbox_data.get('west', bbox_data.get('west_longitude', bbox_data.get('westBoundLongitude')))
            east = bbox_data.get('east', bbox_data.get('east_longitude', bbox_data.get('eastBoundLongitude')))
            south = bbox_data.get('south', bbox_data.get('south_latitude', bbox_data.get('southBoundLatitude')))
            north = bbox_data.get('north', bbox_data.get('north_latitude', bbox_data.get('northBoundLatitude')))

            if any(coord is None for coord in [west, east, south, north]):
                if self.strict_mode:
                    raise ValueError("Incomplete bounding box coordinates")
                return None

            # BoundingBox constructor will validate the coordinates
            return BoundingBox(
                west_longitude=float(west),
                east_longitude=float(east),
                south_latitude=float(south),
                north_latitude=float(north)
            )

        except (TypeError, ValueError) as e:
            if self.strict_mode:
                raise ValueError(f"Invalid bounding box data: {str(e)}")
            return None

    def _parse_datetime(self, date_str: Optional[str]) -> Optional[datetime]:
        """
        Parse a datetime string into a datetime object.

        Supports common ISO 8601 formats:
        - YYYY-MM-DD
        - YYYY-MM-DDTHH:MM:SS
        - YYYY-MM-DDTHH:MM:SSZ

        Args:
            date_str: ISO 8601 formatted date string

        Returns:
            datetime object or None if parsing fails or input is None
        """
        if date_str is None or not isinstance(date_str, str):
            return None

        try:
            # Try parsing with timezone info
            if date_str.endswith('Z'):
                date_str = date_str[:-1] + '+00:00'

            # Handle different datetime formats
            for fmt in [
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%dT%H:%M:%S.%f',
                '%Y-%m-%d',
            ]:
                try:
                    return datetime.strptime(date_str.split('+')[0].split('.')[0], fmt)
                except ValueError:
                    continue

            # If no format matched, return None
            return None

        except Exception:
            return None

    def __repr__(self) -> str:
        """Return string representation of the extractor."""
        mode = "strict" if self.strict_mode else "lenient"
        return f"JSONExtractor(mode={mode})"
