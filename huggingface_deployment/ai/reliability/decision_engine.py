import json
from .score_policy import ScorePolicy
from .unknown_detector import UnknownDetector

class DecisionEngine:
    def __init__(self, weights_dir=None):
        self.score_policy = ScorePolicy(weights_dir)
        self.unknown_detector = UnknownDetector(weights_dir)
        
        # Classes validated in Gate D-2
        self.validated_classes = {0, 1, 2}  # Crab, Wreck, Mine
        self.unvalidated_classes = {3, 4}   # Pipeline, Ghost Net
        
        self.class_names = {
            0: "crab_pot",
            1: "shipwreck",
            2: "mine_cylinder",
            3: "submarine_pipeline",
            4: "ghost_net"
        }
        
    def evaluate_candidate(self, evidence_dict, standardized_features, fusion_score):
        """
        Evaluates a single candidate and returns a Gate E decision payload.
        """
        cls_id = evidence_dict.get("class", -1)
        cls_name = self.class_names.get(cls_id, "unknown_class")
        
        decision = "UNKNOWN"
        reason_codes = []
        is_anomalous = False
        
        # 1. Uncalibrated-class routing takes precedence
        if cls_id in self.unvalidated_classes:
            decision = "REVIEW"
            reason_codes.append("UNCALIBRATED_CLASS_FORCED_REVIEW")
            
            # Default thresholds for Uncalibrated classes are just global fallback
            conf_thresh = self.score_policy.policy.get("confirm_threshold", 0.85)
            rev_thresh = self.score_policy.policy.get("review_threshold", 0.35)
            
            if fusion_score >= conf_thresh:
                reason_codes.append("HIGH_FUSION_EVIDENCE")
            elif fusion_score >= rev_thresh:
                reason_codes.append("MODERATE_FUSION_EVIDENCE")
            else:
                reason_codes.append("LOW_FUSION_EVIDENCE")
                
        else:
            # 2. Unknown Anomaly check (Only for validated classes)
            is_anomalous = self.unknown_detector.check_unknown(standardized_features)
            
            if is_anomalous:
                decision = "UNKNOWN"
                reason_codes.append("INSUFFICIENT_KNOWN_CLASS_EVIDENCE")
                reason_codes.append("ANOMALOUS_PROFILE")
            else:
                # 3. Fusion score decision policy
                decision = self.score_policy.evaluate(fusion_score, cls_id)
                
                if decision == "CONFIRM":
                    reason_codes.append("HIGH_FUSION_EVIDENCE")
                elif decision == "REVIEW":
                    reason_codes.append("MODERATE_FUSION_EVIDENCE")
                else:
                    reason_codes.append("LOW_EVIDENCE")
                    
                shadow_prob = evidence_dict.get("shadow", {}).get("shadow_candidate_presence", 0.0)
                if shadow_prob > 0.5:
                    reason_codes.append("SHADOW_SUPPORTED")
                else:
                    reason_codes.append("NO_SHADOW_SUPPORT")
                    
                boundary_strength = evidence_dict.get("quality", {}).get("boundary_strength", 0.0)
                if decision == "REJECT" and boundary_strength < 10.0:
                    reason_codes.append("WEAK_BOUNDARY")
                    
        # Construct Uncertainty representation
        unc_score = 1.0 - float(fusion_score) if decision != "UNKNOWN" else 1.0
        
        payload = {
            "class": cls_name,
            "fusion_score": round(float(fusion_score), 4),
            "decision": decision,
            "uncertainty": {
                "classification_uncertainty": round(unc_score, 4),
                "novelty_flag": bool(is_anomalous) if cls_id not in self.unvalidated_classes else False,
                "level": "HIGH" if unc_score > 0.6 or is_anomalous else ("MEDIUM" if unc_score > 0.2 else "LOW")
            },
            "evidence": {
                "ai_confidence": round(evidence_dict.get("confidence", 0.0), 4),
                "shadow_candidate_presence": round(evidence_dict.get("shadow", {}).get("shadow_candidate_presence", 0.0), 4),
                "aspect_ratio": round(evidence_dict.get("object", {}).get("aspect_ratio", 0.0), 4),
                "local_contrast": round(evidence_dict.get("seabed", {}).get("local_contrast", 0.0), 4),
                "boundary_strength": round(evidence_dict.get("quality", {}).get("boundary_strength", 0.0), 4)
            },
            "artifact_flags": [k for k, v in evidence_dict.get("quality", {}).get("artifact_flags", {}).items() if v],
            "reason_codes": reason_codes
        }
        
        return payload
