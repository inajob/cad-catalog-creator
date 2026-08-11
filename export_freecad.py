import sys
import os

# FreeCAD bin directory from environment variable
freecad_bin = os.environ.get("FC_BIN_DIR", "")
if freecad_bin and os.path.exists(freecad_bin) and freecad_bin not in sys.path:
    sys.path.append(freecad_bin)

# Standard Linux paths (Ubuntu/PPA)
for p in ["/usr/lib/freecad/lib", "/usr/lib/freecad-daily/lib", "/usr/lib/freecad/lib64"]:
    if os.path.exists(p) and p not in sys.path:
        sys.path.append(p)

try:
    import FreeCAD
    import Mesh
    import Part
except ImportError as e:
    print(f"Error: Could not import FreeCAD modules: {e}")
    print(f"sys.path: {sys.path}")
    sys.exit(1)

def export(input_file, stl_out, step_out):
    print(f"Opening {input_file}...")
    try:
        doc = FreeCAD.open(input_file)
    except Exception as e:
        print(f"Failed to open document: {e}")
        return
    
    # Ensure absolute paths
    stl_out = os.path.abspath(stl_out)
    step_out = os.path.abspath(step_out)
    
    # Find objects to export.
    # Do NOT filter by InList when collecting candidates: bodies inside
    # App::Part / LinkGroup containers (common in FreeCAD 1.x documents) have
    # a non-empty InList and would be skipped, resulting in an empty export.
    # Final-object selection happens below as a preference, with a fallback.
    objs = []
    print(f"Total objects in document: {len(doc.Objects)}")
    for obj in doc.Objects:
        if not hasattr(obj, "Shape"):
            continue
        try:
            shape = obj.Shape
        except Exception:
            continue
        if shape is None or shape.isNull():
            continue
        if obj.Name == "Origin" or "Origin" in obj.TypeId:
            continue
        if obj.TypeId.startswith("Sketcher") or "SketchObject" in obj.TypeId:
            continue
        if shape.ShapeType not in ("Compound", "Solid", "Shell"):
            continue
        objs.append(obj)
        print(f"  Adding {obj.Name} ({obj.TypeId}) to export list")

    # Deduplicate by geometry hash to avoid exporting the same solid twice
    seen = set()
    unique = []
    for obj in objs:
        try:
            h = obj.Shape.hashCode()
        except Exception:
            h = None
        if h is not None and h in seen:
            continue
        if h is not None:
            seen.add(h)
        unique.append(obj)
    objs = unique

    # Prefer final/leaf objects (not used as input by anything else) so the
    # export is the finished part rather than a pile of overlapping features.
    # Fall back to all objects if no final object can be identified.
    finals = [o for o in objs if not o.InList]
    if finals:
        print(f"  Exporting {len(finals)} final objects: {[o.Name for o in finals]}")
        objs = finals

    # Export to STL (using Mesh)
    print(f"Exporting {len(objs)} objects to {stl_out}...")
    try:
        Mesh.export(objs, stl_out)
        print("STL Export successful.")
    except Exception as e:
        print(f"Failed to export STL: {e}")
    if os.path.exists(stl_out) and os.path.getsize(stl_out) == 0:
        print(f"WARNING: {stl_out} is empty (0 bytes). The document may not contain exportable solids.")
    
    # Export to STEP (using Part)
    print(f"Exporting {len(objs)} objects to {step_out}...")
    try:
        Part.export(objs, step_out)
        print("STEP Export successful.")
    except Exception as e:
        print(f"Failed to export STEP: {e}")
    
    FreeCAD.closeDocument(doc.Name)
    print("Script finished successfully.")

if __name__ == "__main__" or os.environ.get("FC_INPUT"):
    # Note: when run through FreeCAD's own interpreter (freecadcmd on Linux,
    # python.exe on Windows) the script's __name__ is NOT "__main__". Check
    # for the FC_INPUT env var as well so the export still runs.
    input_file = os.environ.get("FC_INPUT")
    stl_out = os.environ.get("FC_STL")
    step_out = os.environ.get("FC_STEP")

    if input_file and stl_out and step_out:
        export(input_file, stl_out, step_out)
    else:
        print("Usage: Set environment variables FC_INPUT, FC_STL, FC_STEP")
        sys.exit(1)
    
    sys.exit(0)
