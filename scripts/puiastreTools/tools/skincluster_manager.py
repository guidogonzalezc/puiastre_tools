import maya.cmds as cmds
import maya.api.OpenMaya as om
import maya.api.OpenMayaAnim as oma
import json
import time
import os

class SkinManager(object):
    """
    Fixed SkinManager that handles Stacked SkinClusters (Multiple skins per mesh).
    """
    
    def __init__(self):
        self.tolerance = 0.0001 
    
    def log(self, msg, level="info"):
        prefix = "[SkinManager]"
        if level == "info":
            om.MGlobal.displayInfo(f"{prefix} {msg}")
        elif level == "warning":
            om.MGlobal.displayWarning(f"{prefix} {msg}")
        elif level == "error":
            om.MGlobal.displayError(f"{prefix} {msg}")

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
    # EXPORT (Unchanged)
    # ------------------------------------------------------------------------

    def get_connections(self, skin_node):
        connections = {"input_0": None, "original_geo_0": None, "output_geo_0": None}
        
        # input[0].inputGeometry
        in_conns = cmds.listConnections(f"{skin_node}.input[0].inputGeometry", plugs=True, source=True, destination=False)
        if in_conns: connections["input_0"] = in_conns[0]

        # outputGeometry[0]
        out_conns = cmds.listConnections(f"{skin_node}.outputGeometry[0]", plugs=True, source=False, destination=True)
        if out_conns: connections["output_geo_0"] = out_conns[0]
        
        return connections

    def extract_skin_data(self, skin_node, geometry_path):
        mobj = self.get_mobject(skin_node)
        fn_skin = oma.MFnSkinCluster(mobj)
        components, vtx_count = self.get_mesh_components(geometry_path)
        
        attrs = {
            "skinningMethod": cmds.getAttr(f"{skin_node}.skinningMethod"),
            "normalizeWeights": cmds.getAttr(f"{skin_node}.normalizeWeights"),
            "maintainMaxInfluences": cmds.getAttr(f"{skin_node}.maintainMaxInfluences"),
            "maxInfluences": cmds.getAttr(f"{skin_node}.maxInfluences"),
            "weightDistribution": cmds.getAttr(f"{skin_node}.weightDistribution") 
        }

        conns = self.get_connections(skin_node)
        
        infl_paths = fn_skin.influenceObjects()
        infl_names = [p.partialPathName() for p in infl_paths]
        
        weights_flat, num_infl = fn_skin.getWeights(geometry_path, components)
        sparse_weights = []
        for v in range(vtx_count):
            base_idx = v * num_infl
            for i in range(num_infl):
                w = weights_flat[base_idx + i]
                if w > self.tolerance:
                    sparse_weights.append([v, i, round(w, 5)])

        blend_weights = []
        try:
            raw_blend = fn_skin.getBlendWeights(geometry_path, components)
            for i, w in enumerate(raw_blend):
                if w > self.tolerance:
                    blend_weights.append([i, round(w, 5)])
        except:
            pass

        return {
            "vertex_count": vtx_count,
            "attributes": attrs,
            "connections": conns,
            "influences": infl_names,
            "weights": sparse_weights,
            "blend_weights": blend_weights
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
            
            history = cmds.listHistory(transform, pruneDagObjects=True) or []
            skins = cmds.ls(history, type="skinCluster")
            
            if not skins: continue

            # Reverse to export Bottom -> Top
            skins_ordered = list(reversed(skins))
            
            mesh_data = {}
            dag_path = self.get_dag_path(mesh)
            
            for skin_node in skins_ordered:
                skin_name = skin_node.split(":")[-1]
                self.log(f"Processing: {short_name} -> {skin_name}")
                mesh_data[skin_name] = self.extract_skin_data(skin_node, dag_path)
                count += 1
            
            if mesh_data:
                scene_data[short_name] = mesh_data

        with open(file_path, 'w') as f:
            json.dump(scene_data, f, indent=4)
            
        self.log(f"Export Complete. {count} SkinClusters saved.")

    # ------------------------------------------------------------------------
    # IMPORT (FIXED)
    # ------------------------------------------------------------------------

    def import_skin_cluster(self, mesh_name, skin_name, data):
        # 1. Resolve Mesh
        mesh_path_obj = self.get_dag_path(mesh_name)
        if not mesh_path_obj: 
            self.log(f"Mesh not found: {mesh_name}", "error")
            return
        
        # Get full path string (safe for component logic)
        full_mesh_name = mesh_path_obj.fullPathName()

        # 2. Validate Influences
        file_influences = data['influences']
        scene_influences = [j for j in file_influences if cmds.objExists(j)]
        
        if not scene_influences:
            self.log(f"Skipping {skin_name}: No influences found.", "error")
            return

        # 3. Get or Create SkinCluster
        current_skin = ""
        
        # Check if skin already exists specifically
        if cmds.objExists(skin_name) and cmds.nodeType(skin_name) == "skinCluster":
            # Verify if it's connected to our mesh
            # (Simple loose check usually suffices for import)
            current_skin = skin_name
            self.log(f"Updating existing skin: {current_skin}")
            
            curr_infls = cmds.skinCluster(current_skin, q=True, influence=True) or []
            to_add = list(set(scene_influences) - set(curr_infls))
            if to_add:
                cmds.skinCluster(current_skin, e=True, addInfluence=to_add, wt=0)
        else:
            # --- CREATION LOGIC FIX ---
            self.log(f"Creating new skin: {skin_name}")
            
            # Check if ANY skinCluster exists on this mesh (Stacking detection)
            hist = cmds.listHistory(full_mesh_name, pruneDagObjects=True) or []
            existing_skins = cmds.ls(hist, type="skinCluster")
            
            target_geometry = full_mesh_name
            
            if existing_skins:
                # If a skin exists, we MUST target components (vtx[:]) to force stacking.
                # If we target the transform, Maya throws "already connected".
                
                # We need the shape name for vtx syntax
                shapes = cmds.listRelatives(full_mesh_name, shapes=True, fullPath=True)
                if shapes:
                    target_geometry = f"{shapes[0]}.vtx[:]"
                else:
                    target_geometry = f"{full_mesh_name}.vtx[:]"
                    
                self.log(f"  -> Stacking detected. Targeting components: {target_geometry}")

            try:
                # Create the SkinCluster
                # name=skin_name tries to name it. If taken, Maya creates skinCluster1, etc.
                result = cmds.skinCluster(scene_influences, target_geometry, 
                                          toSelectedBones=True, 
                                          name=skin_name)
                current_skin = result[0]
                
            except Exception as e:
                self.log(f"Creation failed for {skin_name}: {e}", "error")
                return

        # 4. Connection Log
        saved_conns = data.get("connections", {})
        if saved_conns.get("input_0"):
            self.log(f"  -> Expects Input: {saved_conns['input_0']}")

        # 5. Restore Attributes
        attrs = data.get("attributes", {})
        cmds.setAttr(f"{current_skin}.normalizeWeights", 0) 
        if "skinningMethod" in attrs:
            cmds.setAttr(f"{current_skin}.skinningMethod", attrs["skinningMethod"])

        # 6. Apply Weights
        mobj = self.get_mobject(current_skin)
        fn_skin = oma.MFnSkinCluster(mobj)
        
        scene_infl_paths = fn_skin.influenceObjects()
        scene_infl_names = [p.partialPathName() for p in scene_infl_paths]
        
        file_to_scene_map = {}
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

        components, _ = self.get_mesh_components(mesh_path_obj)
        infl_indices = om.MIntArray(range(num_scene_infl))
        fn_skin.setWeights(mesh_path_obj, components, infl_indices, full_weights, False)

        # 7. Apply Blend Weights (DQ)
        blend_data = data.get("blend_weights", [])
        if blend_data:
            full_blend = om.MDoubleArray(num_verts, 0.0)
            for item in blend_data:
                full_blend[int(item[0])] = float(item[1])
            fn_skin.setBlendWeights(mesh_path_obj, components, full_blend)

        # 8. Finalize
        if "normalizeWeights" in attrs:
            cmds.setAttr(f"{current_skin}.normalizeWeights", attrs["normalizeWeights"])
        if "maintainMaxInfluences" in attrs:
            cmds.setAttr(f"{current_skin}.maintainMaxInfluences", attrs["maintainMaxInfluences"])
        if "maxInfluences" in attrs:
            cmds.setAttr(f"{current_skin}.maxInfluences", attrs["maxInfluences"])
        if "weightDistribution" in attrs:
             cmds.setAttr(f"{current_skin}.weightDistribution", attrs["weightDistribution"])

        self.log(f"Rebuilt: {current_skin}")

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
            
            # Deformers dict is ordered (Bottom -> Top). Iterating creates them in correct stack order.
            for skin_name, data in deformers.items():
                self.import_skin_cluster(mesh_name, skin_name, data)

# --- Usage Example ---
if __name__ == "__main__":
    # Example paths - update for your local machine
    path = r"C:\Users\guido\Downloads\skincluster_test.json"
    
    manager = SkinManager()
    
    # 1. Select meshes and run Export
    manager.export_data(path)
    print("Exported skin data.")
    
    # 2. Open new scene (with same geometry) and run Import
    # manager.import_data(path)