"""Test CAD engine core functionality."""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_geometry():
    """Test core geometry types."""
    print("Testing geometry types...")
    from app.cad_engine.core.geometry import Point2D, Point3D, Vector2D, Vector3D, BoundingBox

    p1 = Point2D(0, 0)
    p2 = Point2D(3, 4)
    dist = p1.distance_to(p2)
    assert abs(dist - 5.0) < 0.001, f"Expected 5.0, got {dist}"

    p3 = Point3D(1, 2, 3)
    p4 = Point3D(4, 6, 3)
    dist3d = p3.distance_to(p4)
    assert abs(dist3d - 5.0) < 0.001, f"Expected 5.0, got {dist3d}"

    v1 = Vector2D(1, 0)
    v2 = Vector2D(0, 1)
    dot = v1.dot(v2)
    assert abs(dot) < 0.001, f"Expected 0, got {dot}"

    print("  [OK] Geometry types working")

def test_document():
    """Test document management."""
    print("Testing document management...")
    from app.cad_engine.core.document import CADDokument, Feature, FeatureType

    doc = CADDokument("Test Document")
    assert doc.name == "Test Document"
    assert len(doc.features) == 0

    feature = Feature(
        id="test-1",
        name="Test Feature",
        feature_type=FeatureType.PRIMITIVE,
        parameters={"width": 10, "height": 20}
    )
    doc.add_feature(feature)
    assert len(doc.features) == 1
    assert "test-1" in doc.features

    print("  [OK] Document management working")

def test_modeling():
    """Test 3D modeling operations."""
    print("Testing 3D modeling operations...")
    from app.cad_engine.features.modeling import CADModelingOperations
    from app.cad_engine.core.document import get_active_document, set_active_document, CADDokument

    # Create and set active document
    doc = CADDokument("Modeling Test")
    set_active_document(doc)

    # Create box
    box = CADModelingOperations.create_box(100, 50, 20, "Test Box")
    assert box is not None
    assert box.id in doc._geometry_cache

    # Create cylinder
    cyl = CADModelingOperations.create_cylinder(25, 100, "Test Cylinder")
    assert cyl is not None
    assert cyl.id in doc._geometry_cache

    # Create sphere
    sphere = CADModelingOperations.create_sphere(30, "Test Sphere")
    assert sphere is not None
    assert sphere.id in doc._geometry_cache

    print("  [OK] 3D modeling operations working")

def test_measurement():
    """Test measurement system."""
    print("Testing measurement system...")
    from app.cad_engine.features.modeling import CADModelingOperations
    from app.cad_engine.core.measurement import CADMeasurement
    from app.cad_engine.core.document import get_active_document, set_active_document, CADDokument

    # Create document with box
    doc = CADDokument("Measurement Test")
    set_active_document(doc)
    box = CADModelingOperations.create_box(100, 50, 20, "Measure Box")

    # Test bounding box
    bbox = CADMeasurement.get_bounding_box(box.id)
    assert bbox is not None
    assert "min" in bbox and "max" in bbox

    # Test volume
    volume = CADMeasurement.get_volume(box.id)
    assert volume is not None
    expected_volume = 100 * 50 * 20
    assert abs(volume - expected_volume) < 1.0, f"Expected ~{expected_volume}, got {volume}"

    # Test surface area
    area = CADMeasurement.get_surface_area(box.id)
    assert area is not None
    expected_area = 2 * (100*50 + 100*20 + 50*20)
    assert abs(area - expected_area) < 1.0, f"Expected ~{expected_area}, got {area}"

    # Test face/edge/vertex counts
    faces = CADMeasurement.get_faces(box.id)
    assert faces is not None
    assert len(faces) == 6, f"Box should have 6 faces, got {len(faces)}"

    edges = CADMeasurement.get_edges(box.id)
    assert edges is not None
    assert len(edges) == 12, f"Box should have 12 edges, got {len(edges)}"

    vertices = CADMeasurement.get_vertices(box.id)
    assert vertices is not None
    assert len(vertices) == 8, f"Box should have 8 vertices, got {len(vertices)}"

    print("  [OK] Measurement system working")

