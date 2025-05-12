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
        self.spike()

    def lock_attrs(self, ctl, attrs):
        
        for attr in attrs:
            cmds.setAttr(f"{ctl}.{attr}", lock=True, keyable=False, channelBox=False)

    def import_guides(self):

        self.neck_chain = guides_manager.guide_import(joint_name=f"{self.side}_neck00_JNT", all_descendents=True, filePath=self.guides_path)
        cmds.parent(self.neck_chain[0], self.module_trn)

    def spike(self):

        for side in ["L", "R"]:
            self.spike_call(side, f"{side}_upperSpike_JNT")
            self.spike_call(side, f"{side}_lateralSpike_JNT")


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

    def spike_call(self, side, spike_joint):
        
        name = spike_joint.split("_")[1]
        self.spike_joints = guides_manager.guide_import(joint_name=spike_joint, all_descendents=True, filePath=self.guides_path)
        match_jnt = self.spike_joints[0]
        self.spike_joints.remove(self.spike_joints[0])

        self.spike_transform = cmds.createNode("transform", n=f"{side}_{name}Module_GRP", p=self.module_trn)
        cmds.parent(match_jnt, self.spike_transform)

        # Get the positions of the end joints
        end_jnts = []
        end_jnts_pos = []

        for i, jnts in enumerate(self.spike_joints):
            if i <= 17:
                jnt = cmds.listRelatives(jnts, c=True)
                end_jnts_pos.append(cmds.xform(jnt, q=True, ws=True, t=True))
                end_jnts.append(jnt)
                self.spike_joints.remove(jnt[0])
                cmds.setAttr(f"{jnt[0]}.radius", 5)

        # Create a curve from the end joint positions
        curve = cmds.curve(d=1, p=end_jnts_pos, n=f"{side}_{name}_CRV")
        cmds.parent(curve, self.spike_transform)

        # Create a locator for each point on the curve
        locator_transform = cmds.createNode("transform", n=f"{side}_{name}Locators_GRP", p=self.spike_transform)
        locators = []
        for i in range(len(end_jnts)):
            loc = cmds.spaceLocator(n=f"{side}_{name}0{i}_LOC")[0]
            cmds.connectAttr(f"{curve}.editPoints[{i}]", f"{loc}.translate")
            cmds.parent(loc, locator_transform)
            locators.append(loc)

        # Create a single chain solver for each joint
        hdls_transform = cmds.createNode("transform", n=f"{side}_{name}Handles_GRP", p=self.spike_transform)
        for i, jnt in enumerate(self.spike_joints):
            ik_hdl = cmds.ikHandle(sj=jnt, ee=end_jnts[i][0], sol="ikSCsolver", n=f"{side}_{name}0{i}Ik_HDL")
            cmds.parent(ik_hdl[0], hdls_transform)
            cmds.pointConstraint(locators[i], ik_hdl[0], mo=True)
            cmds.setAttr(f"{jnt}.radius", 5)

        # Add a Sine handle to the curve
        sine_hdl = cmds.nonLinear(curve, type="sine", n=f"{side}_{name}Sine_")

        # Create a controller for the curve and the sine handle
        ctl, grp = curve_tool.controller_creator(f"{side}_{name}", ["GRP"])
        cmds.matchTransform(grp, match_jnt, pos=True, rot=True, scl=False)
        self.lock_attrs(ctl, ["translateX", "translateY", "translateZ", "rotateX", "rotateY", "rotateZ", "scaleX", "scaleY", "scaleZ", "visibility"])
        cmds.addAttr(ctl, ln="Amplitude", at="float", dv=0, keyable=True)
        cmds.addAttr(ctl, ln="Wave", at="float", dv=0, keyable=True)
        cmds.addAttr(ctl, ln="Offset", at="float", dv=0, keyable=True)
        cmds.addAttr(ctl, ln="Dropoff", at="float", dv=0, keyable=True)
        cmds.connectAttr(f"{ctl}.Amplitude", f"{sine_hdl[0]}.amplitude")
        cmds.connectAttr(f"{ctl}.Wave", f"{sine_hdl[0]}.wavelength")
        cmds.connectAttr(f"{ctl}.Offset", f"{sine_hdl[0]}.offset")
        cmds.connectAttr(f"{ctl}.Dropoff", f"{sine_hdl[0]}.dropoff")
        cmds.parent(grp, self.controllers_trn)

            

        

            



       
               
        


        
            
        

        


