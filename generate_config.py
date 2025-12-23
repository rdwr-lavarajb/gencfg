"""
Main script to generate configuration from natural language requirements.
End-to-end pipeline: Requirements → Retrieval → Assembly → Generation
"""

import argparse
import sys
from pathlib import Path
from typing import List, Dict, Any
import json

# Phase 3 imports
from phase3.vector_store import VectorStore
from phase3.embedding_generator import EmbeddingGenerator

# Phase 4 imports
from phase4.requirements_parser import RequirementsParser
from phase4.query_generator import QueryGenerator
from phase4.template_retriever import TemplateRetriever
from phase4.relevance_ranker import RelevanceRanker

# Phase 5 imports
from phase5.value_extractor import ValueExtractor
from phase5.parameter_matcher import ParameterMatcher
from phase5.template_assembler import TemplateAssembler
from phase5.dependency_resolver import DependencyResolver
from phase5.relationship_manager import RelationshipManager
from phase5.config_generator import ConfigGenerator


def generate_config_from_requirement(
    requirement: str,
    top_k: int = 5,
    verbose: bool = False
) -> Dict[str, Any]:
    """
    Generate configuration from natural language requirement.
    
    Args:
        requirement: Natural language requirement
        top_k: Number of templates to retrieve
        verbose: Print detailed progress
        
    Returns:
        Dict with 'config', 'warnings', 'metadata'
    """
    if verbose:
        print("\n" + "=" * 60)
        print("🚀 STARTING CONFIG GENERATION")
        print("=" * 60)
        print(f"\n📝 Requirement: {requirement}\n")
    
    # Step 1: Retrieve templates
    if verbose:
        print("Step 1/5: Retrieving templates...")
    
    # Initialize Phase 3 & 4 components
    vector_store = VectorStore()
    embedding_generator = EmbeddingGenerator()
    requirements_parser = RequirementsParser()
    query_generator = QueryGenerator(embedding_generator)
    retriever = TemplateRetriever(vector_store)
    ranker = RelevanceRanker()
    
    # Parse requirement
    parsed_req = requirements_parser.parse(requirement)
    
    # Generate query
    query = query_generator.generate_query(parsed_req, top_k=top_k)
    
    # Retrieve templates
    retrieved_templates = retriever.retrieve(query)
    
    # Rank templates
    ranked_templates = ranker.rank(retrieved_templates, parsed_req)
    
    if not ranked_templates:
        return {
            'config': None,
            'warnings': ['No templates found for requirement'],
            'metadata': {'success': False}
        }
    
    if verbose:
        print(f"✅ Retrieved {len(ranked_templates)} templates")
        for i, rt in enumerate(ranked_templates[:3], 1):
            print(f"   {i}. {rt.template.module_path} (score: {rt.relevance_score:.2f})")
    
    # Step 2: Extract values from requirement
    if verbose:
        print("\nStep 2/5: Extracting values from requirement...")
    
    extractor = ValueExtractor()
    extracted_values_dict = extractor.extract(requirement)
    
    # Flatten to list for display
    all_values = []
    for value_type, values in extracted_values_dict.items():
        all_values.extend(values)
    
    if verbose:
        print(f"✅ Extracted {len(all_values)} values")
        for ev in all_values[:5]:
            print(f"   - {ev.type}: {ev.value} (confidence: {ev.confidence:.2f})")
    
    # Step 3: Match values to parameters
    if verbose:
        print("\nStep 3/5: Matching values to template parameters...")
    
    matcher = ParameterMatcher()
    assembled_modules = []
    
    # Track indices for different module types
    index_counter = {
        '/c/slb/virt': 1,
        '/c/slb/real': 1,
        '/c/slb/group': 1,
        '/c/port': 1,
        '/c/l2/vlan': 1,
        '/c/l3/if': 1,
    }
    
    # First pass: Create assignment lists without assembling yet
    module_assignments = []
    
    for ranked_template in ranked_templates:
        # Get parameters and defaults from the retrieved template
        retrieved = ranked_template.template  # This is a RetrievedTemplate
        
        assignments = matcher.match(
            retrieved.parameters,
            extracted_values_dict,
            defaults=retrieved.defaults,
            auto_fill_high_confidence=True
        )
        
        #Determine index for this module
        module_path = retrieved.module_path
        index = None
        
        # Check if this module type needs an index
        if module_path in index_counter:
            index = index_counter[module_path]
            index_counter[module_path] += 1
        
        # Store for later assembly
        module_assignments.append({
            'retrieved': retrieved,
            'assignments': assignments,
            'index': index
        })
    
    # Resolve inter-module relationships at the assignment level
    if verbose:
        print("\nStep 4/5: Resolving relationships...")
    
    relationship_mgr = RelationshipManager()
    
    # Build a map of module indices
    module_index_map = {}
    for ma in module_assignments:
        path = ma['retrieved'].module_path
        idx = ma['index']
        if path not in module_index_map:
            module_index_map[path] = []
        if idx is not None:
            module_index_map[path].append(idx)
    
    # Fix relationships in assignments
    for ma in module_assignments:
        module_path = ma['retrieved'].module_path
        
        # Check if this module has relationships
        for rel in relationship_mgr.relationships:
            if module_path == rel.source_module:
                # This module references another module
                target_indices = module_index_map.get(rel.target_module, [])
                
                if target_indices:
                    # Find and update the assignment
                    for assignment in ma['assignments']:
                        if assignment.parameter_name == rel.source_param:
                            # Update value to reference target
                            assignment.value = str(target_indices[0])
                            assignment.source = 'relationship'
                            assignment.confidence = 0.95
                            break
    
    # Now assemble all modules with corrected assignments
    if verbose:
        print("\nStep 5/5: Assembling and ordering modules...")
    
    for ma in module_assignments:
        retrieved = ma['retrieved']
        assignments = ma['assignments']
        index = ma['index']
        
        # Assemble template with matched values
        # TemplateAssembler expects a dict with module_path, template, parameters
        template_dict = {
            'module_path': retrieved.module_path,
            'template': retrieved.template,
            'parameters': retrieved.parameters,
            'metadata': retrieved.metadata
        }
        
        assembler = TemplateAssembler()
        assembled = assembler.assemble(
            template_dict,
            assignments,
            index=index
        )
        assembled_modules.append(assembled)
    
    if verbose:
        print(f"✅ Assembled {len(assembled_modules)} modules")
        total_params = sum(len(m.parameter_assignments) for m in assembled_modules)
        user_params = sum(
            sum(1 for a in m.parameter_assignments if a.source == 'user')
            for m in assembled_modules
        )
        print(f"   Total parameters: {total_params} ({user_params} from user, {total_params - user_params} defaults)")
    
    if verbose:
        total_params = sum(len(m.parameter_assignments) for m in assembled_modules)
        user_params = sum(
            sum(1 for a in m.parameter_assignments if a.source == 'user')
            for m in assembled_modules
        )
        default_params = sum(
            sum(1 for a in m.parameter_assignments if a.source == 'default')
            for m in assembled_modules
        )
        relationship_params = sum(
            sum(1 for a in m.parameter_assignments if a.source == 'relationship')
            for m in assembled_modules
        )
        print(f"✅ Assembled {len(assembled_modules)} modules")
        print(f"   Total parameters: {total_params} ({user_params} user, {default_params} defaults, {relationship_params} relationships)")
    
    # Order modules by dependencies
    resolver = DependencyResolver()
    ordered_modules = resolver.order_modules(assembled_modules)
    
    # Check for missing dependencies (pass empty dict for now)
    missing_deps = resolver.find_missing_dependencies(ordered_modules, {})
    warnings = []
    
    if missing_deps:
        warnings.append(f"Missing dependencies: {', '.join(missing_deps)}")
        if verbose:
            print(f"⚠️  Missing dependencies: {', '.join(missing_deps)}")
            
            # Get suggestions
            suggestions = resolver.suggest_additions(ordered_modules)
            if suggestions:
                print(f"💡 Suggestions: {', '.join(suggestions)}")
    
    if verbose:
        print(f"✅ Ordered {len(ordered_modules)} modules")
    
    # Step 6: Generate final configuration
    if verbose:
        print("\nStep 6/6: Generating configuration...")
    
    generator = ConfigGenerator()
    config = generator.generate(
        ordered_modules,
        requirement=requirement,
        include_header=True,
        include_footer=True,
        add_comments=True
    )
    
    warnings.extend(config.warnings)
    
    if verbose:
        print(f"✅ Generated configuration with {config.metadata['total_lines']} lines")
        generator.print_summary(config)
    
    return {
        'config': config,
        'warnings': warnings,
        'metadata': {
            'success': True,
            'requirement': requirement,
            'templates_retrieved': len(ranked_templates),
            'values_extracted': len(all_values),
            'modules_generated': len(ordered_modules),
            'total_lines': config.metadata['total_lines']
        }
    }


