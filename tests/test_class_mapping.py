import os
import sys

# Add root to sys path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ai.schemas.class_map import CLASS_ID_TO_NAME, CLASS_ID_TO_DISPLAY_NAME

def test_canonical_class_mapping():
    EXPECTED = {
        0: "crab_pot",
        1: "submarine_pipeline",
        2: "shipwreck",
        3: "ghost_net",
        4: "mine_cylinder",
    }

    for cls_id, name in EXPECTED.items():
        assert CLASS_ID_TO_NAME.get(cls_id) == name, f"Mismatch at ID {cls_id}: expected {name}, got {CLASS_ID_TO_NAME.get(cls_id)}"

    print("[SUCCESS] Canonical Class Map is consistent.")

def test_display_mapping():
    EXPECTED_DISPLAY = {
        0: "Crab Pot",
        1: "Submarine Pipeline",
        2: "Shipwreck",
        3: "Ghost Net",
        4: "Mine Cylinder",
    }

    for cls_id, disp_name in EXPECTED_DISPLAY.items():
        assert CLASS_ID_TO_DISPLAY_NAME.get(cls_id) == disp_name, f"Mismatch at ID {cls_id}: expected {disp_name}, got {CLASS_ID_TO_DISPLAY_NAME.get(cls_id)}"

    print("[SUCCESS] Display Class Map is consistent.")

if __name__ == "__main__":
    test_canonical_class_mapping()
    test_display_mapping()
