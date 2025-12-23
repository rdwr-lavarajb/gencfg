"""
Phase 4: Relevance Ranker
Re-ranks retrieved templates using multi-factor scoring.
"""

from dataclasses import dataclass
from typing import List, Dict, Any
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from phase4.template_retriever import RetrievedTemplate
from phase4.requirements_parser import ParsedRequirement


@dataclass
class RankedTemplate:
    """Template with computed relevance score and explanation."""
    template: RetrievedTemplate
    relevance_score: float
    score_breakdown: Dict[str, float]
    explanation: str
    rank: int


class RelevanceRanker:
    """
    Ranks templates using multi-factor scoring.
    
    Scoring Formula:
        Total Score = 
            0.60 × Semantic Similarity (from ChromaDB)
          + 0.15 × Category Match (exact=1.0, related=0.5)
          + 0.10 × Parameter Coverage
          + 0.10 × Examples Seen (confidence)
          + 0.05 × Default Availability
    """
    
    # Scoring weights
    WEIGHT_SIMILARITY = 0.60
    WEIGHT_CATEGORY = 0.15
    WEIGHT_PARAMS = 0.10
    WEIGHT_EXAMPLES = 0.10
    WEIGHT_DEFAULTS = 0.05
    
    # Category relationships for scoring
    RELATED_CATEGORIES = {
        'load_balancing': ['network_layer3', 'network_layer2', 'security_ssl'],
        'security_ssl': ['load_balancing', 'security_access'],
        'network_layer3': ['network_layer2', 'load_balancing'],
        'network_layer2': ['network_layer3'],
        'monitoring': ['system_management'],
    }
    
    # Irrelevant module patterns for common requirements
    # Maps requirement keywords to modules that should be excluded
    EXCLUSION_RULES = {
        'vip': ['/c/port', '/c/vadc'],  # VIP requests don't need port configs or vADC management
        'virtual': ['/c/port', '/c/vadc'],
        'load_balancing': ['/c/port', '/c/vadc'],
        'load balancer': ['/c/port', '/c/vadc'],
        'real server': ['/c/vadc'],
        'server group': ['/c/vadc'],
        'ssl': [],  # SSL can work with many modules
    }
    
    def rank(
        self,
        templates: List[RetrievedTemplate],
        parsed: ParsedRequirement,
        apply_filtering: bool = True
    ) -> List[RankedTemplate]:
        """
        Rank templates by relevance.
        
        Args:
            templates: List of retrieved templates
            parsed: ParsedRequirement for context
            apply_filtering: Whether to filter out irrelevant templates
            
        Returns:
            List of RankedTemplate objects, sorted by relevance_score
        """
        if not templates:
            return []
        
        # Apply filtering to remove irrelevant templates
        if apply_filtering:
            templates = self._filter_irrelevant(templates, parsed)
        
        if not templates:
            return []
        
        # Compute scores for each template
        ranked = []
        for template in templates:
            score_breakdown = self._compute_scores(template, parsed)
            total_score = sum(score_breakdown.values())
            explanation = self._build_explanation(template, score_breakdown, parsed)
            
            ranked.append(RankedTemplate(
                template=template,
                relevance_score=total_score,
                score_breakdown=score_breakdown,
                explanation=explanation,
                rank=0  # Will be set after sorting
            ))
        
        # Sort by relevance score (descending)
        ranked.sort(key=lambda x: x.relevance_score, reverse=True)
        
        # Assign ranks
        for i, rt in enumerate(ranked, 1):
            rt.rank = i
        
        return ranked
    
    def _filter_irrelevant(
        self,
        templates: List[RetrievedTemplate],
        parsed: ParsedRequirement
    ) -> List[RetrievedTemplate]:
        """
        Filter out templates that are clearly irrelevant.
        
        Args:
            templates: List of templates
            parsed: Parsed requirement
            
        Returns:
            Filtered list of templates
        """
        filtered = []
        
        # Extract keywords from requirement
        req_text_lower = parsed.original_text.lower()
        
        for template in templates:
            module_path = template.module_path
            should_exclude = False
            
            # Check exclusion rules
            for keyword, excluded_modules in self.EXCLUSION_RULES.items():
                if keyword in req_text_lower:
                    for excluded in excluded_modules:
                        if module_path.startswith(excluded):
                            should_exclude = True
                            break
                if should_exclude:
                    break
            
            if not should_exclude:
                filtered.append(template)
        
        return filtered
    
    def _compute_scores(
        self,
        template: RetrievedTemplate,
        parsed: ParsedRequirement
    ) -> Dict[str, float]:
        """Compute individual score components."""
        scores = {}
        
        # 1. Semantic Similarity (from ChromaDB)
        scores['similarity'] = template.similarity_score * self.WEIGHT_SIMILARITY
        
        # 2. Category Match
        category_score = self._score_category_match(
            template.metadata.get('category', ''),
            parsed.categories
        )
        scores['category'] = category_score * self.WEIGHT_CATEGORY
        
        # 3. Parameter Coverage
        param_coverage = self._score_parameter_coverage(template, parsed)
        scores['parameters'] = param_coverage * self.WEIGHT_PARAMS
        
        # 4. Examples Seen (confidence)
        examples_score = self._score_examples(template)
        scores['examples'] = examples_score * self.WEIGHT_EXAMPLES
        
        # 5. Default Availability
        defaults_score = self._score_defaults(template)
        scores['defaults'] = defaults_score * self.WEIGHT_DEFAULTS
        
        return scores
    
    def _score_category_match(
        self,
        template_category: str,
        required_categories: List[str]
    ) -> float:
        """
        Score category match.
        
        Returns:
            1.0 for exact match
            0.5 for related category
            0.0 for no match
        """
        if not required_categories:
            return 0.5  # Neutral if no categories specified
        
        # Exact match
        if template_category in required_categories:
            return 1.0
        
        # Check if related
        for req_cat in required_categories:
            related = self.RELATED_CATEGORIES.get(req_cat, [])
            if template_category in related:
                return 0.5
        
        return 0.0
    
    def _score_parameter_coverage(
        self,
        template: RetrievedTemplate,
        parsed: ParsedRequirement
    ) -> float:
        """
        Score how well template parameters cover requirement entities.
        
        Returns:
            0.0 to 1.0 based on coverage
        """
        # If no specific entities mentioned, check if template has parameters
        if not parsed.entities:
            param_count = template.metadata.get('param_count', 0)
            # Templates with parameters get a small bonus
            return 0.5 if param_count > 0 else 0.3
        
        # Check entity type coverage
        entity_types = set(parsed.entities.keys())
        param_types = set()
        
        for param in template.parameters.values():
            param_type = param.get('type', 'unknown')
            # Map parameter types to entity types
            if param_type in ['ipv4_address', 'ipv4_netmask']:
                param_types.add('ipv4')
            elif param_type == 'port':
                param_types.add('port')
            elif param_type == 'vlan_id':
                param_types.add('vlan')
        
        # Calculate coverage
        if not entity_types:
            return 0.5
        
        covered = entity_types & param_types
        coverage = len(covered) / len(entity_types)
        
        return coverage
    
    def _score_examples(self, template: RetrievedTemplate) -> float:
        """
        Score based on number of examples seen (confidence).
        
        More examples = higher confidence in template quality.
        
        Returns:
            0.0 to 1.0 (normalized)
        """
        examples = template.metadata.get('examples_seen', 0)
        
        # Logarithmic scale: 1 example = 0.3, 5 = 0.7, 10+ = 1.0
        if examples == 0:
            return 0.0
        elif examples == 1:
            return 0.3
        elif examples <= 3:
            return 0.5
        elif examples <= 5:
            return 0.7
        elif examples <= 10:
            return 0.9
        else:
            return 1.0
    
    def _score_defaults(self, template: RetrievedTemplate) -> float:
        """
        Score based on availability of learned defaults.
        
        Templates with defaults are easier to use.
        
        Returns:
            0.0 to 1.0 based on default coverage
        """
        has_defaults = template.metadata.get('has_defaults', False)
        
        if not has_defaults:
            return 0.0
        
        # Calculate percentage of parameters with defaults
        param_count = template.metadata.get('param_count', 0)
        if param_count == 0:
            return 0.0
        
        defaults_count = len(template.defaults)
        coverage = defaults_count / param_count
        
        return min(coverage, 1.0)
    
    def _build_explanation(
        self,
        template: RetrievedTemplate,
        scores: Dict[str, float],
        parsed: ParsedRequirement
    ) -> str:
        """Build human-readable explanation for ranking."""
        parts = []
        
        # Similarity
        sim_pct = template.similarity_score * 100
        parts.append(f"Semantic match: {sim_pct:.1f}%")
        
        # Category
        category = template.metadata.get('category', 'unknown')
        if category in parsed.categories:
            parts.append(f"Category: {category} (exact match)")
        elif scores['category'] > 0:
            parts.append(f"Category: {category} (related)")
        
        # Parameters
        param_count = template.metadata.get('param_count', 0)
        if param_count > 0:
            parts.append(f"{param_count} parameters")
            if scores['defaults'] > 0:
                parts.append(f"with defaults")
        
        # Examples
        examples = template.metadata.get('examples_seen', 0)
        if examples > 1:
            parts.append(f"{examples} examples seen")
        
        return " | ".join(parts)
    
    def filter_by_threshold(
        self,
        ranked: List[RankedTemplate],
        threshold: float = 0.3
    ) -> List[RankedTemplate]:
        """
        Filter ranked templates by minimum relevance score.
        
        Args:
            ranked: List of RankedTemplate objects
            threshold: Minimum relevance score (0.0 to 1.0)
            
        Returns:
            Filtered list
        """
        return [rt for rt in ranked if rt.relevance_score >= threshold]
    
    def group_by_category(
        self,
        ranked: List[RankedTemplate]
    ) -> Dict[str, List[RankedTemplate]]:
        """
        Group ranked templates by category.
        
        Args:
            ranked: List of RankedTemplate objects
            
        Returns:
            Dict mapping category to list of templates
        """
        groups = {}
        
        for rt in ranked:
            category = rt.template.metadata.get('category', 'unknown')
            if category not in groups:
                groups[category] = []
            groups[category].append(rt)
        
        return groups