def interactive_mode():
    """Interactive mode for config generation."""
    print("\n" + "=" * 60)
    print("🤖 INTERACTIVE CONFIG GENERATOR")
    print("=" * 60)
    print("\nEnter natural language requirements to generate configurations.")
    print("Type 'quit' or 'exit' to exit.\n")
    
    while True:
        try:
            requirement = input("📝 Requirement: ").strip()
            
            if requirement.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye!")
                break
            
            if not requirement:
                continue
            
            # Generate config
            result = generate_config_from_requirement(
                requirement,
                top_k=5,
                verbose=True
            )
            
            if result['config']:
                generator = ConfigGenerator()
                
                # Print preview
                generator.print_preview(result['config'], max_lines=40)
                
                # Ask if user wants to save
                print("\n")
                save = input("💾 Save to file? (y/N): ").strip().lower()
                
                if save == 'y':
                    filename = input("📁 Filename (default: config.txt): ").strip()
                    if not filename:
                        filename = "config.txt"
                    
                    output_path = Path("output") / filename
                    generator.save_to_file(result['config'], output_path)
                    print(f"✅ Saved to {output_path}")
            
            print("\n" + "-" * 60 + "\n")
        
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            continue


def batch_mode(requirements_file: Path, output_dir: Path, verbose: bool = False):
    """Batch mode for processing multiple requirements."""
    print("\n" + "=" * 60)
    print("📦 BATCH CONFIG GENERATION")
    print("=" * 60)
    
    # Read requirements
    if not requirements_file.exists():
        print(f"❌ Requirements file not found: {requirements_file}")
        return
    
    with open(requirements_file, 'r', encoding='utf-8') as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    print(f"\n📝 Processing {len(requirements)} requirements from {requirements_file}")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    generator = ConfigGenerator()
    results_summary = []
    
    for i, requirement in enumerate(requirements, 1):
        print(f"\n{'=' * 60}")
        print(f"Processing {i}/{len(requirements)}: {requirement[:60]}...")
        print('=' * 60)
        
        try:
            result = generate_config_from_requirement(
                requirement,
                top_k=5,
                verbose=verbose
            )
            
            if result['config']:
                # Save config
                filename = f"config_{i:03d}.txt"
                output_path = output_dir / filename
                generator.save_to_file(result['config'], output_path)
                
                # Save metadata
                metadata_path = output_dir / f"metadata_{i:03d}.json"
                with open(metadata_path, 'w', encoding='utf-8') as f:
                    json.dump(result['metadata'], f, indent=2)
                
                results_summary.append({
                    'index': i,
                    'requirement': requirement,
                    'success': True,
                    'output_file': filename,
                    'warnings': result['warnings'],
                    'metadata': result['metadata']
                })
                
                print(f"✅ Saved to {output_path}")
            else:
                results_summary.append({
                    'index': i,
                    'requirement': requirement,
                    'success': False,
                    'warnings': result['warnings']
                })
                print(f"❌ Failed: {result['warnings']}")
        
        except Exception as e:
            print(f"❌ Error: {e}")
            results_summary.append({
                'index': i,
                'requirement': requirement,
                'success': False,
                'error': str(e)
            })
    
    # Save summary
    summary_path = output_dir / "summary.json"
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(results_summary, f, indent=2)
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 BATCH SUMMARY")
    print("=" * 60)
    
    successful = sum(1 for r in results_summary if r['success'])
    failed = len(results_summary) - successful
    
    print(f"\n✅ Successful: {successful}/{len(results_summary)}")
    print(f"❌ Failed: {failed}/{len(results_summary)}")
    print(f"\n📁 Output directory: {output_dir}")
    print(f"📄 Summary saved to: {summary_path}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate configuration from natural language requirements"
    )
    
    parser.add_argument(
        '--mode',
        choices=['interactive', 'batch', 'single'],
        default='interactive',
        help='Generation mode'
    )
    
    parser.add_argument(
        '--requirement',
        '-r',
        type=str,
        help='Single requirement (for single mode)'
    )
    
    parser.add_argument(
        '--requirements-file',
        '-f',
        type=Path,
        help='File with multiple requirements (for batch mode)'
    )
    
    parser.add_argument(
        '--output',
        '-o',
        type=Path,
        default=Path('output'),
        help='Output directory'
    )
    
    parser.add_argument(
        '--top-k',
        type=int,
        default=5,
        help='Number of templates to retrieve'
    )
    
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Verbose output'
    )
    
    args = parser.parse_args()
    
    try:
        if args.mode == 'interactive':
            interactive_mode()
        
        elif args.mode == 'single':
            if not args.requirement:
                print("❌ Error: --requirement is required for single mode")
                sys.exit(1)
            
            result = generate_config_from_requirement(
                args.requirement,
                top_k=args.top_k,
                verbose=args.verbose
            )
            
            if result['config']:
                generator = ConfigGenerator()
                
                # Print to console
                config_str = generator.to_string(result['config'])
                print("\n" + config_str)
                
                # Save to file
                output_path = args.output / "config.txt"
                generator.save_to_file(result['config'], output_path)
                print(f"\n✅ Saved to {output_path}")
            else:
                print(f"\n❌ Failed: {result['warnings']}")
                sys.exit(1)
        
        elif args.mode == 'batch':
            if not args.requirements_file:
                print("❌ Error: --requirements-file is required for batch mode")
                sys.exit(1)
            
            batch_mode(args.requirements_file, args.output, verbose=args.verbose)
    
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
