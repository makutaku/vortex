#!/usr/bin/env python3
"""
Import update script for Clean Architecture migration.

This script helps update import statements after the package restructuring
to use the new Clean Architecture paths.
"""

import re
import os
from pathlib import Path
from typing import Dict, List, Tuple


class ImportUpdater:
    """Updates import statements to match new Clean Architecture structure."""
    
    # Mapping of old import paths to new paths
    IMPORT_MAPPINGS = {
        # Instruments moved to core/models
        'from vortex.core.models.instruments': 'from vortex.core.models.instruments',
        'import vortex.core.models.instruments': 'import vortex.core.models.instruments',
        
        # Downloaders moved to core/services  
        'from vortex.core.services.downloaders': 'from vortex.core.services.downloaders',
        'import vortex.core.services.downloaders': 'import vortex.core.services.downloaders',
        
        # Data providers moved to infrastructure/providers
        'from vortex.infrastructure.providers.data_providers': 'from vortex.infrastructure.providers.data_providers',
        'import vortex.infrastructure.providers.data_providers': 'import vortex.infrastructure.providers.data_providers',
        
        # Data storage moved to infrastructure/storage
        'from vortex.infrastructure.storage.data_storage': 'from vortex.infrastructure.storage.data_storage',
        'import vortex.infrastructure.storage.data_storage': 'import vortex.infrastructure.storage.data_storage',
        
        # CLI moved to application
        'from vortex.application.cli': 'from vortex.application.cli',
        'import vortex.application.cli': 'import vortex.application.cli',
        
        # Plugins moved to infrastructure
        'from vortex.infrastructure.plugins': 'from vortex.infrastructure.plugins',
        'import vortex.infrastructure.plugins': 'import vortex.infrastructure.plugins',
        
        # Shared modules
        'from vortex.shared.exceptions': 'from vortex.shared.exceptions',
        'import vortex.shared.exceptions': 'import vortex.shared.exceptions',
        'from vortex.shared.logging': 'from vortex.shared.logging',
        'import vortex.shared.logging': 'import vortex.shared.logging',
        'from vortex.shared.resilience': 'from vortex.shared.resilience',
        'import vortex.shared.resilience': 'import vortex.shared.resilience',
        'from vortex.shared.utils': 'from vortex.shared.utils',
        'import vortex.shared.utils': 'import vortex.shared.utils',
    }
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.updated_files: List[Path] = []
        self.errors: List[Tuple[Path, str]] = []
    
    def update_file(self, file_path: Path) -> bool:
        """Update imports in a single file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Apply import mappings
            for old_import, new_import in self.IMPORT_MAPPINGS.items():
                content = content.replace(old_import, new_import)
            
            # Write back if changed
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.updated_files.append(file_path)
                return True
                
            return False
            
        except Exception as e:
            self.errors.append((file_path, str(e)))
            return False
    
    def find_python_files(self) -> List[Path]:
        """Find all Python files in the project."""
        python_files = []
        
        # Search in source code
        src_dir = self.project_root / 'src'
        if src_dir.exists():
            python_files.extend(src_dir.rglob('*.py'))
        
        # Search in tests
        tests_dir = self.project_root / 'tests'
        if tests_dir.exists():
            python_files.extend(tests_dir.rglob('*.py'))
        
        # Search in scripts
        scripts_dir = self.project_root / 'scripts'
        if scripts_dir.exists():
            python_files.extend(scripts_dir.rglob('*.py'))
        
        return python_files
    
    def update_all_imports(self) -> None:
        """Update imports in all Python files."""
        print("🔍 Finding Python files...")
        python_files = self.find_python_files()
        print(f"Found {len(python_files)} Python files")
        
        print("\n📝 Updating import statements...")
        for file_path in python_files:
            if self.update_file(file_path):
                print(f"✅ Updated: {file_path.relative_to(self.project_root)}")
        
        print(f"\n📊 Summary:")
        print(f"  - Files updated: {len(self.updated_files)}")
        print(f"  - Errors: {len(self.errors)}")
        
        if self.errors:
            print("\n❌ Errors encountered:")
            for file_path, error in self.errors:
                print(f"  - {file_path.relative_to(self.project_root)}: {error}")
        
        if self.updated_files:
            print("\n✅ Successfully updated files:")
            for file_path in self.updated_files:
                print(f"  - {file_path.relative_to(self.project_root)}")


def main():
    """Main entry point for the import updater."""
    project_root = Path(__file__).parent.parent
    
    print("🏗️  Vortex Clean Architecture Import Updater")
    print("=" * 50)
    print(f"Project root: {project_root}")
    
    updater = ImportUpdater(project_root)
    updater.update_all_imports()
    
    print("\n🎉 Import update complete!")
    print("\nNext steps:")
    print("1. Run tests to verify imports work correctly")
    print("2. Check for any remaining import issues")
    print("3. Update documentation if needed")


if __name__ == "__main__":
    main()