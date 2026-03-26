import os
import subprocess
import shutil
import sys
import re
from pathlib import Path
from jinja2 import Template
from dotenv import load_dotenv
from PIL import Image
import markdown

# Load local .env if exists
load_dotenv()

# --- Configuration ---
REPO_URL = "https://github.com/inajob/cad-catalog-creator"
m = re.match(r"https://github\.com/([^/]+)/([^/]+)", REPO_URL)
if m:
    BASE_URL = f"https://{m.group(1)}.github.io/{m.group(2)}/"
else:
    BASE_URL = os.getenv("BASE_URL", "/")

OPENSCAD_PATH = os.getenv("OPENSCAD_PATH", "openscad")
FREECAD_PATH = os.getenv("FREECAD_PYTHON_PATH", "python")
FREECAD_BIN_DIR = os.getenv("FREECAD_BIN_DIR", "")

# Preview settings
COLOR_SCHEME = "DeepOcean" 
OBJECT_COLOR = "CornflowerBlue"

MODELS_DIR = Path("models")
DIST_DIR = Path("dist")
SITE_DESC_PATH = MODELS_DIR / "site_description.md"
OG_IMAGE_SRC = MODELS_DIR / "og_image.png"

# --- Templates ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Cad Catalog Creator (CCC)</title>
    
    <!-- OGP Tags -->
    <meta property="og:title" content="Cad Catalog Creator (CCC)">
    <meta property="og:description" content="{{ og_description }}">
    <meta property="og:type" content="website">
    <meta property="og:url" content="{{ base_url }}">
    {% if og_image %}<meta property="og:image" content="{{ base_url }}{{ og_image }}">{% endif %}
    <meta name="twitter:card" content="summary_large_image">
    
    <style>
        body { font-family: sans-serif; margin: 40px; background: #f0f0f0; color: #333; max-width: 1200px; margin-left: auto; margin-right: auto; }
        header { margin-bottom: 40px; border-bottom: 2px solid #ccc; padding-bottom: 20px; position: relative; }
        header h1 { margin-bottom: 10px; color: #222; }
        .repo-link { position: absolute; right: 0; top: 0; font-size: 0.9em; font-weight: bold; }
        .site-description { line-height: 1.6; color: #555; }
        .site-description p { margin: 5px 0; }
        
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

        .description { font-size: 0.9em; color: #666; margin-bottom: 20px; flex-grow: 1; line-height: 1.5; }
        .description p { margin: 10px 0; }
        .links { margin-top: auto; padding-top: 10px; border-top: 1px dashed #eee; display: flex; flex-wrap: wrap; gap: 10px; }
        .links a { text-decoration: none; color: #007bff; font-size: 0.85em; font-weight: bold; }
        .links a:hover { text-decoration: underline; }
        .links .source-link { color: #28a745; }
        
        footer { margin-top: 60px; padding-top: 20px; border-top: 1px solid #ccc; font-size: 0.9em; color: #777; text-align: center; }
        footer a { color: #555; text-decoration: none; font-weight: bold; }
        footer a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <header>
        <h1>Cad Catalog Creator (CCC)</h1>
        <div class="repo-link"><a href="{{ repo_url }}" target="_blank">View on GitHub</a></div>
        <div class="site-description">
            {% if site_description %}{{ site_description|safe }}{% else %}<p>Welcome to my 3D model collection created with CCC.</p>{% endif %}
        </div>
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
            
            <div class="description">
                {% if model.description %}{{ model.description|safe }}{% else %}<p>(No description)</p>{% endif %}
            </div>
            
            <div class="links">
                {% if model.source_url %}<a href="{{ model.source_url }}" class="source-link" target="_blank">Source</a>{% endif %}
                {% if model.stl %}<a href="{{ model.stl }}">STL</a>{% endif %}
                {% if model.step %}<a href="{{ model.step }}">STEP</a>{% endif %}
            </div>
        </div>
        {% endfor %}
    </div>

    <footer>
        <p>Created by <a href="https://inajob.github.io/intro/index.html" target="_blank">inajob</a> | Powered by <a href="{{ repo_url }}" target="_blank">Cad Catalog Creator (CCC)</a></p>
    </footer>
</body>
</html>
"""

def md_to_html(text):
    if not text: return ""
    return markdown.markdown(text)

def strip_tags(html):
    """Remove HTML tags and return plain text."""
    return re.sub(r'<[^>]*>', '', html)

def generate_og_collage(models_info, output_path):
    images = []
    for m in models_info:
        if m.get("png"):
            img_path = DIST_DIR / m["png"]
            if img_path.exists(): images.append(img_path)
    if not images: return None
    W, H = 1200, 630
    canvas = Image.new('RGB', (W, H), color=(240, 240, 240))
    n = len(images)
    if n >= 8: cols, rows = 4, 2
    elif n >= 6: cols, rows = 3, 2
    elif n >= 4: cols, rows = 2, 2
    else: cols, rows = n, 1
    cell_w, cell_h = W // cols, H // rows
    for i in range(min(n, cols * rows)):
        try:
            img = Image.open(images[i])
            img.thumbnail((cell_w, cell_h), Image.Resampling.LANCZOS)
            col, row = i % cols, i // cols
            x_offset = col * cell_w + (cell_w - img.width) // 2
            y_offset = row * cell_h + (cell_h - img.height) // 2
            canvas.paste(img, (x_offset, y_offset))
        except Exception: pass
    canvas.save(output_path)
    return output_path.name

def get_source_url(file_path):
    rel_path = file_path.relative_to(Path(".")).as_posix()
    return f"{REPO_URL}/blob/main/{rel_path}"

def ensure_description(file_path):
    md_path = file_path.with_suffix(".md")
    txt_path = file_path.with_suffix(".txt")
    content = ""
    for p in [md_path, txt_path]:
        if p.exists():
            try: content = p.read_text(encoding="utf-8").strip(); break
            except Exception: pass
    if not content and not md_path.exists() and not txt_path.exists():
        content = f"{file_path.stem}\n\n(ここに説明を入力してください)"
        try: md_path.write_text(content, encoding="utf-8")
        except Exception: pass
    return md_to_html(content)

def run_command(cmd, cwd=None, env=None):
    try: subprocess.run(cmd, check=True, cwd=cwd, capture_output=True, text=True, env=env)
    except subprocess.CalledProcessError: return False
    return True

def render_png_from_stl(stl_path, png_path):
    if not stl_path.exists(): return False
    print(f"  Generating preview: {png_path.name}")
    temp_scad = stl_path.with_suffix(".temp.scad")
    stl_path_str = str(stl_path.absolute()).replace("\\", "/")
    temp_scad.write_text(f'color("{OBJECT_COLOR}") import("{stl_path_str}");', encoding="utf-8")
    success = run_command([OPENSCAD_PATH, "-o", str(png_path.absolute()), f"--colorscheme={COLOR_SCHEME}", "--imgsize=1024,1024", str(temp_scad.absolute())])
    if temp_scad.exists(): temp_scad.unlink()
    return success

def convert_scad(file_path):
    rel_path = file_path.relative_to(MODELS_DIR)
    base_name = str(rel_path.with_suffix("")).replace(os.sep, "_")
    stl_out, png_out = DIST_DIR / f"{base_name}.stl", DIST_DIR / f"{base_name}.png"
    if not all(f.exists() for f in [stl_out, png_out]) or file_path.stat().st_mtime > stl_out.stat().st_mtime:
        print(f"  Building {base_name}...")
        run_command([OPENSCAD_PATH, "-o", str(stl_out.absolute()), str(file_path.absolute())])
        run_command([OPENSCAD_PATH, "-o", str(png_out.absolute()), f"--colorscheme={COLOR_SCHEME}", "--imgsize=1024,1024", str(file_path.absolute())])
    return {"name": base_name, "stl": f"{base_name}.stl" if stl_out.exists() else None, "png": f"{base_name}.png" if png_out.exists() else None, "description": ensure_description(file_path), "source": "OpenSCAD", "source_url": get_source_url(file_path)}

def convert_py(file_path):
    rel_path = file_path.relative_to(MODELS_DIR)
    base_name = str(rel_path.with_suffix("")).replace(os.sep, "_")
    stl_out, step_out, png_out = DIST_DIR/f"{base_name}.stl", DIST_DIR/f"{base_name}.step", DIST_DIR/f"{base_name}.png"
    if not all(f.exists() for f in [stl_out, step_out, png_out]) or file_path.stat().st_mtime > stl_out.stat().st_mtime:
        print(f"  Building {base_name}...")
        wrapper_path = file_path.parent / "_build_wrapper.py"
        stl_abs, step_abs, file_abs = str(stl_out.absolute()).replace("\\", "/"), str(step_out.absolute()).replace("\\", "/"), str(file_path.absolute()).replace("\\", "/")
        wrapper_content = f'import sys, os\nfrom unittest.mock import MagicMock\nimport cadquery as cq\nsys.modules["ocp_vscode"] = MagicMock()\ndef show_object(*args, **kwargs): pass\nnamespace = {{"show_object": show_object, "cq": cq, "__name__": "__main__", "__file__": "{file_abs}"}}\nos.chdir("{str(file_path.parent.absolute()).replace("\\", "/")}")\nwith open("{file_abs}", "r", encoding="utf-8") as f: exec(f.read(), namespace)\nif "result" in namespace:\n    result = namespace["result"]\n    cq.exporters.export(result, "{stl_abs}")\n    cq.exporters.export(result, "{step_abs}")'
        wrapper_path.write_text(wrapper_content, encoding="utf-8")
        run_command([sys.executable, str(wrapper_path.absolute())])
        wrapper_path.unlink()
        if stl_out.exists(): render_png_from_stl(stl_out, png_out)
    return {"name": base_name, "stl": f"{base_name}.stl" if stl_out.exists() else None, "step": f"{base_name}.step" if step_out.exists() else None, "png": f"{base_name}.png" if png_out.exists() else None, "description": ensure_description(file_path), "source": "CadQuery", "source_url": get_source_url(file_path)}

def convert_fcstd(file_path):
    rel_path = file_path.relative_to(MODELS_DIR)
    base_name = str(rel_path.with_suffix("")).replace(os.sep, "_")
    stl_out, step_out, png_out = DIST_DIR/f"{base_name}.stl", DIST_DIR/f"{base_name}.step", DIST_DIR/f"{base_name}.png"
    if not all(f.exists() for f in [stl_out, step_out, png_out]) or file_path.stat().st_mtime > stl_out.stat().st_mtime:
        print(f"  Building {base_name}...")
        env = os.environ.copy()
        env.update({"FC_INPUT": str(file_path.absolute()), "FC_STL": str(stl_out.absolute()), "FC_STEP": str(step_out.absolute()), "FC_BIN_DIR": FREECAD_BIN_DIR})
        run_command([FREECAD_PATH, str(Path("export_freecad.py").absolute())], env=env)
        if stl_out.exists(): render_png_from_stl(stl_out, png_out)
    return {"name": base_name, "stl": f"{base_name}.stl" if stl_out.exists() else None, "step": f"{base_name}.step" if step_out.exists() else None, "png": f"{base_name}.png" if png_out.exists() else None, "description": ensure_description(file_path), "source": "FreeCAD", "source_url": get_source_url(file_path)}

def main():
    if not DIST_DIR.exists(): DIST_DIR.mkdir()
    site_desc_raw = SITE_DESC_PATH.read_text(encoding="utf-8").strip() if SITE_DESC_PATH.exists() else "Cad Catalog Creator (CCC) によって自動生成された3Dモデルカタログです。"
    if not SITE_DESC_PATH.exists(): SITE_DESC_PATH.write_text(site_desc_raw, encoding="utf-8")
    
    site_description_html = md_to_html(site_desc_raw)
    og_description = strip_tags(site_description_html)[:160].replace("\n", " ")

    models_info = []
    for scad_file in sorted(MODELS_DIR.glob("**/*.scad")): models_info.append(convert_scad(scad_file))
    for py_file in sorted(MODELS_DIR.glob("**/*.py")):
        if py_file.name in ["build.py", "export_freecad.py", "site_description.md", "og_image.png"] or py_file.name.startswith("_"): continue
        models_info.append(convert_py(py_file))
    for fcstd_file in sorted(MODELS_DIR.glob("**/*.fcstd")): models_info.append(convert_fcstd(fcstd_file))

    og_image = None
    if OG_IMAGE_SRC.exists():
        shutil.copy(OG_IMAGE_SRC, DIST_DIR / "og_image.png"); og_image = "og_image.png"
    else:
        og_image = generate_og_collage(models_info, DIST_DIR / "og_collage.png")
        if not og_image and models_info:
            for m in models_info:
                if m.get("png"): og_image = m["png"]; break

    template = Template(HTML_TEMPLATE)
    html = template.render(models=models_info, site_description=site_description_html, og_description=og_description, repo_url=REPO_URL, base_url=BASE_URL, og_image=og_image)
    (DIST_DIR / "index.html").write_text(html, encoding="utf-8")
    print(f"\nBuild complete! {len(models_info)} models cataloged.")

if __name__ == "__main__":
    main()