def test_file_io():
    """Test file import/export."""
    print("Testing file I/O...")
    from app.cad_engine.features.modeling import CADModelingOperations
    from app.cad_engine.io.file_io import CADFileIO
    from app.cad_engine.core.document import get_active_document, set_active_document, CADDokument
    import tempfile
    import os

    # Create document with box
    doc = CADDokument("File IO Test")
    set_active_document(doc)
    box = CADModelingOperations.create_box(100, 50, 20, "Export Box")

    # Test STL export
    with tempfile.TemporaryDirectory() as tmpdir:
        stl_path = os.path.join(tmpdir, "test.stl")
        result = CADFileIO.export_stl(box.id, stl_path)
        assert result is True, "STL export failed"
        assert os.path.exists(stl_path), f"STL file not created: {stl_path}"
        assert os.path.getsize(stl_path) > 0, "STL file is empty"

        # Test STL import
        imported = CADFileIO.import_stl(stl_path)
        assert imported is not None, "STL import failed"
        assert imported.id in doc._geometry_cache

    # Test STEP export
    with tempfile.TemporaryDirectory() as tmpdir:
        step_path = os.path.join(tmpdir, "test.step")
        result = CADFileIO.export_step(box.id, step_path)
        assert result is True, "STEP export failed"
        assert os.path.exists(step_path), f"STEP file not created: {step_path}"
        assert os.path.getsize(step_path) > 0, "STEP file is empty"

    # Test BREP export
    with tempfile.TemporaryDirectory() as tmpdir:
        brep_path = os.path.join(tmpdir, "test.brep")
        result = CADFileIO.export_brep(box.id, brep_path)
        assert result is True, "BREP export failed"
        assert os.path.exists(brep_path), f"BREP file not created: {brep_path}"
        assert os.path.getsize(brep_path) > 0, "BREP file is empty"

    print("  [OK] File I/O working")

def test_sketch():
    """Test 2D sketch system."""
    print("Testing 2D sketch system...")
    from app.cad_engine.sketches.sketch import Sketch, SketchPoint, SketchLine, SketchCircle, ConstraintType

    sketch = Sketch("Test Sketch")

    # Add entities - each add_line/add_circle creates points too
    p1 = sketch.add_point(0, 0)
    p2 = sketch.add_point(100, 0)
    p3 = sketch.add_point(100, 50)

    line1 = sketch.add_line(0, 0, 100, 0)
    line2 = sketch.add_line(100, 0, 100, 50)

    circle = sketch.add_circle(50, 25, 10)

    # Should have: 3 explicit points + 4 points from lines + 1 point from circle + 2 lines + 1 circle = 11 entities
    assert len(sketch.entities) == 11, f"Expected 11 entities, got {len(sketch.entities)}"

    # Add constraints - line1 and line2 are already IDs (strings)
    c1 = sketch.add_constraint(ConstraintType.HORIZONTAL, [line1])
    c2 = sketch.add_constraint(ConstraintType.VERTICAL, [line2])

    assert len(sketch.constraints) == 2

    print("  [OK] 2D sketch system working")

def test_undo_redo():
    """Test undo/redo system."""
    print("Testing undo/redo system...")
    from app.cad_engine.core.document import CADDokument, Command

    doc = CADDokument("Undo Test")

    # Add commands
    cmd1 = Command(
        id="cmd-1",
        name="Create Box",
        feature_id="box-1",
        parameters={"width": 100, "height": 50},
    )
    doc.push_undo(cmd1)
    assert len(doc.undo_stack) == 1
    assert len(doc.redo_stack) == 0

    cmd2 = Command(
        id="cmd-2",
        name="Create Cylinder",
        feature_id="cyl-1",
        parameters={"radius": 25, "height": 100},
    )
    doc.push_undo(cmd2)
    assert len(doc.undo_stack) == 2
    assert len(doc.redo_stack) == 0

    # Undo
    undone = doc.undo()
    assert undone is not None
    assert undone.id == "cmd-2"
    assert len(doc.undo_stack) == 1
    assert len(doc.redo_stack) == 1

    # Redo
    redone = doc.redo()
    assert redone is not None
    assert redone.id == "cmd-2"
    assert len(doc.undo_stack) == 2
    assert len(doc.redo_stack) == 0

    print("  [OK] Undo/redo system working")

def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("CAD ENGINE TEST SUITE")
    print("="*60 + "\n")

    try:
        test_geometry()
        test_document()
        test_modeling()
        test_measurement()
        test_file_io()
        test_sketch()
        test_undo_redo()

        print("\n" + "="*60)
        print("ALL TESTS PASSED [OK]")
        print("="*60 + "\n")
        return 0
    except Exception as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
