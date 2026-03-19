<<<<<<< HEAD
# fbxtools
Prepare multi stack FBX animations for Unreal Engine
=======
# FBX Mocap Processing Tools

A Python-based utility for mass-processing and normalizing motion capture (mocap) libraries (e.g., Truebones, Mixamo) for modern game engines like Unreal Engine and Unity.

## 🚀 Overview
Working with large mocap libraries can be challenging due to:
1.  **Heavy Meshes**: Raw files often contain geometry that distorts and bloats the file size.
2.  **Missing Root Joints**: Unreal Engine requires a `root` joint at (0,0,0) for proper Root Motion.
3.  **Multi-Take Files**: Large libraries often pack dozens of animations into a single FBX.
4.  **Inconsistent Scaling**: Mocap data frequently swaps between centimeters and meters.

**FBX Tools** solves these problems with a single command.

## ✨ Key Features
- **Smart Splitting**: Truly isolates animation takes into individual files (reduced file size).
- **Recursive Walk**: Processes every subdirectory and mirrors the folder tree in your output.
- **Master Skeleton Automation**: Automatically keeps the mesh for the first file found (the "Master") and strips it for the rest.
- **Conditional Root Injection**: Smartly detects and adds a missing root bone only if needed.
- **Automated Verification**: Checks every exported clip for the root node and logs the status.
- **Detailed Logging**: Records every source file and its resulting clips in `conversion_log.txt`.

## ⚙️ Installation
1.  **FBX Python SDK**: Download and install the Autodesk FBX Python SDK from the [official Autodesk site](https://www.autodesk.com/developer-network/platform-technologies/fbx-sdk-2020-3).
2.  **FbxCommon.py**: Locate `FbxCommon.py` within your FBX SDK's `samples` folder and **place it in the same directory** as `fbxtools.py`. This is a mandatory dependency for the SDK's basic functions.
3.  **Python Path**: Ensure your Python interpreter can find the `fbx` module (the FBX SDK installer usually handles this, or you can manually copy the `fbx` module files from the SDK installation to your Python's `site-packages`).
4.  **Python Version**: 3.8+ is recommended. 

## 🛠 Usage

### 1. One-Click Batch (Local)
For processing everything in a local `input/` folder and sending to `output/`:
```bash
python fbxtools.py
```

### 2. Unreal Engine Preset (`prepUE`)
Optimized for UE with automated root injection and 0.01 scaling (m to cm). It automatically treats the first file as the "Master Skeleton":
```bash
python fbxtools.py prepUE -i "D:\Mocap\MyLibrary" -o "D:\CleanedClips"
```

### 3. Standard Processing
For manual control over flags:
```bash
python fbxtools.py process -i input_dir -o output_dir --rescale 0.1 --add-root --show-fps
```

## 📖 Command Options
- `-i, --input`: Source directory (scanned recursively).
- `-o, --output`: Target directory for cleaned clips.
- `--add-root`: Force injection of a `root` bone at (0,0,0) as a parent of the `Hips`.
- `--rescale [factor]`: Scale factor (0.01 for UE, 100 for cm-to-m).
- `--keep-mesh`: Keep the mesh geometry (useful for master skeletons).
- `--show-fps`: Report the framerate of your clips in console/log.
- `--list-skeleton`: Print a visual tree of the joint hierarchy.
- `--limit [N]`: Only process the first N animation takes (speeds up testing).

## 📋 Verification & Logging
Every run generates/appends to `conversion_log.txt` in your output directory.

**Example Log Entry:**
```text
[2026-03-19 09:00:00]
  SOURCE: D:\Mocap\Truebones\Adept.fbx
  *** UE MASTER SKELETON (Mesh Kept) ***
  EXTRACTED CLIPS:
    - [ROOT OK] Adept_Run.fbx
    - [ROOT OK] Adept_Idle.fbx
```

## 🧪 Testing
The included `test_fbxtools.py` is a high-speed suite to verify the logic. To run:
```bash
python test_fbxtools.py
```
*(Requires a sample FBX in the input folder named `01-09-FBX.fbx`)*

---
**Maintained by:** Antigravity AI
>>>>>>> 7f29e0d (Final version of fbxtools utility with true splitting and UE smart-chain features)
