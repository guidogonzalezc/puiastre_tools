import maya.cmds as cmds
import maya.api.OpenMaya as om
import maya.api.OpenMayaAnim as oma
import json
import time
import os
import re

class DeformerManager(object):
    """
    Production tool to Export/Import deformer data.
    - Automatic creation of missing Deformers (Tension, DeltaMush, Skin, etc).
    - Robust Index Resolution for plugins.
    - MGlobal Logging.
    """
    
    def __init__(self):
        self.tolerance = 0.0001 

    # ------------------------------------------------------------------------
    # LOGGING
    # ------------------------------------------------------------------------
    
    def log(self, msg, level="info"):
        if level == "info":
            om.MGlobal.displayInfo(f"[DefManager] {msg}")
        elif level == "warning":
            om.MGlobal.displayWarning(f"[DefManager] {msg}")
        elif level == "error":
            om.MGlobal.displayError(f"[DefManager] {msg}")

    # ------------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------------
    
    def get_dag_path(self, node_name):
        sel = om.MSelectionList()
        try:
            sel.add(node_name)
            return sel.getDagPath(0)
        except:
            return None

    def get_mobject(self, node_name):
        sel = om.MSelectionList()
        try:
            sel.add(node_name)
            return sel.getDependNode(0)
        except:
            return None

    def get_mesh_components(self, dag_path):
        fn_mesh = om.MFnMesh(dag_path)
        fn_comp = om.MFnSingleIndexedComponent()
        comp_obj = fn_comp.create(om.MFn.kMeshVertComponent)
        fn_comp.setCompleteData(fn_mesh.numVertices)
        return comp_obj, fn_mesh.numVertices

    def resolve_deformer_index(self, deformer_node, shape_node_name):
        """
        Robustly finds the logical index of the shape in the deformer.
        """
        # 1. Try API
        try:
            mobj_def = self.get_mobject(deformer_node)
            mobj_geo = self.get_mobject(shape_node_name)
            fn_filter = oma.MFnGeometryFilter(mobj_def)
            return fn_filter.indexForOutputShape(mobj_geo)
        except:
            pass 
        
        # 2. Trace Connections
        try:
            conns = cmds.listConnections(deformer_node + ".outputGeometry", 
                                       source=False, destination=True, plugs=True, c=True) or []
            shape_short = shape_node_name.split("|")[-1]
            for i in range(0, len(conns), 2):
                src_plug = conns[i]
                dst_plug = conns[i+1]
                if shape_short in dst_plug:
                    match = re.search(r"\[(\d+)\]", src_plug)
                    if match:
                        return int(match.group(1))
        except Exception as e:
            self.log(f"Connection trace failed: {e}", "warning")

        return 0

    # ------------------------------------------------------------------------
    # EXPORT LOGIC
    # ------------------------------------------------------------------------

    def extract_skin_cluster(self, deformer_node, geometry_path):
        mobj = self.get_mobject(deformer_node)
        fn_skin = oma.MFnSkinCluster(mobj)
        components, vtx_count = self.get_mesh_components(geometry_path)
        
        # Attributes
        attrs = {
            "skinningMethod": cmds.getAttr(f"{deformer_node}.skinningMethod"),
            "normalizeWeights": cmds.getAttr(f"{deformer_node}.normalizeWeights"),
            "maintainMaxInfluences": cmds.getAttr(f"{deformer_node}.maintainMaxInfluences"),
            "maxInfluences": cmds.getAttr(f"{deformer_node}.maxInfluences"),
            "weightDistribution": cmds.getAttr(f"{deformer_node}.weightDistribution") 
        }

        # Joint Weights
        weights_flat, num_infl = fn_skin.getWeights(geometry_path, components)
        infl_paths = fn_skin.influenceObjects()
        infl_names = [p.partialPathName() for p in infl_paths]
        
        sparse_weights = []
        for v in range(vtx_count):
            base_idx = v * num_infl
            for i in range(num_infl):
                w = weights_flat[base_idx + i]
                if w > self.tolerance:
                    sparse_weights.append([v, i, round(w, 5)])

        # DQ Blend Weights
        blend_weights = []
        try:
            raw_blend = fn_skin.getBlendWeights(geometry_path, components)
            for i, w in enumerate(raw_blend):
                if w > self.tolerance:
                    blend_weights.append([i, round(w, 5)])
        except:
            pass

        return {
            "type": "skinCluster",
            "vertex_count": vtx_count,
            "attributes": attrs,
            "influences": infl_names,
            "weights": sparse_weights,
            "blend_weights": blend_weights
        }

    def extract_generic_deformer(self, deformer_node, geometry_path, deformer_type):
        mobj = self.get_mobject(deformer_node)
        fn_filter = oma.MFnGeometryFilter(mobj)
        components, vtx_count = self.get_mesh_components(geometry_path)
        
        dense_weights = []
        
        # Resolve Index
        idx = self.resolve_deformer_index(deformer_node, geometry_path.partialPathName())
        
        # Extract
        max_val = 0.0
        try:
            for i in range(vtx_count):
                w = fn_filter.weightAtIndex(geometry_path, idx, i)
                if w > max_val: max_val = w
                dense_weights.append([i, round(w, 5)])
        except Exception as e:
            self.log(f"API Read Error on {deformer_node}: {e}", "error")

        # Handle Defaults
        default_ones = ["deltaMush", "tension", "cluster", "softMod", "textureDeformer"]
        is_generic_type = any(t in deformer_type for t in default_ones)
        
        if max_val <= self.tolerance and is_generic_type:
            self.log(f"{deformer_node} unpainted. Auto-filling 1.0s.", "warning")
            dense_weights = [[i, 1.0] for i in range(vtx_count)]

        return {
            "type": deformer_type,
            "vertex_count": vtx_count,
            "influences": [], 
            "weights": dense_weights
        }

    def export_data(self, file_path):
        st = time.time()
        self.log(f"Starting Export to: {file_path}")
        
        meshes = cmds.ls(type="mesh", noIntermediate=True, long=True)
        scene_data = {}
        
        count = 0
        for mesh in meshes:
            transform = cmds.listRelatives(mesh, parent=True, fullPath=True)[0]
            short_name = transform.split("|")[-1]
            
            history = cmds.listHistory(transform, pruneDagObjects=True)
            if not history: continue
            
            deformers = cmds.ls(history, type="geometryFilter")
            if not deformers: continue
            
            mesh_data = {}
            dag_path = self.get_dag_path(mesh)
            
            for def_node in deformers:
                if cmds.nodeType(def_node) == "tweak": continue
                
                node_type = cmds.nodeType(def_node)
                def_name = def_node.split(":")[-1]
                
                self.log(f"Processing: {short_name} -> {def_name}")
                
                payload = None
                if node_type == "skinCluster":
                    payload = self.extract_skin_cluster(def_node, dag_path)
                else:
                    payload = self.extract_generic_deformer(def_node, dag_path, node_type)
                
                if payload:
                    mesh_data[def_name] = payload
                    count += 1
            
            if mesh_data:
                scene_data[short_name] = mesh_data

        with open(file_path, 'w') as f:
            json.dump(scene_data, f, indent=4)
            
        self.log(f"Export Complete. {count} deformers saved.")

    # ------------------------------------------------------------------------
    # IMPORT LOGIC
    # ------------------------------------------------------------------------
    
    def create_deformer_node(self, mesh_name, deformer_name, deformer_type):
        """
        Creates a deformer if it is missing.
        """
        self.log(f"Creating missing deformer: {deformer_name} ({deformer_type})")
        
        try:
            cmds.deformer(mesh_name, type=deformer_type, name=deformer_name)
                
            return True
        except Exception as e:
            self.log(f"Failed to create {deformer_name}: {e}", "error")
            return False

    def set_skin_weights(self, mesh_name, data):
        mesh_path = self.get_dag_path(mesh_name)
        if not mesh_path: return

        # Influences
        file_influences = data['influences']
        scene_influences = [j for j in file_influences if cmds.objExists(j)]
        
        if not scene_influences:
            self.log(f"Skipping {mesh_name}: No influences found.", "error")
            return

        # SkinCluster Creation
        hist = cmds.listHistory(mesh_name, pruneDagObjects=True)
        skins = cmds.ls(hist, type="skinCluster")
        skin_name = ""
        
        if skins:
            skin_name = skins[0]
            curr_infls = cmds.skinCluster(skin_name, q=True, influence=True) or []
            to_add = list(set(scene_influences) - set(curr_infls))
            if to_add:
                cmds.skinCluster(skin_name, e=True, addInfluence=to_add, wt=0)
        else:
            skin_name = cmds.skinCluster(scene_influences, mesh_name, toSelectedBones=True, tsb=True)[0]

        # Attributes
        attrs = data.get("attributes", {})
        cmds.setAttr(f"{skin_name}.normalizeWeights", 0) 
        if "skinningMethod" in attrs:
            cmds.setAttr(f"{skin_name}.skinningMethod", attrs["skinningMethod"])

        # Weights
        mobj = self.get_mobject(skin_name)
        fn_skin = oma.MFnSkinCluster(mobj)
        
        file_to_scene_map = {}
        scene_infl_paths = fn_skin.influenceObjects()
        scene_infl_names = [p.partialPathName() for p in scene_infl_paths]
        
        for file_idx, name in enumerate(file_influences):
            if name in scene_infl_names:
                file_to_scene_map[file_idx] = scene_infl_names.index(name)

        num_scene_infl = len(scene_infl_names)
        num_verts = data['vertex_count']
        full_weights = om.MDoubleArray(num_verts * num_scene_infl, 0.0)
        
        for item in data['weights']:
            vtx, file_inf_idx, val = int(item[0]), int(item[1]), float(item[2])
            if file_inf_idx in file_to_scene_map:
                scene_inf_idx = file_to_scene_map[file_inf_idx]
                flat_idx = (vtx * num_scene_infl) + scene_inf_idx
                full_weights[flat_idx] = val

        components, _ = self.get_mesh_components(mesh_path)
        infl_indices = om.MIntArray(range(num_scene_infl))
        fn_skin.setWeights(mesh_path, components, infl_indices, full_weights, False)

        # DQ Blend
        blend_data = data.get("blend_weights", [])
        if blend_data:
            full_blend = om.MDoubleArray(num_verts, 0.0)
            for item in blend_data:
                full_blend[int(item[0])] = float(item[1])
            fn_skin.setBlendWeights(mesh_path, components, full_blend)

        # Restore Attributes
        if "normalizeWeights" in attrs:
            cmds.setAttr(f"{skin_name}.normalizeWeights", attrs["normalizeWeights"])
        if "maintainMaxInfluences" in attrs:
            cmds.setAttr(f"{skin_name}.maintainMaxInfluences", attrs["maintainMaxInfluences"])
        if "maxInfluences" in attrs:
            cmds.setAttr(f"{skin_name}.maxInfluences", attrs["maxInfluences"])

        self.log(f"Rebuilt SkinCluster: {skin_name}")

    def set_generic_weights(self, mesh_name, node_name, data):
            # 1. Create if Missing (Using your simplified creator)
            if not cmds.objExists(node_name):
                success = self.create_deformer_node(mesh_name, node_name, data['type'])
                if not success: return

            # 2. Resolve Index
            # We need the logical index of the geometry to know WHICH weight array to target.
            mesh_path = self.get_dag_path(mesh_name)
            idx = self.resolve_deformer_index(node_name, mesh_path.partialPathName())
            
            # 3. Prepare Data
            # The data['weights'] is a list of [vtx_id, value]. 
            # For efficiency, we want to construct a dense list to set in one command 
            # if the data covers all vertices (which my dense export does).
            
            # Helper: Construct full list matching vertex count
            # (This ensures we don't get mismatch errors if the file is sparse)
            vtx_count = data['vertex_count']
            full_weights = [1.0] * vtx_count # Default to 1.0 (safest for deformers)
            
            # Fill from data
            for item in data['weights']:
                vtx = int(item[0])
                val = float(item[1])
                if vtx < vtx_count:
                    full_weights[vtx] = val
                    
            # 4. Apply using cmds (Fastest for Batch)
            # API 2.0 MPlug iteration is slow for 10k+ verts. cmds.setAttr with a list is instant.
            # Syntax: setAttr node.weightList[idx].weights[0:N] v1 v2 v3 ...
            
            attr_path = f"{node_name}.weightList[{idx}].weights[0:{vtx_count-1}]"
            
            try:
                # *full_weights expands the list into arguments
                cmds.setAttr(attr_path, *full_weights) 
                self.log(f"Applied {vtx_count} weights to: {node_name}")
                
            except Exception as e:
                self.log(f"Batch setAttr failed on {node_name}: {e}. Falling back to slow loop.", "warning")
                # Fallback: Plug Iteration (API 2.0 style)
                try:
                    mobj = self.get_mobject(node_name)
                    fn_filter = oma.MFnGeometryFilter(mobj)
                    wl_plug = fn_filter.findPlug("weightList", False).elementByLogicalIndex(idx)
                    w_plug = wl_plug.child(0) # The 'weights' array
                    
                    for vtx, val in enumerate(full_weights):
                        w_plug.elementByLogicalIndex(vtx).setFloat(val)
                except Exception as e2:
                    self.log(f"Critical Fail on {node_name}: {e2}", "error")

    def import_data(self, file_path):
        if not os.path.exists(file_path):
            self.log("File not found.", "error")
            return

        with open(file_path, 'r') as f:
            scene_data = json.load(f)

        for mesh_name, deformers in scene_data.items():
            if not cmds.objExists(mesh_name):
                self.log(f"Mesh not found: {mesh_name}", "warning")
                continue
            
            for def_name, data in deformers.items():
                if data['type'] == "skinCluster":
                    self.set_skin_weights(mesh_name, data)
                else:
                    self.set_generic_weights(mesh_name, def_name, data)
# --- Usage ---
import os
manager = DeformerManager()
# manager.export_data(r"C:\Users\guido.gonzalez\Downloads\scene_weights.json")
manager.import_data(r"C:\Users\guido.gonzalez\Downloads\scene_weights.json")