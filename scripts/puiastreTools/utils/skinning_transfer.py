import maya.cmds as cmds
import os
from maya.OpenMaya import MGlobal as om

from ngSkinTools2 import api as ngst_api

def load_skincluster():
    # cmds.parent("Aycedrhal_GEO", "MODEL")
    cmds.parent("Maiasaurio_GEO", "MODEL")
    cmds.setAttr("C_preferences_CTL.meshLods", 2)
    cmds.setAttr("C_preferences_CTL.showSkeleton", 0)

    # for item in cmds.listRelatives("Aycedrhal_GEO", allDescendents=True, type="transform"):
    #     if not "C_body_GEO" in item:
    #         cmds.setAttr(f"{item}.visibility", 0)

    for item in cmds.listRelatives("Maiasaurio_GEO", allDescendents=True, type="transform"):
        if not "C_body_GEO" in item:
            cmds.setAttr(f"{item}.visibility", 0)

    cmds.setAttr("perspShape.nearClipPlane", 1)

    # skinning_path = r"P:\VFX_Project_20\DCC_CUSTOM\MAYA\modules\puiastre_tools\exported_skinnings\aychedral\aychedral_skinning_011.json"
    skinning_path = r"P:\VFX_Project_20\DCC_CUSTOM\MAYA\modules\puiastre_tools\exported_skinnings\aychedral\maiasaurio_skinning_001.json"

    joints = cmds.listRelatives("skeletonHierarchy_GRP", allDescendents=True, type="joint")

    # skinCluster = cmds.skinCluster(joints, "C_body_GEO", toSelectedBones=True, maximumInfluences=1, normalizeWeights=1, name="Aycedrhal_SkinCluster")[0]
    skinCluster = cmds.skinCluster(joints, "C_body_GEO", toSelectedBones=True, maximumInfluences=1, normalizeWeights=1, name="Maiasaurio_SkinCluster")[0]
    cmds.setAttr(f"{skinCluster}.skinningMethod", 1)  # Set skinning method to Dual Quaternion


    config = ngst_api.InfluenceMappingConfig()
    config.use_distance_matching = True
    config.use_name_matching = False

    # run the import
    ngst_api.import_json(
        skinCluster,
        file=skinning_path,
        vertex_transfer_mode=ngst_api.VertexTransferMode.vertexId,
        influences_mapping_config=config,
    )

    om.displayWarning("Importing skinning from {}".format(skinning_path))



"""
cmds.select("C_body_GEO")
from maya.OpenMaya import MGlobal as om

om.displayWarning("Importing skinning from P:\VFX_Project_20\DCC_CUSTOM\MAYA\modules\puiastre_tools\exported_skinnings\aychedral\aychedral_skinning_011.json")


"""