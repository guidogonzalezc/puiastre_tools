import maya.cmds as cmds
import json
import open
import maya.api.OpenMaya as om
from puiastreTools.utils import guides_manager
from puiastreTools.utils import data_export
from importlib import reload
reload(guides_manager) 

class SkinClusterTool:

    def __init__(self):

        self.skin_cluster = None

    def export_skin_cluster(self, skin_cluster_name):

        """
        Exports the skin cluster to a file.
        :param skin_cluster_name: Name of the skin cluster to export.
        Select the GEO_GRP, get a joint list and export the skin cluster data to a JSON file.
        """
        
        geo_trn = cmds.ls(sl=True, type='transform')

        if not geo_trn:

            om.MGlobal.displayError("Please select a geometry transform node.")
            return
        
        skin_cluster_data = {
            'skin_cluster': skin_cluster_name,
            'influences': [],
            'weights': {}
        }

        
        for msh in cmds.listRelatives(geo_trn, shapes=True, fullPath=True):

            history = cmds.listHistory(msh, pruneDagObjects=True)
            skin_cluster = cmds.ls(history, type='skinCluster')
            joint_list = cmds.skinCluster(skin_cluster, influence=True)


            for jnt in joint_list:

                weight = cmds.skinPercent(jnt, )



            if not skin_cluster:

                continue





            

        

        dialog = cmds.fileDialog2(
            dialogStyle=2,
            fileMode=0,
            caption="Export Skin Cluster",
            okCaption="Export",
            fileFilter="JSON Files (*.json)"
        )


    def import_skin_cluster(self, file_path):

        """
        Imports a skin cluster from a file.
        :param file_path: Path to the file containing the skin cluster data.
        """



        dialog = cmds.fileDialog2(
            dialogStyle=2,
            fileMode=1,
            caption="Import Skin Cluster",
            okCaption="Import",
            fileFilter="JSON Files (*.json)"
        )

        if dialog:
            file_path = dialog[0]

            if not file_path.endswith('.json'):
                cmds.warning("Please select a valid JSON file.")
                return
            
            with open(file_path, 'r') as file:
                data = json.load(file)
                self.skin_cluster = data.get('skin_cluster', None)
                if self.skin_cluster:
                    print(f"Skin cluster '{self.skin_cluster}' imported successfully.")
                else:
                    print("No skin cluster data found in the file.")


