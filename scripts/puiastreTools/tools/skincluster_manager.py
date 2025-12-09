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
    Updated to support:
    - Exact node naming.
    - Input/Output connection reconstruction (Deformation Chain).
    - Manual node creation via createNode.
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
        try:
            mobj_def = self.get_mobject(deformer_node)
            mobj_geo = self.get_mobject(shape_node_name)
            fn_filter = oma.MFnGeometryFilter(mobj_def)
            return fn_filter.indexForOutputShape(mobj_geo)
        except:
            pass 
        return 0

    def get_connections(self, deformer_node):
        """
        Captures the upstream and downstream geometry connections.
        This allows us to rebuild the deformation stack order.
        """
        connections = {"input": None, "output": None}
        
        # 1. Input (Upstream) - Usually input[0].inputGeometry
        # We store the Source Plug (e.g., 'previousDeformer.outputGeometry[0]')
        inputs = cmds.listConnections(f"{deformer_node}.input[0].inputGeometry", plugs=True, source=True, destination=False)
        if inputs:
            connections["input"] = inputs[0]

        # 2. Output (Downstream) - Usually outputGeometry[0]
        # We store the Destination Plug (e.g., 'nextDeformer.input[0].inputGeometry' or 'meshShape.inMesh')
        outputs = cmds.listConnections(f"{deformer_node}.outputGeometry[0]", plugs=True, source=False, destination=True)
        if outputs:
            connections["output"] = outputs[0]
            
        return connections

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
        }

        # Connections
        conns = self.get_connections(deformer_node)

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
            "connections": conns,
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
        conns = self.get_connections(deformer_node)
        
        # Extract
        try:
            for i in range(vtx_count):
                w = fn_filter.weightAtIndex(geometry_path, idx, i)
                dense_weights.append([i, round(w, 5)])
        except Exception as e:
            self.log(f"API Read Error on {deformer_node}: {e}", "error")

        return {
            "type": deformer_type,
            "vertex_count": vtx_count,
            "connections": conns,
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
            
            # Reverse deformers so we export bottom-up (Input -> Output) 
            # or keep them as is. Usually ls history returns newest first. 
            # We will store them in a dict, order matters for re-construction.
            
            mesh_data = {}
            dag_path = self.get_dag_path(mesh)
            
            for def_node in deformers:
                if cmds.nodeType(def_node) == "tweak": continue
                
                node_type = cmds.nodeType(def_node)
                # Keep simple name for key
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
    
    def reconstruct_connections(self, node_name, data, mesh_fallback=None):
        """
        Reconnects the deformer. 
        FAIL-SAFE: If the recorded input source is missing (common with Orig shapes),
        it attempts to use the mesh_fallback (the current mesh shape) as the input
        to ensure the deformer has valid geometry data.
        """
        conns = data.get("connections", {})
        
        # 1. Connect Inputs (Upstream)
        input_src = conns.get("input")
        input_connected = False
        
        if input_src and cmds.objExists(input_src):
            try:
                cmds.connectAttr(input_src, f"{node_name}.input[0].inputGeometry", f=True)
                self.log(f"Connected Input: {input_src} -> {node_name}")
                input_connected = True
            except Exception as e:
                self.log(f"Failed to connect recorded Input {input_src}: {e}", "warning")
        
        # FALLBACK: If recorded input is missing, find a valid shape
        if not input_connected and mesh_fallback:
            self.log(f"Input source {input_src} missing. Attempting fallback...", "warning")
            # Try to find an 'Orig' shape or use the mesh itself if it's the start of the chain
            shapes = cmds.listRelatives(cmds.listRelatives(mesh_fallback, p=True)[0], s=True, f=True)
            orig_shape = [s for s in shapes if s.endswith("Orig")]
            
            source_plug = None
            if orig_shape:
                source_plug = f"{orig_shape[0]}.worldMesh[0]"
            else:
                # Dangerous but better than nothing: feed the mesh itself (circular check needed usually)
                # Ideally, we look for the last deformer in the chain, but for now let's warn.
                self.log("Could not auto-find an Orig shape. SkinCluster might be missing input geometry.", "error")

            if source_plug:
                try:
                    cmds.connectAttr(source_plug, f"{node_name}.input[0].inputGeometry", f=True)
                    self.log(f"Connected Fallback Input: {source_plug} -> {node_name}")
                    input_connected = True
                except Exception as e:
                    self.log(f"Fallback connection failed: {e}", "error")

        # 2. Connect Deformer -> Outputs (Downstream)
        output_dst = conns.get("output")
        if output_dst:
            node_dst = output_dst.split('.')[0]
            if cmds.objExists(node_dst):
                try:
                    cmds.connectAttr(f"{node_name}.outputGeometry[0]", output_dst, f=True)
                    self.log(f"Connected Output: {node_name} -> {output_dst}")
                except Exception as e:
                    self.log(f"Failed to connect Output {output_dst}: {e}", "warning")
                    
        return input_connected

    def create_bare_node(self, node_type, name):
        """
        Creates the node using createNode (pure dependency graph node).
        Does NOT attach it to geometry automatically.
        """
        if cmds.objExists(name):
            # Decide if you want to delete or skip. Here we skip/return existing.
            if cmds.nodeType(name) == node_type:
                return name
            else:
                self.log(f"Name collision: {name} exists but is wrong type.", "error")
                return None
        
        return cmds.createNode(node_type, name=name)

    def set_skin_weights(self, mesh_name, node_name, data):
        # 1. Create Node Manually
        skin_node = self.create_bare_node("skinCluster", node_name)
        if not skin_node: return
        
        # Lock node during setup to prevent premature evaluation crashes
        cmds.setAttr(f"{skin_node}.nodeState", 1) # 1 = PassThrough/Cache

        # 2. Re-establish Graph Connections
        # We pass mesh_name as fallback to ensure we get *some* input geometry
        has_input = self.reconstruct_connections(skin_node, data, mesh_fallback=mesh_name)
        
        # 3. Add Influences
        file_influences = data['influences']
        scene_influences = [j for j in file_influences if cmds.objExists(j)]
        
        if scene_influences:
            # IMPORTANT: We add 'geometry=mesh_name'. 
            # This forces the SkinCluster to register the geometry association 
            # even if the connections above were "weird".
            try:
                cmds.skinCluster(skin_node, e=True, 
                                 addInfluence=scene_influences, 
                                 geometry=mesh_name, # Explicit association
                                 wt=0)
            except Exception as e:
                self.log(f"Add Influence Error: {e}", "error")

        # 4. Attributes
        attrs = data.get("attributes", {})
        cmds.setAttr(f"{skin_node}.normalizeWeights", 0) 
        if "skinningMethod" in attrs:
            cmds.setAttr(f"{skin_node}.skinningMethod", attrs["skinningMethod"])

        # 5. Set Weights (API)
        # Only proceed if we have valid input geometry, otherwise API crashes
        if has_input:
            try:
                mesh_path = self.get_dag_path(mesh_name)
                mobj = self.get_mobject(skin_node)
                fn_skin = oma.MFnSkinCluster(mobj)
                
                # Map file indices to scene indices
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
                
                # Verify size matches perfectly to avoid 'Unexpected Internal Failure'
                if len(full_weights) == len(infl_indices) * num_verts:
                    fn_skin.setWeights(mesh_path, components, infl_indices, full_weights, False)
                else:
                    self.log(f"Weight Array Mismatch on {node_name}. Skipping SetWeights.", "error")
            except Exception as e:
                self.log(f"API SetWeights Failed on {node_name}: {e}", "error")
        else:
             self.log(f"Skipping API Weights on {node_name} due to missing Input Geometry.", "error")

        # DQ Blend
        blend_data = data.get("blend_weights", [])
        if blend_data and has_input:
            try:
                full_blend = om.MDoubleArray(num_verts, 0.0)
                for item in blend_data:
                    full_blend[int(item[0])] = float(item[1])
                fn_skin.setBlendWeights(mesh_path, components, full_blend)
            except:
                pass

        # Unlock Node
        cmds.setAttr(f"{skin_node}.nodeState", 0) # Normal

        # Restore Attributes
        if "normalizeWeights" in attrs:
            cmds.setAttr(f"{skin_node}.normalizeWeights", attrs["normalizeWeights"])
        if "maxInfluences" in attrs:
            cmds.setAttr(f"{skin_node}.maxInfluences", attrs["maxInfluences"])

        self.log(f"Rebuilt SkinCluster: {skin_node}")

    def set_generic_weights(self, mesh_name, node_name, data):
        # 1. Create Node Manually
        def_node = self.create_bare_node(data['type'], node_name)
        if not def_node: return

        # 2. Re-establish Graph Connections
        self.reconstruct_connections(def_node, data)
        
        # 3. Set Weights
        # Resolve Index - Since we just connected it, logical index is likely 0
        # But we verify via API
        mesh_path = self.get_dag_path(mesh_name)
        idx = self.resolve_deformer_index(def_node, mesh_path.partialPathName())
        
        vtx_count = data['vertex_count']
        full_weights = [1.0] * vtx_count
        
        for item in data['weights']:
            vtx = int(item[0])
            val = float(item[1])
            if vtx < vtx_count:
                full_weights[vtx] = val
                
        attr_path = f"{def_node}.weightList[{idx}].weights[0:{vtx_count-1}]"
        
        try:
            cmds.setAttr(attr_path, *full_weights) 
            self.log(f"Applied weights to: {def_node}")
        except Exception as e:
            self.log(f"Batch setAttr failed on {def_node}: {e}", "warning")

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
            
            # Sort keys logic could be added here if needed, 
            # currently relying on JSON save order.
            
            for def_name, data in deformers.items():
                if data['type'] == "skinCluster":
                    self.set_skin_weights(mesh_name, def_name, data)
                else:
                    self.set_generic_weights(mesh_name, def_name, data)



# --- Usage ---
import os
manager = DeformerManager()
# manager.export_data(r"C:\Users\guido\Downloads\scene_weights.json")
manager.import_data(r"C:\Users\guido\Downloads\scene_weights.json")