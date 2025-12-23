"""
Phase 4: Requirements Parser
Parses natural language requirements into structured format for retrieval.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Any, Set


@dataclass
class ParsedRequirement:
    """Structured representation of user requirements."""
    original_text: str
    intent: str  # create, configure, setup, enable, etc.
    entities: Dict[str, List[str]] = field(default_factory=dict)
    categories: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    constraints: Dict[str, Any] = field(default_factory=dict)
    query_text: str = ""  # Optimized text for embedding


class RequirementsParser:
    """Parses user requirements using pattern-based NLP."""
    
    # Intent patterns
    INTENT_PATTERNS = {
        'create': r'\b(create|new|add|setup|initialize)\b',
        'configure': r'\b(configure|config|set|setup|define)\b',
        'update': r'\b(update|modify|change|edit)\b',
        'enable': r'\b(enable|activate|turn on)\b',
        'disable': r'\b(disable|deactivate|turn off)\b',
        'delete': r'\b(delete|remove|destroy)\b',
    }
    
    # Entity patterns
    ENTITY_PATTERNS = {
        'ipv4': r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
        'ipv4_cidr': r'\b(?:\d{1,3}\.){3}\d{1,3}/\d{1,2}\b',
        'port': r'\bport\s+(\d+)\b',
        'vlan': r'\bvlan\s+(\d+)\b',
        'subnet_mask': r'\b(?:255\.){3}\d{1,3}\b',
    }
    
    # Category keywords
    CATEGORY_KEYWORDS = {
        'load_balancing': [
            'load balanc', 'virtual server', 'vip', 'real server',
            'backend', 'pool', 'server group', 'lb', 'slb'
        ],
        'network_layer3': [
            'ip address', 'layer 3', 'l3', 'routing', 'gateway',
            'interface', 'subnet', 'network'
        ],
        'network_layer2': [
            'vlan', 'layer 2', 'l2', 'switch', 'port', 'ethernet'
        ],
        'security_ssl': [
            'ssl', 'tls', 'certificate', 'cert', 'https', 'encryption'
        ],
        'security_access': [
            'user', 'access', 'authentication', 'password', 'login',
            'credential', 'permission'
        ],
        'monitoring': [
            'monitor', 'log', 'ntp', 'time', 'snmp', 'syslog'
        ],
        'system_management': [
            'system', 'management', 'admin', 'config'
        ],
    }
    
    # Module-specific keywords
    MODULE_KEYWORDS = {
        '/c/sys/mmgmt': ['management interface', 'management ip', 'mgmt', 'dhcp'],
        '/c/sys/ntp': ['ntp', 'time sync', 'time server'],
        '/c/slb/virt': ['virtual server', 'vip', 'virtual ip'],
        '/c/slb/real': ['real server', 'backend server', 'pool member'],
        '/c/slb/group': ['server group', 'group', 'pool'],
        '/c/l3/if': ['layer 3 interface', 'l3 interface', 'ip interface'],
        '/c/l2/vlan': ['vlan config', 'vlan'],
        '/c/port': ['port config', 'port vlan'],
    }
    
    # Category relationships (for query expansion)
    CATEGORY_RELATIONS = {
        'load_balancing': ['network_layer3', 'network_layer2'],
        'security_ssl': ['load_balancing'],
        'network_layer3': ['network_layer2'],
    }
    
    def parse(self, requirement: str) -> ParsedRequirement:
        """
        Parse user requirement into structured format.
        
        Args:
            requirement: Natural language requirement string
            
        Returns:
            ParsedRequirement object
        """
        req = requirement.lower().strip()
        
        # Extract intent
        intent = self._extract_intent(req)
        
        # Extract entities
        entities = self._extract_entities(req)
        
        # Identify categories
        categories = self._identify_categories(req)
        
        # Extract keywords
        keywords = self._extract_keywords(req)
        
        # Build optimized query text
        query_text = self._build_query_text(req, categories, keywords)
        
        # Extract constraints
        constraints = self._extract_constraints(req, entities)
        
        return ParsedRequirement(
            original_text=requirement,
            intent=intent,
            entities=entities,
            categories=categories,
            keywords=keywords,
            constraints=constraints,
            query_text=query_text
        )
    
    def _extract_intent(self, text: str) -> str:
        """Extract primary intent from text."""
        for intent, pattern in self.INTENT_PATTERNS.items():
            if re.search(pattern, text, re.IGNORECASE):
                return intent
        return 'configure'  # Default intent
    
    def _extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract entities like IPs, ports, VLANs."""
        entities = {}
        
        # Extract IPv4 addresses
        ipv4_matches = re.findall(self.ENTITY_PATTERNS['ipv4'], text)
        if ipv4_matches:
            entities['ipv4'] = list(set(ipv4_matches))
        
        # Extract ports
        port_matches = re.findall(self.ENTITY_PATTERNS['port'], text, re.IGNORECASE)
        if port_matches:
            entities['port'] = list(set(port_matches))
        
        # Extract VLANs
        vlan_matches = re.findall(self.ENTITY_PATTERNS['vlan'], text, re.IGNORECASE)
        if vlan_matches:
            entities['vlan'] = list(set(vlan_matches))
        
        # Extract numbers (for indices, IDs)
        number_pattern = r'\b(\d+)\b'
        numbers = re.findall(number_pattern, text)
        if numbers:
            entities['numbers'] = [n for n in numbers if int(n) < 10000][:5]  # Limit
        
        return entities
    
    def _identify_categories(self, text: str) -> List[str]:
        """Identify relevant categories from text."""
        matched_categories = []
        
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    matched_categories.append(category)
                    break
        
        # Remove duplicates while preserving order
        seen = set()
        categories = []
        for cat in matched_categories:
            if cat not in seen:
                categories.append(cat)
                seen.add(cat)
        
        # Add related categories
        expanded = categories.copy()
        for cat in categories:
            if cat in self.CATEGORY_RELATIONS:
                for related in self.CATEGORY_RELATIONS[cat]:
                    if related not in expanded:
                        expanded.append(related)
        
        return expanded if expanded else ['system_management']  # Default
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords from text."""
        # Remove common words
        stopwords = {
            'i', 'need', 'to', 'want', 'the', 'a', 'an', 'and', 'or', 'but',
            'in', 'on', 'at', 'for', 'with', 'from', 'by', 'of', 'is', 'are'
        }
        
        # Tokenize and filter
        words = re.findall(r'\b\w+\b', text.lower())
        keywords = [w for w in words if w not in stopwords and len(w) > 2]
        
        # Extract bigrams (2-word phrases)
        bigrams = []
        for i in range(len(keywords) - 1):
            bigram = f"{keywords[i]} {keywords[i+1]}"
            bigrams.append(bigram)
        
        # Combine and deduplicate
        all_keywords = keywords + bigrams
        
        # Return most important (unique, maintain order)
        seen = set()
        result = []
        for kw in all_keywords:
            if kw not in seen:
                result.append(kw)
                seen.add(kw)
        
        return result[:20]  # Limit to top 20
    
    def _build_query_text(
        self,
        text: str,
        categories: List[str],
        keywords: List[str]
    ) -> str:
        """Build optimized text for embedding generation."""
        parts = []
        
        # Add original text (cleaned)
        cleaned = re.sub(r'\s+', ' ', text).strip()
        parts.append(cleaned)
        
        # Add categories as context
        if categories:
            cat_text = ', '.join(categories[:3])  # Top 3
            parts.append(f"Category: {cat_text}")
        
        # Add key phrases
        key_phrases = [kw for kw in keywords if ' ' in kw][:3]
        if key_phrases:
            parts.append(' '.join(key_phrases))
        
        return ' | '.join(parts)
    
    def _extract_constraints(
        self,
        text: str,
        entities: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """Extract constraints for filtering."""
        constraints = {}
        
        # Require index if specific numbers mentioned
        if entities.get('numbers'):
            constraints['may_need_index'] = True
        
        # Require parameters if specific values given
        if entities.get('ipv4') or entities.get('port') or entities.get('vlan'):
            constraints['must_have_parameters'] = True
        
        # SSL requirement
        if 'ssl' in text or 'tls' in text or 'https' in text:
            constraints['requires_ssl'] = True
        
        return constraints
    
    def parse_batch(self, requirements: List[str]) -> List[ParsedRequirement]:
        """
        Parse multiple requirements.
        
        Args:
            requirements: List of requirement strings
            
        Returns:
            List of ParsedRequirement objects
        """
        return [self.parse(req) for req in requirements]
    
    def suggest_modules(self, parsed: ParsedRequirement) -> List[str]:
        """
        Suggest likely module paths based on parsed requirements.
        
        Args:
            parsed: ParsedRequirement object
            
        Returns:
            List of suggested module paths
        """
        suggestions = []
        text = parsed.original_text.lower()
        
        for module_path, keywords in self.MODULE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    suggestions.append(module_path)
                    break
        
        return suggestions
