import os
import json
import traceback
import maya.cmds as cmds
import maya.api.OpenMaya as om
import maya.api.OpenMayaAnim as oma

# ---------------------------------------------------------
# Utility
# ---------------------------------------------------------

def _ensure_dir(path):
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d)

def _get_mobject(node):
    sel = om.MSelectionList()
    sel.add(node)
    return sel.getDependNode(0)

def _get_dagpath(node):
    sel = om.MSelectionList()
    sel.add(node)
    return sel.getDagPath(0)

def _safe_getattr(node, attr):
    try:
        return cmds.getAttr(f"{node}.{attr}")
    except Exception:
        return None

def _get_user_attributes(node):
    """
    Scrapes keyable and channel-box attributes to save deformer settings.
    Logic inspired by 'getSaveAttributesDict' in weights.py.
    """
    attrs = {}
    # Get keyable attributes (standard settings)
    keyable = cmds.listAttr(node, keyable=True, scalar=True) or []
    # Get channel box attributes (non-keyable but visible)
    cb = cmds.listAttr(node, channelBox=True, scalar=True) or []
    
    all_attrs = list(set(keyable + cb))
    
    # Attributes to skip (system attributes)
    skip_list = ['weightList', 'weights', 'input', 'outputGeometry', 'groupId']
    
    for attr in all_attrs:
        if any(x in attr for x in skip_list):
            continue
        try:
            val = cmds.getAttr(f"{node}.{attr}")
            # Only store simple types (int, float, bool)
            if isinstance(val, (float, int, bool)):
                attrs[attr] = val
        except Exception:
            continue
    return attrs

def _get_deformer_stack(mesh):
    """
    Returns a list of deformers on the mesh.
    """
    hist = cmds.listHistory(mesh, pruneDagObjects=True) or []
    # Standard deformer types
    deformer_types = cmds.listNodeTypes('deformer')
    # Filter history for deformers
    found = [h for h in hist if cmds.nodeType(h) in deformer_types and cmds.nodeType(h) != 'tweak']
    return found

# ---------------------------------------------------------
# EXPORT
# ---------------------------------------------------------

def export_deformers_json(path=None, selection_only=False):
    """
    Export all deformers (SkinCluster, Cluster, DeltaMush, etc.) to JSON.
    Includes:
      - Deformer Type
      - Weights (Map)
      - Keyable Attributes
    """
    if path is None:
        path = r"C:\temp\deformers.json" # Default path
    path = os.path.abspath(path)
    _ensure_dir(path)

    # 1. Gather Geometry
    meshes = []
    if selection_only:
        sel = cmds.ls(sl=True, long=True, dag=True, type='mesh') or []
        meshes = sel
    else:
        # If nothing selected, maybe grab all meshes in scene? 
        # For safety, let's stick to selection or explicit list, 
        # but here we defaults to selection if selection_only is False for safety.
        meshes = cmds.ls(sl=True, long=True, dag=True, type='mesh') or []

    data = {}

    for mesh in meshes:
        # Get Transform
        transform = cmds.listRelatives(mesh, parent=True, fullPath=True)[0]
        
        # Get Deformers
        deformers = _get_deformer_stack(transform)
        
        for dfm in deformers:
            try:
                dfm_type = cmds.nodeType(dfm)
                
                # Setup Base Block
                block = {
                    "mesh_name": transform,
                    "type": dfm_type,
                    "attrs": _get_user_attributes(dfm),
                    "weights": {} # For generic
                }

                # --- SKINCLUSTER LOGIC ---
                if dfm_type == "skinCluster":
                    sc_mobj = _get_mobject(dfm)
                    sc_fn = oma.MFnSkinCluster(sc_mobj)
                    geo_dp = _get_dagpath(transform)

                    # Influences
                    inf_paths = sc_fn.influenceObjects()
                    inf_names = [om.MFnDagNode(p).fullPathName() for p in inf_paths]
                    block["joint_list"] = inf_names
                    
                    # Store Skinning Method specifically
                    block["skinningMethod"] = _safe_getattr(dfm, "skinningMethod") or 0

                    # Dual Quaternion Map (blendWeights)
                    dq_array = []
                    vtx_count = cmds.polyEvaluate(transform, vertex=True)
                    # Try efficient getter, fallback to getAttr loop if needed
                    # Note: OpenMaya doesn't have a clean getBlendWeights for all verts easily exposed in Python API 1.0 style
                    # We will use MFnSkinCluster.getBlendWeights in API 2.0
                    try:
                         # API 2.0 getBlendWeights returns MDoubleArray
                        weights_marray = sc_fn.getBlendWeights(geo_dp, _get_mobject(transform))
                        dq_array = list(weights_marray)
                    except:
                        # Fallback
                        pass 
                    
                    if not dq_array or len(dq_array) != vtx_count:
                        # Zero fill if failed
                        dq_array = [0.0] * vtx_count
                        
                    block["dq_vertex_map"] = dq_array

                    # Weights extraction
                    weights_data = {}
                    it_geo = om.MItGeometry(geo_dp)
                    while not it_geo.isDone():
                        idx = it_geo.index()
                        vals, inf_count = sc_fn.getWeights(geo_dp, it_geo.currentItem())
                        
                        # Compress weights (only store non-zero)
                        row = {}
                        for i, w in enumerate(vals):
                            if w > 0.001: # Epsilon
                                row[inf_names[i]] = float(w)
                        if row:
                            weights_data[f"{idx}"] = row # Use index as key to save space
                        it_geo.next()
                    
                    block["skin_percentage"] = weights_data

                # --- GENERIC DEFORMER LOGIC (Cluster, DeltaMush, etc) ---
                else:
                    # Logic derived from weights.py _saveDeformerToFile
                    # Most deformers use MFnGeometryFilter and store weights in weightList[0]
                    
                    geo_dp = _get_dagpath(transform)
                    dfm_mobj = _get_mobject(dfm)
                    
                    # Check if it is a geometry filter (has weights)
                    if not dfm_mobj.hasFn(om.MFn.kGeometryFilter):
                        print(f"[Export] Skipping {dfm} (Not a geometry filter)")
                        continue

                    geo_filt_fn = oma.MFnGeometryFilter(dfm_mobj)
                    
                    # We need the index of the geometry in the deformer
                    # Usually 0 if it's the only mesh, but let's be safe
                    index = geo_filt_fn.indexForOutputShape(_get_mobject(mesh))
                    
                    # Get Components (All Vertices)
                    # We create a component covering all verts
                    vtx_count = cmds.polyEvaluate(transform, vertex=True)
                    idx_fn = om.MFnSingleIndexedComponent()
                    comp_obj = idx_fn.create(om.MFn.kMeshVertComponent)
                    idx_fn.setElements(list(range(vtx_count)))
                    
                    # Get Weights
                    # MFnGeometryFilter.weights(path, component, index) -> MFloatArray
                    try:
                        w_vals = geo_filt_fn.weights(geo_dp, comp_obj) # This returns a float array of weights
                        block["weights"] = list(w_vals)
                    except Exception as e:
                        # Fallback for some deformers that might not expose standard weights via API
                        print(f"[Export] API weight read failed for {dfm}: {e}. Trying attributes.")
                        pass

                # Save block
                data[dfm] = block
                print(f"[Export] Processed {dfm} ({dfm_type})")

            except Exception:
                traceback.print_exc()

    with open(path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"[export] Wrote {len(data)} deformers to {path}")
    return path


