"""
Memory guardrails - safety checks for memory content.

Blocks:
- PII patterns (SSN, credit cards, etc.)
- Instruction-like content
- Enforces limits (max notes, max length)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .state import MemoryNote, MemoryState


@dataclass
class GuardrailConfig:
    """Configuration for memory guardrails."""
    
    # Content limits
    max_note_length: int = 500
    max_notes_per_user: int = 100
    max_session_notes: int = 20
    
    # PII patterns to block
    block_ssn: bool = True
    block_credit_card: bool = True
    block_phone: bool = True
    block_email: bool = False  # Often legitimate
    
    # Instruction blocking
    block_instructions: bool = True
    
    # Custom blocked patterns (regex)
    custom_patterns: list[str] | None = None


# Common PII patterns
PATTERNS = {
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    "credit_card": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
    "phone": r"\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
}

# Instruction-like patterns
INSTRUCTION_PATTERNS = [
    r"(?i)\b(ignore|disregard|forget)\s+(all\s+)?(previous|prior|above)",
    r"(?i)\b(system|admin)\s*(:|prompt|instruction)",
    r"(?i)\byou\s+(are|must|should|will)\s+now\b",
    r"(?i)\b(new|updated?)\s+(instruction|rule|directive)",
    r"(?i)\bremember\s+(this\s+)?(as\s+)?(a\s+)?(system|rule|instruction)",
]


@dataclass
class ValidationResult:
    """Result of guardrail validation."""
    is_valid: bool
    violations: list[str]
    
    def __bool__(self) -> bool:
        return self.is_valid


def validate_note_content(
    text: str,
    config: GuardrailConfig | None = None,
) -> ValidationResult:
    """
    Validate note content against guardrails.
    
    Args:
        text: Note text to validate
        config: Guardrail configuration
        
    Returns:
        ValidationResult with is_valid and list of violations
    """
    config = config or GuardrailConfig()
    violations = []
    
    # Length check
    if len(text) > config.max_note_length:
        violations.append(f"Note exceeds max length ({len(text)} > {config.max_note_length})")
    
    # PII checks
    if config.block_ssn and re.search(PATTERNS["ssn"], text):
        violations.append("Contains SSN pattern")
    
    if config.block_credit_card and re.search(PATTERNS["credit_card"], text):
        violations.append("Contains credit card pattern")
    
    if config.block_phone and re.search(PATTERNS["phone"], text):
        violations.append("Contains phone number pattern")
    
    if config.block_email and re.search(PATTERNS["email"], text):
        violations.append("Contains email pattern")
    
    # Instruction blocking
    if config.block_instructions:
        for pattern in INSTRUCTION_PATTERNS:
            if re.search(pattern, text):
                violations.append("Contains instruction-like content")
                break
    
    # Custom patterns
    if config.custom_patterns:
        for pattern in config.custom_patterns:
            if re.search(pattern, text):
                violations.append(f"Matches blocked pattern: {pattern}")
    
    return ValidationResult(
        is_valid=len(violations) == 0,
        violations=violations,
    )


def validate_state_limits(
    state: "MemoryState",
    config: GuardrailConfig | None = None,
) -> ValidationResult:
    """
    Validate state against limit guardrails.
    
    Args:
        state: Memory state to validate
        config: Guardrail configuration
        
    Returns:
        ValidationResult
    """
    config = config or GuardrailConfig()
    violations = []
    
    total_notes = len(state.global_memory) + len(state.session_memory)
    if total_notes > config.max_notes_per_user:
        violations.append(f"Total notes exceed limit ({total_notes} > {config.max_notes_per_user})")
    
    if len(state.session_memory) > config.max_session_notes:
        violations.append(f"Session notes exceed limit ({len(state.session_memory)} > {config.max_session_notes})")
    
    return ValidationResult(
        is_valid=len(violations) == 0,
        violations=violations,
    )


def sanitize_note(
    text: str,
    config: GuardrailConfig | None = None,
) -> str:
    """
    Sanitize note content by removing/masking blocked patterns.
    
    Args:
        text: Note text to sanitize
        config: Guardrail configuration
        
    Returns:
        Sanitized text
    """
    config = config or GuardrailConfig()
    result = text
    
    # Mask PII
    if config.block_ssn:
        result = re.sub(PATTERNS["ssn"], "[SSN REDACTED]", result)
    
    if config.block_credit_card:
        result = re.sub(PATTERNS["credit_card"], "[CARD REDACTED]", result)
    
    if config.block_phone:
        result = re.sub(PATTERNS["phone"], "[PHONE REDACTED]", result)
    
    if config.block_email:
        result = re.sub(PATTERNS["email"], "[EMAIL REDACTED]", result)
    
    # Truncate if too long
    if len(result) > config.max_note_length:
        result = result[:config.max_note_length - 3] + "..."
    
    return result


class GuardedMemoryState:
    """
    Wrapper around MemoryState that enforces guardrails.
    
    Usage:
        state = MemoryState(user_id="user_123")
        guarded = GuardedMemoryState(state, config=GuardrailConfig())
        
        # Will raise ValueError if content is blocked
        guarded.add_session_note("Prefers vegetarian meals")
        
        # Or use try_add for non-raising version
        success, violations = guarded.try_add_session_note("...")
    """
    
    def __init__(
        self,
        state: "MemoryState",
        config: GuardrailConfig | None = None,
    ):
        self.state = state
        self.config = config or GuardrailConfig()
    
    def add_session_note(
        self,
        text: str,
        keywords: list[str] | None = None,
        confidence: float = 1.0,
        ttl: int | None = None,
    ) -> "MemoryNote":
        """Add session note with guardrail validation. Raises on violation."""
        # Validate content
        result = validate_note_content(text, self.config)
        if not result.is_valid:
            raise ValueError(f"Guardrail violation: {', '.join(result.violations)}")
        
        # Check limits
        limits = validate_state_limits(self.state, self.config)
        if not limits.is_valid:
            raise ValueError(f"Limit violation: {', '.join(limits.violations)}")
        
        return self.state.add_session_note(
            text=text,
            keywords=keywords,
            confidence=confidence,
            ttl=ttl,
        )
    
    def try_add_session_note(
        self,
        text: str,
        keywords: list[str] | None = None,
        confidence: float = 1.0,
        ttl: int | None = None,
        sanitize: bool = False,
    ) -> tuple[bool, list[str]]:
        """
        Try to add session note. Returns (success, violations) tuple.
        
        Args:
            sanitize: If True, sanitize content instead of rejecting
        """
        if sanitize:
            text = sanitize_note(text, self.config)
        
        result = validate_note_content(text, self.config)
        limits = validate_state_limits(self.state, self.config)
        
        all_violations = result.violations + limits.violations
        
        if all_violations:
            return False, all_violations
        
        self.state.add_session_note(
            text=text,
            keywords=keywords,
            confidence=confidence,
            ttl=ttl,
        )
        
        return True, []
    
    # Delegate other methods to underlying state
    def __getattr__(self, name):
        return getattr(self.state, name)

