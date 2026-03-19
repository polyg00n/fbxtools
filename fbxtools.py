import argparse
import os
import fbx
import FbxCommon
import datetime

def cleanup_meshes(node):
    """Recursively removes mesh attributes from nodes to leave only the skeleton."""
    if not node:
        return
    attribute = node.GetNodeAttribute()
    if attribute and attribute.GetAttributeType() == fbx.FbxNodeAttribute.EType.eMesh:
        node.RemoveNodeAttribute(attribute)
    for i in range(node.GetChildCount()):
        cleanup_meshes(node.GetChild(i))

def get_framerate(scene):
    """Returns the framerate as a string."""
    lGlobalSettings = scene.GetGlobalSettings()
    time_mode = lGlobalSettings.GetTimeMode()
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

def inject_proxy_mesh(scene, manager):
    """Injects a 1x1x1 cube bound to the first discovered joint."""
    root_node = scene.GetRootNode()
    target_joint = None
    # Breadth-first search for first skeleton node
    queue = [root_node]
    while queue:
        curr = queue.pop(0)
        attr = curr.GetNodeAttribute()
        if attr and attr.GetAttributeType() == fbx.FbxNodeAttribute.EType.eSkeleton:
            target_joint = curr
            break
        for i in range(curr.GetChildCount()):
            queue.append(curr.GetChild(i))
    
    if not target_joint:
        print("  ! Error: No skeleton found for proxy injection.")
        return False

    mesh = fbx.FbxMesh.Create(scene, "ProxyCube")
    pts = [(-0.5,-0.5,-0.5), (0.5,-0.5,-0.5), (0.5,0.5,-0.5), (-0.5,0.5,-0.5),
           (-0.5,-0.5,0.5), (0.5,-0.5,0.5), (0.5,0.5,0.5), (-0.5,0.5,0.5)]
    mesh.InitControlPoints(8)
    for i, pt in enumerate(pts):
        mesh.SetControlPointAt(fbx.FbxVector4(pt[0], pt[1], pt[2]), i)
    faces = [(0,1,2,3), (4,5,6,7), (0,1,5,4), (1,2,6,5), (2,3,7,6), (3,0,4,7)]
    for f in faces:
        mesh.BeginPolygon(); [mesh.AddPolygon(v) for v in f]; mesh.EndPolygon()
    
    mesh_node = fbx.FbxNode.Create(scene, "MESH_PROXY")
    mesh_node.SetNodeAttribute(mesh)
    root_node.AddChild(mesh_node)
    
    skin = fbx.FbxSkin.Create(scene, "ProxySkin")
    cluster = fbx.FbxCluster.Create(scene, "ProxyCluster")
    cluster.SetLink(target_joint)
    cluster.SetLinkMode(fbx.FbxCluster.ELinkMode.eTotalOne)
    for i in range(8): cluster.AddControlPointIndex(i, 1.0)
    skin.AddCluster(cluster)
    mesh.AddDeformer(skin)
    print(f"  > Successfully injected Proxy Mesh bound to '{target_joint.GetName()}'")
    return True

def print_hierarchy(node, depth=0):
    indent = "  " * depth
    attr = node.GetNodeAttribute()
    marker = " [Joint]" if attr and attr.GetAttributeType() == fbx.FbxNodeAttribute.EType.eSkeleton else ""
    print(f"{indent} \u2514\u2500 {node.GetName()}{marker}")
    for i in range(node.GetChildCount()): print_hierarchy(node.GetChild(i), depth + 1)

def rename_nodes(node, find_str, replace_str):
    if not node: return
    old_name = node.GetName()
    if find_str in old_name: node.SetName(old_name.replace(find_str, replace_str))
    for i in range(node.GetChildCount()): rename_nodes(node.GetChild(i), find_str, replace_str)

def add_root_joint(scene, manager):
    root_node = scene.GetRootNode()
    hips_node = None
    for i in range(root_node.GetChildCount()):
        child = root_node.GetChild(i)
        if "hips" in child.GetName().lower():
            hips_node = child
            break
    if not hips_node: return False
    new_root = fbx.FbxNode.Create(manager, "root")
    attr = fbx.FbxSkeleton.Create(manager, "root_attr")
    attr.SetSkeletonType(fbx.FbxSkeleton.EType.eRoot)
    new_root.SetNodeAttribute(attr)
    new_root.LclTranslation.Set(fbx.FbxDouble3(0,0,0))
    root_node.RemoveChild(hips_node)
    new_root.AddChild(hips_node)
    root_node.AddChild(new_root)
    print("  > Successfully injected 'root' bone at (0,0,0).")
    return True

