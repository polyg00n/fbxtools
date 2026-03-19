# FBX Mocap Processing Tools

A professional Python-based utility for mass-processing and normalizing motion capture (mocap) libraries (e.g., Truebones, Mixamo) for modern game engines like Unreal Engine 5.

## 🚀 Overview
**FBX Tools** provides a resilient pipeline for cleaning raw mocap data. It utilizes a custom **ASCII Surgical Splitter** to bypass binary serialisation bugs in the FBX SDK, ensuring 100% reliable file-size reduction when splitting multi-take animation files.

## 🛠 Command Reference

### Subcommands
The script uses a subparser architecture. You must provide a subcommand before any subcommand-specific flags.

#### 1. `process`
Standard recursive batch processing. Inherits all global arguments.
```bash
python fbxtools.py process -i input/ -o output/ --audit
```

#### 2. `prepUE`
Optimized for Unreal Engine workflows. 
- **Default Presets**: Automatically attempts to inject a `root` bone and sets the rescale factor to `1.0`.
- **Master Skeleton**: Automatically keeps the mesh for the first file processed in the batch (initializing your `USkeleton` asset) and strips it for the rest.
```bash
python fbxtools.py prepUE --inject-proxy
```

## 📖 Global Arguments
These arguments are shared between `process` and `prepUE` via a parent parser:

- **`-i, --input`**: Source folder for raw FBX files (default: `input`).
- **`-o, --output`**: Target folder for processed assets (default: `output`).
- **`--audit`**: Generates a technical report on mesh counts and `FbxSkin` binding status.
- **`--inject-proxy`**: Injects a 1x1x1 cube bound to the first joint (e.g., Hips). Required for establishing a `USkeleton` in Unreal when only animation data is present.
- **`--add-root`**: Force injection of a `root` joint at (0,0,0) as a parent to the `Hips`.
- **`--rescale [float]`**: Multiply scene scale (default: 1.0).
- **`--keep-mesh`**: Disables the automated mesh stripping (keeps geometry for all files).
- **`--limit [int]`**: Limits processing to the first N animation clips discovered in the source.
- **`--list-skeleton`**: Prints a technical hierarchy tree of the skeletal joints.
- **`--show-fps`**: Reports the framerate and TimeMode of the source file.
- **`--rename-find [str]`**: Search string for node renaming.
- **`--rename-replace [str]`**: Replacement string for node renaming.

## 📋 Subcommand Specific Arguments

### `prepUE`
- **`--no-root`**: Overrides the `prepUE` default to disable root joint injection.

## 🏗 Key Workflows

### The "Skeleton-Only" Unreal Import
If you have a folder of animations without meshes, use this specialized command to generate a placeholder master:
1.  **Command**: `python fbxtools.py prepUE --inject-proxy`
2.  **Unreal Result**: You will get a `_Skel.fbx` file. Import this first to create your `Skeletal Mesh` and `Skeleton` assets.
3.  **Animation Import**: Target all subsequent `_Split.fbx` files to the skeleton created in step 2.

### Mesh Audit Verification
To verify if your files are properly bound before a production run:
```bash
python fbxtools.py process --audit
```

---
**Technical Maintainer:** Antigravity AI
