"""
Configuration Ingestion Script - Phase 1

Reads all configuration files from the configs/ directory,
parses them into module blocks, removes duplicates, and stores results.
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Set
from utils.parser import ConfigParser, ModuleBlock
from datetime import datetime


class ConfigIngestion:
    """Handles ingestion and storage of parsed configurations"""
    
    def __init__(self, config_dir: str = "configs", output_dir: str = "data/parsed", force: bool = False):
        self.config_dir = Path(config_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.parser = ConfigParser()
        self.force = force
        
        # Track unique modules (for duplicate detection)
        self.unique_modules: Dict[str, ModuleBlock] = {}
        self.module_signatures: Set[str] = set()
        
        # State tracking
        self.state_file = self.output_dir / "ingestion_state.json"
        self.processed_files: Dict[str, Dict] = self._load_state()
        
    def _generate_signature(self, module: ModuleBlock) -> str:
        """Generate unique signature for duplicate detection"""
        # Signature based on: path + index + normalized sub-lines
        sig_parts = [
            module.module_path,
            module.index or "",
            module.module_type.value,
            "\n".join(sorted(module.sub_lines))  # Sort for consistency
        ]
        return "|".join(sig_parts)
    
    def _load_state(self) -> Dict[str, Dict]:
        """Load previously processed files state"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                return state.get('processed_files', {})
            except Exception as e:
                print(f"⚠️  Warning: Could not load state file: {e}")
        return {}
    
    def _save_state(self):
        """Save state of processed files"""
        state = {
            'last_updated': datetime.now().isoformat(),
            'processed_files': self.processed_files
        }
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2)
    
    def _should_process_file(self, config_file: Path) -> bool:
        """Check if file should be processed based on modification time"""
        if self.force:
            return True
        
        file_key = config_file.name
        file_mtime = config_file.stat().st_mtime
        
        if file_key in self.processed_files:
            last_processed_mtime = self.processed_files[file_key].get('mtime', 0)
            if file_mtime <= last_processed_mtime:
                # File hasn't changed
                return False
        
        return True
    
    def _mark_file_processed(self, config_file: Path, modules_count: int):
        """Mark file as processed with current timestamp"""
        self.processed_files[config_file.name] = {
            'mtime': config_file.stat().st_mtime,
            'processed_at': datetime.now().isoformat(),
            'modules_count': modules_count
        }
    
    def _is_duplicate(self, module: ModuleBlock) -> bool:
        """Check if module is a duplicate"""
        signature = self._generate_signature(module)
        if signature in self.module_signatures:
            return True
        self.module_signatures.add(signature)
        
        # Store unique module with a unique key
        key = f"{module.module_path}_{module.index or 'no_index'}_{len(self.unique_modules)}"
        self.unique_modules[key] = module
        return False
    
    def read_config_files(self) -> List[str]:
        """Read all .txt and .cfg files from configs directory"""
        if not self.config_dir.exists():
            print(f"❌ Config directory not found: {self.config_dir}")
            return []
        
        config_files = []
        for ext in ['*.txt', '*.cfg', '*.conf']:
            config_files.extend(self.config_dir.glob(ext))
        
        return sorted(config_files)
    
    def ingest_all(self):
        """Main ingestion process"""
        print("=" * 60)
        print("Configuration Ingestion - Phase 1")
        if self.force:
            print("[FORCE MODE: Processing all files]")
        else:
            print("[INCREMENTAL MODE: Processing new/modified files only]")
        print("=" * 60)
        print()
        
        config_files = self.read_config_files()
        
        if not config_files:
            print(f"⚠️  No configuration files found in {self.config_dir}/")
            print(f"   Please add .txt, .cfg, or .conf files to the configs/ directory")
            return
        
        # Check which files need processing
        files_to_process = []
        skipped_files = []
        
        for config_file in config_files:
            if self._should_process_file(config_file):
                files_to_process.append(config_file)
            else:
                skipped_files.append(config_file)
        
        print(f"📂 Found {len(config_files)} configuration file(s)")
        if skipped_files:
            print(f"⏭️  Skipping {len(skipped_files)} unchanged file(s)")
        print(f"🔄 Processing {len(files_to_process)} file(s)")
        print()
        
        if not files_to_process:
            print("✅ All files are up to date. Use --force to reprocess all files.")
            return
        
        total_modules = 0
        duplicates_found = 0
        
        for config_file in files_to_process:
            print(f"📄 Processing: {config_file.name}")
            
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_text = f.read()
                
                # Parse the configuration
                modules = self.parser.parse(config_text)
                
                # Check for duplicates
                before_count = len(self.unique_modules)
                for module in modules:
                    if self._is_duplicate(module):
                        duplicates_found += 1
                
                after_count = len(self.unique_modules)
                unique_from_file = after_count - before_count
                
                print(f"   ✓ Parsed {len(modules)} modules ({unique_from_file} unique, "
                      f"{len(modules) - unique_from_file} duplicates)")
                total_modules += len(modules)
                
                # Mark as processed
                self._mark_file_processed(config_file, len(modules))
                
            except Exception as e:
                print(f"   ❌ Error parsing {config_file.name}: {e}")
        
        print()
        print("=" * 60)
        print("Summary")
        print("=" * 60)
        print(f"Files processed:          {len(files_to_process)}")
        print(f"Files skipped:            {len(skipped_files)}")
        print(f"Total modules parsed:     {total_modules}")
        print(f"Unique modules:           {len(self.unique_modules)}")
        print(f"Duplicates removed:       {duplicates_found}")
        print()
        
        # Save results and state
        self._save_results()
        self._save_state()
        print(f"💾 State saved to: {self.state_file}")
        print()
    
    def _save_results(self):
        """Save parsed modules to JSON file"""
        output_file = self.output_dir / f"parsed_modules_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # Convert modules to serializable format
        modules_data = []
        for key, module in self.unique_modules.items():
            modules_data.append({
                "module_path": module.module_path,
                "index": module.index,
                "module_type": module.module_type.value,
                "sub_lines": module.sub_lines,
                "raw_lines": module.raw_lines,
                "multiline_content": module.multiline_content,
                "multiline_metadata": module.multiline_metadata,
                "action_params": module.action_params,
                "start_line": module.start_line,
                "end_line": module.end_line,
                "form_factor": module.form_factor,
                "hypervisor_support": module.hypervisor_support
            })
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "total_unique_modules": len(self.unique_modules),
                    "phase": "1 - Parsing"
                },
                "modules": modules_data
            }, f, indent=2)
        
        print(f"💾 Saved parsed modules to: {output_file}")
        print()
    
    def get_statistics(self) -> Dict:
        """Get statistics about parsed modules"""
        stats = {
            "total_unique": len(self.unique_modules),
            "by_type": {},
            "by_path": {}
        }
        
        for module in self.unique_modules.values():
            # Count by type
            module_type = module.module_type.value
            stats["by_type"][module_type] = stats["by_type"].get(module_type, 0) + 1
            
            # Count by path (top-level)
            path_parts = module.module_path.split('/')
            if len(path_parts) > 2:
                top_path = '/'.join(path_parts[:3])
                stats["by_path"][top_path] = stats["by_path"].get(top_path, 0) + 1
        
        return stats


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Phase 1: Parse configuration files into modules',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ingest_configs.py              # Process only new/modified files
  python ingest_configs.py --force      # Reprocess all files
        """
    )
    parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Force reprocessing of all config files (default: process only new/modified files)'
    )
    
    args = parser.parse_args()
    
    ingestion = ConfigIngestion(force=args.force)
    ingestion.ingest_all()
    
    # Display statistics
    stats = ingestion.get_statistics()
    print("📊 Module Statistics")
    print("=" * 60)
    print("\nBy Type:")
    for mod_type, count in sorted(stats["by_type"].items()):
        print(f"  {mod_type:20s}: {count:4d}")
    
    print("\nBy Top-Level Path (top 10):")
    sorted_paths = sorted(stats["by_path"].items(), key=lambda x: x[1], reverse=True)[:10]
    for path, count in sorted_paths:
        print(f"  {path:30s}: {count:4d}")
    print()


if __name__ == "__main__":
    main()