def write_log(output_folder, source_path, outputs, file_version, take_count, is_master=False):
    log_path = os.path.join(output_folder, "conversion_log.txt")
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_path, "a") as f:
        f.write(f"[{ts}]\n  SOURCE: {source_path}\n")
        f.write(f"  DIAGNOSTICS: FBX v{file_version} | TAKES: {take_count}\n")
        if is_master: f.write(f"  *** UE MASTER SKELETON (Mesh Kept) ***\n")
        if outputs:
            f.write(f"  CONVERSION RESULTS:\n")
            for out, status in outputs: f.write(f"    - [{status}] {out}\n")
        else: f.write("  ! WARNING: Zero output clips generated.\n")
        f.write("-" * 60 + "\n")

def process_fbx_files(args):
    input_folder = os.path.abspath(args.input)
    output_folder = os.path.abspath(args.output)
    if not os.path.exists(input_folder): return
    is_prep_ue = hasattr(args, 'subcommand') and args.subcommand == 'prepUE'
    add_root = args.add_root or (is_prep_ue and not args.no_root)
    rescale = args.rescale if args.rescale != 1.0 else 1.0
    manager = fbx.FbxManager.Create()
    ios = fbx.FbxIOSettings.Create(manager, fbx.IOSROOT); manager.SetIOSettings(ios)
    processed_count = 0
    master_handled = False
    for root, dirs, files in os.walk(input_folder):
        for filename in files:
            if filename.lower().endswith(".fbx"):
                processed_count += 1
                is_this_master = False
                if is_prep_ue and not master_handled:
                    is_this_master = True
                    master_handled = True
                file_path = os.path.join(root, filename)
                target_depth = os.path.join(output_folder, os.path.relpath(root, input_folder))
                if not os.path.exists(target_depth): os.makedirs(target_depth)
                scene = fbx.FbxScene.Create(manager, "ScanScene")
                importer = fbx.FbxImporter.Create(manager, "")
                if not importer.Initialize(file_path, -1, manager.GetIOSettings()): continue
                v_major, v_minor, v_rev = importer.GetFileVersion()
                file_version_str = f"{v_major}.{v_minor}.{v_rev}"
                importer.Import(scene); importer.Destroy()
                take_count = scene.GetSrcObjectCount(fbx.FbxCriteria.ObjectType(fbx.FbxAnimStack.ClassId))
                take_names = [scene.GetSrcObject(fbx.FbxCriteria.ObjectType(fbx.FbxAnimStack.ClassId), i).GetName() for i in range(take_count)]
                print(f"--- Processing: {filename} ---\n  > FBX Version: {file_version_str}\n  > Takes Found: {take_count}")
                if args.audit:
                    mesh_count = scene.GetSrcObjectCount(fbx.FbxCriteria.ObjectType(fbx.FbxMesh.ClassId))
                    print(f"  > Audit: {mesh_count} Meshes found.")
                    for m_idx in range(mesh_count):
                        mesh = scene.GetSrcObject(fbx.FbxCriteria.ObjectType(fbx.FbxMesh.ClassId), m_idx)
                        m_node = mesh.GetNode(); m_node_name = m_node.GetName() if m_node else "Unparented"
                        has_skin = any(mesh.GetDeformer(d).IsA(fbx.FbxSkin.ClassId) for d in range(mesh.GetDeformerCount()))
                        print(f"    - Mesh: '{mesh.GetName()}' (Node: '{m_node_name}') [Bound: {has_skin}]")
                if take_count == 0 and not is_prep_ue and not args.inject_proxy:
                    scene.Destroy(); continue
                if rescale != 1.0:
                    s_root = scene.GetRootNode()
                    for j in range(s_root.GetChildCount()):
                        child = s_root.GetChild(j); cur = child.LclScaling.Get()
                        child.LclScaling.Set(fbx.FbxDouble3(cur[0]*rescale, cur[1]*rescale, cur[2]*rescale))
                if args.rename_find: rename_nodes(scene.GetRootNode(), args.rename_find, args.rename_replace)
                if add_root: add_root_joint(scene, manager)
                if args.inject_proxy: inject_proxy_mesh(scene, manager)
                ascii_format = -1; reg = manager.GetIOPluginRegistry()
                for f_idx in range(reg.GetWriterFormatCount()):
                    if reg.WriterIsFBX(f_idx) and "ascii" in reg.GetWriterFormatDescription(f_idx).lower():
                        ascii_format = f_idx; break
                temp_ascii = os.path.join(target_depth, "_temp_base.fbx")
                exporter = fbx.FbxExporter.Create(manager, "")
                if not exporter.Initialize(temp_ascii, ascii_format, manager.GetIOSettings()): continue
                exporter.Export(scene); exporter.Destroy(); scene.Destroy()
                with open(temp_ascii, 'r', encoding='utf-8', errors='ignore') as f:
                    print(f"  > Header: {f.readline().strip()} | {f.readline().strip()}"); f.seek(0); ascii_lines = f.readlines()
                stack_blocks = []; current_start = -1; depth = 0
                for idx, line in enumerate(ascii_lines):
                    if "{" in line:
                        if depth == 0: current_start = idx
                        depth += line.count("{")
                    if "}" in line:
                        depth -= line.count("}"); 
                        if depth == 0 and current_start != -1:
                            hdr = ascii_lines[current_start].strip()
                            if any(tag in hdr for tag in ["AnimationStack:", "AnimStack:", "Take:"]):
                                parts = hdr.split('"')
                                if len(parts) >= 2: stack_blocks.append({"name": parts[1], "start": current_start, "end": idx})
                            current_start = -1
                extracted_clips = []
                if not stack_blocks:
                    out_name = f"{os.path.splitext(filename)[0]}_Skel.fbx"; out_path = os.path.join(target_depth, out_name)
                    with open(temp_ascii, 'r', encoding='utf-8', errors='ignore') as f_in, open(out_path, 'w', encoding='utf-8') as f_out: f_out.write(f_in.read())
                    extracted_clips.append((out_name, "SKELETON ONLY"))
                    print(f"  > Exported Skeleton: {out_name} [{os.path.getsize(out_path)/(1024*1024):.2f} MB]")
                else:
                    limit = args.limit if args.limit > 0 else take_count
                    for i in range(min(take_count, limit)):
                        target_take = take_names[i]; out_name = f"{os.path.splitext(filename)[0]}_{target_take}.fbx"
                        out_path = os.path.join(target_depth, out_name); target_info = next((s for s in stack_blocks if s["name"] == target_take), None)
                        if not target_info: continue
                        with open(out_path, 'w', encoding='utf-8') as f_out:
                            skip_until = -1
                            for idx, line in enumerate(ascii_lines):
                                if idx < skip_until: continue
                                unw = next((s for s in stack_blocks if s["name"] != target_take and idx == s["start"]), None)
                                if unw: skip_until = unw["end"] + 1; continue
                                f_out.write(line)
                        extracted_clips.append((out_name, "SPLIT OK"))
                        print(f"  > Exported: {out_name} [{os.path.getsize(out_path)/(1024*1024):.2f} MB]")
                if os.path.exists(temp_ascii): os.remove(temp_ascii)
                write_log(output_folder, file_path, extracted_clips, file_version_str, take_count, is_this_master)
    manager.Destroy()

