import os
import subprocess
import shutil
import sys
import re
import struct
import math
import zipfile
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

FREECAD_BIN_DIR = os.getenv("FREECAD_BIN_DIR", "")

def resolve_openscad_command():
    """Prefer OPENSCAD_PATH if it points to a real binary, else find openscad on PATH."""
    configured = os.environ.get("OPENSCAD_PATH")
    if configured and shutil.which(configured):
        return configured
    for cand in ("openscad", "openscad-nightly"):
        if shutil.which(cand):
            return cand
    return "openscad"

def resolve_freecad_command():
    """Prefer FreeCAD's own interpreter; its python bindings are guaranteed to load there."""
    configured = os.environ.get("FREECAD_PYTHON_PATH")
    if configured and shutil.which(configured):
        return configured
    for cand in ("freecadcmd", "FreeCADCmd", "python"):
        if shutil.which(cand):
            return cand
    return "python"

OPENSCAD_PATH = resolve_openscad_command()
FREECAD_PATH = resolve_freecad_command()

# Preview settings
COLOR_SCHEME = "DeepOcean" 
OBJECT_COLOR = "CornflowerBlue"

# Preview rendering
BLANK_VARIANCE_THRESHOLD = 40.0
FRAME_FILL_RATIO = 0.92

MODELS_DIR = Path("models")
DIST_DIR = Path("dist")
SITE_DESC_PATH = MODELS_DIR / "site_description.md"
OG_IMAGE_SRC = MODELS_DIR / "og_image.png"

# --- Templates ---
STYLE = """
    body { font-family: sans-serif; margin: 40px; background: #f0f0f0; color: #333; max-width: 1200px; margin-left: auto; margin-right: auto; }
    header { margin-bottom: 30px; border-bottom: 2px solid #ccc; padding-bottom: 20px; position: relative; }
    header h1 { margin-bottom: 10px; color: #222; }
    .repo-link { position: absolute; right: 0; top: 0; font-size: 0.9em; font-weight: bold; }
    .breadcrumb { font-size: 0.85em; color: #888; margin-bottom: 15px; }
    .breadcrumb a { color: #007bff; text-decoration: none; }
    .breadcrumb a:hover { text-decoration: underline; }
    .site-description { line-height: 1.6; color: #555; }
    .site-description p { margin: 5px 0; }
    .dir-title { margin: 40px 0 10px 0; padding-top: 20px; border-top: 2px solid #ccc; color: #222; }
    .dir-title:first-of-type { border-top: none; padding-top: 0; margin-top: 0; }
    .dir-title a { color: #222; text-decoration: none; }
    .dir-title a:hover { text-decoration: underline; }
    .dir-description { color: #777; font-size: 0.9em; margin-bottom: 15px; line-height: 1.5; }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 30px; }
    .card { background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); display: flex; flex-direction: column; position: relative; }
    .card img { max-width: 100%; height: auto; border-radius: 4px; background: #eee; min-height: 100px; object-fit: contain; }
    .card h3 { margin: 15px 0 5px 0; font-size: 1.1em; word-break: break-all; border-bottom: 1px solid #eee; padding-bottom: 5px; }
    .card h3 a { color: #222; text-decoration: none; }
    .card h3 a:hover { text-decoration: underline; }
    .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.75em; font-weight: bold; margin-bottom: 10px; }
    .badge-openscad { background: #fff3cd; color: #856404; border: 1px solid #ffeeba; }
    .badge-freecad { background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }
    .badge-cadquery { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
    .description { font-size: 0.9em; color: #666; margin-bottom: 20px; flex-grow: 1; line-height: 1.5; }
    .description p { margin: 10px 0; }
    .links { margin-top: auto; padding-top: 10px; border-top: 1px dashed #eee; display: flex; flex-wrap: wrap; gap: 10px; }
    .links a { text-decoration: none; color: #007bff; font-size: 0.85em; font-weight: bold; }
    .links a:hover { text-decoration: underline; }
    .links .source-link { color: #28a745; }
    .no-preview { height: 200px; background: #ddd; display: flex; align-items: center; justify-content: center; color: #666; }
    .viewer-wrap { margin: 20px 0; }
    .viewer { width: 100%; height: 480px; border: 1px solid #ddd; border-radius: 8px; }
    .preview-wrap { margin: 10px 0; }
    .preview-img { max-width: 100%; border-radius: 8px; }
    .nav-prev-next { display: flex; justify-content: space-between; margin: 40px 0 20px; gap: 20px; }
    .nav-prev-next a { color: #007bff; text-decoration: none; font-weight: bold; }
    .nav-prev-next a:hover { text-decoration: underline; }
    footer { margin-top: 60px; padding-top: 20px; border-top: 1px solid #ccc; font-size: 0.9em; color: #777; text-align: center; }
    footer a { color: #555; text-decoration: none; font-weight: bold; }
    footer a:hover { text-decoration: underline; }
"""

