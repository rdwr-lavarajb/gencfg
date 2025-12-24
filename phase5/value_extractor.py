"""
Phase 5: Value Extractor
Extracts concrete values from user requirements.
"""

import re
from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class ExtractedValue:
    """A value extracted from user requirements."""
    value: Any
    type: str
    confidence: float
    context: str  # Surrounding text that led to extraction


class ValueExtractor:
    """Extracts concrete values from natural language requirements."""
    
    # Value patterns with types
    PATTERNS = {
        'ipv4_address': r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b',
        'ipv4_netmask': r'\b(255\.255\.255\.\d{1,3})\b',
        'ipv4_cidr': r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d{1,2})\b',
        'port': r'\bport\s+(\d{1,5})\b',
        'vlan_id': r'\bvlan\s+(\d{1,4})\b',
        'integer': r'\b(\d+)\b',
        'quoted_string': r'"([^"]+)"',
    }
    
    # Context keywords for disambiguation
    CONTEXT_KEYWORDS = {
        'ipv4_address': ['ip', 'address', 'vip', 'real', 'server', 'host', 'gateway', 'gw'],
        'port': ['port', 'service'],
        'vlan': ['vlan', 'vlanid'],
        'name': ['name', 'called', 'named'],
    }
    
    def extract(self, requirement: str, parsed_entities: Dict[str, List[str]] = None) -> Dict[str, List[ExtractedValue]]:
        """
        Extract values from requirement text.
        
        Args:
            requirement: Natural language requirement
            parsed_entities: Optional pre-parsed entities from Phase 4
            
        Returns:
            Dict mapping value types to lists of ExtractedValue objects
        """
        extracted = {}
        text = requirement.lower()
        
        # Use pre-parsed entities if available
        if parsed_entities:
            for entity_type, values in parsed_entities.items():
                if entity_type not in extracted:
                    extracted[entity_type] = []
                for value in values:
                    extracted[entity_type].append(ExtractedValue(
                        value=value,
                        type=entity_type,
                        confidence=0.9,
                        context=self._get_context(text, value)
                    ))
        
        # Extract additional patterns
        for value_type, pattern in self.PATTERNS.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            
            if not matches:
                continue
            
            if value_type not in extracted:
                extracted[value_type] = []
            
            for match in matches:
                # Check if already extracted
                if any(ev.value == match for ev in extracted.get(value_type, [])):
                    continue
                
                context = self._get_context(text, match)
                confidence = self._calculate_confidence(value_type, match, context)
                
                extracted[value_type].append(ExtractedValue(
                    value=match,
                    type=value_type,
                    confidence=confidence,
                    context=context
                ))
        
        # Post-process integers (filter out likely non-parameter values)
        if 'integer' in extracted:
            extracted['integer'] = [
                ev for ev in extracted['integer']
                if self._is_likely_parameter_value(ev.value, ev.context)
            ]
        
        # Post-process IP addresses (filter out invalid IPs)
        if 'ipv4_address' in extracted:
            extracted['ipv4_address'] = [
                ev for ev in extracted['ipv4_address']
                if self._is_valid_ip(ev.value)
            ]
        
        return extracted
    
    def _get_context(self, text: str, value: str, window: int = 30) -> str:
        """Get surrounding context for a value."""
        value_str = str(value).lower()
        pos = text.find(value_str)
        
        if pos == -1:
            return ""
        
        start = max(0, pos - window)
        end = min(len(text), pos + len(value_str) + window)
        
        return text[start:end].strip()
    
    def _calculate_confidence(self, value_type: str, value: str, context: str) -> float:
        """Calculate confidence score for extracted value."""
        confidence = 0.7  # Base confidence
        
        # Check for context keywords
        keywords = self.CONTEXT_KEYWORDS.get(value_type, [])
        for keyword in keywords:
            if keyword in context:
                confidence += 0.1
                break
        
        # Validate value format
        if value_type == 'ipv4_address':
            # Check if valid IP
            parts = value.split('.')
            if len(parts) == 4 and all(0 <= int(p) <= 255 for p in parts):
                confidence += 0.1
        elif value_type == 'port':
            # Check if valid port
            if 1 <= int(value) <= 65535:
                confidence += 0.1
        elif value_type == 'vlan_id':
            # Check if valid VLAN
            if 1 <= int(value) <= 4094:
                confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _is_likely_parameter_value(self, value: str, context: str) -> bool:
        """Check if an integer is likely a parameter value vs noise."""
        num = int(value)
        
        # Filter out years, large numbers
        if num > 10000:
            return False
        
        # Check for parameter context
        param_contexts = ['index', 'id', 'number', 'count', 'priority', 'weight']
        if any(ctx in context for ctx in param_contexts):
            return True
        
        # Small numbers in range context likely parameters
        if num <= 100:
            return True
        
        return False
    
    def _is_valid_ip(self, ip: str) -> bool:
        """Check if IP address is valid."""
        try:
            parts = ip.split('.')
            if len(parts) != 4:
                return False
            for part in parts:
                num = int(part)
                if num < 0 or num > 255:
                    return False
            return True
        except (ValueError, AttributeError):
            return False
    
    def extract_names(self, requirement: str) -> List[ExtractedValue]:
        """
        Extract likely names from requirement.
        
        Looks for quoted strings or capitalized words.
        """
        names = []
        text = requirement
        
        # Extract quoted strings
        quoted = re.findall(r'"([^"]+)"', text)
        for name in quoted:
            names.append(ExtractedValue(
                value=name,
                type='string',
                confidence=0.9,
                context=self._get_context(text.lower(), name.lower())
            ))
        
        # Extract capitalized words (potential names)
        capitalized = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', text)
        for name in capitalized:
            if len(name) > 2:  # Skip short words
                names.append(ExtractedValue(
                    value=name,
                    type='string',
                    confidence=0.6,
                    context=self._get_context(text.lower(), name.lower())
                ))
        
        return names
    
    def extract_ip_ranges(self, requirement: str) -> List[List[str]]:
        """
        Extract IP address ranges.
        
        Example: "10.1.1.10-12" → ["10.1.1.10", "10.1.1.11", "10.1.1.12"]
        """
        ranges = []
        
        # Pattern: 10.1.1.10-12 or 10.1.1.10 to 10.1.1.12
        pattern = r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.)(\d{1,3})[-\s]+(?:to\s+)?(?:\d{1,3}\.\d{1,3}\.\d{1,3}\.)?(\d{1,3})'
        matches = re.findall(pattern, requirement, re.IGNORECASE)
        
        for prefix, start, end in matches:
            start_num = int(start)
            end_num = int(end)
            
            if start_num < end_num <= 255:
                ip_range = [f"{prefix}{i}" for i in range(start_num, end_num + 1)]
                ranges.append(ip_range)
        
        return ranges
    
    def extract_by_keyword(self, requirement: str, keywords: List[str]) -> List[ExtractedValue]:
        """
        Extract values associated with specific keywords.
        
        Example: "primary NTP 10.1.1.1" with keywords=['primary', 'ntp']
        """
        extracted = []
        text = requirement.lower()
        
        for keyword in keywords:
            # Look for keyword followed by value
            pattern = rf'\b{keyword}\s+(\S+)'
            matches = re.findall(pattern, text, re.IGNORECASE)
            
            for match in matches:
                extracted.append(ExtractedValue(
                    value=match,
                    type='keyword_value',
                    confidence=0.8,
                    context=self._get_context(text, match)
                ))
        
        return extracted
