import maya.cmds as cmds
from puiastreTools.utils import core
import json

def export_skincluster():

    file_path = core.DataManager.get_skinning_data()

    skinclusters = cmds.ls(type="skinCluster")

    for skincluster in skinclusters:
        # Get the geometry associated with the skinCluster
        geometries = cmds.skinCluster(skincluster, query=True, geometry=True)
        if not geometries:
            continue

        geometry = geometries[0]

        # Get the influence joints
        influences = cmds.skinCluster(skincluster, query=True, influence=True)

        # Get the weights for each vertex
        vertex_count = cmds.polyEvaluate(geometry, vertex=True)
        weights_data = {}

        for i in range(vertex_count):
            vertex_name = f"{geometry}.vtx[{i}]"
            weights = cmds.skinPercent(skincluster, vertex_name, query=True, value=True)
            weights_data[vertex_name] = dict(zip(influences, weights))

        # Export the weights data to a file in the desired format
        if file_path:
            export_data = {skincluster:{
            "mesh_name": geometry,
            "joint_list": influences,
            "skin_percentage": weights_data
            }}
            with open(file_path, 'w') as f:
                json.dump(export_data, f, indent=4)
            print(f"Exported weights data to: {file_path}")
        else:
            print("No valid path provided for exporting skinning data.")

def import_skincluster():

    file_path = core.DataManager.get_skinning_data()

    if not file_path:
        print("No valid path provided for importing skinning data.")
        return

    with open(file_path, 'r') as f:
        import_data = json.load(f)

    geometry = import_data["mesh_name"]
    influences = import_data["joint_list"]
    weights_data = import_data["skin_percentage"]

    # Create a new skinCluster
    skincluster = cmds.skinCluster(influences, geometry, name = "test",toSelectedBones=True)[0]
    print(f"Created skinCluster: {skincluster} on geometry: {geometry}")

    # Apply the weights to each vertex
    for vertex_name, weights in weights_data.items():
        for joint, weight in weights.items():
            cmds.skinPercent(skincluster, vertex_name, transformValue=[joint, weight])
            print(f"Set weight for vertex {vertex_name}, joint {joint}: {weight}")
    print(f"Imported weights data from: {file_path}")

core.DataManager.set_skinning_data(r"P:\VFX_Project_20\DCC_CUSTOM\MAYA\modules\puiastre_tools\assets\maiasaura\skinning\CHAR_Maiasaura_001.skn")

export_skincluster()

cmds.delete("C_body_GEO", ch=True)

import_skincluster()