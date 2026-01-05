"""
Infrastructure: XMLExtractor

This module implements the metadata extraction strategy for XML-formatted
ISO 19115/19139 metadata files. ISO 19139 is the XML encoding schema for
ISO 19115 geographic metadata.

This is part of the Infrastructure layer and handles the technical details of
parsing XML with proper namespace handling.

Design Pattern: Strategy Pattern (Concrete Strategy)

Author: University of Manchester RSE Team
"""

import logging
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
import sys

logger = logging.getLogger(__name__)

from lxml import etree

# Add the parent directory to the path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../../')))

from application.interfaces.metadata_extractor import (
    IMetadataExtractor,
    MetadataExtractionError,
    UnsupportedFormatError
)
from domain.entities.metadata import Metadata, BoundingBox


class XMLExtractor(IMetadataExtractor):
    """
    Concrete implementation of IMetadataExtractor for ISO 19115/19139 XML metadata.

    ISO 19139 is the XML implementation of the ISO 19115 geographic information
    metadata standard. This extractor handles the complex namespace structure
    and XPath queries required to extract metadata elements.

    XML Namespaces handled:
        - gmd: http://www.isotc211.org/2005/gmd (Geographic MetaData)
        - gco: http://www.isotc211.org/2005/gco (Geographic Common Objects)
        - gml: http://www.opengis.net/gml/3.2 (Geography Markup Language)
        - gmx: http://www.isotc211.org/2005/gmx (Geographic Metadata XML)

    Strategy Pattern:
        - Implements the IMetadataExtractor interface
        - Provides XML-specific extraction logic with namespace handling
        - Can be swapped with JSONExtractor or other extractors

    Attributes:
        strict_mode: If True, raises errors for missing mandatory fields.
                    If False, uses default values for missing fields.
        namespaces: Dictionary of XML namespace prefixes and URIs

    Example ISO 19139 structure:
        <gmd:MD_Metadata>
          <gmd:identificationInfo>
            <gmd:MD_DataIdentification>
              <gmd:citation>
                <gmd:CI_Citation>
                  <gmd:title>
                    <gco:CharacterString>Dataset Title</gco:CharacterString>
                  </gmd:title>
                </gmd:CI_Citation>
              </gmd:citation>
              <gmd:abstract>
                <gco:CharacterString>Dataset abstract...</gco:CharacterString>
              </gmd:abstract>
            </gmd:MD_DataIdentification>
          </gmd:identificationInfo>
        </gmd:MD_Metadata>
    """

    # ISO 19139 XML namespaces
    NAMESPACES = {
        'gmd': 'http://www.isotc211.org/2005/gmd',
        'gco': 'http://www.isotc211.org/2005/gco',
        'gml': 'http://www.opengis.net/gml/3.2',
        'gml32': 'http://www.opengis.net/gml',  # Alternative GML namespace
        'gmx': 'http://www.isotc211.org/2005/gmx',
        'srv': 'http://www.isotc211.org/2005/srv',
        'xlink': 'http://www.w3.org/1999/xlink'
    }

    def __init__(self, strict_mode: bool = False):
        """
        Initialize the XML extractor.

        Args:
            strict_mode: If True, require all mandatory fields to be present.
                        If False, use defaults for missing optional fields.
        """
        self.strict_mode = strict_mode
        self.namespaces = self.NAMESPACES

    def extract(self, source_path: str) -> Metadata:
        """
        Extract metadata from an ISO 19139 XML file.

        Args:
            source_path: Path to the XML metadata file

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
            raise UnsupportedFormatError(source_path, ["XML"])

        try:
            # Parse XML file
            tree = etree.parse(source_path)
            root = tree.getroot()

            # Transform XML to Metadata entity
            metadata = self._transform_to_metadata(root)

            return metadata

        except etree.XMLSyntaxError as e:
            raise MetadataExtractionError(
                source_path,
                f"Invalid XML syntax: {str(e)}"
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
            bool: True if file has .xml extension, False otherwise
        """
        return source_path.lower().endswith('.xml')

    def get_supported_format(self) -> str:
        """
        Get the format name this extractor supports.

        Returns:
            str: 'XML (ISO 19139)'
        """
        return 'XML (ISO 19139)'

    def _transform_to_metadata(self, root: etree._Element) -> Metadata:
        """
        Transform XML root element into a Metadata domain entity.

        This method navigates the ISO 19139 XML structure using XPath queries
        with proper namespace handling to extract all metadata elements.

        Args:
            root: Root element of the parsed XML tree

        Returns:
            Metadata: Validated metadata entity

        Raises:
            ValueError: If required fields are missing in strict mode
        """
        # Extract mandatory fields
        title = self._extract_title(root)
        abstract = self._extract_abstract(root)

        # Extract optional fields
        keywords = self._extract_keywords(root)
        bounding_box = self._extract_bounding_box(root)
        temporal_start, temporal_end = self._extract_temporal_extent(root)
        contact_org, contact_email = self._extract_contact_info(root)
        metadata_date = self._extract_metadata_date(root)
        language = self._extract_language(root)
        topic_category = self._extract_topic_category(root)

        # Extract distribution info (now returns 3 values including access_type)
        download_url, landing_page_url, access_type = self._extract_distribution_info(root)

        # Create and return Metadata entity
        return Metadata(
            title=title,
            abstract=abstract,
            keywords=keywords,
            bounding_box=bounding_box,
            temporal_extent_start=temporal_start,
            temporal_extent_end=temporal_end,
            contact_organization=contact_org,
            contact_email=contact_email,
            metadata_date=metadata_date,
            dataset_language=language,
            topic_category=topic_category,
            download_url=download_url,
            landing_page_url=landing_page_url,
            access_type=access_type
        )

    def _extract_title(self, root: etree._Element) -> str:
        """
        Extract dataset title from XML.

        XPath: .//gmd:identificationInfo//gmd:citation//gmd:title/gco:CharacterString

        Args:
            root: XML root element

        Returns:
            str: Dataset title
        """
        # Try multiple XPath patterns for robustness
        xpath_patterns = [
            './/gmd:identificationInfo//gmd:citation//gmd:title/gco:CharacterString',
            './/gmd:identificationInfo//gmd:citation//gmd:title/gmx:Anchor',
            './/gmd:MD_DataIdentification/gmd:citation//gmd:title/gco:CharacterString'
        ]

        title = self._extract_text(root, xpath_patterns)

        if not title:
            if self.strict_mode:
                raise ValueError("Required field 'title' is missing")
            return "[Missing Title]"

        return title

    def _extract_abstract(self, root: etree._Element) -> str:
        """
        Extract dataset abstract from XML.

        XPath: .//gmd:identificationInfo//gmd:abstract/gco:CharacterString

        Args:
            root: XML root element

        Returns:
            str: Dataset abstract
        """
        xpath_patterns = [
            './/gmd:identificationInfo//gmd:abstract/gco:CharacterString',
            './/gmd:MD_DataIdentification/gmd:abstract/gco:CharacterString'
        ]

        abstract = self._extract_text(root, xpath_patterns)

        if not abstract:
            if self.strict_mode:
                raise ValueError("Required field 'abstract' is missing")
            return "[Missing Abstract]"

        return abstract

    def _extract_keywords(self, root: etree._Element) -> List[str]:
        """
        Extract keywords from XML.

        XPath: .//gmd:descriptiveKeywords//gmd:keyword/gco:CharacterString

        Args:
            root: XML root element

        Returns:
            List of keyword strings
        """
        keywords = []

        xpath_patterns = [
            './/gmd:descriptiveKeywords//gmd:keyword/gco:CharacterString',
            './/gmd:descriptiveKeywords//gmd:keyword/gmx:Anchor'
        ]

        for pattern in xpath_patterns:
            elements = root.xpath(pattern, namespaces=self.namespaces)
            for elem in elements:
                if elem.text and elem.text.strip():
                    keyword = elem.text.strip()
                    if keyword not in keywords:
                        keywords.append(keyword)

        return keywords

    def _extract_bounding_box(self, root: etree._Element) -> Optional[BoundingBox]:
        """
        Extract geographic bounding box from XML.

        XPath base: .//gmd:extent//gmd:EX_GeographicBoundingBox

        Args:
            root: XML root element

        Returns:
            BoundingBox or None if not present
        """
        try:
            # Find bounding box element
            bbox_xpath = './/gmd:extent//gmd:EX_GeographicBoundingBox'
            bbox_elements = root.xpath(bbox_xpath, namespaces=self.namespaces)

            if not bbox_elements:
                return None

            bbox_elem = bbox_elements[0]

            # Extract coordinates
            west = self._extract_decimal(
                bbox_elem,
                './/gmd:westBoundLongitude/gco:Decimal'
            )
            east = self._extract_decimal(
                bbox_elem,
                './/gmd:eastBoundLongitude/gco:Decimal'
            )
            south = self._extract_decimal(
                bbox_elem,
                './/gmd:southBoundLatitude/gco:Decimal'
            )
            north = self._extract_decimal(
                bbox_elem,
                './/gmd:northBoundLatitude/gco:Decimal'
            )

            if any(coord is None for coord in [west, east, south, north]):
                return None

            # BoundingBox constructor will validate
            return BoundingBox(
                west_longitude=west,
                east_longitude=east,
                south_latitude=south,
                north_latitude=north
            )

        except (ValueError, IndexError):
            return None

    def _extract_temporal_extent(
        self,
        root: etree._Element
    ) -> tuple[Optional[datetime], Optional[datetime]]:
        """
        Extract temporal extent (start and end dates) from XML.

        XPath: .//gmd:extent//gmd:EX_TemporalExtent

        Args:
            root: XML root element

        Returns:
            Tuple of (start_date, end_date), both may be None
        """
        try:
            # Extract start date
            start_xpath = './/gmd:extent//gml:TimePeriod/gml:beginPosition'
            start_elements = root.xpath(start_xpath, namespaces=self.namespaces)

            # Try alternative GML namespace
            if not start_elements:
                start_xpath = './/gmd:extent//gml32:TimePeriod/gml32:beginPosition'
                start_elements = root.xpath(start_xpath, namespaces=self.namespaces)

            start_date = None
            if start_elements and start_elements[0].text:
                start_date = self._parse_datetime(start_elements[0].text)

            # Extract end date
            end_xpath = './/gmd:extent//gml:TimePeriod/gml:endPosition'
            end_elements = root.xpath(end_xpath, namespaces=self.namespaces)

            # Try alternative GML namespace
            if not end_elements:
                end_xpath = './/gmd:extent//gml32:TimePeriod/gml32:endPosition'
                end_elements = root.xpath(end_xpath, namespaces=self.namespaces)

            end_date = None
            if end_elements and end_elements[0].text:
                end_date = self._parse_datetime(end_elements[0].text)

            return start_date, end_date

        except Exception:
            return None, None

    def _extract_contact_info(self, root: etree._Element) -> tuple[str, str]:
        """
        Extract contact organization and email from XML.

        XPath: .//gmd:contact//gmd:organisationName and .//gmd:electronicMailAddress

        Args:
            root: XML root element

        Returns:
            Tuple of (organization, email)
        """
        # Extract organization
        org_xpath = './/gmd:contact//gmd:organisationName/gco:CharacterString'
        organization = self._extract_text(root, [org_xpath]) or ""

        # Extract email
        email_xpath = './/gmd:contact//gmd:electronicMailAddress/gco:CharacterString'
        email = self._extract_text(root, [email_xpath]) or ""

        return organization, email

    def _extract_metadata_date(self, root: etree._Element) -> datetime:
        """
        Extract metadata date stamp from XML.

        XPath: .//gmd:dateStamp/gco:DateTime or .//gmd:dateStamp/gco:Date

        Args:
            root: XML root element

        Returns:
            datetime: Metadata date or current time if not found
        """
        xpath_patterns = [
            './/gmd:dateStamp/gco:DateTime',
            './/gmd:dateStamp/gco:Date'
        ]

        date_str = self._extract_text(root, xpath_patterns)

        if date_str:
            parsed_date = self._parse_datetime(date_str)
            if parsed_date:
                return parsed_date

        return datetime.utcnow()

    def _extract_language(self, root: etree._Element) -> str:
        """
        Extract dataset language from XML.

        XPath: .//gmd:identificationInfo//gmd:language/gco:CharacterString

        Args:
            root: XML root element

        Returns:
            str: ISO 639-2 language code (default: 'eng')
        """
        xpath_patterns = [
            './/gmd:identificationInfo//gmd:language/gco:CharacterString',
            './/gmd:identificationInfo//gmd:language/gmd:LanguageCode'
        ]

        language = self._extract_text(root, xpath_patterns)
        return language if language else 'eng'

    def _extract_topic_category(self, root: etree._Element) -> str:
        """
        Extract ISO 19115 topic category from XML.

        XPath: .//gmd:topicCategory/gmd:MD_TopicCategoryCode

        Args:
            root: XML root element

        Returns:
            str: Topic category code
        """
        xpath_pattern = './/gmd:topicCategory/gmd:MD_TopicCategoryCode'
        return self._extract_text(root, [xpath_pattern]) or ""

    def _extract_text(
        self,
        element: etree._Element,
        xpath_patterns: List[str]
    ) -> Optional[str]:
        """
        Extract text content from element using multiple XPath patterns.

        Tries each XPath pattern until one returns a result.

        Args:
            element: XML element to search within
            xpath_patterns: List of XPath patterns to try

        Returns:
            Extracted text or None if not found
        """
        for pattern in xpath_patterns:
            try:
                results = element.xpath(pattern, namespaces=self.namespaces)
                if results and results[0].text:
                    return results[0].text.strip()
            except Exception:
                continue

        return None

    def _extract_decimal(
        self,
        element: etree._Element,
        xpath_pattern: str
    ) -> Optional[float]:
        """
        Extract a decimal number from an element.

        Args:
            element: XML element to search within
            xpath_pattern: XPath pattern to use

        Returns:
            float value or None if not found or invalid
        """
        try:
            results = element.xpath(xpath_pattern, namespaces=self.namespaces)
            if results and results[0].text:
                return float(results[0].text.strip())
        except (ValueError, IndexError, AttributeError):
            pass

        return None

    def _parse_datetime(self, date_str: Optional[str]) -> Optional[datetime]:
        """
        Parse a datetime string into a datetime object.

        Supports ISO 8601 formats commonly found in ISO 19139:
        - YYYY-MM-DD
        - YYYY-MM-DDTHH:MM:SS
        - YYYY-MM-DDTHH:MM:SSZ
        - YYYY-MM-DDTHH:MM:SS.ffffff

        Args:
            date_str: ISO 8601 formatted date string

        Returns:
            datetime object or None if parsing fails
        """
        if not date_str or not isinstance(date_str, str):
            return None

        # Clean up the string
        date_str = date_str.strip()

        # Remove timezone indicator 'Z'
        if date_str.endswith('Z'):
            date_str = date_str[:-1]

        # Remove timezone offset (e.g., +00:00)
        if '+' in date_str:
            date_str = date_str.split('+')[0]

        # Try different datetime formats
        formats = [
            '%Y-%m-%dT%H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d',
            '%Y',  # Year only
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        return None

    def _extract_distribution_info(self, root: etree._Element) -> tuple[str, str, str]:
        """
        Extract download URL, landing page URL, and access type from XML.

        XPath: .//gmd:distributionInfo//gmd:onLine//gmd:CI_OnlineResource

        Access types (per PDF requirements):
        - "download": Dataset provided as ZIP file (most common)
        - "fileAccess": Dataset available through web-accessible folder
        
        Args:
            root: XML root element

        Returns:
            Tuple of (download_url, landing_page_url, access_type)
        """
        download_url = ""
        landing_page_url = ""
        access_type = "download"  # Default to download

        # XPath to find all online resources
        xpath = './/gmd:distributionInfo//gmd:onLine//gmd:CI_OnlineResource'
        resources = root.xpath(xpath, namespaces=self.namespaces)

        if not resources:
            return "", "", "download"

        # Track all candidate URLs and their function codes
        download_candidates = []
        landing_candidates = []
        detected_access_types = []

        for resource in resources:
            # Extract URL
            url_xpath = './/gmd:linkage/gmd:URL'
            urls = resource.xpath(url_xpath, namespaces=self.namespaces)
            if not urls or not urls[0].text:
                continue

            url = urls[0].text.strip()

            # Extract description/name
            name_xpath = './/gmd:name/gco:CharacterString'
            name_elems = resource.xpath(name_xpath, namespaces=self.namespaces)
            name = name_elems[0].text.strip() if name_elems and name_elems[0].text else ""

            # Extract function/role - this tells us download vs fileAccess
            # Codes: 'download', 'fileAccess', 'information', 'search', etc.
            func_xpath = './/gmd:function/gmd:CI_OnLineFunctionCode'
            funcs = resource.xpath(func_xpath, namespaces=self.namespaces)

            func_code = ""
            if funcs and 'codeListValue' in funcs[0].attrib:
                func_code = funcs[0].attrib['codeListValue']
            elif funcs and funcs[0].text:
                func_code = funcs[0].text.strip()

            # CRITICAL: Check for fileAccess access type
            if func_code.lower() == 'fileaccess':
                detected_access_types.append('fileAccess')
            elif func_code.lower() == 'download':
                detected_access_types.append('download')

            # ENHANCED: Check for CEH-specific patterns
            is_ceh_datastore = 'datastore/eidchub' in url or 'eidc/download' in url
            is_zip_file = url.endswith('.zip')
            is_download = 'download' in func_code.lower() or 'download' in name.lower()
            is_file_access = 'fileaccess' in func_code.lower()
            is_landing = 'information' in func_code.lower() or 'landing' in url or 'documents/' in url

            # Prioritize download URLs (both download and fileAccess point to data)
            if is_download or is_file_access or is_ceh_datastore or is_zip_file:
                priority = 0
                if (is_download or is_file_access) and is_ceh_datastore:
                    priority = 3  # Highest: explicit function + CEH datastore
                elif is_ceh_datastore:
                    priority = 2  # High: CEH datastore
                elif is_download or is_file_access:
                    priority = 1  # Medium: explicit function
                download_candidates.append((priority, url, func_code.lower()))

            # Track landing pages
            if is_landing or ('catalogue.ceh.ac.uk/documents/' in url):
                landing_candidates.append(url)

        # Determine access type from detected types
        if 'fileAccess' in detected_access_types:
            access_type = 'fileAccess'
        elif 'download' in detected_access_types:
            access_type = 'download'

        # Select best download URL (highest priority)
        if download_candidates:
            download_candidates.sort(key=lambda x: x[0], reverse=True)
            download_url = download_candidates[0][1]
            # Also check if the best candidate is fileAccess
            top_func = download_candidates[0][2] if len(download_candidates[0]) > 2 else ""
            if top_func == 'fileaccess':
                access_type = 'fileAccess'

        # Select landing page
        if landing_candidates:
            landing_page_url = landing_candidates[0]

        # FALLBACK: If no download URL found, check for fileIdentifier to construct CEH URL
        if not download_url:
            file_id_xpath = './/gmd:fileIdentifier/gco:CharacterString'
            file_ids = root.xpath(file_id_xpath, namespaces=self.namespaces)
            if file_ids and file_ids[0].text:
                file_id = file_ids[0].text.strip()
                # Construct potential CEH datastore URL
                download_url = f"https://catalogue.ceh.ac.uk/datastore/eidchub/{file_id}"
                # Note: constructed URLs could be either type - default to download

        # If no explicit landing page, use download URL if it's not a direct file
        if not landing_page_url and download_url and not download_url.endswith('.zip'):
            landing_page_url = download_url

        return download_url, landing_page_url, access_type

    def __repr__(self) -> str:
        """Return string representation of the extractor."""
        mode = "strict" if self.strict_mode else "lenient"
        return f"XMLExtractor(mode={mode})"
