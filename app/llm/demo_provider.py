"""Deterministic Mock LLM Provider for Demo Mode and Offline Testing."""

import json
from typing import Any, Dict, Optional, Type
from pydantic import BaseModel

from app.llm.base import LLMProvider


class DemoProvider(LLMProvider):
    """Provides deterministic, evidence-grounded responses without calling external APIs."""

    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        lower_p = prompt.lower()
        if "root cause" in lower_p:
            return "The root cause is in cart.py at line 42 where calculate_total changed its return type from a dictionary to CartTotal."
        elif "why is payment.py affected" in lower_p or "payment" in lower_p:
            return "payment.py line 89 performs dictionary subscription total['tax'], but calculate_total now returns a CartTotal object instance."
        elif "risk" in lower_p:
            return "The risk is evaluated as HIGH because payment processing directly consumes the changed return type and will raise TypeError at runtime."
        return "This is a deterministic response from CodeImpact DemoProvider based on supplied evidence."

    async def generate_structured(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        response_model: Optional[Type[BaseModel]] = None,
    ) -> Dict[str, Any]:
        """Return deterministic JSON matching the requested prompt context."""
        lower_p = prompt.lower()

        # Fix proposal request
        if "fix" in lower_p or "propose" in lower_p or "instruction" in lower_p:
            # Check if CartTotal attribute 'tax' is supported in the prompt evidence
            has_class_def = "class carttotal" in lower_p or "self.tax" in lower_p or "tax field" in lower_p
            has_insufficient_evidence = "insufficient" in lower_p or "no_evidence" in lower_p or not has_class_def

            if has_insufficient_evidence:
                return {
                    "status": "NEEDS_MORE_EVIDENCE",
                    "summary": "Cannot safely rewrite caller without definition of CartTotal showing how fields are exposed.",
                    "changes": [],
                    "diff": None,
                    "assumptions": [],
                    "uncertainties": [
                        "Supplied evidence does not include the CartTotal class definition or its exposed attributes/methods."
                    ],
                    "confidence": "MEDIUM",
                    "message": "Please provide the file or snippet defining CartTotal to avoid guessing property access vs dict vs method call.",
                }

            # If evidence supports total.tax
            return {
                "status": "PROPOSED",
                "summary": "Update dictionary lookup total['tax'] to attribute access total.tax in payment.py.",
                "changes": [
                    {
                        "file": "payment.py",
                        "start_line": 89,
                        "end_line": 89,
                        "old_code": "tax = total['tax']",
                        "new_code": "tax = total.tax",
                        "reason": "calculate_total now returns CartTotal instance which exposes tax as an attribute.",
                        "citations": [
                            {
                                "file": "payment.py",
                                "start_line": 89,
                                "end_line": 89,
                                "symbol": "process_payment",
                                "snippet": "tax = total['tax']",
                                "verified": True,
                            }
                        ],
                    }
                ],
                "diff": "--- a/payment.py\n+++ b/payment.py\n@@ -89,1 +89,1 @@\n-tax = total['tax']\n+tax = total.tax\n",
                "assumptions": [],
                "uncertainties": [],
                "confidence": "HIGH",
                "message": "Proposed fix generated safely from verified CartTotal attribute evidence.",
            }

        # Ask / Q&A request
        if "question" in lower_p:
            return {
                "answer": (
                    "payment.py is affected because line 89 accesses total['tax'] assuming a dictionary, "
                    "whereas cart.py:42 now returns a CartTotal object. This will trigger a TypeError at runtime."
                ),
                "claims": [
                    {
                        "statement": "cart.py:42 returns CartTotal instance instead of dictionary",
                        "category": "FACT",
                        "citations": [
                            {
                                "file": "cart.py",
                                "start_line": 42,
                                "end_line": 48,
                                "symbol": "calculate_total",
                                "snippet": "return CartTotal(subtotal, tax)",
                                "verified": True,
                            }
                        ],
                        "verified": True,
                    },
                    {
                        "statement": "payment.py:89 expects a dictionary and uses subscript lookup",
                        "category": "FACT",
                        "citations": [
                            {
                                "file": "payment.py",
                                "start_line": 87,
                                "end_line": 90,
                                "symbol": "process_payment",
                                "snippet": "tax = total['tax']",
                                "verified": True,
                            }
                        ],
                        "verified": True,
                    },
                ],
                "citations": [
                    {"file": "cart.py", "start_line": 42, "end_line": 48, "verified": True},
                    {"file": "payment.py", "start_line": 87, "end_line": 90, "verified": True},
                ],
                "recommended_actions": [
                    "Inspect payment.py line 89 and adapt dictionary access to CartTotal attribute access.",
                    "Run automated tests on payment.py.",
                ],
                "confidence": "HIGH",
                "uncertainties": [],
            }

        # Default: Impact Explanation structured output
        return {
            "summary": (
                "Function calculate_total in cart.py modified its return type from a dictionary to a CartTotal "
                "object instance. Downstream caller payment.py uses dictionary subscript syntax, leading to runtime failure."
            ),
            "risk": {
                "level": "HIGH",
                "reason": (
                    "Direct caller payment.py in the payment flow performs subscript access total['tax'] on an object, "
                    "causing unhandled TypeError during checkout execution."
                ),
                "factors": [
                    "Breaking return type change across module boundary",
                    "Direct caller payment.py relies on dictionary contract",
                    "Payment domain logic critical for checkout execution",
                ],
            },
            "impact_type": "RETURN_TYPE_CHANGE",
            "root_cause": {
                "file": "cart.py",
                "line": 42,
                "symbol": "calculate_total",
                "reason": "Return type contract was altered from dict to CartTotal without updating caller access patterns.",
                "citations": [
                    {
                        "file": "cart.py",
                        "start_line": 42,
                        "end_line": 48,
                        "symbol": "calculate_total",
                        "snippet": "return CartTotal(subtotal, tax)",
                        "verified": True,
                    }
                ],
            },
            "direct_impacts": [
                {
                    "file": "payment.py",
                    "symbol": "process_payment",
                    "line_range": "87-90",
                    "reason": "Directly invokes calculate_total and executes total['tax'], expecting dict.",
                    "citations": [
                        {
                            "file": "payment.py",
                            "start_line": 87,
                            "end_line": 90,
                            "symbol": "process_payment",
                            "snippet": "tax = total['tax']",
                            "verified": True,
                        }
                    ],
                }
            ],
            "indirect_impacts": [
                {
                    "file": "checkout.py",
                    "symbol": "checkout",
                    "reason": "Transitively impacted caller in the execution chain calling process_payment.",
                    "path": ["cart.py:calculate_total", "payment.py:process_payment", "checkout.py:checkout"],
                    "citations": [],
                }
            ],
            "impact_chain": [
                "cart.py:calculate_total",
                "payment.py:process_payment",
                "checkout.py:checkout",
            ],
            "claims": [
                {
                    "statement": "cart.py:42 changed return type to CartTotal",
                    "category": "FACT",
                    "citations": [
                        {
                            "file": "cart.py",
                            "start_line": 42,
                            "end_line": 48,
                            "symbol": "calculate_total",
                            "verified": True,
                        }
                    ],
                    "verified": True,
                },
                {
                    "statement": "payment.py:89 relies on dictionary subscription syntax",
                    "category": "FACT",
                    "citations": [
                        {
                            "file": "payment.py",
                            "start_line": 87,
                            "end_line": 90,
                            "symbol": "process_payment",
                            "verified": True,
                        }
                    ],
                    "verified": True,
                },
                {
                    "statement": "checkout.py may fail if payment execution fails",
                    "category": "INFERENCE",
                    "citations": [],
                    "verified": False,
                    "notes": "checkout.py file content not directly provided in evidence.",
                },
            ],
            "recommended_actions": [
                "Update payment.py line 89 to access total.tax instead of total['tax']",
                "Verify whether CartTotal defines __getitem__ or exposes properties",
                "Run test suite for payment processing",
            ],
            "confidence": "HIGH",
            "uncertainties": [
                "Full definition of CartTotal is not in evidence snippet, assuming attributes based on constructor call."
            ],
        }
