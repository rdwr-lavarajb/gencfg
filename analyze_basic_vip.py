"""
Analyze why basic VIP test generates incorrect config
"""

from generate_config import generate_config_from_requirement
from phase4.requirements_parser import RequirementsParser
from phase4.query_generator import QueryGenerator
from phase3.embedding_generator import EmbeddingGenerator
from phase3.vector_store import VectorStore

requirement = "Create VIP 192.168.1.100 on port 80"

print("="*80)
print("ANALYZING: ", requirement)
print("="*80)

# Step 1: Parse requirement
print("\n1. PARSING REQUIREMENT")
print("-"*80)
parser = RequirementsParser()
parsed = parser.parse(requirement)
print(f"Intent: {parsed.intent}")
print(f"Categories: {parsed.categories}")
print(f"Entities: {parsed.entities}")
print(f"Query text: {parsed.query_text}")

# Step 2: Retrieve templates
print("\n2. TEMPLATE RETRIEVAL")
print("-"*80)
embedding_gen = EmbeddingGenerator()
query_gen = QueryGenerator(embedding_gen)
query = query_gen.generate_query(parsed, top_k=10)

from phase4.template_retriever import TemplateRetriever
from phase4.relevance_ranker import RelevanceRanker

retriever = TemplateRetriever(VectorStore())
retrieved = retriever.retrieve(query)

ranker = RelevanceRanker()
ranked = ranker.rank(retrieved, parsed)

print(f"\nTop 10 ranked templates:")
for i, rt in enumerate(ranked[:10], 1):
    print(f"{i}. {rt.template.module_path:40} | score: {rt.relevance_score:.4f}")

# Step 3: Full generation to see module order
print("\n3. FULL GENERATION")
print("-"*80)
result = generate_config_from_requirement(requirement, verbose=False)
config = result['config']

print(f"\nGenerated modules (in order):")
for i, module in enumerate(config.modules, 1):
    assignments = {a.parameter_name: a.value for a in module.parameter_assignments}
    print(f"{i}. {module.module_path}")
    if assignments:
        for param, value in list(assignments.items())[:3]:  # Show first 3 params
            print(f"     {param} = {value}")

# Step 4: Check value extraction
print("\n4. VALUE EXTRACTION")
print("-"*80)
from phase5.value_extractor import ValueExtractor
extractor = ValueExtractor()
extracted = extractor.extract(requirement)
print("Extracted values:")
for value_type, values in extracted.items():
    for v in values:
        print(f"  {value_type}: {v.value} (conf: {v.confidence:.2f})")
