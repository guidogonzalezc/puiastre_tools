import maya.cmds as cmds
import maya.api.OpenMaya as om
import puiastreTools.tools.curve_tool as curve_tool
from puiastreTools.utils import guides_manager
from importlib import reload
import puiastreTools.utils.data_export as data_export

reload(data_export)

class NeckModule:

    """
    A class to create and manage the neck module in a character rig.
    """

    def __init__(self):

        """
        Initialize the NeckModule class.
        This constructor sets up the paths for guides and curves, retrieves basic structure data, and initializes module, skeleton, and master walk groups.
        """
        self.data_exporter = data_export.DataExport()

        self.modules_grp = self.data_exporter.get_data("basic_structure", "modules_GRP")
        self.skel_grp = self.data_exporter.get_data("basic_structure", "skel_GRP")
        self.masterWalk_ctl = self.data_exporter.get_data("basic_structure", "masterWalk_CTL")

    def make(self, side="C"):
        """
        Create the neck module with the specified side.
        Args:
            side (str): The side of the neck module to create. Default is "C" for center.
        """

        self.side = side

        self.module_trn = cmds.createNode("transform", n=f"{self.side}_neckModule_GRP", p=self.modules_grp)
        self.controllers_trn = cmds.createNode("transform", n=f"{self.side}_neckControllers_GRP", p=self.masterWalk_ctl)
        self.skinning_trn = cmds.createNode("transform", n=f"{self.side}_neckSkinningJoints_GRP", p=self.skel_grp)

        self.import_guides()
        self.controllers()
        self.ik_setup()
        self.out_skinning_jnts()
        self.space_switch()

        self.data_exporter.append_data("C_neckModule", {"neck00_ctl": self.neck_ctl})
        self.data_exporter.append_data("C_neckModule",{"head_ctl": self.head_ctl})

    def lock_attrs(self, ctl, attrs):

        """
        Lock and hide specified attributes on a controller.
        Args:
            ctl (str): The name of the controller.
            attrs (list): A list of attribute names to lock and hide.
        """
        
        for attr in attrs:
            cmds.setAttr(f"{ctl}.{attr}", lock=True, keyable=False, channelBox=False)

    def import_guides(self):

        """
        Import the neck guides from the guides file and parent them to the module transform.
        """

        self.neck_chain = guides_manager.guide_import(joint_name=f"{self.side}_neck00_JNT", all_descendents=True)
        cmds.parent(self.neck_chain[0], self.module_trn)


    def get_offset_matrix(self, child, parent):

        """
        Calculate the offset matrix between a child and parent transform in Maya.
        Args:
            child (str): The name of the child transform.
            parent (str): The name of the parent transform. 
        Returns:
            om.MMatrix: The offset matrix that transforms the child into the parent's space.
        """
        child_dag = om.MSelectionList().add(child).getDagPath(0)
        parent_dag = om.MSelectionList().add(parent).getDagPath(0)
        
        child_world_matrix = child_dag.inclusiveMatrix()
        parent_world_matrix = parent_dag.inclusiveMatrix()
        
        offset_matrix = child_world_matrix * parent_world_matrix.inverse()

        return offset_matrix


    def controllers(self):

        """
        Create controllers for the neck chain and head.
        This function creates controllers for the neck chain, including a mid-neck controller, an end-neck controller, and a head controller.
        It also sets up the necessary attributes and constraints for these controllers.
        """

        self.neck_ctl, self.neck_grp = curve_tool.controller_creator("C_neck", ["GRP"])
        cmds.matchTransform(self.neck_grp[0], self.neck_chain[0], pos=True, rot=True, scl=False)
        self.lock_attrs(self.neck_ctl, ["scaleX", "scaleY", "scaleZ", "visibility"])
       

        self.neck_ctl_mid, self.neck_grp_mid = curve_tool.controller_creator("C_neckMid", ["GRP", "OFF"])
        cmds.addAttr(self.neck_ctl_mid, ln="EXTRA_ATTRIBUTES___", at="enum", en="___")
        cmds.setAttr(f"{self.neck_ctl_mid}.EXTRA_ATTRIBUTES___", lock=True, keyable=False, channelBox=True)
        cmds.addAttr(self.neck_ctl_mid, ln="Follow_Neck", at="float", dv=1, min=0, max=1, keyable=True)
        cmds.matchTransform(self.neck_grp_mid[0], self.neck_chain[5], pos=True, rot=True, scl=False)
        self.lock_attrs(self.neck_ctl_mid, ["scaleX", "scaleY", "scaleZ", "visibility"])



        self.neck_end_ctl, self.neck_end_grp = curve_tool.controller_creator("C_neckEnd", ["GRP", "OFF"])
        cmds.matchTransform(self.neck_end_grp[0], self.neck_chain[-1], pos=True, rot=True, scl=False)
        cmds.addAttr(self.neck_end_ctl, ln="EXTRA_ATTRIBUTES___", at="enum", en="___")
        cmds.setAttr(f"{self.neck_end_ctl}.EXTRA_ATTRIBUTES___", lock=True, keyable=False, channelBox=True)
        cmds.addAttr(self.neck_end_ctl, ln="Follow_Neck", at="float", dv=1, min=0, max=1, keyable=True)
        self.lock_attrs(self.neck_end_ctl, ["scaleX", "scaleY", "scaleZ", "visibility"])

        self.head_ctl, self.head_grp = curve_tool.controller_creator("C_head", ["GRP"])
        cmds.matchTransform(self.head_grp[0], self.neck_chain[-1], rot=True, scl=False)
        self.lock_attrs(self.head_ctl, ["scaleX", "scaleY", "scaleZ", "visibility"])
        cmds.parent(self.neck_grp[0], self.neck_grp_mid[0], self.neck_end_grp[0], self.head_grp[0], self.controllers_trn)

    def ik_setup(self):

        """
        Set up the IK handle for the neck chain and create the necessary joints for the IK spline.
        This function creates an IK spline handle, a curve for the IK, and additional joints for the neck and head.
        """

        self.ik_curve = cmds.curve(d=2, n=f"{self.side}_neckIkCurve_CRV", p=(cmds.xform(self.neck_chain[0], q=True, ws=True, t=True), cmds.xform(self.neck_chain[len(self.neck_chain)//2], q=True, ws=True, t=True), cmds.xform(self.neck_chain[-1], q=True, ws=True, t=True)))
        # self.ik_curve = cmds.rebuildCurve(self.ik_curve, ch=True, rpo=True, rt=0, d=1, tol=0.01, s=4 , n=f"{self.side}_neckIkCurve_CRV")[0]
        self.ik_spring_hdl = cmds.ikHandle(sj=self.neck_chain[0], ee=self.neck_chain[-1], sol="ikSplineSolver", n=f"{self.side}_neckIkSpline_HDL", parentCurve=False, curve=self.ik_curve, createCurve=False)
        cmds.parent(self.ik_curve, self.ik_spring_hdl[0], self.module_trn)
        

        # self.neck_start_jnt_offset = cmds.createNode("transform", n=f"{self.side}_neckStart_OFFSET", p=self.module_trn)
        # self.neck_start_jnt = cmds.createNode("joint", n=f"{self.side}_neckStart_JNT", p=self.neck_start_jnt_offset)
        # cmds.matchTransform(self.neck_start_jnt_offset, self.neck_chain[0], pos=True, rot=True, scl=False)
        # cmds.parentConstraint(self.neck_ctl, self.neck_start_jnt_offset, mo=True)

        # self.neck_mid_jnt_offset = cmds.createNode("transform", n=f"{self.side}_neckMid_OFFSET", p=self.module_trn)
        # self.neck_mid_jnt = cmds.createNode("joint", n=f"{self.side}_neckMid_JNT", p=self.neck_mid_jnt_offset)
        # cmds.matchTransform(self.neck_mid_jnt_offset, self.neck_chain[5], pos=True, rot=True, scl=False)
        # cmds.parentConstraint(self.neck_ctl_mid, self.neck_mid_jnt_offset, mo=True)

        # self.head_neck_end_jnt_offset = cmds.createNode("transform", n=f"{self.side}_headNeckEnd_OFFSET", p=self.module_trn)
        # self.head_neck_end_jnt = cmds.createNode("joint", n=f"{self.side}_headNeckEnd_JNT", p=self.head_neck_end_jnt_offset)
        # cmds.matchTransform(self.head_neck_end_jnt_offset, self.neck_chain[-1], pos=True, rot=True, scl=False)

        for i, ctl in enumerate([self.neck_ctl, self.neck_ctl_mid, self.neck_end_ctl]):
            decompose_matrix = cmds.createNode("decomposeMatrix", n=ctl.replace("CTL", "DCM"), ss=True)
            cmds.connectAttr(f"{ctl}.worldMatrix[0]", f"{decompose_matrix}.inputMatrix")
            cmds.connectAttr(f"{decompose_matrix}.outputTranslate", f"{self.ik_curve}.controlPoints[{i}]")


        
        # Skin the curve to the joints
        # self.curve_skin_cluster = cmds.skinCluster(self.neck_start_jnt, self.neck_mid_jnt, self.head_neck_end_jnt, self.ik_curve, tsb=True, n=f"{self.side}_neckSkinCluster_SKIN", mi=5)

        # Set the spline with the correct settings
        cmds.setAttr(f"{self.ik_spring_hdl[0]}.dTwistControlEnable", 1)
        cmds.setAttr(f"{self.ik_spring_hdl[0]}.dWorldUpType", 4)
        cmds.setAttr(f"{self.ik_spring_hdl[0]}.dForwardAxis", 4)
        cmds.connectAttr(f"{self.neck_ctl}.worldMatrix[0]", f"{self.ik_spring_hdl[0]}.dWorldUpMatrix")
        cmds.connectAttr(f"{self.neck_end_ctl}.worldMatrix[0]", f"{self.ik_spring_hdl[0]}.dWorldUpMatrixEnd")
        # cmds.parentConstraint(self.neck_end_ctl, self.head_neck_end_jnt, mo=True)

        parent = cmds.parentConstraint(self.neck_ctl, self.masterWalk_ctl, self.neck_grp_mid[1], mo=True)[0]
        rev_00 = cmds.createNode("reverse", n=f"{self.side}_neckMidReverse_REV", ss=True)
        cmds.connectAttr(f"{self.neck_ctl_mid}.Follow_Neck", f"{parent}.w0")
        cmds.connectAttr(f"{self.neck_ctl_mid}.Follow_Neck", f"{rev_00}.inputX")
        cmds.connectAttr(f"{rev_00}.outputX", f"{parent}.w1")

        parent_02 = cmds.parentConstraint(self.neck_ctl, self.masterWalk_ctl, self.neck_end_grp[1], mo=True)[0]
        rev_01 = cmds.createNode("reverse", n=f"{self.side}_headReverse_REV")
        cmds.connectAttr(f"{self.neck_end_ctl}.Follow_Neck", f"{parent_02}.w0")
        cmds.connectAttr(f"{self.neck_end_ctl}.Follow_Neck", f"{rev_01}.inputX")
        cmds.connectAttr(f"{rev_01}.outputX", f"{parent_02}.w1")


        # COMMENTED FOR AYCHEDRAL, COULD BE USED ON ANOTHER MODULE

        # self.jaw_jnts = guides_manager.guide_import(joint_name=f"{self.side}_jaw_JNT", all_descendents=True)
        # self.upper_jaw_jnts = guides_manager.guide_import(joint_name=f"{self.side}_upperJaw_JNT", all_descendents=True)
        # cmds.parent(self.jaw_jnts, self.upper_jaw_jnts, self.module_trn)
        


    def out_skinning_jnts(self):

        """
        Create skinning joints for the neck chain and head joint.
        These joints will be used for skinning the mesh to the skeleton.
        """

        skinning_jnts = []
        for i, jnt in enumerate(self.neck_chain):
            cmds.select(clear=True)
            skin_joint = cmds.joint(n=jnt.replace("_JNT", "Skinning_JNT"))
            cmds.connectAttr(f"{jnt}.worldMatrix[0]", f"{skin_joint}.offsetParentMatrix")
            cmds.parent(skin_joint, self.skinning_trn)
            skinning_jnts.append(skin_joint)
        
        cmds.connectAttr(f"{self.neck_chain[-1]}.worldMatrix[0]", f"{self.head_grp[0]}.offsetParentMatrix")
        cmds.connectAttr(f"{self.head_ctl}.worldMatrix[0]", f"{skinning_jnts[-1]}.offsetParentMatrix", force=True)
        cmds.select(clear=True)


    def space_switch(self):

        """
        Create a space switch for the head controller that allows it to follow the masterWalk controller, neck end controller, or body controller.
        """

        body_ctl = self.data_exporter.get_data("C_spineModule", "body")

        # Create the attribute for the head controller
        cmds.addAttr(self.head_ctl, ln="SPACE_SWITCHES", at="enum", en="____", keyable=True)
        cmds.setAttr(f"{self.head_ctl}.SPACE_SWITCHES", lock=True, keyable=False, channelBox=True)
        cmds.addAttr(self.head_ctl, ln="Space_Switch", at="enum", en="Neck:Masterwalk:Body", keyable=True)
        cmds.addAttr(self.head_ctl, ln="Follow", at="float", dv=1, min=0, max=1, keyable=True)

        decompose_matrix_masterwalk = cmds.createNode("decomposeMatrix", n=f"{self.side}_masterWalk_DCM")
        cmds.connectAttr(f"{self.masterWalk_ctl}.worldMatrix[0]", f"{decompose_matrix_masterwalk}.inputMatrix")

        blend_colors = cmds.createNode("blendColors", n=f"{self.side}_blendMatrix_BLC")

        cmds.connectAttr(f"{self.head_ctl}.Follow", f"{blend_colors}.blender")
        cmds.connectAttr(f"{decompose_matrix_masterwalk}.outputRotate", f"{blend_colors}.color2")

        condition_masterwalk = cmds.createNode("condition", n=f"{self.side}_masterWalk_CON")
        condition_body = cmds.createNode("condition", n=f"{self.side}_body_CON")
        condition_neck = cmds.createNode("condition", n=f"{self.side}_neckEnd_CON")
        cmds.setAttr(f"{condition_neck}.operation", 0)
        cmds.setAttr(f"{condition_neck}.secondTerm", 0)
        cmds.setAttr(f"{condition_neck}.colorIfTrueR", 1)
        cmds.setAttr(f"{condition_neck}.colorIfFalseR", 0)
        cmds.setAttr(f"{condition_masterwalk}.operation", 0)
        cmds.setAttr(f"{condition_masterwalk}.secondTerm", 1)
        cmds.setAttr(f"{condition_masterwalk}.colorIfTrueR", 1)
        cmds.setAttr(f"{condition_masterwalk}.colorIfFalseR", 0)
        cmds.setAttr(f"{condition_body}.operation", 0)
        cmds.setAttr(f"{condition_body}.secondTerm", 2)
        cmds.setAttr(f"{condition_body}.colorIfTrueR", 1)
        cmds.setAttr(f"{condition_body}.colorIfFalseR", 0)

        cmds.connectAttr(f"{self.head_ctl}.Space_Switch", f"{condition_masterwalk}.firstTerm")
        cmds.connectAttr(f"{self.head_ctl}.Space_Switch", f"{condition_body}.firstTerm")
        cmds.connectAttr(f"{self.head_ctl}.Space_Switch", f"{condition_neck}.firstTerm")

        parent_matrix_node = cmds.createNode("parentMatrix", n=f"{self.side}_headParentMatrix_PM")
        cmds.connectAttr(f"{self.head_grp[0]}.worldMatrix[0]", f"{parent_matrix_node}.inputMatrix")

        cmds.connectAttr(f"{self.masterWalk_ctl}.worldMatrix[0]", f"{parent_matrix_node}.target[0].targetMatrix")
        cmds.connectAttr(f"{condition_masterwalk}.outColorR", f"{parent_matrix_node}.target[0].weight")
        cmds.connectAttr(f"{self.neck_end_ctl}.worldMatrix[0]", f"{parent_matrix_node}.target[1].targetMatrix")
        cmds.connectAttr(f"{condition_neck}.outColorR", f"{parent_matrix_node}.target[1].weight")
        cmds.connectAttr(f"{body_ctl}.worldMatrix[0]", f"{parent_matrix_node}.target[2].targetMatrix")
        cmds.connectAttr(f"{condition_body}.outColorR", f"{parent_matrix_node}.target[2].weight")

        head_off = cmds.getAttr(f"{self.head_ctl}.worldMatrix[0]")

        
        masterwalk_offset = self.get_offset_matrix(self.head_ctl, self.masterWalk_ctl)
        neck_offset = self.get_offset_matrix(self.head_ctl, self.neck_end_ctl)
        body_offset = self.get_offset_matrix(self.head_ctl, body_ctl)
        cmds.setAttr(f"{parent_matrix_node}.target[0].offsetMatrix", masterwalk_offset, type="matrix")
        cmds.setAttr(f"{parent_matrix_node}.target[1].offsetMatrix", neck_offset, type="matrix")
        cmds.setAttr(f"{parent_matrix_node}.target[2].offsetMatrix", body_offset, type="matrix")


        mult_matrix_offset = cmds.createNode("multMatrix", n=f"{self.side}_head_MMX")
        cmds.connectAttr(f"{parent_matrix_node}.outputMatrix", f"{mult_matrix_offset}.matrixIn[0]")
        cmds.connectAttr(f"{self.head_grp[0]}.worldInverseMatrix", f"{mult_matrix_offset}.matrixIn[1]")

        decompose_head = cmds.createNode("decomposeMatrix", n=f"{self.side}_head_DCM")
        cmds.connectAttr(f"{mult_matrix_offset}.matrixSum", f"{decompose_head}.inputMatrix")
        compose_end = cmds.createNode("composeMatrix", n=f"{self.side}_head_COM")
        cmds.connectAttr(f"{decompose_head}.outputTranslate", f"{compose_end}.inputTranslate")
        cmds.connectAttr(f"{decompose_head}.outputRotate", f"{blend_colors}.color1")
        cmds.connectAttr(f"{decompose_head}.outputScale", f"{compose_end}.inputScale")
        cmds.connectAttr(f"{decompose_head}.outputShear", f"{compose_end}.inputShear")
        cmds.connectAttr(f"{decompose_head}.outputQuat", f"{compose_end}.inputQuat")
        cmds.connectAttr(f"{blend_colors}.output", f"{compose_end}.inputRotate")

        cmds.connectAttr(f"{compose_end}.outputMatrix", f"{self.head_ctl}.offsetParentMatrix")

