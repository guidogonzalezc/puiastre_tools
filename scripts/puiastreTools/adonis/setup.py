from adn.api.adnx import Adonis
from adn.api.adnx import AdonisTools
from adn.scripts.maya import mirror
import maya.cmds as cmds
from importlib import reload

from puiastreTools.utils import data_export

reload(data_export)

class AdonisSetup():

    """
    Create a simple Adonis setup for muscles in Maya.
    """

    def __init__(self):

        """
        Initialize the Adonis setup.
        """
        
        self.adonis_grp = data_export.DataExport().get_data("basic_structure", "adonis_GRP")

        nodes_to_create = ["joints", "mummy", "animSkin", "locators", "muscles", "glue", "fascia", "fat", "simSkin", "renderSkin"]

        for node in nodes_to_create:

            cmds.createNode("transform", name=f"{node}_GRP", parent=self.adonis_grp)

    def create_joints(self, skeleton_joints):

        """
        Create the push joints for the introduced joint.
        """

        pass

    def mirror_setup(self):

        """
        Mirror the Adonis setup. It mirrors: deformers, locators, sensors and activation nodes.
        Must have:
            - Complete setup on one side either left or right.
            - Consistent naming convention (e.g., "_L" for left side joints).
            - Symmetric muscle topology.
        Functionality:
            - Select all the muscles and locators on the side you want to mirror.
        """
        
        report_data = {"errors": [], "warnings": []}
        result = mirror.apply_mirror(left_convention="L_*", right_convention="R_*", report_data=report_data)