# ---------------------------------------------------------
# IMPORT
# ---------------------------------------------------------

def import_deformers_json(path=None, verbose=True):
    """
    Import JSON deformers.
    Handles:
      - Recreation of Deformers (SkinCluster, Cluster, DeltaMush, etc.)
      - Attributes
      - Weights
    """
    if path is None:
        return
        
    path = os.path.abspath(path)
    if not os.path.exists(path):
        raise IOError(f"File does not exist: {path}")

    with open(path, "r") as f:
        data = json.load(f)

    for sc_name, block in data.items():
        try:
            geo = block["mesh_name"]
            dfm_type = block.get("type", "skinCluster")
            attrs = block.get("attrs", {})

            if not cmds.objExists(geo):
                print(f"[import] Geo not found: {geo} (skip {sc_name})")
                continue

            # ---------------------------------------------------------
            # 1. GET OR CREATE DEFORMER
            # ---------------------------------------------------------
            dfm_node = None
            
            # Check if exists
            if cmds.objExists(sc_name) and cmds.nodeType(sc_name) == dfm_type:
                dfm_node = sc_name
            else:
                # --- CREATE SKINCLUSTER ---
                if dfm_type == "skinCluster":
                    joints = block.get("joint_list", [])
                    # Ensure joints exist
                    safe_joints = []
                    for j in joints:
                        if cmds.objExists(j):
                            safe_joints.append(j)
                        else:
                            # Create dummy if needed (weights.py logic)
                            print(f"[Import] Missing joint {j}, creating dummy.")
                            cmds.select(cl=True)
                            safe_joints.append(cmds.joint(n=j))
                    
                    if safe_joints:
                        # Create SkinCluster
                        # tsb=True (to selection bucket)
                        try:
                            res = cmds.skinCluster(safe_joints, geo, tsb=True, n=sc_name)
                            dfm_node = res[0]
                        except Exception as e:
                            print(f"[Import] Failed to create skinCluster {sc_name}: {e}")
                            continue
                
                # --- CREATE GENERIC DEFORMER ---
                else:
                    # Basic creation for standard types (deltaMush, cluster, etc)
                    # Some deformers require specific creation commands.
                    try:
                        cmds.select(geo)
                        if dfm_type == 'cluster':
                            # Clusters need a handle
                            res = cmds.cluster(n=sc_name)
                            dfm_node = res[0]
                        elif dfm_type == 'blendShape':
                            res = cmds.blendShape(n=sc_name)
                            dfm_node = res[0]
                        elif dfm_type == 'deltaMush':
                            res = cmds.deltaMush(geo, n=sc_name)
                            dfm_node = res[0]
                        else:
                            # Generic fallback using deformer command
                            # This works for: lattice, wire, non-linear, textureDeformer
                            res = cmds.deformer(geo, type=dfm_type, n=sc_name)
                            dfm_node = res[0]
                    except Exception as e:
                         print(f"[Import] Failed to create {dfm_type} '{sc_name}': {e}")
                         continue

            if not dfm_node:
                continue

            # ---------------------------------------------------------
            # 2. RESTORE ATTRIBUTES
            # ---------------------------------------------------------
            for attr, val in attrs.items():
                try:
                    cmds.setAttr(f"{dfm_node}.{attr}", val)
                except Exception:
                    pass
            
            # ---------------------------------------------------------
            # 3. RESTORE WEIGHTS
            # ---------------------------------------------------------
            
            geo_dp = _get_dagpath(geo)
            dfm_mobj = _get_mobject(dfm_node)

            # --- RESTORE SKIN WEIGHTS ---
            if dfm_type == "skinCluster":
                
                # Disable Norm temporarily
                try: cmds.setAttr(f"{dfm_node}.normalizeWeights", 0)
                except: pass

                sc_fn = oma.MFnSkinCluster(dfm_mobj)
                
                # Remap Influences indices
                inf_paths = sc_fn.influenceObjects()
                current_inf_names = [om.MFnDagNode(p).fullPathName() for p in inf_paths]
                inf_map = {name: i for i, name in enumerate(current_inf_names)}
                
                weights_data = block.get("skin_percentage", {})
                
                # Build MDoubleArray for SetWeights
                # We need a flat array: [vtx0_inf0, vtx0_inf1, ... vtx1_inf0...]
                num_inf = len(current_inf_names)
                
                # Create Component for all verts
                vtx_count = cmds.polyEvaluate(geo, vertex=True)
                
                # Prepare bulk array (init zero)
                full_weights = om.MDoubleArray(vtx_count * num_inf, 0.0)
                
                # Fill array from JSON
                for vtx_idx_str, w_dict in weights_data.items():
                    vtx_idx = int(vtx_idx_str)
                    base_offset = vtx_idx * num_inf
                    for j_name, w_val in w_dict.items():
                        if j_name in inf_map:
                            full_weights[base_offset + inf_map[j_name]] = w_val

                # Apply
                idx_fn = om.MFnSingleIndexedComponent()
                comp_obj = idx_fn.create(om.MFn.kMeshVertComponent)
                idx_fn.setElements(list(range(vtx_count)))
                
                sc_fn.setWeights(geo_dp, comp_obj, full_weights, normalize=False)
                
                # Restore Dual Quaternion (BlendWeights)
                dq_map = block.get("dq_vertex_map", [])
                if dq_map:
                    dq_marray = om.MDoubleArray(dq_map)
                    sc_fn.setBlendWeights(geo_dp, comp_obj, dq_marray)

                # Re-enable Norm based on saved attr
                nw_val = attrs.get("normalizeWeights", 1)
                try: cmds.setAttr(f"{dfm_node}.normalizeWeights", nw_val)
                except: pass
                
                if verbose: print(f"[Import] Restored SkinCluster {dfm_node}")

            # --- RESTORE GENERIC WEIGHTS ---
            else:
                weights = block.get("weights", [])
                if weights:
                    # Use MFnGeometryFilter to set weights
                    if dfm_mobj.hasFn(om.MFn.kGeometryFilter):
                        geo_filt_fn = oma.MFnGeometryFilter(dfm_mobj)
                        
                        vtx_count = cmds.polyEvaluate(geo, vertex=True)
                        if len(weights) == vtx_count:
                             # Component
                            idx_fn = om.MFnSingleIndexedComponent()
                            comp_obj = idx_fn.create(om.MFn.kMeshVertComponent)
                            idx_fn.setElements(list(range(vtx_count)))
                            
                            # Float Array
                            w_float = om.MFloatArray(weights)
                            
                            # Set
                            geo_filt_fn.setWeights(geo_dp, comp_obj, w_float)
                            if verbose: print(f"[Import] Restored weights for {dfm_node}")
                        else:
                            print(f"[Import] Weight count mismatch for {dfm_node} (Json:{len(weights)} vs Mesh:{vtx_count})")

        except Exception:
            traceback.print_exc()
            print(f"[Import] Error processing block {sc_name}")

# UI WRAPPERS

path = r"P:\VFX_Project_20\DCC_CUSTOM\MAYA\modules\puiastre_tools\assets\varyndor\skinning\CHAR_varyndor_001.skn"
export_deformers_json(path)#, selection_only=True)
# import_deformers_json(path)