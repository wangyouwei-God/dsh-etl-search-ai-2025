#!/usr/bin/env python3
"""
Project Structure Setup Script
Dataset Search and Discovery Solution - University of Manchester

This script automatically creates the entire folder structure following Clean Architecture principles.
It creates all directories and __init__.py files for the project.

Usage:
    python setup_project.py
"""

import os
from pathlib import Path
from typing import List, Dict


class ProjectStructureBuilder:
    """Builds the complete project directory structure following Clean Architecture."""

    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.created_dirs: List[Path] = []
        self.created_files: List[Path] = []

    def get_structure(self) -> Dict[str, list]:
        """
        Returns the complete directory structure.
        Key: directory path, Value: list of files to create in that directory
        """
        return {
            # Root level
            "": ["README.md"],
            "docs": ["architecture.md", "api-specification.md"],

            # Backend structure
            "backend/src": ["__init__.py"],

            # Domain layer (innermost - no dependencies)
            "backend/src/domain": ["__init__.py"],
            "backend/src/domain/entities": [
                "__init__.py",
                "dataset.py",
                "metadata.py",
                "search_result.py"
            ],
            "backend/src/domain/value_objects": [
                "__init__.py",
                "dataset_id.py",
                "embedding_vector.py",
                "iso_metadata_fields.py"
            ],
            "backend/src/domain/repositories": [
                "__init__.py",
                "dataset_repository.py",
                "vector_repository.py"
            ],
            "backend/src/domain/services": [
                "__init__.py",
                "metadata_validator.py",
                "iso19115_validator.py"
            ],
            "backend/src/domain/exceptions": [
                "__init__.py",
                "domain_exceptions.py"
            ],

            # Application layer
            "backend/src/application": ["__init__.py"],
            "backend/src/application/use_cases": [
                "__init__.py",
                "ingest_dataset.py",
                "search_datasets.py",
                "semantic_search.py",
                "get_dataset_details.py"
            ],
            "backend/src/application/interfaces": [
                "__init__.py",
                "metadata_extractor.py",
                "embedding_service.py",
                "logger.py"
            ],
            "backend/src/application/dto": [
                "__init__.py",
                "dataset_dto.py",
                "search_request_dto.py"
            ],

            # Infrastructure layer (outermost)
            "backend/src/infrastructure": ["__init__.py"],

            # Persistence
            "backend/src/infrastructure/persistence": ["__init__.py"],
            "backend/src/infrastructure/persistence/sqlite": [
                "__init__.py",
                "dataset_repository_impl.py",
                "models.py",
                "connection.py"
            ],
            "backend/src/infrastructure/persistence/migrations": ["__init__.py"],

            # ETL subsystem
            "backend/src/infrastructure/etl": ["__init__.py"],
            "backend/src/infrastructure/etl/extractors": [
                "__init__.py",
                "base_extractor.py",
                "json_extractor.py",
                "xml_extractor.py"
            ],
            "backend/src/infrastructure/etl/factory": [
                "__init__.py",
                "extractor_factory.py"
            ],
            "backend/src/infrastructure/etl/transformers": [
                "__init__.py",
                "metadata_transformer.py"
            ],
            "backend/src/infrastructure/etl/loaders": [
                "__init__.py",
                "dataset_loader.py"
            ],

            # Vector database
            "backend/src/infrastructure/vector_db": [
                "__init__.py",
                "vector_repository_impl.py",
                "embedding_service_impl.py"
            ],

            # External services
            "backend/src/infrastructure/external": [
                "__init__.py",
                "http_client.py"
            ],

            # Logging
            "backend/src/infrastructure/logging": [
                "__init__.py",
                "logger_impl.py"
            ],

            # API layer (Interface Adapters)
            "backend/src/api": ["__init__.py"],
            "backend/src/api/rest": [
                "__init__.py",
                "main.py"
            ],
            "backend/src/api/rest/routes": [
                "__init__.py",
                "datasets.py",
                "search.py",
                "health.py"
            ],
            "backend/src/api/rest/schemas": [
                "__init__.py",
                "request_schemas.py"
            ],
            "backend/src/api/rest/dependencies": [
                "__init__.py",
                "container.py"
            ],
            "backend/src/api/cli": [
                "__init__.py",
                "commands.py"
            ],
            "backend/src/api/middleware": [
                "__init__.py",
                "error_handler.py",
                "cors.py"
            ],

            # Tests
            "backend/tests": ["__init__.py"],
            "backend/tests/unit": ["__init__.py"],
            "backend/tests/unit/domain": ["__init__.py"],
            "backend/tests/unit/application": ["__init__.py"],
            "backend/tests/unit/infrastructure": ["__init__.py"],
            "backend/tests/integration": ["__init__.py"],
            "backend/tests/e2e": ["__init__.py"],

            # Backend config files (at backend root)
            "backend": [
                "requirements.txt",
                "requirements-dev.txt",
                "pyproject.toml"
            ],

            # Frontend structure
            "frontend/src": [],
            "frontend/src/lib": [],
            "frontend/src/lib/api": [],
            "frontend/src/lib/stores": [],
            "frontend/src/lib/types": [],
            "frontend/src/lib/utils": [],
            "frontend/src/routes": ["+page.svelte"],
            "frontend/src/routes/datasets/[id]": ["+page.svelte"],
            "frontend/src/components": [
                "SearchBar.svelte",
                "DatasetCard.svelte",
                "MetadataViewer.svelte"
            ],
            "frontend/static": [],
            "frontend/tests": [],
            "frontend": [
                "package.json",
                "tsconfig.json",
                "svelte.config.js"
            ],

            # Docker
            "docker": [
                "Dockerfile.backend",
                "Dockerfile.frontend",
                "docker-compose.yml"
            ],
        }

    def create_directory(self, dir_path: Path) -> None:
        """Create a directory if it doesn't exist."""
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            self.created_dirs.append(dir_path)
            print(f"✓ Created directory: {dir_path}")
        else:
            print(f"  Already exists: {dir_path}")

    def create_file(self, file_path: Path) -> None:
        """Create an empty file if it doesn't exist."""
        if not file_path.exists():
            file_path.touch()
            self.created_files.append(file_path)
            print(f"  ✓ Created file: {file_path}")
        else:
            print(f"    Skipped (exists): {file_path}")

    def build(self) -> None:
        """Build the entire project structure."""
        print("=" * 80)
        print("Dataset Search and Discovery Solution - Project Setup")
        print("University of Manchester")
        print("=" * 80)
        print()

        structure = self.get_structure()

        for directory, files in structure.items():
            # Create the directory
            dir_path = self.base_path / directory if directory else self.base_path
            self.create_directory(dir_path)

            # Create files in the directory
            for file_name in files:
                file_path = dir_path / file_name
                self.create_file(file_path)

        self.print_summary()

    def print_summary(self) -> None:
        """Print a summary of created items."""
        print()
        print("=" * 80)
        print("Setup Complete!")
        print("=" * 80)
        print(f"Directories created: {len(self.created_dirs)}")
        print(f"Files created: {len(self.created_files)}")
        print()
        print("Next steps:")
        print("1. Review the structure in your file explorer")
        print("2. Set up Python virtual environment:")
        print("   cd backend && python -m venv venv && source venv/bin/activate")
        print("3. Install dependencies (once requirements.txt is populated)")
        print("4. Start implementing domain entities and use cases")
        print()
        print("Architecture layers (dependency direction: outer → inner):")
        print("  API → Infrastructure → Application → Domain")
        print("=" * 80)


def main():
    """Main entry point."""
    # Get the project root (current directory where this script is located)
    script_dir = Path(__file__).parent
    project_root = script_dir  # Use current directory instead of subdirectory

    print(f"Setting up project at: {project_root.absolute()}")
    print()

    # Ask for confirmation
    response = input("Continue? (y/n): ").strip().lower()
    if response != 'y':
        print("Setup cancelled.")
        return

    # Build the structure
    builder = ProjectStructureBuilder(base_path=project_root)
    builder.build()


if __name__ == "__main__":
    main()
