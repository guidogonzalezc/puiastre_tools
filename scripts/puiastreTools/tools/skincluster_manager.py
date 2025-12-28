"""
SkinCluster IO - Production Grade (FINAL FIX)
Author: Senior Rigging TD
Compatible: Maya 2024, 2025, 2026
"""

import json
import os
import maya.cmds as cmds
import maya.api.OpenMaya as om
import maya.api.OpenMayaAnim as oma

class SkinIO:
    def __init__(self):
        self.k_skin_attrs = [
            "skinningMethod",
            "normalizeWeights",
            "maintainMaxInfluences",
            "maxInfluences",
            "weightDistribution"
        ]

    def _get_dag_path(self, node_name):
        """Helper para obtener MDagPath de un string."""
        sel = om.MSelectionList()
        try:
            sel.add(node_name)
            return sel.getDagPath(0)
        except:
            return None

    def _get_skin_clusters(self, dag_path):
        """
        Retorna una lista de MObjects de skinClusters adjuntos a la mesh,
        ordenados por orden de evaluación (deformación).
        """
        # Usamos cmds para listar historia porque es seguro y ordenado para el stack
        history = cmds.listHistory(dag_path.fullPathName(), pruneDagObjects=True, interestLevel=1) or []
        skins = [x for x in history if cmds.nodeType(x) == "skinCluster"]
        
        # skins viene ordenado del final del grafo hacia arriba (Top -> Bottom)
        # Lo invertimos para guardar: Bottom (primero que deforma) -> Top (ultimo)
        return list(reversed(skins))

    def export_skins(self, file_path):
        om.MGlobal.displayInfo(f"--- Iniciando Export a: {file_path} ---")
        
        # 1. Detectar selección o Mesh global
        sel = om.MGlobal.getActiveSelectionList()
        meshes_to_process = []

        if sel.length() > 0:
            it_sel = om.MItSelectionList(sel, om.MFn.kMesh)
            while not it_sel.isDone():
                path = it_sel.getDagPath()
                path.extendToShape()
                # Check intermediate object (shapes de historia)
                mf_dag = om.MFnDagNode(path)
                if not mf_dag.isIntermediateObject:
                    meshes_to_process.append(path)
                it_sel.next()
        else:
            it_dag = om.MItDag(om.MItDag.kDepthFirst, om.MFn.kMesh)
            while not it_dag.isDone():
                path = it_dag.getPath()
                # CORRECCION AQUI: Usar MFnDagNode para checkear la propiedad
                mf_dag = om.MFnDagNode(path)
                if not mf_dag.isIntermediateObject: 
                     meshes_to_process.append(path)
                it_dag.next()

        if not meshes_to_process:
            om.MGlobal.displayWarning("No se encontraron meshes válidas para exportar.")
            return

        full_data = {}

        for mesh_path in meshes_to_process:
            mesh_name = mesh_path.partialPathName()
            
            mf_mesh = om.MFnMesh(mesh_path)
            vtx_count = mf_mesh.numVertices
            
            skins = self._get_skin_clusters(mesh_path)
            if not skins:
                continue

            om.MGlobal.displayInfo(f"Procesando: {mesh_name} | Skins: {len(skins)}")
            
            mesh_data = []
            
            for skin_name in skins:
                sel_skin = om.MSelectionList()
                sel_skin.add(skin_name)
                skin_obj = sel_skin.getDependNode(0)
                mf_skin = oma.MFnSkinCluster(skin_obj)

                # Atributos
                attrs = {}
                for attr in self.k_skin_attrs:
                    try:
                        val = cmds.getAttr(f"{skin_name}.{attr}")
                        attrs[attr] = val
                    except:
                        om.MGlobal.displayWarning(f"Attr {attr} no encontrado en {skin_name}")

                # Influencias
                influences_paths = mf_skin.influenceObjects()
                inf_names = [p.partialPathName() for p in influences_paths]

                # Pesos (Flat list)
                single_comp = om.MFnSingleIndexedComponent()
                vertex_comp = single_comp.create(om.MFn.kMeshVertComponent) # CORRECTED
                single_comp.setCompleteData(vtx_count)
                
                weights_marray, _ = mf_skin.getWeights(mesh_path, vertex_comp)
                
                # Blend Weights (Dual Quaternion)
                blend_weights_marray = mf_skin.getBlendWeights(mesh_path, vertex_comp)
                
                skin_entry = {
                    "name": skin_name,
                    "vertex_count": vtx_count,
                    "attributes": attrs,
                    "influences": inf_names,
                    "weights": list(weights_marray),
                    "blend_weights": list(blend_weights_marray)
                }
                mesh_data.append(skin_entry)

            full_data[mesh_name] = mesh_data

        with open(file_path, 'w') as f:
            json.dump(full_data, f, indent=4)
            
        om.MGlobal.displayInfo("Export completado exitosamente.")

    def import_skins(self, file_path):
        om.MGlobal.displayInfo(f"--- Iniciando Import desde: {file_path} ---")
        
        if not os.path.exists(file_path):
            om.MGlobal.displayError("El archivo JSON no existe.")
            return

        with open(file_path, 'r') as f:
            data = json.load(f)

        for mesh_name, skins_list in data.items():
            # 1. Buscar Mesh
            mesh_path = self._get_dag_path(mesh_name)
            if not mesh_path:
                om.MGlobal.displayWarning(f"Mesh skipped (No encontrada): {mesh_name}")
                continue
            
            mesh_path.extendToShape()
            mf_mesh = om.MFnMesh(mesh_path)
            
            # 2. Loop SkinClusters
            processed_skins = []

            for skin_data in skins_list:
                skin_name = skin_data["name"]
                target_vtx_count = skin_data["vertex_count"]
                
                # Check Vertices
                if mf_mesh.numVertices != target_vtx_count:
                    om.MGlobal.displayError(
                        f"ABORTANDO {skin_name} en {mesh_name}: Topología no coincide. "
                        f"Scene: {mf_mesh.numVertices}, JSON: {target_vtx_count}"
                    )
                    continue 

                # Check Influencias
                json_influences = skin_data["influences"]
                
                skin_exists = cmds.objExists(skin_name) and cmds.nodeType(skin_name) == "skinCluster"
                
                mf_skin = None
                
                if skin_exists:
                    hist = cmds.listHistory(mesh_path.fullPathName(), pdo=True)
                    if skin_name not in hist:
                        om.MGlobal.displayWarning(f"{skin_name} existe pero no está conectado a {mesh_name}. Saltando.")
                        continue
                    
                    om.MGlobal.displayInfo(f"Actualizando existente: {skin_name}")
                    
                    sel_s = om.MSelectionList()
                    sel_s.add(skin_name)
                    mf_skin = oma.MFnSkinCluster(sel_s.getDependNode(0))
                    
                    scene_infs = [p.partialPathName() for p in mf_skin.influenceObjects()]
                    missing_infs = [inf for inf in json_influences if inf not in scene_infs]
                    
                    if missing_infs:
                        om.MGlobal.displayInfo(f"Añadiendo {len(missing_infs)} influencias faltantes a {skin_name}")
                        cmds.skinCluster(skin_name, e=True, addInfluence=missing_infs, weight=0.0)

                else:
                    om.MGlobal.displayInfo(f"Creando nuevo: {skin_name}")
                    valid_joints = []
                    for j in json_influences:
                        if cmds.objExists(j):
                            valid_joints.append(j)
                        else:
                            om.MGlobal.displayWarning(f"Joint {j} no existe. Ignorada para {skin_name}")
                    
                    if not valid_joints:
                        om.MGlobal.displayError(f"No hay joints validas para {skin_name}. Saltando.")
                        continue

                    new_skin = cmds.skinCluster(
                        valid_joints, 
                        mesh_path.fullPathName(), 
                        n=skin_name, 
                        toSelectedBones=True, 
                        multi=True
                    )[0]
                    
                    sel_s = om.MSelectionList()
                    sel_s.add(new_skin)
                    mf_skin = oma.MFnSkinCluster(sel_s.getDependNode(0))

                # --- Seteo de Atributos ---
                for attr, val in skin_data["attributes"].items():
                    try:
                        if attr == "maintainMaxInfluences":
                            cmds.setAttr(f"{skin_name}.{attr}", bool(val))
                        else:
                            cmds.setAttr(f"{skin_name}.{attr}", val)
                    except:
                        pass

                # --- Seteo de Pesos ---
                scene_inf_paths = mf_skin.influenceObjects()
                scene_inf_names = [p.partialPathName() for p in scene_inf_paths]
                scene_inf_map = {name: i for i, name in enumerate(scene_inf_names)}
                
                mapped_indices = []
                valid_json_indices = [] 
                
                for idx, j_name in enumerate(json_influences):
                    if j_name in scene_inf_map:
                        mapped_indices.append(scene_inf_map[j_name])
                        valid_json_indices.append(idx)
                
                m_influence_indices = om.MIntArray(mapped_indices)
                
                json_weights = skin_data["weights"]
                final_weights = om.MDoubleArray()
                
                if len(mapped_indices) == len(json_influences):
                    final_weights = om.MDoubleArray(json_weights)
                else:
                    stride = len(json_influences)
                    num_verts = target_vtx_count
                    temp_weights = [0.0] * (len(mapped_indices) * num_verts)
                    
                    cursor = 0
                    for v in range(num_verts):
                        base = v * stride
                        for j_idx in valid_json_indices:
                            temp_weights[cursor] = json_weights[base + j_idx]
                            cursor += 1
                    final_weights = om.MDoubleArray(temp_weights)

                single_comp = om.MFnSingleIndexedComponent()
                vertex_comp = single_comp.create(om.MFn.kMeshVertComponent) # CORRECTED
                single_comp.setCompleteData(target_vtx_count)
                
                mf_skin.setWeights(mesh_path, vertex_comp, m_influence_indices, final_weights, False)

                # --- Blend Weights ---
                blend_w = om.MDoubleArray(skin_data["blend_weights"])
                mf_skin.setBlendWeights(mesh_path, vertex_comp, blend_w)

                processed_skins.append(skin_name)

            # 3. Reordenamiento
            if processed_skins:
                current_hist = cmds.listHistory(mesh_path.fullPathName(), pruneDagObjects=True, interestLevel=1)
                current_skins = [x for x in current_hist if cmds.nodeType(x) == "skinCluster"]
                current_skins = list(reversed(current_skins))
                
                unknown_skins = [s for s in current_skins if s not in processed_skins]
                desired_order = unknown_skins + processed_skins
                
                om.MGlobal.displayInfo(f"Reordenando deformadores en {mesh_name}...")
                
                for skin in reversed(desired_order):
                    try:
                        cmds.reorderDeformers(skin, mesh_path.fullPathName(), back=True)
                    except:
                        pass

        om.MGlobal.displayInfo("--- Importación Finalizada ---")
import os
# Ejemplo de uso:
# exporter = SkinIO()
path = r"D:\git\maya\puiastre_tools\assets\varyndor\skinning\CHAR_varyndor_001.skn"
# SkinIO().export_skins(file_path = path)
SkinIO().import_skins(file_path = path)