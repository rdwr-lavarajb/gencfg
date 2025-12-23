"""
Configuration Normalization Script - Phase 2 Main Orchestrator

Coordinates all Phase 2 components to transform parsed modules into templates.
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict
from collections import defaultdict

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import Phase 2 components
from phase2.value_extractor import ValueExtractor
from phase2.ai_analyzer import AIAnalyzer
from phase2.template_generator import TemplateGenerator
from phase2.default_calculator import DefaultCalculator


class ConfigNormalizer:
    """Main orchestrator for Phase 2"""
    
    def __init__(self, api_key: str = None, force: bool = False):
        """
        Initialize normalizer
        
        Args:
            api_key: OpenAI API key (or set OPENAI_API_KEY env var)
            force: Force regeneration of all templates (default: incremental)
        """
        self.value_extractor = ValueExtractor()
        self.ai_analyzer = AIAnalyzer(api_key)
        self.template_generator = TemplateGenerator()
        self.default_calculator = DefaultCalculator()
        self.force = force
        
        # State tracking
        self.templates_dir = Path("data/templates")
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.templates_dir / "template_state.json"
        self.processed_paths: Dict[str, Dict] = self._load_state()
        
        self.stats = {
            'modules_processed': 0,
            'templates_generated': 0,
            'ai_calls': 0,
            'tokens_used': 0,
            'errors': 0,
            'start_time': None,
            'end_time': None
        }
    
    def _load_state(self) -> Dict[str, Dict]:
        """Load previously processed module paths"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                return state.get('processed_paths', {})
            except Exception as e:
                print(f"⚠️  Warning: Could not load state file: {e}")
        return {}
    
    def _save_state(self):
        """Save state of processed module paths"""
        state = {
            'last_updated': datetime.now().isoformat(),
            'processed_paths': self.processed_paths
        }
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2)
    
    def _should_process_path(self, module_path: str, modules_count: int) -> bool:
        """Check if module path should be processed"""
        if self.force:
            return True
        
        if module_path in self.processed_paths:
            last_count = self.processed_paths[module_path].get('modules_count', 0)
            # Reprocess if module count changed (new instances added)
            if modules_count == last_count:
                return False
        
        return True
    
    def _mark_path_processed(self, module_path: str, modules_count: int):
        """Mark module path as processed"""
        self.processed_paths[module_path] = {
            'modules_count': modules_count,
            'processed_at': datetime.now().isoformat()
        }
    
    def normalize_from_file(self, input_file: str, output_dir: str = "data/templates"):
        """
        Main entry point: Load parsed modules and generate templates
        
        Args:
            input_file: Path to parsed modules JSON from Phase 1
            output_dir: Directory to save templated modules
        """
        print("=" * 70)
        print("Phase 2: Configuration Normalization & Templating")
        if self.force:
            print("[FORCE MODE: Regenerating all templates]")
        else:
            print("[INCREMENTAL MODE: Generating templates for new/modified modules only]")
        print("=" * 70)
        print()
        
        self.stats['start_time'] = datetime.now()
        
        # Load parsed modules
        print(f"📂 Loading parsed modules from: {input_file}")
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        modules = data.get('modules', [])
        print(f"✅ Loaded {len(modules)} parsed modules")
        print()
        
        # Group modules by path
        print("🔍 Grouping modules by path...")
        grouped_modules = self._group_modules_by_path(modules)
        print(f"✅ Found {len(grouped_modules)} unique module paths")
        
        # Check which paths need processing
        paths_to_process = {}
        skipped_paths = []
        
        for module_path, module_group in grouped_modules.items():
            if self._should_process_path(module_path, len(module_group)):
                paths_to_process[module_path] = module_group
            else:
                skipped_paths.append(module_path)
        
        if skipped_paths:
            print(f"⏭️  Skipping {len(skipped_paths)} unchanged module paths")
        print(f"🔄 Processing {len(paths_to_process)} module paths")
        print()
        
        if not paths_to_process:
            print("✅ All templates are up to date. Use --force to regenerate all templates.")
            return
        
        # Process each group
        templates = []
        for i, (module_path, module_group) in enumerate(paths_to_process.items(), 1):
            print(f"[{i}/{len(paths_to_process)}] Processing: {module_path} ({len(module_group)} instances)")
            
            try:
                template = self._process_module_group(module_path, module_group)
                templates.append(template)
                self._mark_path_processed(module_path, len(module_group))
                print(f"  ✅ Template generated")
            except Exception as e:
                print(f"  ❌ Error: {e}")
                self.stats['errors'] += 1
            
            print()
        
        self.stats['end_time'] = datetime.now()
        
        # Save results and state
        self._save_templates(templates, output_dir)
        self._save_state()
        print(f"💾 State saved to: {self.state_file}")
        print()
        
        # Print summary
        self._print_summary(len(skipped_paths))
    
    def _group_modules_by_path(self, modules: List[Dict]) -> Dict[str, List[Dict]]:
        """Group modules by their path"""
        grouped = defaultdict(list)
        
        for module in modules:
            path = module.get('module_path', '')
            if path:
                grouped[path].append(module)
                self.stats['modules_processed'] += 1
        
        return dict(grouped)
    
    def _process_module_group(self, module_path: str, modules: List[Dict]) -> Dict:
        """Process a group of modules with the same path"""
        
        # Step 1: Extract value patterns
        patterns = self.value_extractor.extract_patterns(modules)
        
        # Step 2: AI analysis
        ai_analysis = self.ai_analyzer.analyze_module_group(
            module_path=module_path,
            modules=modules,
            patterns=patterns
        )
        self.stats['ai_calls'] += 1
        self.stats['tokens_used'] += self.ai_analyzer.stats.get('tokens_used', 0)
        
        # Step 3: Generate template
        template = self.template_generator.generate_template(
            module_path=module_path,
            modules=modules,
            patterns=patterns,
            ai_analysis=ai_analysis
        )
        self.stats['templates_generated'] += 1
        
        # Step 4: Calculate defaults
        defaults = self.default_calculator.calculate_defaults(patterns)
        self.default_calculator.apply_defaults_to_template(template, defaults)
        
        # Add timestamp
        template.created_at = datetime.now().isoformat()
        
        return template.to_dict()
    
    def _save_templates(self, templates: List[Dict], output_dir: str):
        """Save templates to JSON file"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = output_path / f"templated_modules_{timestamp}.json"
        
        # Calculate processing time
        processing_time = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        
        # Build output data
        output_data = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "phase": "2 - Templating & Normalization",
                "total_templates": len(templates),
                "total_instances_analyzed": self.stats['modules_processed'],
                "ai_model": "gpt-4-turbo",
                "ai_calls_made": self.stats['ai_calls'],
                "tokens_used": self.stats['tokens_used'],
                "processing_time_seconds": round(processing_time, 2),
                "errors": self.stats['errors']
            },
            "templates": templates
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2)
        
        print("=" * 70)
        print(f"💾 Templates saved to: {output_file}")
        print("=" * 70)
    
    def _print_summary(self, skipped_count: int = 0):
        """Print processing summary"""
        processing_time = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        
        print()
        print("=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"Modules Processed:       {self.stats['modules_processed']}")
        print(f"Templates Generated:     {self.stats['templates_generated']}")
        print(f"Templates Skipped:       {skipped_count}")
        print(f"AI Calls Made:           {self.stats['ai_calls']}")
        print(f"Tokens Used:             {self.stats['tokens_used']:,}")
        print(f"Errors:                  {self.stats['errors']}")
        print(f"Processing Time:         {processing_time:.2f} seconds")
        print()
        
        # Component stats
        print("Component Statistics:")
        print(f"  ValueExtractor:        {self.value_extractor.stats}")
        print(f"  AIAnalyzer:            {self.ai_analyzer.stats}")
        print(f"  TemplateGenerator:     {self.template_generator.stats}")
        print(f"  DefaultCalculator:     {self.default_calculator.stats}")
        print()
        
        # Cost estimation (rough)
        if self.stats['tokens_used'] > 0:
            # GPT-4-turbo pricing: ~$0.01/1K input, ~$0.03/1K output (estimate)
            estimated_cost = (self.stats['tokens_used'] / 1000) * 0.02  # Average
            print(f"Estimated Cost:          ~${estimated_cost:.2f}")
            print()


def main():
    """Main entry point"""
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Phase 2: Generate templates from parsed modules using AI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python normalize_configs.py              # Process only new/modified modules
  python normalize_configs.py --force      # Regenerate all templates
        """
    )
    parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Force regeneration of all templates (default: generate only for new/modified modules)'
    )
    
    args = parser.parse_args()
    
    # Check for API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ Error: OPENAI_API_KEY not set")
        print()
        print("Please run: python setup_env.py")
        print("Or set the environment variable manually")
        sys.exit(1)
    
    # Find most recent parsed modules file
    parsed_dir = Path("data/parsed")
    if not parsed_dir.exists():
        print("❌ Error: No parsed modules found")
        print()
        print("Please run Phase 1 first: python ingest_configs.py")
        sys.exit(1)
    
    parsed_files = sorted(parsed_dir.glob("parsed_modules_*.json"))
    if not parsed_files:
        print("❌ Error: No parsed modules files found in data/parsed/")
        print()
        print("Please run Phase 1 first: python ingest_configs.py")
        sys.exit(1)
    
    # Use most recent file
    input_file = parsed_files[-1]
    
    print("Using input file:", input_file)
    print()
    
    # Run normalization
    normalizer = ConfigNormalizer(api_key, force=args.force)
    normalizer.normalize_from_file(str(input_file))


if __name__ == "__main__":
    main()
