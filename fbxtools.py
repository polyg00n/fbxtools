import argparse
import os
import fbx
import FbxCommon

def cleanup_meshes(node):
    """Recursively removes mesh attributes from nodes to leave only the skeleton."""
    if not node:
        return

    # Check if the node has a mesh attribute
    attribute = node.GetNodeAttribute()
    if attribute and attribute.GetAttributeType() == fbx.FbxNodeAttribute.EType.eMesh:
        # Remove the mesh attribute but keep the node (it might be a joint/transform)
        node.RemoveNodeAttribute(attribute)

    # Recursively check children
    for i in range(node.GetChildCount()):
        cleanup_meshes(node.GetChild(i))

def get_framerate(scene):
    """Returns the framerate as a string based on the scene's GlobalSettings."""
    lGlobalSettings = scene.GetGlobalSettings()
    time_mode = lGlobalSettings.GetTimeMode()
    
    # Mapping of common FBX TimeModes to FPS strings
    modes = {
        fbx.FbxTime.EMode.eFrames120: "120",
        fbx.FbxTime.EMode.eFrames100: "100",
        fbx.FbxTime.EMode.eFrames60: "60",
        fbx.FbxTime.EMode.eFrames50: "50",
        fbx.FbxTime.EMode.eFrames30: "30",
        fbx.FbxTime.EMode.eFrames30Drop: "30 (Drop)",
        fbx.FbxTime.EMode.eNTSCFramerate: "29.97",
        fbx.FbxTime.EMode.ePAL: "25",
        fbx.FbxTime.EMode.eCinema: "24",
        fbx.FbxTime.EMode.eCustom: "Custom"
    }
    return modes.get(time_mode, "Unknown")

def print_hierarchy(node, depth=0):
    """Recursively prints the node hierarchy as a tree."""
    indent = "  " * depth
    node_name = node.GetName()
    
    # Check if it's a joint/skeleton node
    attr = node.GetNodeAttribute()
    marker = " [Joint]" if attr and attr.GetAttributeType() == fbx.FbxNodeAttribute.eSkeleton else ""
    
    print(f"{indent} \u2514\u2500 {node_name}{marker}")
    
    for i in range(node.GetChildCount()):
        print_hierarchy(node.GetChild(i), depth + 1)

def rename_nodes(node, find_str, replace_str):
    """Recursively finds and replaces strings in node names."""
    if not node:
        return
    
    old_name = node.GetName()
    if find_str in old_name:
        new_name = old_name.replace(find_str, replace_str)
        node.SetName(new_name)
    
    for i in range(node.GetChildCount()):
        rename_nodes(node.GetChild(i), find_str, replace_str)

def add_root_joint(scene, manager):
    """
    Injects a 'root' joint at (0,0,0) and parents the 'Hips' joint to it.
    Useful for Unreal Engine/Unity compatibility for Mixamo-style rigs.
    """
    root_node = scene.GetRootNode()
    
    # 1. Find the current top-level joint (usually "Hips")
    hips_node = None
    for i in range(root_node.GetChildCount()):
        child = root_node.GetChild(i)
        if "hips" in child.GetName().lower():
            hips_node = child
            break
            
    if not hips_node:
        print("  ! Could not find Hips node. Root injection skipped.")
        return False

    # 2. Create the new Root Node
    new_root_node = fbx.FbxNode.Create(manager, "root")
    
    # 3. Create a Skeleton attribute so engines recognize it as a bone
    skeleton_attribute = fbx.FbxSkeleton.Create(manager, "root_attr")
    # Note: Using EType.eRoot for compatibility across SDK versions
    skeleton_attribute.SetSkeletonType(fbx.FbxSkeleton.EType.eRoot)
    new_root_node.SetNodeAttribute(skeleton_attribute)
    
    # 4. Set position to 0,0,0
    new_root_node.LclTranslation.Set(fbx.FbxDouble3(0, 0, 0))
    new_root_node.LclRotation.Set(fbx.FbxDouble3(0, 0, 0))
    new_root_node.LclScaling.Set(fbx.FbxDouble3(1, 1, 1))

    # 5. Perform the Parents Transition
    root_node.RemoveChild(hips_node)
    new_root_node.AddChild(hips_node)
    root_node.AddChild(new_root_node)
    
    print("  > Successfully injected 'root' bone at (0,0,0).")
    return True

import datetime

