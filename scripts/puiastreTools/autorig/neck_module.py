import maya.cmds as cmds
import os
import puiastreTools.tools.curve_tool as curve_tool
from puiastreTools.utils import guides_manager
from importlib import reload

reload(curve_tool)
reload(guides_manager)

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

        self.import_guides()
        self.controllers()
        self.ik_setup()

    def lock_attrs(self, ctl, attrs):
        
        for attr in attrs:
            cmds.setAttr(f"{ctl}.{attr}", lock=True, keyable=False, channelBox=False)

    def import_guides(self):

        self.neck_chain = guides_manager.guide_import(joint_name=f"{self.side}_neck00_JNT", all_descendents=True, filePath=self.guides_path)
    
    def controllers(self):

        self.neck_ctl, self.neck_grp = curve_tool.controller_creator("C_neck", ["GRP", "OFF"])
        cmds.matchTransform(self.neck_grp[0], self.neck_chain[0], pos=True, rot=True, scl=False)
        self.lock_attrs(self.neck_ctl, ["scaleX", "scaleY", "scaleZ", "visibility"])

        self.neck_ctl_mid, self.neck_grp_mid = curve_tool.controller_creator("C_neckMid", ["GRP", "OFF"])
        cmds.matchTransform(self.neck_grp_mid[0], len(self.neck_chain)/2, pos=True, rot=True, scl=False)
        self.lock_attrs(self.neck_ctl_mid, ["scaleX", "scaleY", "scaleZ", "visibility"])

        self.head_ctl, self.head_grp = curve_tool.controller_creator("C_head", ["GRP", "OFF"])
        cmds.matchTransform(self.head_grp[0], self.neck_chain[-1], pos=True, rot=True, scl=False)
        self.lock_attrs(self.head_ctl, ["scaleX", "scaleY", "scaleZ", "visibility"])

    def ik_setup(self):

        self.ik_spring_hdl = cmds.ikHandle(sj=self.neck_chain[0], ee=self.neck_chain[-1], sol="ikSpringSolver", n=f"{self.side}_neckIKSpring_HDL", createCurve=True)
        print(self.ik_spring_hdl)
        self.ik_curve = self.ik_spring_hdl[0]
        self.ik_curve = cmds.rename(self.ik_curve, f"{self.side}_neckIKCurve_CRV")

    