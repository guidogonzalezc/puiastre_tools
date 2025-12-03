import maya.cmds as cmds
import maya.api.OpenMaya as om
import maya.api.OpenMayaAnim as oma
import json
import time
import os

class DeformerManager(object):
    """
    Production tool to Export and Import/Rebuild deformer weights.
    Fixed to correctly handle DeltaMush/Generic deformer default states and zero-weights.
    """
    
    def __init__(self):
        self.tolerance = 0.0001 

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

    # ------------------------------------------------------------------------
    # EXPORT LOGIC
    # ------------------------------------------------------------------------

    def extract_skin_cluster(self, deformer_node, geometry_path):
        """
        Exports SkinCluster data.
        OPTIMIZATION: We only store non-zero weights (> 0.0001) for SkinClusters.
        """
        mobj = self.get_mobject(deformer_node)
        fn_skin = oma.MFnSkinCluster(mobj)
        
        components, vtx_count = self.get_mesh_components(geometry_path)
        weights_flat, num_infl = fn_skin.getWeights(geometry_path, components)
        
        infl_paths = fn_skin.influenceObjects()
        infl_names = [p.partialPathName() for p in infl_paths]
        
        sparse_weights = []
        
        for v in range(vtx_count):
            base_idx = v * num_infl
            for i in range(num_infl):
                w = weights_flat[base_idx + i]
                if w > self.tolerance:
                    # [Vertex ID, Influence Index, Weight Value]
                    sparse_weights.append([v, i, round(w, 5)])

        return {
            "type": "skinCluster",
            "vertex_count": vtx_count,
            "influences": infl_names,
            "weights": sparse_weights
        }

    def extract_generic_deformer(self, deformer_node, geometry_path, deformer_type):
        """
        Exports Generic Deformer (DeltaMush, BlendShape) data.
        FIX: Exports DENSE data (every vertex) to preserve 0.0 masks.
        FIX: Handles unpainted state by defaulting to 1.0.
        """
        mobj = self.get_mobject(deformer_node)
        fn_filter = oma.MFnGeometryFilter(mobj)
        components, vtx_count = self.get_mesh_components(geometry_path)
        
        dense_weights = []
        
        try:
            # 1. Resolve Index
            idx = fn_filter.indexForOutputShape(geometry_path.node())
            
            # 2. Check for "Unpainted" State
            # If the weightList[idx] plug is empty/null, the user sees 1.0 (default), 
            # but the API sees 0.0 (raw). We must verify physical existence.
            wl_plug = fn_filter.findPlug("weightList", False)
            
            is_painted = False
            if wl_plug.isArray():
                # We assume if the logical index exists, it's painted.
                # getExistingArrayAttributeIndices is the safest check.
                existing_indices = wl_plug.getExistingArrayAttributeIndices()
                if idx in existing_indices:
                    is_painted = True

            # 3. Extract
            if is_painted:
                # User has painted weights. We must export EXACTLY what is there.
                # Even if it is 0.0 (masked). Do not optimize generic deformers.
                for i in range(vtx_count):
                    w = fn_filter.weightAtIndex(geometry_path, idx, i)
                    # [Vertex ID, Weight Value]
                    dense_weights.append([i, round(w, 5)])
            else:
                # Unpainted = Default DeltaMush is 1.0 everywhere.
                print(f"   -> {deformer_node}: No paint detected. Exporting 1.0 defaults.")
                for i in range(vtx_count):
                    dense_weights.append([i, 1.0])
                    
        except Exception as e:
            print(f"Warning reading {deformer_node}: {e}")

        return {
            "type": deformer_type,
            "vertex_count": vtx_count,
            "influences": [], 
            "weights": dense_weights
        }

    def export_data(self, file_path):
        st = time.time()
        meshes = cmds.ls(type="mesh", noIntermediate=True, long=True)
        scene_data = {}
        
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
                
                print(f">> Exporting: {def_name} ({node_type})")
                
                payload = None
                if node_type == "skinCluster":
                    payload = self.extract_skin_cluster(def_node, dag_path)
                elif node_type in ["deltaMush", "cluster", "blendShape", "nonLinear", "softMod", "tension"]:
                    payload = self.extract_generic_deformer(def_node, dag_path, node_type)
                
                if payload:
                    mesh_data[def_name] = payload
            
            if mesh_data:
                scene_data[short_name] = mesh_data

        with open(file_path, 'w') as f:
            json.dump(scene_data, f, indent=4)
            
        print(f"Export Complete: {time.time() - st:.4f}s")

    # ------------------------------------------------------------------------
    # IMPORT / REBUILD LOGIC
    # ------------------------------------------------------------------------

    def set_skin_weights(self, mesh_name, data):
        mesh_path = self.get_dag_path(mesh_name)
        if not mesh_path: return

        file_influences = data['influences']
        scene_influences = []
        for jnt in file_influences:
            if cmds.objExists(jnt):
                scene_influences.append(jnt)
        
        if not scene_influences: return

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
            vtx = int(item[0])
            file_inf_idx = int(item[1])
            val = float(item[2])
            if file_inf_idx in file_to_scene_map:
                scene_inf_idx = file_to_scene_map[file_inf_idx]
                flat_idx = (vtx * num_scene_infl) + scene_inf_idx
                full_weights[flat_idx] = val

        components, _ = self.get_mesh_components(mesh_path)
        infl_indices = om.MIntArray(range(num_scene_infl))
        fn_skin.setWeights(mesh_path, components, infl_indices, full_weights, False)
        print(f"Rebuilt SkinCluster: {skin_name}")

    def set_generic_weights(self, mesh_name, node_name, data):
        mesh_path = self.get_dag_path(mesh_name)
        if not cmds.objExists(node_name): return
            
        mobj = self.get_mobject(node_name)
        fn_filter = oma.MFnGeometryFilter(mobj)
        try:
            idx = fn_filter.indexForOutputShape(mesh_path.node())
            
            # Since we now export dense data (every vertex), we can iterate safely.
            # Optimization: If the array is huge, MPlug.setEnums is faster, 
            # but for <50k verts, this loop is instantaneous.
            for item in data['weights']:
                vtx = int(item[0])
                val = float(item[1])
                fn_filter.setWeight(mesh_path, idx, vtx, val)
                
            print(f"Applied weights: {node_name}")
        except Exception as e:
            print(f"Error on {node_name}: {e}")

    def import_data(self, file_path):
        if not os.path.exists(file_path): return
        with open(file_path, 'r') as f:
            scene_data = json.load(f)
        for mesh_name, deformers in scene_data.items():
            if not cmds.objExists(mesh_name): continue
            print(f"Importing for: {mesh_name}")
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