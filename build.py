import os
import subprocess
import shutil
import sys
from pathlib import Path
from jinja2 import Template
from dotenv import load_dotenv

# Load local .env if exists
load_dotenv()

# --- Configuration (with defaults for GitHub Actions) ---
OPENSCAD_PATH = os.getenv("OPENSCAD_PATH", "openscad")
FREECAD_PATH = os.getenv("FREECAD_PYTHON_PATH", "python")
FREECAD_BIN_DIR = os.getenv("FREECAD_BIN_DIR", "")

# Preview settings
COLOR_SCHEME = "DeepOcean" 
OBJECT_COLOR = "CornflowerBlue"

MODELS_DIR = Path("models")
DIST_DIR = Path("dist")
SITE_DESC_PATH = MODELS_DIR / "site_description.md"

# --- Templates ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>3D Model Catalog</title>
    <style>
        body { font-family: sans-serif; margin: 40px; background: #f0f0f0; color: #333; max-width: 1200px; margin-left: auto; margin-right: auto; }
        header { margin-bottom: 40px; border-bottom: 2px solid #ccc; padding-bottom: 20px; }
        header h1 { margin-bottom: 10px; color: #222; }
        .site-description { line-height: 1.6; color: #555; white-space: pre-wrap; }
        
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 30px; }
        .card { background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); display: flex; flex-direction: column; position: relative; }
        .card img { max-width: 100%; height: auto; border-radius: 4px; background: #eee; min-height: 100px; object-fit: contain; }
        .card h3 { margin: 15px 0 5px 0; font-size: 1.1em; word-break: break-all; border-bottom: 1px solid #eee; padding-bottom: 5px; }
        
        .badge { 
            display: inline-block; 
            padding: 2px 8px; 
            border-radius: 4px; 
            font-size: 0.75em; 
            font-weight: bold; 
            margin-bottom: 10px;
        }
        .badge-openscad { background: #fff3cd; color: #856404; border: 1px solid #ffeeba; }
        .badge-freecad { background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }
        .badge-cadquery { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }

        .description { font-size: 0.9em; color: #666; margin-bottom: 20px; flex-grow: 1; white-space: pre-wrap; line-height: 1.5; }
        .links { margin-top: auto; padding-top: 10px; border-top: 1px dashed #eee; }
        .links a { margin-right: 15px; text-decoration: none; color: #007bff; font-size: 0.9em; font-weight: bold; }
        .links a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <header>
        <h1>3D Model Catalog</h1>
        <div class="site-description">{% if site_description %}{{ site_description }}{% else %}Welcome to my 3D model collection.{% endif %}</div>
    </header>

    <div class="grid">
        {% for model in models %}
        <div class="card">
            {% if model.png %}
            <img src="{{ model.png }}" alt="{{ model.name }}">
            {% else %}
            <div style="height: 200px; background: #ddd; display: flex; align-items: center; justify-content: center; color: #666;">No Preview</div>
            {% endif %}
            
            <h3>{{ model.name }}</h3>
            <div>
                <span class="badge badge-{{ model.source|lower }}">{{ model.source }}</span>
            </div>
            
            <div class="description">{% if model.description %}{{ model.description }}{% else %}(No description){% endif %}</div>
            
            <div class="links">
                {% if model.stl %}<a href="{{ model.stl }}">STL</a>{% endif %}
                {% if model.step %}<a href="{{ model.step }}">STEP</a>{% endif %}
            </div>
        </div>
        {% endfor %}
    </div>
</body>
</html>
"""

def ensure_description(file_path):
    """説明文ファイルを確認し、なければ雛形を生成して内容を返す"""
    md_path = file_path.with_suffix(".md")
    txt_path = file_path.with_suffix(".txt")
    for p in [md_path, txt_path]:
        if p.exists():
            try:
                return p.read_text(encoding="utf-8").strip()
            except Exception:
                return ""
    placeholder = f"{file_path.stem}\n\n(ここに説明を入力してください)"
    try:
        md_path.write_text(placeholder, encoding="utf-8")
    except Exception:
        pass
    return placeholder

def run_command(cmd, cwd=None, env=None):
    try:
        subprocess.run(cmd, check=True, cwd=cwd, capture_output=True, text=True, env=env)
    except subprocess.CalledProcessError:
        return False
    return True

def render_png_from_stl(stl_path, png_path):
    if not stl_path.exists():
        return False
    temp_scad = stl_path.with_suffix(".temp.scad")
    stl_path_str = str(stl_path.absolute()).replace("\\", "/")
    temp_scad.write_text(f'color("{OBJECT_COLOR}") import("{stl_path_str}");', encoding="utf-8")
    success = run_command([
        OPENSCAD_PATH, "-o", str(png_path.absolute()), 
        f"--colorscheme={COLOR_SCHEME}", "--imgsize=1024,1024", str(temp_scad.absolute())
    ])
    if temp_scad.exists():
        temp_scad.unlink()
    return success

def convert_scad(file_path):
    rel_path = file_path.relative_to(MODELS_DIR)
    base_name = str(rel_path.with_suffix("")).replace(os.sep, "_")
    stl_out = DIST_DIR / f"{base_name}.stl"
    png_out = DIST_DIR / f"{base_name}.png"
    
    # Check modification times
    if not all(f.exists() for f in [stl_out, png_out]) or \
       file_path.stat().st_mtime > stl_out.stat().st_mtime:
        print(f"  Building {base_name}...")
        run_command([OPENSCAD_PATH, "-o", str(stl_out.absolute()), str(file_path.absolute())])
        run_command([
            OPENSCAD_PATH, "-o", str(png_out.absolute()), 
            f"--colorscheme={COLOR_SCHEME}", "--imgsize=1024,1024", str(file_path.absolute())
        ])
    return {
        "name": base_name, "stl": f"{base_name}.stl" if stl_out.exists() else None, 
        "png": f"{base_name}.png" if png_out.exists() else None,
        "description": ensure_description(file_path),
        "source": "OpenSCAD"
    }

def convert_py(file_path):
    rel_path = file_path.relative_to(MODELS_DIR)
    base_name = str(rel_path.with_suffix("")).replace(os.sep, "_")
    stl_out = DIST_DIR / f"{base_name}.stl"
    step_out = DIST_DIR / f"{base_name}.step"
    png_out = DIST_DIR / f"{base_name}.png"
    
    if not all(f.exists() for f in [stl_out, step_out, png_out]) or \
       file_path.stat().st_mtime > stl_out.stat().st_mtime:
        print(f"  Building {base_name}...")
        wrapper_path = file_path.parent / "_build_wrapper.py"
        stl_abs = str(stl_out.absolute()).replace("\\", "/")
        step_abs = str(step_out.absolute()).replace("\\", "/")
        file_abs = str(file_path.absolute()).replace("\\", "/")
        wrapper_content = f"""
import sys, os
from unittest.mock import MagicMock
import cadquery as cq
sys.modules["ocp_vscode"] = MagicMock()
def show_object(*args, **kwargs): pass
namespace = {{"show_object": show_object, "cq": cq, "__name__": "__main__", "__file__": "{file_abs}"}}
os.chdir("{str(file_path.parent.absolute()).replace("\\", "/")}")
with open("{file_abs}", "r", encoding="utf-8") as f: exec(f.read(), namespace)
if "result" in namespace:
    result = namespace["result"]
    cq.exporters.export(result, "{stl_abs}")
    cq.exporters.export(result, "{step_abs}")
"""
        wrapper_path.write_text(wrapper_content, encoding="utf-8")
        run_command([sys.executable, str(wrapper_path.absolute())])
        wrapper_path.unlink()
        if stl_out.exists():
            render_png_from_stl(stl_out, png_out)
    return {
        "name": base_name, "stl": f"{base_name}.stl" if stl_out.exists() else None, 
        "step": f"{base_name}.step" if step_out.exists() else None, 
        "png": f"{base_name}.png" if png_out.exists() else None,
        "description": ensure_description(file_path),
        "source": "CadQuery"
    }

def convert_fcstd(file_path):
    rel_path = file_path.relative_to(MODELS_DIR)
    base_name = str(rel_path.with_suffix("")).replace(os.sep, "_")
    stl_out = DIST_DIR / f"{base_name}.stl"
    step_out = DIST_DIR / f"{base_name}.step"
    png_out = DIST_DIR / f"{base_name}.png"
    
    if not all(f.exists() for f in [stl_out, step_out, png_out]) or \
       file_path.stat().st_mtime > stl_out.stat().st_mtime:
        print(f"  Building {base_name}...")
        env = os.environ.copy()
        env["FC_INPUT"] = str(file_path.absolute())
        env["FC_STL"] = str(stl_out.absolute())
        env["FC_STEP"] = str(step_out.absolute())
        env["FC_BIN_DIR"] = FREECAD_BIN_DIR
        script_path = Path("export_freecad.py").absolute()
        run_command([FREECAD_PATH, str(script_path)], env=env)
        if stl_out.exists():
            render_png_from_stl(stl_out, png_out)
    return {
        "name": base_name, "stl": f"{base_name}.stl" if stl_out.exists() else None, 
        "step": f"{base_name}.step" if step_out.exists() else None, 
        "png": f"{base_name}.png" if png_out.exists() else None,
        "description": ensure_description(file_path),
        "source": "FreeCAD"
    }

def main():
    if not DIST_DIR.exists():
        DIST_DIR.mkdir()

    # Get site description
    site_description = ""
    if SITE_DESC_PATH.exists():
        site_description = SITE_DESC_PATH.read_text(encoding="utf-8").strip()
    else:
        site_description = "3Dプリンタ用モデルのカタログです。各モデルのSTLとSTEPファイルをダウンロードできます。"
        try:
            SITE_DESC_PATH.write_text(site_description, encoding="utf-8")
        except Exception:
            pass

    models_info = []
    for scad_file in sorted(MODELS_DIR.glob("**/*.scad")):
        models_info.append(convert_scad(scad_file))
    for py_file in sorted(MODELS_DIR.glob("**/*.py")):
        if py_file.name in ["build.py", "export_freecad.py"] or py_file.name.startswith("_"):
            continue
        models_info.append(convert_py(py_file))
    for fcstd_file in sorted(MODELS_DIR.glob("**/*.fcstd")):
        models_info.append(convert_fcstd(fcstd_file))

    template = Template(HTML_TEMPLATE)
    html = template.render(models=models_info, site_description=site_description, base_url="")
    (DIST_DIR / "index.html").write_text(html, encoding="utf-8")
    print(f"\nBuild complete! {len(models_info)} models cataloged.")

if __name__ == "__main__":
    main()