CARD_MACRO = """
{% macro model_card(model) %}
<div class="card">
    <a href="{{ model.link }}">{% if model.img %}<img src="{{ model.img }}" alt="{{ model.name }}">{% else %}<div class="no-preview">No Preview</div>{% endif %}</a>
    <h3><a href="{{ model.link }}">{{ model.name }}</a></h3>
    <div><span class="badge badge-{{ model.source|lower }}">{{ model.source }}</span></div>
    <div class="description">{% if model.description %}{{ model.description|safe }}{% else %}<p>(No description)</p>{% endif %}</div>
    <div class="links">
        {% if model.source_url %}<a href="{{ model.source_url }}" class="source-link" target="_blank">Source</a>{% endif %}
        {% if model.stl %}<a href="{{ model.stl }}">STL</a>{% endif %}
        {% if model.step %}<a href="{{ model.step }}">STEP</a>{% endif %}
        <a href="{{ model.link }}">Page</a>
    </div>
</div>
{% endmacro %}
"""

INDEX_TEMPLATE = CARD_MACRO + """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Cad Catalog Creator (CCC)</title>
    <meta property="og:title" content="Cad Catalog Creator (CCC)">
    <meta property="og:description" content="{{ og_description }}">
    <meta property="og:type" content="website">
    <meta property="og:url" content="{{ base_url }}">
    {% if og_image %}<meta property="og:image" content="{{ base_url }}{{ og_image }}">{% endif %}
    <meta name="twitter:card" content="summary_large_image">
    <style>{{ style }}</style>
</head>
<body>
    <header>
        <h1>Cad Catalog Creator (CCC)</h1>
        <div class="repo-link"><a href="{{ repo_url }}" target="_blank">View on GitHub</a></div>
        <div class="site-description">
            {% if site_description %}{{ site_description|safe }}{% else %}<p>Welcome to my 3D model collection created with CCC.</p>{% endif %}
        </div>
    </header>

    {% for group in groups %}
    <section>
        <h2 class="dir-title">{% if group.dir %}<a href="{{ group.dir }}/">{% endif %}{{ group.title }}{% if group.dir %}</a>{% endif %}</h2>
        {% if group.description %}<div class="dir-description">{{ group.description|safe }}</div>{% endif %}
        <div class="grid">
            {% for model in group.models %}
            {{ model_card(model) }}
            {% endfor %}
        </div>
    </section>
    {% endfor %}

    <footer>
        <p>Created by <a href="https://inajob.github.io/intro/index.html" target="_blank">inajob</a> | Powered by <a href="{{ repo_url }}" target="_blank">Cad Catalog Creator (CCC)</a></p>
    </footer>
</body>
</html>
"""

