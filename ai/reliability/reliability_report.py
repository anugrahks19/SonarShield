def generate_sonar_shield_report(payload):
    """
    Formats the JSON payload from the Decision Engine into an explainable 
    SONAR-SHIELD ANALYSIS report block.
    """
    class_map = {
        "crab_pot": "Crab Pot",
        "shipwreck": "Wreck",
        "mine_cylinder": "Mine",
        "submarine_pipeline": "Pipeline",
        "ghost_net": "Ghost Net",
        "unknown_class": "Unknown Target Type"
    }
    
    cls_str = class_map.get(payload["class"], payload["class"])
    
    lines = []
    lines.append("SONAR-SHIELD ANALYSIS")
    lines.append("-" * 25)
    lines.append(f"Candidate: {cls_str}")
    lines.append(f"AI confidence:       {payload['evidence']['ai_confidence']:.4f}")
    lines.append(f"Local contrast:      {payload['evidence']['local_contrast']:.4f}")
    lines.append(f"Geometry evidence:   {payload['evidence']['aspect_ratio']:.4f}")
    lines.append(f"Shadow evidence:     {payload['evidence']['shadow_candidate_presence']:.4f}")
    lines.append(f"Boundary evidence:   {payload['evidence']['boundary_strength']:.4f}")
    lines.append("")
    
    decision = payload["decision"]
    lines.append(f"Decision: {decision}")
    
    # Generate human-readable reason
    reason_str = "No specific reason provided."
    codes = payload["reason_codes"]
    
    if decision == "UNKNOWN":
        reason_str = "Candidate feature profile does not match validated true positive distributions (Anomalous Profile)."
    elif decision == "LOW_EVIDENCE":
        if "LOW_FUSION_EVIDENCE" in codes:
            reason_str = "Insufficient multi-source sonar evidence."
            if "WEAK_BOUNDARY" in codes:
                reason_str += " Candidate has weak boundary strength."
            if "NO_SHADOW_SUPPORT" in codes:
                reason_str += " Lack of supportive shadow evidence."
    elif decision == "REVIEW":
        if "UNCALIBRATED_CLASS_FORCED_REVIEW" in codes:
            if "HIGH_FUSION_EVIDENCE" in codes:
                reason_str = "High fusion evidence, but routed to conservative review because the target class is uncalibrated."
            else:
                reason_str = "Target class is uncalibrated. Placed in conservative review path."
        elif "MODERATE_FUSION_EVIDENCE" in codes:
            reason_str = "Moderate multi-source sonar evidence, but insufficient confidence for confirmation."
    elif decision == "CONFIRM":
        reason_str = "Strong multi-source sonar evidence supporting positive detection."
        if "SHADOW_SUPPORTED" in codes:
            reason_str += " High-quality shadow and boundary present."
            
    if payload.get("artifact_flags"):
        flags_str = ", ".join(payload["artifact_flags"])
        reason_str += f"\nWarning: Artifact flags detected ({flags_str})."
        
    lines.append("Reason:")
    lines.append(reason_str)
    
    return "\n".join(lines)
