from typing import List, Dict, Any, Tuple

class GroundednessChecker:
    def __init__(self, min_score_threshold: float = 0.2):
        self.min_score_threshold = min_score_threshold

    def evaluate(self, chunks: List[Dict[str, Any]]) -> Tuple[bool, str]:
        if not chunks:
            return False, "No context chunks retrieved."

        # Find maximum score among retrieved chunks
        max_score = max(c.get("score", 0.0) for c in chunks)
        
        if max_score < self.min_score_threshold:
            return False, f"Confidence too low (max score: {max_score:.2f})."

        return True, "Context sufficient for grounded response."