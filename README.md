# Cad Catalog Creator (CCC)

CCC is a lightweight static site generator (SSG) framework designed to transform your 3D CAD models into a beautiful, web-based catalog.

## Features

- **Multi-Format Support**: Automatically converts `.scad` (OpenSCAD), `.py` (CadQuery), and `.fcstd` (FreeCAD) files.
- **Incremental Build**: Only rebuilds models that have changed, saving time.
- **Automated Previews**: Generates PNG previews for all models using OpenSCAD as a rendering engine.
- **Description Management**: Automatically generates and includes descriptions from `.md` or `.txt` files.
- **GitHub Actions Ready**: Built-in workflow for automatic deployment to GitHub Pages with no history bloating.

## Project Structure

- `models/`: Place your CAD files here.
- `build.py`: The main build script.
- `export_freecad.py`: Helper script for FreeCAD conversion.
- `dist/`: The generated static site (ignored by Git).

## Quick Start

1. Clone this repository.
2. Set up your `.env` file with paths to `openscad` and `FreeCAD`'s python interpreter.
3. Run the build script:
   ```bash
   python build.py
   ```
4. Open `dist/index.html` to view your catalog.

## License

MIT
