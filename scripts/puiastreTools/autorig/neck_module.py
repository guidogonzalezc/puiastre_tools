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
        self.guides_path = os.path.join(self.relative_path, "guides", "dragon_guides_template_01.guides")
        self.curves_path = os.path.join(self.relative_path, "curves", "neck_ctl.json")

    def make(self, side="C"):

        self.side = side

        self.module_trn = cmds.createNode("transform", n=f"{self.side}_neckModule_GRP")
        self.controllers_trn = cmds.createNode("transform", n=f"{self.side}_neckControllers_GRP")
        self.skinning_trn = cmds.createNode("transform", n=f"{self.side}_neckSkinningJoints_GRP")

        self.import_guides()
        self.controllers()
        self.ik_setup()

    def lock_attrs(self, ctl, attrs):
        
        for attr in attrs:
            cmds.setAttr(f"{ctl}.{attr}", lock=True, keyable=False, channelBox=False)

    def import_guides(self):

        self.neck_chain = guides_manager.guide_import(joint_name=f"{self.side}_neck00_JNT", all_descendents=True, filePath=self.guides_path)
        cmds.parent(self.neck_chain[0], self.module_trn)

    def controllers(self):

        self.neck_ctl, self.neck_grp = curve_tool.controller_creator("C_neck", ["GRP", "OFF"])
        cmds.matchTransform(self.neck_grp[0], self.neck_chain[0], pos=True, rot=True, scl=False)
        self.lock_attrs(self.neck_ctl, ["scaleX", "scaleY", "scaleZ", "visibility"])
       

        self.neck_ctl_mid, self.neck_grp_mid = curve_tool.controller_creator("C_neckMid", ["GRP", "OFF"])
        # point = cmds.parentConstraint(self.neck_chain[0], self.neck_chain[-1], self.neck_grp_mid[0], mo=False)
        # cmds.delete(point)
        cmds.matchTransform(self.neck_grp_mid[0], self.neck_chain[5], pos=True, rot=True, scl=False)
        self.lock_attrs(self.neck_ctl_mid, ["scaleX", "scaleY", "scaleZ", "visibility"])
       

        self.head_ctl, self.head_grp = curve_tool.controller_creator("C_head", ["GRP", "OFF"])
        cmds.matchTransform(self.head_grp[0], self.neck_chain[-1], pos=True, rot=True, scl=False)
        self.lock_attrs(self.head_ctl, ["scaleX", "scaleY", "scaleZ", "visibility"])
        cmds.parent(self.neck_grp[0], self.neck_grp_mid[0], self.head_grp[0], self.controllers_trn)

    def ik_setup(self):

        self.ik_spring_hdl = cmds.ikHandle(sj=self.neck_chain[0], ee=self.neck_chain[-1], sol="ikSplineSolver", n=f"{self.side}_neckIkSpline_HDL", createCurve=True)
        cmds.parent(self.ik_spring_hdl[0], self.module_trn)
        self.ik_curve = self.ik_spring_hdl[2]
        self.ik_curve = cmds.rename(self.ik_curve, f"{self.side}_neckIkCurve_CRV")

        self.neck_offset = cmds.createNode("transform", n=f"{self.side}_neckOffset_GRP", p=self.neck_ctl)
        self.neck_trn = cmds.createNode("transform", n=f"{self.side}_neck_TRN", p=self.neck_offset)
        cmds.matchTransform(self.neck_trn, self.neck_chain[0], pos=True, rot=True, scl=False)
        cmds.move(0, 130, 0, self.neck_offset, r=True)

        self.head_offset = cmds.createNode("transform", n=f"{self.side}_headOffset_GRP", p=self.head_ctl)
        self.head_trn = cmds.createNode("transform", n=f"{self.side}_head_TRN", p=self.head_offset)
        cmds.matchTransform(self.head_trn, self.neck_chain[-1], pos=True, rot=True, scl=False)
        cmds.move( 0, 100, 0, self.head_offset, r=True)

        self.neck_start_jnt_offset = cmds.createNode("transform", n=f"{self.side}_neckStart_OFFSET", p=self.module_trn)
        self.neck_start_jnt = cmds.createNode("joint", n=f"{self.side}_neckStart_JNT", p=self.neck_start_jnt_offset)
        cmds.matchTransform(self.neck_start_jnt_offset, self.neck_chain[0], pos=True, rot=True, scl=False)

        self.neck_mid_jnt_offset = cmds.createNode("transform", n=f"{self.side}_neckMid_OFFSET", p=self.module_trn)
        self.neck_mid_jnt = cmds.createNode("joint", n=f"{self.side}_neckMid_JNT", p=self.neck_mid_jnt_offset)
        cmds.matchTransform(self.neck_mid_jnt_offset, self.neck_chain[5], pos=True, rot=True, scl=False)

        self.head_jnt_offset = cmds.createNode("transform", n=f"{self.side}_head_OFFSET", p=self.module_trn)
        self.head_jnt = cmds.createNode("joint", n=f"{self.side}_head_JNT", p=self.head_jnt_offset)
        cmds.matchTransform(self.head_jnt_offset, self.neck_chain[-1], pos=True, rot=True, scl=False)

            

    