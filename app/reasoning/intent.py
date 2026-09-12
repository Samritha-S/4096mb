"""Intent analysis for developer inquiries."""

import re


class IntentAnalyzer:
    """Analyzes developer question intent for repository-grounded assistance."""

    FIX_PATTERNS = [
        re.compile(r"\b(fix|patch|repair|rewrite|correct|resolve|refactor)\b", re.IGNORECASE),
        re.compile(r"\bhow (do|can) (i|we) fix\b", re.IGNORECASE),
        re.compile(r"\bpropose (a )?(fix|solution|change)\b", re.IGNORECASE),
    ]

    RISK_PATTERNS = [
        re.compile(r"\b(risk|severity|dangerous|critical|safe|breakage)\b", re.IGNORECASE),
        re.compile(r"\bwhy is (this|it) (high|medium|low|critical)\b", re.IGNORECASE),
    ]

    ROOT_CAUSE_PATTERNS = [
        re.compile(r"\b(root cause|origin|why did it happen|what caused)\b", re.IGNORECASE),
        re.compile(r"\bwhere did (the|this) (break|error|bug|change) come from\b", re.IGNORECASE),
    ]

    CHAIN_PATTERNS = [
        re.compile(r"\b(impact chain|call chain|dependency chain|blast radius|propagation)\b", re.IGNORECASE),
        re.compile(r"\bwho calls\b", re.IGNORECASE),
    ]

    TEST_PATTERNS = [
        re.compile(r"\b(test|verify|validate|unit test|integration test)\b", re.IGNORECASE),
        re.compile(r"\bwhat should (i|we) test\b", re.IGNORECASE),
    ]

    @classmethod
    def is_fix_request(cls, question: str) -> bool:
        return any(pattern.search(question) for pattern in cls.FIX_PATTERNS)

    @classmethod
    def is_risk_inquiry(cls, question: str) -> bool:
        return any(pattern.search(question) for pattern in cls.RISK_PATTERNS)

    @classmethod
    def is_root_cause_inquiry(cls, question: str) -> bool:
        return any(pattern.search(question) for pattern in cls.ROOT_CAUSE_PATTERNS)

    @classmethod
    def is_chain_inquiry(cls, question: str) -> bool:
        return any(pattern.search(question) for pattern in cls.CHAIN_PATTERNS)

    @classmethod
    def is_test_inquiry(cls, question: str) -> bool:
        return any(pattern.search(question) for pattern in cls.TEST_PATTERNS)
