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
        cmds.addAttr(self.neck_ctl_mid, ln="EXTRA_ATTRIBUTES___", at="enum", en="___")
        cmds.setAttr(f"{self.neck_ctl_mid}.EXTRA_ATTRIBUTES___", lock=True, keyable=False, channelBox=True)
        cmds.addAttr(self.neck_ctl_mid, ln="Follow_Neck", at="bool", dv=0, min=0, max=1, keyable=False)
        cmds.setAttr(f"{self.neck_ctl_mid}.Follow_Neck", keyable=True, channelBox=False)
        cmds.matchTransform(self.neck_grp_mid[0], self.neck_chain[5], pos=True, rot=True, scl=False)
        self.lock_attrs(self.neck_ctl_mid, ["scaleX", "scaleY", "scaleZ", "visibility"])
       

        self.head_ctl, self.head_grp = curve_tool.controller_creator("C_head", ["GRP", "OFF"])
        cmds.matchTransform(self.head_grp[0], self.neck_chain[-1], pos=True, rot=True, scl=False)
        cmds.addAttr(self.head_ctl, ln="EXTRA_ATTRIBUTES___", at="enum", en="___")
        cmds.setAttr(f"{self.head_ctl}.EXTRA_ATTRIBUTES___", lock=True, keyable=False, channelBox=True)
        cmds.addAttr(self.head_ctl, ln="Follow_Neck", at="bool", dv=0, min=0, max=1, keyable=False)
        cmds.setAttr(f"{self.head_ctl}.Follow_Neck", keyable=True, channelBox=False)
        self.lock_attrs(self.head_ctl, ["scaleX", "scaleY", "scaleZ", "visibility"])
        cmds.parent(self.neck_grp[0], self.neck_grp_mid[0], self.head_grp[0], self.controllers_trn)

    def ik_setup(self):

        self.ik_spring_hdl = cmds.ikHandle(sj=self.neck_chain[0], ee=self.neck_chain[-1], sol="ikSplineSolver", n=f"{self.side}_neckIkSpline_HDL", createCurve=True,  ns=3)
        cmds.parent(self.ik_spring_hdl[0], self.module_trn)
        self.ik_curve = self.ik_spring_hdl[2]
        self.ik_curve = cmds.rename(self.ik_curve, f"{self.side}_neckIkCurve_CRV")

        # self.neck_offset = cmds.createNode("transform", n=f"{self.side}_neckOffset_GRP", p=self.neck_ctl)
        # self.neck_trn = cmds.spaceLocator(n=f"{self.side}_neck_LOC")[0]
        # cmds.parent(self.neck_trn, self.neck_offset)
        # cmds.matchTransform(self.neck_trn, self.neck_chain[0], pos=True, rot=True, scl=False)
        # cmds.move(0, 130, 0, self.neck_offset, r=True)

        # self.head_offset = cmds.createNode("transform", n=f"{self.side}_headNeckEndOffset_GRP", p=self.head_ctl)
        # self.head_trn = cmds.spaceLocator(n=f"{self.side}_head_LOC")[0]
        # cmds.parent(self.head_trn, self.head_offset)
        # cmds.matchTransform(self.head_trn, self.neck_chain[-1], pos=True, rot=True, scl=False)
        # cmds.move(0, 100, 0, self.head_offset, r=True)

        self.neck_start_jnt_offset = cmds.createNode("transform", n=f"{self.side}_neckStart_OFFSET", p=self.module_trn)
        self.neck_start_jnt = cmds.createNode("joint", n=f"{self.side}_neckStart_JNT", p=self.neck_start_jnt_offset)
        cmds.matchTransform(self.neck_start_jnt_offset, self.neck_chain[0], pos=True, rot=True, scl=False)
        cmds.parentConstraint(self.neck_ctl, self.neck_start_jnt_offset, mo=True)

        self.neck_mid_jnt_offset = cmds.createNode("transform", n=f"{self.side}_neckMid_OFFSET", p=self.module_trn)
        self.neck_mid_jnt = cmds.createNode("joint", n=f"{self.side}_neckMid_JNT", p=self.neck_mid_jnt_offset)
        cmds.matchTransform(self.neck_mid_jnt_offset, self.neck_chain[5], pos=True, rot=True, scl=False)
        cmds.parentConstraint(self.neck_ctl_mid, self.neck_mid_jnt_offset, mo=True)

        self.head_neck_end_jnt_offset = cmds.createNode("transform", n=f"{self.side}_headNeckEnd_OFFSET", p=self.module_trn)
        self.head_neck_end_jnt = cmds.createNode("joint", n=f"{self.side}_headNeckEnd_JNT", p=self.head_neck_end_jnt_offset)
        cmds.matchTransform(self.head_neck_end_jnt_offset, self.neck_chain[-1], pos=True, rot=True, scl=False)
        
        # Skin the curve to the joints
        self.curve_skin_cluster = cmds.skinCluster(self.neck_start_jnt, self.neck_mid_jnt, self.head_neck_end_jnt, self.ik_curve, tsb=True, n=f"{self.side}_neckSkinCluster_SKIN", mi=5)

        # Set the spline with the correct settings
        cmds.setAttr(f"{self.ik_spring_hdl[0]}.dTwistControlEnable", 1)
        cmds.setAttr(f"{self.ik_spring_hdl[0]}.dWorldUpType", 4)
        cmds.setAttr(f"{self.ik_spring_hdl[0]}.dForwardAxis", 4)
        cmds.connectAttr(f"{self.neck_ctl}.worldMatrix[0]", f"{self.ik_spring_hdl[0]}.dWorldUpMatrix")
        cmds.connectAttr(f"{self.head_ctl}.worldMatrix[0]", f"{self.ik_spring_hdl[0]}.dWorldUpMatrixEnd")

        self.head_jnt_offset = cmds.createNode("transform", n=f"{self.side}_head_OFFSET", p=self.module_trn)
        self.head_jnt = cmds.createNode("joint", n=f"{self.side}_head_JNT", p=self.head_jnt_offset)
        cmds.matchTransform(self.head_jnt_offset, self.neck_chain[-1], pos=True, rot=True, scl=False)

        cmds.parentConstraint(self.head_ctl, self.head_neck_end_jnt, mo=True)
        cmds.pointConstraint(self.neck_chain[-1], self.head_jnt, mo=True)
        cmds.orientConstraint(self.head_ctl, self.head_jnt, mo=True)

        parent = cmds.parentConstraint(self.neck_ctl, self.neck_grp_mid[0], mo=True)[0]
        cmds.connectAttr(f"{self.neck_ctl_mid}.Follow_Neck", f"{parent}.w0")

        parent_02 = cmds.parentConstraint(self.neck_ctl, self.head_grp[1], mo=True)[0]
        cmds.connectAttr(f"{self.head_ctl}.Follow_Neck", f"{parent_02}.w0")


        self.jaw_jnts = guides_manager.guide_import(joint_name=f"{self.side}_jaw_JNT", all_descendents=True, filePath=self.guides_path)
        cmds.parent(self.jaw_jnts[0], self.head_jnt)
        self.upper_jaw_jnts = guides_manager.guide_import(joint_name=f"{self.side}_upperJaw_JNT", all_descendents=True, filePath=self.guides_path)
        cmds.parent(self.upper_jaw_jnts[0], self.head_jnt)

    def spike(self):

        self.upper_spike_joints = guides_manager.guide_import(joint_name=f"{self.side}_upperSpike_JNT", all_descendents=True, filePath=self.guides_path)

        self.upper_spike_ends_joints = []
        self.upper_spike_ends_joints_pos = []

        for i, end in enumerate(self.upper_spike_joints):

            side = end.split("_")[0]
            end = cmds.rename(end, f"{side}_upperSpike0{i}_JNT")

            child_jnt = cmds.listRelatives(end, c=True)[0]
            child_jnt_pos = cmds.xform(child_jnt, q=True, ws=True, t=True)
            cmds.ikHandle(sj=end, ee=child_jnt, sol="ikSCsolver", n=f"{side}_upperSpike0{i}IkSpline_HDL", createCurve=True, ns=3)
            self.upper_spike_ends_joints.append(child_jnt)
            self.upper_spike_ends_joints_pos.append(child_jnt_pos)
            
        self.upper_spike_curve = cmds.curve(d=3, p=self.upper_spike_ends_joints_pos, n=f"{self.side}_upperSpikeCurve_CRV")


        
            
        

        


