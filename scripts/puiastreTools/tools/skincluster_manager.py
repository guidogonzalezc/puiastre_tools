"""
skincluster_json_fast_dq.py

Fast JSON-based skinCluster export/import using Maya API 2.0.
Supports:
 - Classic Linear skinning
 - Dual Quaternion skinning
 - Blended DQ per-vertex map (blendWeights)
 - Per-vertex weight export via MFnSkinCluster.getWeights()
 - Bulk import via MFnSkinCluster.setWeights()

DQ MAP (Correct):
 - In Maya, Dual Quaternion influence is per-vertex, stored in:
       skinCluster.blendWeights[vtx_index]
 - NOT per influence!
 - Always exported, regardless of skinningMethod.

JSON FORMAT:

{
  "skinClusterName": {
    "mesh_name": "pSphereShape1",
    "joint_list": [...],
    "skinningMethod": 2,
    "dq_vertex_map": [0.0, 0.34, 1.0, ...],   <-- OPTION B
    "skin_percentage": {
       "pSphereShape1.vtx[0]": {"joint1": 0.2, "joint2": 0.8},
       ...
    },
    "attrs": {
       "normalizeWeights": 1,
       "maxInfluences": 4,
       "dropoff": 4.0
    }
  }
}
"""

import os
import json
import traceback
import maya.cmds as cmds
import maya.api.OpenMaya as om
import maya.api.OpenMayaAnim as oma

DEFAULT_EXPORT_PATH = r"/mnt/data/skincluster_export.skn.json"


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


# ---------------------------------------------------------
# EXPORT
# ---------------------------------------------------------

def export_skinclusters_json(path=None, selection_only=False, verbose=True):
    """
    Export all or selected skinClusters to JSON.
    Includes:
      - classic weights
      - skinningMethod
      - blendWeights[] (the TRUE dual quaternion map)
    """
    if path is None:
        path = DEFAULT_EXPORT_PATH
    path = os.path.abspath(path)
    _ensure_dir(path)

    # find skinClusters
    if selection_only:
        scs = []
        sel = cmds.ls(sl=True, long=True) or []
        for s in sel:
            hist = cmds.listHistory(s, f=False) or []
            scs += [h for h in hist if cmds.nodeType(h) == "skinCluster"]
        scs = list(set(scs))
    else:
        scs = cmds.ls(type="skinCluster") or []

    data = {}

    for sc in scs:
        try:
            geo_list = cmds.skinCluster(sc, q=True, geometry=True) or []
            if not geo_list:
                continue
            geo = geo_list[0]

            sc_mobj = _get_mobject(sc)
            sc_fn = oma.MFnSkinCluster(sc_mobj)

            inf_paths = sc_fn.influenceObjects()
            inf_names = [om.MFnDagNode(p).fullPathName() for p in inf_paths]

            geo_dp = _get_dagpath(geo)
            it_geo = om.MItGeometry(geo_dp)

            # -----------------------------------------
            # EXPORT CLASSIC WEIGHTS
            # -----------------------------------------
            weights_data = {}
            while not it_geo.isDone():
                comp = it_geo.currentItem()
                idx = it_geo.index()
                vals, inf_count = sc_fn.getWeights(geo_dp, comp)

                row = {}
                for i, w in enumerate(vals):
                    if abs(w) > 0.0:
                        row[inf_names[i]] = float(w)

                if row:
                    weights_data[f"{geo}.vtx[{idx}]"] = row

                it_geo.next()

            # -----------------------------------------
            # EXPORT DQ MAP (blendWeights), OPTION B
            # -----------------------------------------
            dq_array = []
            vtx_count = cmds.polyEvaluate(geo, vertex=True)
            for i in range(vtx_count):
                try:
                    dq_val = cmds.getAttr(f"{sc}.blendWeights[{i}]")
                    dq_array.append(float(dq_val))
                except Exception:
                    dq_array.append(0.0)

            # -----------------------------------------
            # SKINCLUSTER ATTRIBUTES
            # -----------------------------------------
            attrs = {}
            nw = _safe_getattr(sc, "normalizeWeights")
            if nw is None:
                nw = _safe_getattr(sc, "nw")
            if nw is not None:
                attrs["normalizeWeights"] = nw

            mi = _safe_getattr(sc, "maxInfluences")
            if mi is not None:
                attrs["maxInfluences"] = mi

            dr = _safe_getattr(sc, "dropoff")
            if dr is not None:
                if isinstance(dr, (list, tuple)):
                    dr = dr[0][0]
                attrs["dropoff"] = float(dr)

            skin_method = _safe_getattr(sc, "skinningMethod")
            if skin_method is not None:
                skin_method = int(skin_method)

            # -----------------------------------------
            # BUILD JSON BLOCK
            # -----------------------------------------
            data[sc] = {
                "mesh_name": geo,
                "joint_list": inf_names,
                "skinningMethod": skin_method,
                "dq_vertex_map": dq_array,       # OPTION B
                "skin_percentage": weights_data,
                "attrs": attrs
            }

            if verbose:
                print(f"[export] {sc} -> joints={len(inf_names)} verts={len(weights_data)} dqCount={len(dq_array)}")

        except Exception:
            traceback.print_exc()

    # write file
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

    if verbose:
        print(f"[export] Wrote {len(data)} skinClusters to {path}")

    return path


# ---------------------------------------------------------
# IMPORT
# ---------------------------------------------------------