DIR_TEMPLATE = CARD_MACRO + """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{{ dir_name }} - Cad Catalog Creator (CCC)</title>
    <meta property="og:title" content="{{ dir_name }}">
    <meta property="og:type" content="website">
    <meta property="og:url" content="{{ og_url }}">
    {% if og_image %}<meta property="og:image" content="{{ og_image }}">{% endif %}
    <meta name="twitter:card" content="summary_large_image">
    <style>{{ style }}</style>
</head>
<body>
    <header>
        <div class="breadcrumb"><a href="../index.html">Top</a> &gt; {{ dir_name }}</div>
        <h1>{{ dir_name }}</h1>
        {% if dir_description %}<div class="site-description">{{ dir_description|safe }}</div>{% endif %}
    </header>

    <div class="grid">
        {% for model in models %}
        {{ model_card(model) }}
        {% endfor %}
    </div>

    <footer>
        <p><a href="../index.html">← Top</a> | Powered by <a href="{{ repo_url }}" target="_blank">Cad Catalog Creator (CCC)</a></p>
    </footer>
</body>
</html>
"""

MODEL_TEMPLATE = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{{ model.name }} - Cad Catalog Creator (CCC)</title>
    <meta property="og:title" content="{{ model.name }}">
    <meta property="og:description" content="{{ og_description }}">
    <meta property="og:type" content="article">
    <meta property="og:url" content="{{ og_url }}">
    {% if og_image %}<meta property="og:image" content="{{ og_image }}">{% endif %}
    <meta name="twitter:card" content="summary_large_image">
    <style>{{ style }}</style>
</head>
<body>
    <header>
        <div class="breadcrumb">
            <a href="{{ top_href }}">Top</a>{% if model.dir %} &gt; <a href="{{ dir_href }}">{{ model.dir }}</a>{% endif %} &gt; {{ model.name }}
        </div>
        <h1>{{ model.name }}</h1>
        <div><span class="badge badge-{{ model.source|lower }}">{{ model.source }}</span></div>
    </header>

    {% if viewer_url %}
    <div class="viewer-wrap">
        <iframe class="viewer" src="{{ viewer_url }}" allowfullscreen></iframe>
    </div>
    {% endif %}

    {% if model.png %}
    <div class="preview-wrap">
        <img class="preview-img" src="{{ model.png }}" alt="{{ model.name }}">
    </div>
    {% else %}
    <div class="no-preview">No Preview</div>
    {% endif %}

    <div class="description">
        {% if model.description %}{{ model.description|safe }}{% else %}<p>(No description)</p>{% endif %}
    </div>

    <div class="links">
        {% if model.stl %}<a href="{{ model.stl }}">STL</a>{% endif %}
        {% if model.step %}<a href="{{ model.step }}">STEP</a>{% endif %}
        {% if model.source_url %}<a href="{{ model.source_url }}" class="source-link" target="_blank">Source</a>{% endif %}
    </div>

    {% if prev or next %}
    <div class="nav-prev-next">
        <div class="nav-prev">{% if prev %}<a href="{{ prev.href }}">← {{ prev.name }}</a>{% endif %}</div>
        <div class="nav-next">{% if next %}<a href="{{ next.href }}">{{ next.name }} →</a>{% endif %}</div>
    </div>
    {% endif %}

    <footer>
        <p><a href="{{ back_href }}">← 戻る</a> | Powered by <a href="{{ repo_url }}" target="_blank">Cad Catalog Creator (CCC)</a></p>
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

def model_targets(file_path):
    """Compute nested output paths and asset names for a model file.

    Returns (dir_name, stem, out_dir, page_url, asset_prefix). Assets live
    beside the model page: dist/<dir>/<stem>/<stem>.{stl,step,png}.
    """
    rel_path = file_path.relative_to(MODELS_DIR)
    dir_name = rel_path.parent.as_posix()
    if dir_name == ".":
        dir_name = ""
    stem = rel_path.stem
    out_dir = DIST_DIR / dir_name / stem
    out_dir.mkdir(parents=True, exist_ok=True)
    page_url = f"{dir_name}/{stem}/" if dir_name else f"{stem}/"
    asset_prefix = f"{dir_name}/{stem}/{stem}" if dir_name else f"{stem}/{stem}"
    return dir_name, stem, out_dir, page_url, asset_prefix