def write_log(output_folder, source_path, outputs, is_master=False):
    """Appends conversion details to a log file in the output directory."""
    log_path = os.path.join(output_folder, "conversion_log.txt")
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with open(log_path, "a") as f:
        f.write(f"[{timestamp}]\n")
        f.write(f"  SOURCE: {source_path}\n")
        if is_master:
            f.write(f"  *** UE MASTER SKELETON (Mesh Kept) ***\n")
        if outputs:
            f.write(f"  EXTRACTED CLIPS:\n")
            for out, status in outputs:
                f.write(f"    - [{status}] {out}\n")
        else:
            f.write("  ! No clips extracted.\n")
        f.write("-" * 50 + "\n")

def process_fbx_files(args):
    """
    Main processing loop with recursive recursion and logging.
    """
    input_folder = os.path.abspath(args.input)
    output_folder = os.path.abspath(args.output)
    
    if not os.path.exists(input_folder):
        print(f"Error: Input directory '{input_folder}' does not exist.")
        return

    # Check for prepUE presets
    is_prep_ue = hasattr(args, 'subcommand') and args.subcommand == 'prepUE'
    add_root = args.add_root or (is_prep_ue and not args.no_root)
    rescale = args.rescale if args.rescale != 1.0 else (0.01 if is_prep_ue else 1.0)

    manager = fbx.FbxManager.Create()
    ios = fbx.FbxIOSettings.Create(manager, fbx.IOSROOT)
    manager.SetIOSettings(ios)

    processed_count = 0
    master_handled = False
    
    # ---------------------------------------------------------
    # RECURSIVE WALK
    # ---------------------------------------------------------
    for root, dirs, files in os.walk(input_folder):
        for filename in files:
            if filename.lower().endswith(".fbx"):
                processed_count += 1
                
                # Determine "Master Skeleton" status for this file
                # In prepUE mode, the first file found keeps its mesh to act as a template
                is_this_master = False
                if is_prep_ue and not master_handled:
                    is_this_master = True
                    master_handled = True
                
                # Setup Paths
                file_path = os.path.join(root, filename)
                rel_path = os.path.relpath(root, input_folder)
                target_depth = os.path.join(output_folder, rel_path)
                
                if not os.path.exists(target_depth):
                    os.makedirs(target_depth)

                # Initialize Loader
                scene = fbx.FbxScene.Create(manager, "ImportScene")
                importer = fbx.FbxImporter.Create(manager, "")
                
                if not importer.Initialize(file_path, -1, manager.GetIOSettings()):
                    print(f"--- FAILED TO LOAD: {filename} ---")
                    continue
                
                importer.Import(scene)
                importer.Destroy()

                fps_info = f" ({get_framerate(scene)} FPS)" if args.show_fps else ""
                master_marker = " [MASTER SKELETON]" if is_this_master else ""
                print(f"--- Processing: {filename}{fps_info}{master_marker} ---")

                # Operation 1: Scale
                if rescale != 1.0:
                    scene_root = scene.GetRootNode()
                    for i in range(scene_root.GetChildCount()):
                        child = scene_root.GetChild(i)
                        curr_scale = child.LclScaling.Get()
                        child.LclScaling.Set(fbx.FbxDouble3(curr_scale[0] * rescale, 
                                                           curr_scale[1] * rescale, 
                                                           curr_scale[2] * rescale))
                    print(f"  > Rescaled by {rescale}")

                # Operation 2: Rename
                if args.rename_find:
                    rename_nodes(scene.GetRootNode(), args.rename_find, args.rename_replace)
                    print(f"  > Renamed '{args.rename_find}' to '{args.rename_replace}'")

                # Operation 3: Add Root Bone
                if add_root:
                    add_root_joint(scene, manager)

                # Operation 4: List
                if args.list_skeleton:
                    print_hierarchy(scene.GetRootNode())

                # Operation 5: Strip Meshes
                # Keep mesh if either the global flag is set OR this is our designated master
                if not args.keep_mesh and not is_this_master:
                    cleanup_meshes(scene.GetRootNode())
                else:
                    reason = "Master status" if is_this_master else "--keep-mesh flag"
                    print(f"  > Keeping mesh data ({reason})")

                # Operation 6: Export Takes
                take_count = scene.GetSrcObjectCount(fbx.FbxCriteria.ObjectType(fbx.FbxAnimStack.ClassId))
                extracted_clips = []
                
                if take_count > 0:
                    # Collect all stacks first because we'll be pruning the scene
                    all_stacks = []
                    for i in range(take_count):
                        all_stacks.append(scene.GetSrcObject(fbx.FbxCriteria.ObjectType(fbx.FbxAnimStack.ClassId), i))

                    limit = args.limit if args.limit > 0 else take_count
                    for i in range(min(take_count, limit)):
                        # We need a fresh scene state or careful pruning for each take
                        target_stack = all_stacks[i]
                        take_name = "".join([c for c in target_stack.GetName() if c.isalnum() or c in (' ', '_')]).rstrip()
                        output_name = f"{os.path.splitext(filename)[0]}_{take_name}.fbx"
                        output_path = os.path.join(target_depth, output_name)

                        # Set the current take
                        scene.SetCurrentAnimationStack(target_stack)

                        # EXTREMELY IMPORTANT: To truly "split" the file, 
                        # we must tell the exporter to only include the current stack.
                        # The most reliable way is to temporarily disconnect other stacks.
                        for other_stack in all_stacks:
                            if other_stack != target_stack:
                                scene.DisconnectSrcObject(other_stack)

                        # VERIFICATION: Verify that the 'root' node exists 
                        # in the final scene state before export
                        has_root = False
                        root_node = scene.GetRootNode()
                        for i in range(root_node.GetChildCount()):
                            if root_node.GetChild(i).GetName().lower() == "root":
                                has_root = True
                                break
                        
                        root_status = "ROOT OK" if has_root else "ROOT MISSING"

                        exporter = fbx.FbxExporter.Create(manager, "")
                        if exporter.Initialize(output_path, -1, manager.GetIOSettings()):
                            exporter.Export(scene)
                            extracted_clips.append((output_name, root_status))
                            print(f"  > Exported: {output_name} ({root_status})")
                        exporter.Destroy()
                        
                        # Reconnect them so the next iteration can find its target
                        for other_stack in all_stacks:
                            if other_stack != target_stack:
                                scene.ConnectSrcObject(other_stack)
                
                # Logging
                write_log(output_folder, file_path, extracted_clips, is_this_master)

    if processed_count == 0:
        print(f"No FBX files found in '{input_folder}'.")
    
    manager.Destroy()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FBX Tools: Mocap Batch Processor")
    subparsers = parser.add_subparsers(dest='subcommand', help='Sub-commands')

    # Shared Arguments Definition
    def add_standard_args(p):
        # Changed to optional with defaults "input" and "output"
        p.add_argument("-i", "--input", default="input", help="Directory containing source FBX files.")
        p.add_argument("-o", "--output", default="output", help="Directory where processed clips are saved.")
        p.add_argument("--list-skeleton", action="store_true", help="Print hierarchy tree.")
        p.add_argument("--show-fps", action="store_true", help="Report framerate.")
        p.add_argument("--rescale", type=float, default=1.0, help="Multiply scene scale.")
        p.add_argument("--rename-find", help="String to find in node names.")
        p.add_argument("--rename-replace", default="", help="String to replace with.")
        p.add_argument("--add-root", action="store_true", help="Inject 'root' bone.")
        p.add_argument("--limit", type=int, default=0, help="Limit takes to process.")
        p.add_argument("--keep-mesh", action="store_true", help="Do NOT strip meshes. Useful for creating Master Skeletons.")

    # 1. COMMAND: process (Standard)
    p_std = subparsers.add_parser('process', help='Standard recursive batch processing.')
    add_standard_args(p_std)

    # 2. COMMAND: prepUE (Unreal Presets)
    p_ue = subparsers.add_parser('prepUE', help='Optimized for Unreal Engine (adds root + scale 0.01 by default).')
    add_standard_args(p_ue)
    p_ue.add_argument("--no-root", action="store_true", help="Disable default root injection for prepUE.")

    args = parser.parse_args()
    
    # DEFAULT BEHAVIOR: 
    # If no command is given, default to the 'process' command using 'input' and 'output' folders
    if not args.subcommand:
        args.subcommand = 'process'
        args.input = 'input'
        args.output = 'output'
        args.list_skeleton = False
        args.show_fps = False
        args.rescale = 1.0
        args.rename_find = None
        args.rename_replace = ""
        args.add_root = False
        args.limit = 0
        args.keep_mesh = False

    process_fbx_files(args)