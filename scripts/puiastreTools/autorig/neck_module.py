import maya.cmds as cmds
import os
from puiastreTools.tools.curve_tool import controller_creator
from puiastreTools.utils import data_export
from importlib import reload
reload(data_export)
reload(controller_creator)

class NeckModule:

    def __init__(self):

        complete_path = os.path.realpath(__file__)
        self.relative_path = complete_path.split("\scripts")[0]
        self.guides_path = os.path.join(self.relative_path, "guides", "neck_guides_v001.guides")
        self.curves_path = os.path.join(self.relative_path, "curves", "neck_ctl.json")

    def make(self, side):

        self.side = side

        self.module_trn = cmds.createNode("transform", n=f"{self.side}_neckModule_GRP")
        self.controllers_trn = cmds.createNode("transform", n=f"{self.side}_neckControllers_GRP")
        self.skinning_trn = cmds.createNode("transform", n=f"{self.side}_neckSkinningJoints_GRP", p=self.module_trn)

    def lock_attrs(self, ctl, attrs):
        
        for attr in attrs:
            cmds.setAttr(f"{ctl}.{attr}", lock=True, keyable=False, channelBox=False)

    def create_guides(self):

        pass
    
    
    def controllers(self):

        self.neck_ctl, self.neck_grp = self.controller_creator("C_neck", ["GRP", "OFF"])
        cmds.matchTransform(self.neck_grp[0], )
        self.neck_ctl_mid, self.neck_grp_mid = self.controller_creator("C_neckMid", ["GRP", "OFF"])
        self.head_ctl, self.head_grp = self.controller_creator("C_head", ["GRP", "OFF"])
    