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

def is_visible(obj):
    """Check if object is visible in the 3D view."""
    if not hasattr(obj, "ViewObject") or obj.ViewObject is None:
        return True
    return getattr(obj.ViewObject, "Visibility", True)

def get_export_objects(doc):
    """Get list of visible, exportable objects from document."""
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
        if not is_visible(obj):
            print(f"  Skipping hidden object: {obj.Name}")
            continue
        objs.append(obj)
        print(f"  Adding {obj.Name} ({obj.TypeId}) to export list")
    return objs

def deduplicate_objects(objs):
    """Deduplicate by geometry hash."""
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
    return unique

def export_individual(input_file, stl_dir, step_dir):
    """Export each visible body as separate STL/STEP files."""
    print(f"Opening {input_file}...")
    try:
        doc = FreeCAD.open(input_file)
    except Exception as e:
        print(f"Failed to open document: {e}")
        return []
    
    objs = get_export_objects(doc)
    objs = deduplicate_objects(objs)
    
    # Prefer final/leaf objects
    finals = [o for o in objs if not o.InList]
    if finals:
        print(f"  Exporting {len(finals)} final objects: {[o.Name for o in finals]}")
        objs = finals
    else:
        print(f"  Exporting {len(objs)} objects: {[o.Name for o in objs]}")
    
    exported = []
    for obj in objs:
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in obj.Name)
        stl_path = os.path.join(stl_dir, f"{safe_name}.stl")
        step_path = os.path.join(step_dir, f"{safe_name}.step")
        
        # Export STL
        try:
            Mesh.export([obj], stl_path)
            print(f"  STL Export successful: {safe_name}.stl")
        except Exception as e:
            print(f"  Failed to export STL for {obj.Name}: {e}")
            if os.path.exists(stl_path):
                os.remove(stl_path)
            continue
        
        if os.path.getsize(stl_path) == 0:
            print(f"  WARNING: {safe_name}.stl is empty")
            os.remove(stl_path)
            continue
        
        # Export STEP
        try:
            Part.export([obj], step_path)
            print(f"  STEP Export successful: {safe_name}.step")
        except Exception as e:
            print(f"  Failed to export STEP for {obj.Name}: {e}")
            if os.path.exists(step_path):
                os.remove(step_path)
        
        exported.append({
            "name": obj.Name,
            "safe_name": safe_name,
            "stl": stl_path if os.path.exists(stl_path) else None,
            "step": step_path if os.path.exists(step_path) else None,
        })
    
    FreeCAD.closeDocument(doc.Name)
    print("Script finished successfully.")
    return exported

if __name__ == "__main__" or os.environ.get("FC_INPUT"):
    input_file = os.environ.get("FC_INPUT")
    stl_dir = os.environ.get("FC_STL_DIR")
    step_dir = os.environ.get("FC_STEP_DIR")
    
    # Backward compatibility: if FC_STL/FC_STEP are set (single file), use old behavior
    stl_out = os.environ.get("FC_STL")
    step_out = os.environ.get("FC_STEP")
    
    if input_file and stl_dir and step_dir:
        export_individual(input_file, stl_dir, step_dir)
    elif input_file and stl_out and step_out:
        # Legacy single-file export
        def export(input_file, stl_out, step_out):
            print(f"Opening {input_file}...")
            try:
                doc = FreeCAD.open(input_file)
            except Exception as e:
                print(f"Failed to open document: {e}")
                return
            
            stl_out = os.path.abspath(stl_out)
            step_out = os.path.abspath(step_out)
            
            objs = get_export_objects(doc)
            objs = deduplicate_objects(objs)
            finals = [o for o in objs if not o.InList]
            if finals:
                objs = finals
            
            print(f"Exporting {len(objs)} objects to {stl_out}...")
            try:
                Mesh.export(objs, stl_out)
                print("STL Export successful.")
            except Exception as e:
                print(f"Failed to export STL: {e}")
            if os.path.exists(stl_out) and os.path.getsize(stl_out) == 0:
                print(f"WARNING: {stl_out} is empty (0 bytes).")
            
            print(f"Exporting {len(objs)} objects to {step_out}...")
            try:
                Part.export(objs, step_out)
                print("STEP Export successful.")
            except Exception as e:
                print(f"Failed to export STEP: {e}")
            
            FreeCAD.closeDocument(doc.Name)
            print("Script finished successfully.")
        
        export(input_file, stl_out, step_out)
    else:
        print("Usage: Set environment variables FC_INPUT, FC_STL_DIR, FC_STEP_DIR (for multi-body)")
        print("       Or FC_INPUT, FC_STL, FC_STEP (for single-file legacy)")
        sys.exit(1)
    
    sys.exit(0)
