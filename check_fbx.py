import fbx
import os
import sys

def check_integrity(file_path):
    manager = fbx.FbxManager.Create()
    scene = fbx.FbxScene.Create(manager, "Scene")
    importer = fbx.FbxImporter.Create(manager, "")
    
    print(f"\n--- INTEGRITY CHECK: {file_path} ---")
    if not importer.Initialize(file_path, -1, manager.GetIOSettings()):
        print("FAIL: Importer could not initialize.")
        return False

    if not importer.Import(scene):
        print("FAIL: Scene could not be imported.")
        return False
        
    print(f"File Version: {importer.GetFileVersion()}")
    
    # 1. Count All Objects
    root = scene.GetRootNode()
    mesh_count = scene.GetSrcObjectCount(fbx.FbxCriteria.ObjectType(fbx.FbxMesh.ClassId))
    stack_count = scene.GetSrcObjectCount(fbx.FbxCriteria.ObjectType(fbx.FbxAnimStack.ClassId))
    layer_count = scene.GetSrcObjectCount(fbx.FbxCriteria.ObjectType(fbx.FbxAnimLayer.ClassId))
    curve_count = scene.GetSrcObjectCount(fbx.FbxCriteria.ObjectType(fbx.FbxAnimCurve.ClassId))
    node_count = scene.GetSrcObjectCount(fbx.FbxCriteria.ObjectType(fbx.FbxNode.ClassId))
    skin_count = scene.GetSrcObjectCount(fbx.FbxCriteria.ObjectType(fbx.FbxSkin.ClassId))

    print(f"\nOBJECT COUNTS:")
    print(f"  Nodes (Bones/Empty): {node_count}")
    print(f"  Meshes: {mesh_count}")
    print(f"  Skins (Weights): {skin_count}")
    print(f"  Anim Stacks (Takes): {stack_count}")
    print(f"  Anim Layers: {layer_count}")
    print(f"  Anim Curves: {curve_count}")

    # 2. Check for Point Caches
    cache_count = scene.GetSrcObjectCount(fbx.FbxCriteria.ObjectType(fbx.FbxCache.ClassId))
    print(f"  Point Caches: {cache_count}")

    # 3. Check node hierarchy for anything strange
    print("\nTOP LEVEL NODES:")
    for i in range(root.GetChildCount()):
        child = root.GetChild(i)
        print(f"  - {child.GetName()} ({child.GetTypeName()})")

    importer.Destroy()
    manager.Destroy()
    return True

if __name__ == "__main__":
    target = "input/01-09-FBX.fbx"
    if os.path.exists(target):
        check_integrity(target)
    else:
        print(f"Target file not found: {target}")