def import_skinclusters_json(path=None, verbose=True, allow_missing_joints=True):
    """
    Import JSON skinClusters created by export_skinclusters_json().
    Sets:
       - mesh binding
       - classic weights (fast API)
       - skinningMethod
       - blendWeights (dq_vertex_map array)
    """
    if path is None:
        path = DEFAULT_EXPORT_PATH
    path = os.path.abspath(path)
    if not os.path.exists(path):
        raise IOError(f"File does not exist: {path}")

    with open(path, "r") as f:
        data = json.load(f)

    built = []

    for sc_name, block in data.items():
        try:
            geo = block["mesh_name"]
            if not cmds.objExists(geo):
                print(f"[import] Geo not found: {geo} (skip {sc_name})")
                continue

            joints = block["joint_list"]
            skin_method = block.get("skinningMethod")
            dq_array = block.get("dq_vertex_map", [])
            weights_data = block.get("skin_percentage", {})
            attrs = block.get("attrs", {})

            # ---------------------------------------------------------
            # ENSURE JOINTS EXIST
            # ---------------------------------------------------------
            missing = [j for j in joints if not cmds.objExists(j)]
            if missing:
                if allow_missing_joints:
                    for m in missing:
                        cmds.select(clear=True)
                        cmds.joint(name=m, position=(0, 0, 0))
                    if verbose:
                        print(f"[import] Created dummy joints: {missing}")
                else:
                    print(f"[import] Missing joints {missing} (skip {sc_name})")
                    continue

            # ---------------------------------------------------------
            # CREATE / REUSE SKINCLUSTER
            # ---------------------------------------------------------
            existing = None
            hist = cmds.listHistory(geo, f=False) or []
            for h in hist:
                if cmds.nodeType(h) == "skinCluster":
                    existing = h
                    break

            if existing:
                sc = existing
                if verbose:
                    print(f"[import] Using existing skinCluster {sc}")
            else:
                sc = cmds.skinCluster(joints, geo, tsb=True, name=sc_name)[0]
                if verbose:
                    print(f"[import] Created skinCluster {sc}")

            # ---------------------------------------------------------
            # APPLY SKINNING METHOD
            # ---------------------------------------------------------
            if skin_method is not None:
                try:
                    cmds.setAttr(f"{sc}.skinningMethod", int(skin_method))
                except Exception:
                    pass

            # ---------------------------------------------------------
            # DISABLE NORMALIZATION FOR PRECISE WEIGHT APPLICATION
            # ---------------------------------------------------------
            norm_save = _safe_getattr(sc, "normalizeWeights")
            if norm_save is None:
                norm_save = _safe_getattr(sc, "nw")

            try:
                cmds.setAttr(f"{sc}.normalizeWeights", 0)
            except Exception:
                try:
                    cmds.setAttr(f"{sc}.nw", 0)
                except Exception:
                    pass

            # ---------------------------------------------------------
            # API FAST CLASSIC WEIGHT IMPORT
            # ---------------------------------------------------------
            sc_mobj = _get_mobject(sc)
            sc_fn = oma.MFnSkinCluster(sc_mobj)
            geo_dp = _get_dagpath(geo)

            inf_paths = sc_fn.influenceObjects()
            inf_names = [om.MFnDagNode(p).fullPathName() for p in inf_paths]
            inf_index_map = {nm: i for i, nm in enumerate(inf_names)}
            influence_count = len(inf_names)

            comp_mfn = om.MFnSingleIndexedComponent()
            comp_obj = comp_mfn.create(om.MFn.kMeshVertComponent)
            comp_fn = om.MFnSingleIndexedComponent(comp_obj)

            weight_array = om.MDoubleArray()

            it_geo = om.MItGeometry(geo_dp)
            while not it_geo.isDone():
                idx = it_geo.index()
                comp_fn.addElement(idx)

                row = [0.0] * influence_count
                vtx_name = f"{geo}.vtx[{idx}]"

                if vtx_name in weights_data:
                    for j, wv in weights_data[vtx_name].items():
                        i = inf_index_map.get(j)
                        if i is not None:
                            row[i] = float(wv)

                for wv in row:
                    weight_array.append(wv)

                it_geo.next()

            sc_fn.setWeights(geo_dp, comp_obj, weight_array, normalize=False)

            # ---------------------------------------------------------
            # RESTORE BLENDWEIGHTS (DQ MAP) OPTION B
            # ---------------------------------------------------------
            if dq_array:
                for idx, dq_val in enumerate(dq_array):
                    try:
                        cmds.setAttr(f"{sc}.blendWeights[{idx}]", float(dq_val))
                    except Exception:
                        pass

            # ---------------------------------------------------------
            # RESTORE ATTRIBUTES
            # ---------------------------------------------------------
            if norm_save is not None:
                try:
                    cmds.setAttr(f"{sc}.normalizeWeights", int(norm_save))
                except Exception:
                    try:
                        cmds.setAttr(f"{sc}.nw", int(norm_save))
                    except Exception:
                        pass

            if "maxInfluences" in attrs:
                try:
                    cmds.setAttr(f"{sc}.maxInfluences", int(attrs["maxInfluences"]))
                except Exception:
                    pass

            if "dropoff" in attrs:
                try:
                    cmds.setAttr(f"{sc}.dropoff", float(attrs["dropoff"]))
                except Exception:
                    pass

            if verbose:
                print(f"[import] Imported weights + dq_map for {sc}")

            built.append(sc)

        except Exception:
            traceback.print_exc()

    if verbose:
        print(f"[import] Done. {len(built)} skinClusters processed.")

    return built


# ---------------------------------------------------------
# UI WRAPPERS
# ---------------------------------------------------------

def export_ui():
    path = cmds.fileDialog2(fileFilter="*.json", fileMode=0, caption="Export SkinClusters to JSON")
    if path:
        export_skinclusters_json(path[0], selection_only=False, verbose=True)

def import_ui():
    path = cmds.fileDialog2(fileFilter="*.json", fileMode=1, caption="Import SkinClusters JSON")
    if path:
        import_skinclusters_json(path[0], verbose=True)


import_ui()