import os
import json

class ScorePolicy:
    def __init__(self, weights_dir=None):
        if weights_dir is None:
            weights_dir = r"E:\GITHUB\a sih 2026\ai\reliability\weights"
            
        policy_path = os.path.join(weights_dir, "score_policy.json")
        if not os.path.exists(policy_path):
            raise FileNotFoundError(f"Score policy not found at {policy_path}")
            
        with open(policy_path, 'r') as f:
            self.policy = json.load(f)
            
    def evaluate(self, fusion_score, cls_id):
        """
        Maps a fusion score to a decision string based on calibrated thresholds.
        """
        cls_str = str(cls_id)
        if "classes" in self.policy and cls_str in self.policy["classes"]:
            cls_policy = self.policy["classes"][cls_str]
            review_threshold = cls_policy["review_threshold"]
            confirm_enabled = cls_policy.get("confirm", {}).get("enabled", False)
            confirm_threshold = cls_policy.get("confirm", {}).get("threshold", 1.1)
        else:
            review_threshold = self.policy.get("review_threshold", 0.35)
            confirm_enabled = True
            confirm_threshold = self.policy.get("confirm_threshold", 0.85)
            
        if confirm_enabled and confirm_threshold is not None and fusion_score >= confirm_threshold:
            return "CONFIRM"
        elif fusion_score >= review_threshold:
            return "REVIEW"
        else:
            return "REJECT"
