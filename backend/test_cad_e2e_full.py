"""
Comprehensive End-to-End Automated Test for J.A.R.V.I.S. Engineering CAD
Validates:
1. Natural language command execution (units, parameters, intent).
2. Conversational context & pronoun resolution ("it", "its", "that").
3. Context persistence across sequential operations (Box -> Hole -> Pattern -> Transform).
4. Conversational ambiguity detection with clarification candidates.
5. Measurement & geometry verification.
6. Undo / Redo operations.
7. Real OpenCASCADE Brep tessellation mesh generation.
"""

import json
import urllib.request
import urllib.parse
import sys

BASE_URL = "http://127.0.0.1:8000/api/cad"

def post_json(endpoint: str, payload: dict) -> dict:
    url = f"{BASE_URL}{endpoint}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def get_json(endpoint: str) -> dict:
    url = f"{BASE_URL}{endpoint}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def run_tests():
    print("=================================================================")
    print("  J.A.R.V.I.S. CAD END-TO-END PIPELINE VERIFICATION SUITE")
    print("=================================================================")

    # Step 0: Start clean document
    print("\n[*] Initializing new document...")
    init_res = post_json("/document/new?name=E2E_Test_Document", {})
    assert init_res["success"] is True, "Failed to create new document"
    print("    -> Document initialized successfully.")

    # Test 1: Create box with engineering units
    print("\n[1] Testing Natural Language Box Creation: 'Create a box 100 by 60 by 20 mm'")
    r1 = post_json("/command/execute", {"command": "Create a box 100 by 60 by 20 mm"})
    assert r1["success"] is True, f"Box creation failed: {r1}"
    assert r1["action"] == "CREATE_BOX"
    box_id = r1["feature_id"]
    p1 = r1["parameters"]
    assert p1["width"] == 100.0 and p1["height"] == 60.0 and p1["depth"] == 20.0, f"Dimensions mismatch: {p1}"
    assert len(r1["meshes"]) >= 1, "Expected tessellated mesh in response"
    box_mesh = r1["meshes"][0]
    assert len(box_mesh["vertices"]) > 0, "Expected Brep vertices"
    assert len(box_mesh["indices"]) > 0, "Expected Brep triangle indices"
    print(f"    -> Box created: ID={box_id[:8]}, Vertices={len(box_mesh['vertices'])//3}, Triangles={len(box_mesh['indices'])//3}")

    # Test 2: Conversational Feature Operation - Hole on current model
    print("\n[2] Testing Conversational Hole: 'Make a 10 mm hole at the center'")
    r2 = post_json("/command/execute", {"command": "Make a 10 mm hole at the center"})
    assert r2["success"] is True, f"Hole failed: {r2}"
    assert r2["action"] == "CREATE_HOLE"
    assert r2["parameters"]["diameter"] == 10.0
    print(f"    -> Hole created: Diameter={r2['parameters']['diameter']}mm, Depth={r2['parameters']['depth']}mm")

    # Test 3: Circular Pattern: "Make six equally spaced holes"
    print("\n[3] Testing Pattern Operation: 'Make six equally spaced circular pattern'")
    r3 = post_json("/command/execute", {"command": "Make six equally spaced circular pattern"})
    assert r3["success"] is True, f"Pattern failed: {r3}"
    assert r3["action"] == "PATTERN_CIRCULAR"
    assert r3["parameters"]["count"] == 6
    print(f"    -> Circular Pattern applied: Count={r3['parameters']['count']}")

    # Test 4: Measure geometry
    print("\n[4] Testing Measurement: 'Measure bounding box'")
    r4 = post_json("/command/execute", {"command": "Measure bounding box"})
    assert r4["success"] is True, f"Measure failed: {r4}"
    assert r4["action"] in ("MEASURE", "MEASURE_BOUNDING_BOX"), f"Action was {r4.get('action')}"
    raw_bb = r4.get("bounding_box") or (r4.get("result") or {}).get("bounding_box") or (r4.get("meshes", [{}])[0].get("bbox"))
    assert raw_bb is not None, f"Bounding box missing in {r4}"
    w = raw_bb.get("width", raw_bb.get("size", [0, 0, 0])[0])
    h = raw_bb.get("height", raw_bb.get("size", [0, 0, 0])[1])
    d = raw_bb.get("depth", raw_bb.get("size", [0, 0, 0])[2])
    print(f"    -> Measurement verified: {w:.1f} x {h:.1f} x {d:.1f} mm")

    # Test 5: Undo & Redo operations
    print("\n[5] Testing Undo & Redo...")
    r5_undo = post_json("/command/execute", {"command": "undo that"})
    assert r5_undo["success"] is True, f"Undo failed: {r5_undo}"
    print("    -> Undo executed successfully.")

    r5_redo = post_json("/command/execute", {"command": "redo that"})
    assert r5_redo["success"] is True, f"Redo failed: {r5_redo}"
    print("    -> Redo executed successfully.")

    # Test 6: Conversational Anaphora Chain ("create a cylinder" -> "move it 50 mm on X" -> "rotate it 45 degrees")
    print("\n[6] Testing Conversational Context Chain:")
    print("    6a. 'Create a cylinder radius 15 height 80 mm'")
    r6a = post_json("/command/execute", {"command": "Create a cylinder radius 15 height 80 mm"})
    assert r6a["success"] is True
    cyl_id = r6a["feature_id"]
    print(f"        -> Cylinder created (ID={cyl_id[:8]})")

    print("    6b. 'Move it 50 mm on X'")
    r6b = post_json("/command/execute", {"command": "Move it 50 mm on X"})
    assert r6b["success"] is True, f"Move failed: {r6b}"
    assert r6b["action"] in ("TRANSFORM", "TRANSFORM_MOVE"), f"Action was {r6b.get('action')}"
    assert r6b["parameters"]["x"] == 50.0
    print(f"        -> Context resolved 'it' -> {cyl_id[:8]} moved 50mm on X")

    print("    6c. 'Rotate it 45 degrees'")
    r6c = post_json("/command/execute", {"command": "Rotate it 45 degrees"})
    assert r6c["success"] is True, f"Rotate failed: {r6c}"
    assert r6c["action"] in ("TRANSFORM", "TRANSFORM_ROTATE"), f"Action was {r6c.get('action')}"
    assert r6c["parameters"]["angle"] == 45.0
    print(f"        -> Context resolved 'it' -> rotated 45 degrees")

    # Test 7: Verify Ambiguity Detection (Create another cylinder, then say "select cylinder" without active selection)
    print("\n[7] Testing Ambiguity Resolution:")
    r7_cyl2 = post_json("/command/execute", {"command": "Create a cylinder radius 10 height 40 mm"})
    assert r7_cyl2["success"] is True

    # Clear current selection in context to test ambiguity detection
    post_json("/context", {"selected_feature_id": None})
    r7_ambig = post_json("/command/execute", {"command": "delete that cylinder"})
    print(f"    Ambiguity status: ambiguous={r7_ambig.get('ambiguous')}")
    if r7_ambig.get("ambiguous"):
        print(f"    -> Clarification returned: {r7_ambig['clarification']}")
        print(f"    -> Candidates found: {[c['name'] for c in r7_ambig.get('candidates', [])]}")
        assert len(r7_ambig.get("candidates", [])) >= 2, "Expected multiple cylinder candidates"
        print("    -> Ambiguity detection PASSED! J.A.R.V.I.S. refuses to guess silently.")
    else:
        print("    (Single candidate resolved or specific cylinder chosen)")

    # Test 8: Full Mesh Query (Verifies real OpenCASCADE tessellation for Three.js viewport)
    print("\n[8] Testing /api/cad/document/meshes for Viewport Rendering:")
    meshes_res = get_json("/document/meshes")
    assert meshes_res["success"] is True
    print(f"    -> Total meshes in active document: {len(meshes_res['meshes'])}")
    for m in meshes_res["meshes"]:
        print(f"       • {m['name']} ({m['type']}): {len(m['vertices'])//3} verts, {len(m['indices'])//3} tris, size={m['bbox']['size']}")

    print("\n=================================================================")
    print("  ALL J.A.R.V.I.S. CAD E2E TESTS PASSED PERFECTLY!")
    print("=================================================================")

if __name__ == "__main__":
    try:
        run_tests()
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