def prepare_models(models, base):
    """Resolve per-view card link/image/download paths for a page.

    base="" renders cards for the index page at dist/;
    base=<dir> renders cards for dist/<dir>/index.html.
    """
    prepared = []
    for m in models:
        d = dict(m)
        if base:
            d["link"] = f"{m['stem']}/"
            d["img"] = f"{m['stem']}/{m['stem']}.png" if m.get("png") else None
            d["stl"] = f"{m['stem']}/{m['stem']}.stl" if m.get("stl") else None
            d["step"] = f"{m['stem']}/{m['stem']}.step" if m.get("step") else None
        else:
            d["link"] = m["page_url"]
            d["img"] = m.get("png")
            d["stl"] = m.get("stl")
            d["step"] = m.get("step")
        prepared.append(d)
    return prepared

def get_dir_description(dir_name):
    if not dir_name:
        return ""
    for p in (MODELS_DIR / dir_name / "_index.md", MODELS_DIR / dir_name / "_index.txt"):
        if p.exists():
            try:
                return md_to_html(p.read_text(encoding="utf-8").strip())
            except Exception:
                return ""
    return ""

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
    try:
        subprocess.run(cmd, check=True, cwd=cwd, capture_output=True, text=True, env=env)
    except subprocess.CalledProcessError as e:
        if e.stderr and e.stderr.strip():
            print(f"  [error] {' '.join(cmd)} failed:\n{e.stderr.strip()}")
        return False
    except OSError as e:
        print(f"  [error] could not run {' '.join(cmd)}: {e}")
        return False
    return True

def is_blank_image(png_path):
    """True if the PNG looks like a blank/uniform image (model not visible)."""
    if not png_path.exists() or png_path.stat().st_size == 0:
        return True
    try:
        img = Image.open(png_path).convert("L").resize((128, 128))
        px = list(img.getdata())
        n = len(px)
        mean = sum(px) / n
        var = sum((v - mean) ** 2 for v in px) / n
        return var < BLANK_VARIANCE_THRESHOLD
    except Exception:
        return True