if __name__ == "__main__":
    pp = argparse.ArgumentParser(add_help=False)
    pp.add_argument("-i", "--input", default="input", help="Source directory.")
    pp.add_argument("-o", "--output", default="output", help="Target directory.")
    pp.add_argument("--list-skeleton", action="store_true")
    pp.add_argument("--show-fps", action="store_true")
    pp.add_argument("--rescale", type=float, default=1.0)
    pp.add_argument("--rename-find", help="String to find.")
    pp.add_argument("--rename-replace", default="")
    pp.add_argument("--add-root", action="store_true")
    pp.add_argument("--limit", type=int, default=0)
    pp.add_argument("--keep-mesh", action="store_true")
    pp.add_argument("--audit", action="store_true")
    pp.add_argument("--inject-proxy", action="store_true")

    parser = argparse.ArgumentParser(description="FBX Tools")
    subparsers = parser.add_subparsers(dest='subcommand')
    subparsers.add_parser('process', help='Standard processing', parents=[pp])
    p_ue = subparsers.add_parser('prepUE', help='Unreal presets (scale 1.0)', parents=[pp])
    p_ue.add_argument("--no-root", action="store_true")

    args = parser.parse_args()
    if not args.subcommand:
        args.subcommand = 'process'
        for attr in ['input','output','rescale','limit','rename_replace']:
            if not hasattr(args, attr): setattr(args, attr, pp.get_default(attr))
        for attr in ['add_root','keep_mesh','audit','inject_proxy','show_fps','list_skeleton']:
            if not hasattr(args, attr): setattr(args, attr, False)
        if not hasattr(args, 'rename_find'): args.rename_find = None
    process_fbx_files(args)