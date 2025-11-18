"""
Infrastructure layer metadata handling.

This module provides file I/O operations for metadata persistence.
The Metadata class itself has been moved to vortex.models.metadata
following Clean Architecture principles.
"""

import json
import os
from dataclasses import asdict

from vortex.models.metadata import Metadata, default_serializer
from vortex.utils.utils import convert_date_strings_to_datetime


class MetadataHandler:
    def __init__(self, file_path):
        self.file_path = file_path
        self.metadata_file = os.path.join(
            os.path.dirname(file_path), f"{os.path.basename(file_path)}.json"
        )

    def set_metadata(self, new_metadata: Metadata):
        # Save the new metadata to the file (overwriting previous metadata)
        with open(self.metadata_file, "w") as json_file:
            json.dump(
                asdict(new_metadata), json_file, default=default_serializer, indent=2
            )

    def get_metadata(self) -> Metadata:
        with open(self.metadata_file, "r") as json_file:
            metadata_dict = json.load(json_file)
            metadata_dict = convert_date_strings_to_datetime(metadata_dict)
            return Metadata(**metadata_dict)


#
# # Example usage:
# file_path = '/path/to/your/file.txt'
#
# # Create a MetadataHandler instance
# metadata_handler = MetadataHandler(file_path)
#
# # Create a Metadata instance
# new_metadata = Metadata(author='John Doe', created_date='2024-02-03')
#
# # Set metadata
# metadata_handler.set_metadata(new_metadata)
#
# # Get metadata
# retrieved_metadata = metadata_handler.get_metadata()
# print(f"Retrieved metadata: {retrieved_metadata}")