def frame_content(png_path, bg_threshold=20, fill_ratio=FRAME_FILL_RATIO):
    """Trim uniform background margins and center the model in the frame."""
    try:
        img = Image.open(png_path).convert("RGB")
    except Exception:
        return
    w, h = img.size
    scale = max(1, min(w, h) // 512)
    small = img.resize((w // scale, h // scale), Image.Resampling.LANCZOS)
    spx = small.load()
    sw, sh = small.size
    bg = tuple(sum(spx[x, y][c] for x, y in [(0, 0), (sw - 1, 0), (0, sh - 1), (sw - 1, sh - 1)]) // 4 for c in range(3))
    min_x, min_y, max_x, max_y = sw, sh, -1, -1
    th2 = bg_threshold ** 2
    for y in range(sh):
        for x in range(sw):
            r, g, b = spx[x, y]
            if (r - bg[0]) ** 2 + (g - bg[1]) ** 2 + (b - bg[2]) ** 2 > th2:
                if x < min_x: min_x = x
                if x > max_x: max_x = x
                if y < min_y: min_y = y
                if y > max_y: max_y = y
    if max_x < min_x:
        return
    box = (min_x * scale, min_y * scale, min((max_x + 1) * scale, w), min((max_y + 1) * scale, h))
    crop = img.crop(box)
    target = int(min(w, h) * fill_ratio)
    r = target / max(crop.width, crop.height)
    if r > 1:
        crop = crop.resize((max(1, int(crop.width * r)), max(1, int(crop.height * r))), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (w, h), bg)
    canvas.paste(crop, ((w - crop.width) // 2, (h - crop.height) // 2))
    canvas.save(png_path)

def render_scad_png(scad_path, png_path):
    """Render a .scad file to a preview PNG, retrying until the model is visible."""
    if not scad_path.exists():
        return False
    print(f"  Generating preview: {png_path.name}")
    base = [OPENSCAD_PATH, "-o", str(png_path.absolute()), f"--colorscheme={COLOR_SCHEME}", "--imgsize=1024,1024", "--autocenter", "--viewall"]
    src = str(scad_path.absolute())
    for extra in (None, "--projection=ortho"):
        cmd = base + ([extra] if extra else [])
        if not run_command(cmd + [src]):
            continue
        if is_blank_image(png_path):
            continue
        frame_content(png_path)
        return True
    return False

def render_png_from_stl(stl_path, png_path):
    if not stl_path.exists() or stl_path.stat().st_size == 0:
        return False
    temp_scad = stl_path.with_suffix(".temp.scad")
    stl_path_str = str(stl_path.absolute()).replace("\\", "/")
    temp_scad.write_text(f'color("{OBJECT_COLOR}") import("{stl_path_str}");', encoding="utf-8")
    try:
        return render_scad_png(temp_scad, png_path)
    finally:
        if temp_scad.exists(): temp_scad.unlink()

def find_fallback_stl(model_dir):
    """Return a non-empty STL already present in the model directory, if any."""
    for pattern in ("*Body*.stl", "*.stl"):
        for p in sorted(model_dir.glob(pattern)):
            if p.exists() and p.stat().st_size > 0:
                return p
    return None

def extract_fcstd_thumbnail(fcstd_path, png_path):
    """Extract the thumbnail embedded in a .FCStd file as a fallback preview."""
    try:
        with zipfile.ZipFile(fcstd_path) as z:
            thumb = z.read("thumbnails/Thumbnail.png")
        png_path.write_bytes(thumb)
        return png_path
    except Exception:
        return None

def convert_scad(file_path):
    dir_name, stem, out_dir, page_url, asset_prefix = model_targets(file_path)
    stl_out, png_out = out_dir / f"{stem}.stl", out_dir / f"{stem}.png"
    if not all(f.exists() for f in [stl_out, png_out]) or file_path.stat().st_mtime > stl_out.stat().st_mtime:
        print(f"  Building {page_url}...")
        run_command([OPENSCAD_PATH, "-o", str(stl_out.absolute()), str(file_path.absolute())])
        if stl_out.exists() and stl_out.stat().st_size == 0:
            stl_out.unlink()
        ok = render_scad_png(file_path, png_out)
        if not ok and png_out.exists():
            png_out.unlink()
    stl = f"{asset_prefix}.stl" if stl_out.exists() and stl_out.stat().st_size > 0 else None
    png = f"{asset_prefix}.png" if png_out.exists() and png_out.stat().st_size > 0 else None
    return {"name": stem, "dir": dir_name, "stem": stem, "page_url": page_url, "stl": stl, "png": png, "description": ensure_description(file_path), "source": "OpenSCAD", "source_url": get_source_url(file_path)}

def convert_py(file_path):
    dir_name, stem, out_dir, page_url, asset_prefix = model_targets(file_path)
    stl_out, step_out, png_out = out_dir/f"{stem}.stl", out_dir/f"{stem}.step", out_dir/f"{stem}.png"
    if not all(f.exists() for f in [stl_out, png_out]) or file_path.stat().st_mtime > stl_out.stat().st_mtime:
        print(f"  Building {page_url}...")
        wrapper_path = file_path.parent / "_build_wrapper.py"
        stl_abs, step_abs, file_abs = str(stl_out.absolute()).replace("\\", "/"), str(step_out.absolute()).replace("\\", "/"), str(file_path.absolute()).replace("\\", "/")
        wrapper_content = f'import sys, os\nfrom unittest.mock import MagicMock\nimport cadquery as cq\nsys.modules["ocp_vscode"] = MagicMock()\ndef show_object(*args, **kwargs): pass\nnamespace = {{"show_object": show_object, "cq": cq, "__name__": "__main__", "__file__": "{file_abs}"}}\nos.chdir("{str(file_path.parent.absolute()).replace("\\", "/")}")\nwith open("{file_abs}", "r", encoding="utf-8") as f: exec(f.read(), namespace)\nif "result" in namespace:\n    result = namespace["result"]\n    cq.exporters.export(result, "{stl_abs}")\n    cq.exporters.export(result, "{step_abs}")'
        wrapper_path.write_text(wrapper_content, encoding="utf-8")
        run_command([sys.executable, str(wrapper_path.absolute())])
        wrapper_path.unlink()
        if not stl_out.exists() or stl_out.stat().st_size == 0:
            fallback = find_fallback_stl(file_path.parent)
            if fallback:
                print(f"  Export produced no STL; using existing {fallback.name}")
                shutil.copy(fallback, stl_out)
        if stl_out.exists() and stl_out.stat().st_size > 0:
            ok = render_png_from_stl(stl_out, png_out)
            if not ok and png_out.exists():
                png_out.unlink()
    stl = f"{asset_prefix}.stl" if stl_out.exists() and stl_out.stat().st_size > 0 else None
    step = f"{asset_prefix}.step" if step_out.exists() and step_out.stat().st_size > 0 else None
    png = f"{asset_prefix}.png" if png_out.exists() and png_out.stat().st_size > 0 else None
    return {"name": stem, "dir": dir_name, "stem": stem, "page_url": page_url, "stl": stl, "step": step, "png": png, "description": ensure_description(file_path), "source": "CadQuery", "source_url": get_source_url(file_path)}

def convert_fcstd(file_path):
    dir_name, stem, out_dir, page_url, asset_prefix = model_targets(file_path)
    stl_out, step_out, png_out = out_dir/f"{stem}.stl", out_dir/f"{stem}.step", out_dir/f"{stem}.png"
    if not all(f.exists() for f in [stl_out, png_out]) or file_path.stat().st_mtime > stl_out.stat().st_mtime:
        print(f"  Building {page_url}...")
        env = os.environ.copy()
        env.update({"FC_INPUT": str(file_path.absolute()), "FC_STL": str(stl_out.absolute()), "FC_STEP": str(step_out.absolute()), "FC_BIN_DIR": FREECAD_BIN_DIR})
        run_command([FREECAD_PATH, str(Path("export_freecad.py").absolute())], env=env)
        if not stl_out.exists() or stl_out.stat().st_size == 0:
            fallback = find_fallback_stl(file_path.parent)
            if fallback:
                print(f"  Export produced no STL; using existing {fallback.name}")
                shutil.copy(fallback, stl_out)
        if stl_out.exists() and stl_out.stat().st_size > 0:
            ok = render_png_from_stl(stl_out, png_out)
        else:
            ok = False
        if not ok:
            if png_out.exists():
                png_out.unlink()
            if extract_fcstd_thumbnail(file_path, png_out):
                ok = True
                print(f"  Using embedded FreeCAD thumbnail as preview")
    stl = f"{asset_prefix}.stl" if stl_out.exists() and stl_out.stat().st_size > 0 else None
    step = f"{asset_prefix}.step" if step_out.exists() and step_out.stat().st_size > 0 else None
    png = f"{asset_prefix}.png" if png_out.exists() and png_out.stat().st_size > 0 else None
    return {"name": stem, "dir": dir_name, "stem": stem, "page_url": page_url, "stl": stl, "step": step, "png": png, "description": ensure_description(file_path), "source": "FreeCAD", "source_url": get_source_url(file_path)}

def main():
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    DIST_DIR.mkdir()
    site_desc_raw = SITE_DESC_PATH.read_text(encoding="utf-8").strip() if SITE_DESC_PATH.exists() else "Cad Catalog Creator (CCC) によって自動生成された3Dモデルカタログです。"
    if not SITE_DESC_PATH.exists(): SITE_DESC_PATH.write_text(site_desc_raw, encoding="utf-8")

    site_description_html = md_to_html(site_desc_raw)
    og_description = strip_tags(site_description_html)[:160].replace("\n", " ")

    models_info = []
    for scad_file in sorted(MODELS_DIR.glob("**/*.scad")): models_info.append(convert_scad(scad_file))
    for py_file in sorted(MODELS_DIR.glob("**/*.py")):
        if py_file.name in ["build.py", "export_freecad.py", "site_description.md", "og_image.png"] or py_file.name.startswith("_"): continue
        models_info.append(convert_py(py_file))
    for fcstd_file in sorted(MODELS_DIR.glob("**/*.FCStd")): models_info.append(convert_fcstd(fcstd_file))

    og_image = None
    if OG_IMAGE_SRC.exists():
        shutil.copy(OG_IMAGE_SRC, DIST_DIR / "og_image.png"); og_image = "og_image.png"
    else:
        og_image = generate_og_collage(models_info, DIST_DIR / "og_collage.png")
        if not og_image and models_info:
            for m in models_info:
                if m.get("png"): og_image = m["png"]; break

    groups = {}
    for m in models_info:
        groups.setdefault(m["dir"], []).append(m)
    ordered_dirs = sorted(groups, key=lambda d: ("\uffff" if d == "" else d))

    index_groups = [{"dir": d, "title": d or "その他", "description": get_dir_description(d), "models": prepare_models(groups[d], "")} for d in ordered_dirs]
    index_html = Template(INDEX_TEMPLATE).render(groups=index_groups, site_description=site_description_html, og_description=og_description, repo_url=REPO_URL, base_url=BASE_URL, og_image=og_image, style=STYLE)
    (DIST_DIR / "index.html").write_text(index_html, encoding="utf-8")

    for d in ordered_dirs:
        dir_html = Template(DIR_TEMPLATE).render(dir_name=d or "その他", dir_description=get_dir_description(d), models=prepare_models(groups[d], d), repo_url=REPO_URL, og_url=f"{BASE_URL}{d}/" if d else BASE_URL, og_image=og_image, style=STYLE)
        if d:
            (DIST_DIR / d / "index.html").write_text(dir_html, encoding="utf-8")
        else:
            print(f"  [warning] root-level model pages generated without a directory page")

    for d in ordered_dirs:
        dm = groups[d]
        for idx, m in enumerate(dm):
            prev = dm[idx - 1] if idx > 0 else None
            next_m = dm[idx + 1] if idx < len(dm) - 1 else None
            og_url = f"{BASE_URL}{m['page_url']}"
            og_image_m = f"{BASE_URL}{m['png']}" if m.get("png") else None
            viewer_url = f"https://3dviewer.net/embed.html#model={BASE_URL}{m['page_url']}{m['stem']}.stl" if m.get("stl") else None
            ctx = {
                "model": {
                    "name": m["name"],
                    "dir": m["dir"],
                    "source": m["source"],
                    "description": m["description"],
                    "png": f"{m['stem']}.png" if m.get("png") else None,
                    "stl": f"{m['stem']}.stl" if m.get("stl") else None,
                    "step": f"{m['stem']}.step" if m.get("step") else None,
                    "source_url": m["source_url"],
                },
                "og_url": og_url,
                "og_image": og_image_m,
                "og_description": strip_tags(m.get("description") or "")[:200],
                "viewer_url": viewer_url,
                "top_href": "../../index.html" if m["dir"] else "../index.html",
                "dir_href": "../index.html",
                "back_href": "../index.html",
                "prev": {"name": prev["name"], "href": f"{prev['stem']}/"} if prev else None,
                "next": {"name": next_m["name"], "href": f"{next_m['stem']}/"} if next_m else None,
                "repo_url": REPO_URL,
                "style": STYLE,
            }
            model_html = Template(MODEL_TEMPLATE).render(**ctx)
            page_dir = DIST_DIR / m["dir"] / m["stem"] if m["dir"] else DIST_DIR / m["stem"]
            page_dir.mkdir(parents=True, exist_ok=True)
            (page_dir / "index.html").write_text(model_html, encoding="utf-8")

    print(f"\nBuild complete! {len(models_info)} models in {len(ordered_dirs)} directories.")

if __name__ == "__main__":
    main()
