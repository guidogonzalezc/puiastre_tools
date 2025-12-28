"""
SkinCluster IO - SPARSE OPTIMIZED (Small File Size)
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
        # Cualquier peso menor a esto se considera 0 y no se guarda
        self.tolerance = 1e-5 

    def _get_dag_path(self, node_name):
        sel = om.MSelectionList()
        try:
            sel.add(node_name)
            return sel.getDagPath(0)
        except:
            return None

    def _get_skin_clusters(self, dag_path):
        history = cmds.listHistory(dag_path.fullPathName(), pruneDagObjects=True, interestLevel=1) or []
        skins = [x for x in history if cmds.nodeType(x) == "skinCluster"]
        return list(reversed(skins))

    def export_skins(self, file_path):
        om.MGlobal.displayInfo(f"--- Iniciando Export OPTIMIZADO a: {file_path} ---")
        
        sel = om.MGlobal.getActiveSelectionList()
        meshes_to_process = []

        if sel.length() > 0:
            it_sel = om.MItSelectionList(sel, om.MFn.kMesh)
            while not it_sel.isDone():
                path = it_sel.getDagPath()
                path.extendToShape()
                mf_dag = om.MFnDagNode(path)
                if not mf_dag.isIntermediateObject:
                    meshes_to_process.append(path)
                it_sel.next()
        else:
            it_dag = om.MItDag(om.MItDag.kDepthFirst, om.MFn.kMesh)
            while not it_dag.isDone():
                path = it_dag.getPath()
                mf_dag = om.MFnDagNode(path)
                if not mf_dag.isIntermediateObject: 
                     meshes_to_process.append(path)
                it_dag.next()

        if not meshes_to_process:
            om.MGlobal.displayWarning("No se encontraron meshes válidas.")
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
                mf_skin = oma.MFnSkinCluster(sel_skin.getDependNode(0))

                # --- Atributos ---
                attrs = {}
                for attr in self.k_skin_attrs:
                    try:
                        attrs[attr] = cmds.getAttr(f"{skin_name}.{attr}")
                    except:
                        pass

                # --- Influencias ---
                influences_paths = mf_skin.influenceObjects()
                inf_names = [p.partialPathName() for p in influences_paths]

                # --- Pesos (Logica Sparse) ---
                single_comp = om.MFnSingleIndexedComponent()
                vertex_comp = single_comp.create(om.MFn.kMeshVertComponent)
                single_comp.setCompleteData(vtx_count)
                
                # Obtenemos la lista gigante plana (Dense)
                weights_marray, _ = mf_skin.getWeights(mesh_path, vertex_comp)
                flat_weights = list(weights_marray)
                
                # Convertimos a Sparse: Diccionario por Joint { "joint": {"id": [], "w": []} }
                sparse_weights = {}
                stride = len(inf_names)
                
                # Iteramos para comprimir. 
                # Nota: Esto es un poco mas lento en Python puro que el dump directo, 
                # pero ahorra GBs de disco.
                
                for inf_idx, inf_name in enumerate(inf_names):
                    # Listas temporales para esta joint
                    j_indices = []
                    j_weights = []
                    
                    # Recorremos todos los vértices para esta influencia específica
                    # Math: El peso del vertice V para la influencia I está en: V * stride + I
                    for v_idx in range(vtx_count):
                        val = flat_weights[v_idx * stride + inf_idx]
                        
                        if val > self.tolerance: # Solo guardamos si es relevante
                            # Redondeamos a 5 decimales para limpiar "ruido" de floats y ahorrar texto
                            j_indices.append(v_idx)
                            j_weights.append(round(val, 5))
                    
                    # Solo guardamos la joint si tiene algun peso
                    if j_indices:
                        sparse_weights[inf_name] = {
                            "ix": j_indices, # Indices de vertices
                            "vw": j_weights  # Valores de peso
                        }

                # --- Blend Weights (Dual Quaternion) ---
                # Tambien lo comprimimos porque suele ser 0 o 1
                blend_weights_marray = mf_skin.getBlendWeights(mesh_path, vertex_comp)
                flat_blend = list(blend_weights_marray)
                sparse_blend = {}
                
                # Blend weights es 1 valor por vertice, más fácil
                b_indices = []
                b_values = []
                for v_idx, val in enumerate(flat_blend):
                    if val > self.tolerance:
                        b_indices.append(v_idx)
                        b_values.append(round(val, 5))
                
                if b_indices:
                    sparse_blend = {"ix": b_indices, "vw": b_values}
                
                skin_entry = {
                    "name": skin_name,
                    "vertex_count": vtx_count,
                    "attributes": attrs,
                    "influences": inf_names, # Mantenemos la lista completa para referencia
                    "sparse_weights": sparse_weights,
                    "sparse_blend": sparse_blend
                }
                mesh_data.append(skin_entry)

            full_data[mesh_name] = mesh_data

        with open(file_path, 'w') as f:
            # separators elimina espacios en blanco innecesarios en el JSON (minifica)
            json.dump(full_data, f, separators=(',', ':'))
            
        om.MGlobal.displayInfo(f"Export completado. Archivo optimizado.")

    def import_skins(self, file_path):
        om.MGlobal.displayInfo(f"--- Iniciando Import OPTIMIZADO desde: {file_path} ---")
        
        if not os.path.exists(file_path):
            om.MGlobal.displayError("El archivo JSON no existe.")
            return

        with open(file_path, 'r') as f:
            data = json.load(f)

        for mesh_name, skins_list in data.items():
            mesh_path = self._get_dag_path(mesh_name)
            if not mesh_path:
                om.MGlobal.displayWarning(f"Mesh skipped: {mesh_name}")
                continue
            
            mesh_path.extendToShape()
            mf_mesh = om.MFnMesh(mesh_path)
            processed_skins = []

            for skin_data in skins_list:
                skin_name = skin_data["name"]
                target_vtx_count = skin_data["vertex_count"]
                
                if mf_mesh.numVertices != target_vtx_count:
                    om.MGlobal.displayError(f"Topología no coincide en {skin_name}. Skip.")
                    continue 

                # Gestionar Creación/Busqueda de SkinCluster (Codigo anterior reutilizado)
                json_influences = skin_data["influences"]
                skin_exists = cmds.objExists(skin_name) and cmds.nodeType(skin_name) == "skinCluster"
                mf_skin = None
                
                if skin_exists:
                    sel_s = om.MSelectionList()
                    sel_s.add(skin_name)
                    mf_skin = oma.MFnSkinCluster(sel_s.getDependNode(0))
                    scene_infs = [p.partialPathName() for p in mf_skin.influenceObjects()]
                    missing_infs = [inf for inf in json_influences if inf not in scene_infs]
                    if missing_infs:
                        cmds.skinCluster(skin_name, e=True, addInfluence=missing_infs, weight=0.0)
                else:
                    valid_joints = [j for j in json_influences if cmds.objExists(j)]
                    if not valid_joints: continue
                    new_skin = cmds.skinCluster(valid_joints, mesh_path.fullPathName(), n=skin_name, toSelectedBones=True, multi=True)[0]
                    sel_s = om.MSelectionList()
                    sel_s.add(new_skin)
                    mf_skin = oma.MFnSkinCluster(sel_s.getDependNode(0))

                # Atributos
                for attr, val in skin_data["attributes"].items():
                    try:
                        cmds.setAttr(f"{skin_name}.{attr}", val)
                    except: pass

                # --- RECONSTRUCCION DE PESOS (De Sparse a Denso) ---
                
                # 1. Mapa de indices Escena vs JSON
                scene_inf_paths = mf_skin.influenceObjects()
                scene_inf_names = [p.partialPathName() for p in scene_inf_paths]
                scene_inf_map = {name: i for i, name in enumerate(scene_inf_names)}
                
                # Necesitamos construir un array plano GIGANTE lleno de ceros
                # Tamaño = NumVertices * NumInfluenciasEnEscena
                num_verts = target_vtx_count
                num_scene_infs = len(scene_inf_names)
                
                # Array inicializado en 0.0 (float)
                # Esta es la parte critica de memoria, pero es necesaria para setWeights
                full_weight_list = [0.0] * (num_verts * num_scene_infs)
                
                sparse_data = skin_data.get("sparse_weights", {})
                
                # Rellenamos solo donde hay datos
                for j_name, data_block in sparse_data.items():
                    if j_name not in scene_inf_map:
                        continue # La joint no existe en la escena, ignoramos sus pesos
                    
                    scene_inf_idx = scene_inf_map[j_name]
                    indices = data_block["ix"]
                    values = data_block["vw"]
                    
                    # Rellenar el array plano
                    # Formula: index_plano = vtx_idx * stride + inf_idx
                    for v_idx, weight_val in zip(indices, values):
                        flat_index = (v_idx * num_scene_infs) + scene_inf_idx
                        full_weight_list[flat_index] = weight_val
                
                # Aplicar a Maya
                m_influence_indices = om.MIntArray(list(range(num_scene_infs)))
                final_weights = om.MDoubleArray(full_weight_list)
                
                single_comp = om.MFnSingleIndexedComponent()
                vertex_comp = single_comp.create(om.MFn.kMeshVertComponent)
                single_comp.setCompleteData(num_verts)
                
                mf_skin.setWeights(mesh_path, vertex_comp, m_influence_indices, final_weights, False)

                # --- Blend Weights ---
                sparse_blend = skin_data.get("sparse_blend", {})
                if sparse_blend:
                    full_blend = [0.0] * num_verts
                    for v_idx, val in zip(sparse_blend["ix"], sparse_blend["vw"]):
                        full_blend[v_idx] = val
                    mf_skin.setBlendWeights(mesh_path, vertex_comp, om.MDoubleArray(full_blend))
                else:
                    # Si no hay data sparse pero es un formato antiguo o todo ceros
                    pass 

                processed_skins.append(skin_name)

            # Reordenar (mismo codigo)
            if processed_skins:
                current_hist = cmds.listHistory(mesh_path.fullPathName(), pruneDagObjects=True, interestLevel=1)
                current_skins = [x for x in current_hist if cmds.nodeType(x) == "skinCluster"]
                current_skins = list(reversed(current_skins))
                unknown = [s for s in current_skins if s not in processed_skins]
                order = unknown + processed_skins
                for skin in reversed(order):
                    try: cmds.reorderDeformers(skin, mesh_path.fullPathName(), back=True)
                    except: pass

        om.MGlobal.displayInfo("--- Importación Finalizada ---")


path = r"D:\git\maya\puiastre_tools\assets\varyndor\skinning\CHAR_varyndor_001.skn"
# SkinIO().export_skins(file_path = path)
SkinIO().import_skins(file_path = path)