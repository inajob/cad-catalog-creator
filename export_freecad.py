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
    objs = []
    print(f"Total objects in document: {len(doc.Objects)}")
    for obj in doc.Objects:
        if hasattr(obj, "Shape") and obj.Shape:
            # Only export top-level visible objects that are likely the final result
            if obj.InList:
                continue
            objs.append(obj)
            print(f"  Adding {obj.Name} to export list")
    
    if not objs:
        # Fallback: if no top-level objects with shape found, try to find any Body
        for obj in doc.Objects:
            if obj.isDerivedFrom("PartDesign::Body") or obj.isDerivedFrom("Part::Feature"):
                 if not obj.InList:
                     objs.append(obj)
                     print(f"  Adding {obj.Name} (Body/Feature) to export list")

    # Export to STL (using Mesh)
    print(f"Exporting {len(objs)} objects to {stl_out}...")
    try:
        Mesh.export(objs, stl_out)
        print("STL Export successful.")
    except Exception as e:
        print(f"Failed to export STL: {e}")
    
    # Export to STEP (using Part)
    print(f"Exporting {len(objs)} objects to {step_out}...")
    try:
        Part.export(objs, step_out)
        print("STEP Export successful.")
    except Exception as e:
        print(f"Failed to export STEP: {e}")
    
    FreeCAD.closeDocument(doc.Name)
    print("Script finished successfully.")

if __name__ == "__main__":
    # Get paths from environment variables
    input_file = os.environ.get("FC_INPUT")
    stl_out = os.environ.get("FC_STL")
    step_out = os.environ.get("FC_STEP")

    if input_file and stl_out and step_out:
        export(input_file, stl_out, step_out)
    else:
        print("Usage: Set environment variables FC_INPUT, FC_STL, FC_STEP")
        sys.exit(1)
    
    sys.exit(0)
