import maya.cmds as cmds
import puiastreTools.tools.curve_tool as curve_tool
from puiastreTools.utils import guides_manager
from puiastreTools.utils import data_export
from importlib import reload
reload(guides_manager)

class EyebrowModule():

    def __init__(self):

        self.data_exporter = data_export.DataExport()

        self.modules_grp = self.data_exporter.get_data("basic_structure", "modules_GRP")
        self.skel_grp = self.data_exporter.get_data("basic_structure", "skel_GRP")
        self.masterWalk_ctl = self.data_exporter.get_data("basic_structure", "masterWalk_CTL")
        self.head_ctl = self.data_exporter.get_data("C_neckModule", "head_ctl")

    def make(self, side):

        self.side = side

        self.module_trn = cmds.createNode("transform", n=f"{side}_eyebrowModule_GRP", p=self.modules_grp)
        self.skinning_trn = cmds.createNode("transform", n=f"{side}_eyebrowSkinningJoints_GRP", p=self.skel_grp)
        self.controllers_trn = cmds.createNode("transform", n=f"{side}_eyebrowControllers_GRP")
        cmds.parent(self.controllers_trn, "C_head_CTL")

        self.eyebrow = guides_manager.guide_import(joint_name=f"{side}_eyebrow_JNT", all_descendents=True)
        

        for i, jnt in enumerate(self.eyebrow):
            if i != 0:
                cmds.parent(jnt, self.module_trn)
        
        self.eyebrow_jnts = cmds.listRelatives(self.module_trn, allDescendents=True, type="joint")

        cmds.delete(self.eyebrow[0])
        # self.controller_creation()

    def local(self, ctl, grp):

        """
        This function sets the local space for a controller and its group.
        It connects the controller's worldMatrix to the group's offsetParentMatrix.
        """

        mult_matrix = cmds.createNode("multMatrix", n=ctl.replace("CTL", "MMX"), ss=True)
        cmds.connectAttr(f"{ctl}.worldMatrix[0]", f"{mult_matrix}.matrixIn[0]")
        cmds.connectAttr(f"{grp}.worldInverseMatrix[0]", f"{mult_matrix}.matrixIn[1]")
        grp_local = cmds.createNode("transform", n=ctl.replace("_CTL", "Local_GRP"), ss=True)
        trn_local = cmds.createNode("transform", n=ctl.replace("_CTL", "Local_TRN"), ss=True)
        cmds.parent(trn_local, grp_local)
        cmds.matchTransform(grp_local, grp, pos=True, rot=True, scl=True)
        cmds.parent(grp_local, self.module_trn)
        cmds.connectAttr(f"{mult_matrix}.matrixSum", f"{trn_local}.offsetParentMatrix")

        return trn_local

    
    def controller_creation(self):

        print(self.eyebrow_jnts)

        p1 = cmds.xform(self.eyebrow_jnts[0], q=True, ws=True, t=True)
        p2 = cmds.xform(self.eyebrow_jnts[len(self.eyebrow_jnts)//2], q=True, ws=True, t=True)
        p3 = cmds.xform(self.eyebrow_jnts[-1], q=True, ws=True, t=True)

        self.eyebrow_bezier = cmds.curve(
            n=f"{self.side}_eyebrowBezier_CRV",
            d=1,
            p=[p1, p2, p3])
        
        self.eyebrow_bezier = cmds.rebuildCurve(
            self.eyebrow_bezier,
            ch=1,
            rpo=1,
            rt=0,
            end=1,
            kr=0,
            kcp=1,
            kep=0,
            d=3,
            tol=0.01,
            s=4)[0]
        
        cmds.select(self.eyebrow_bezier)
        self.eyebrow_bezier = cmds.nurbsCurveToBezier()
        
        cmds.select(f"{self.eyebrow_bezier[0]}.cv[0]")     
        cmds.bezierAnchorPreset(p=1)
        cmds.select(f"{self.eyebrow_bezier[0]}.cv[6]")
        cmds.bezierAnchorPreset(p=1)   
        cmds.select(f"{self.eyebrow_bezier[0]}.cv[3]")
        cmds.bezierAnchorPreset(p=0)

        bezier_cvs = cmds.ls(f"{self.eyebrow_bezier}.cv[*]", fl=True)
        
        self.eyebrow_main_ctl, self.eyebrow_main_grp = curve_tool.controller_creator(f"{self.side}_eyebrowMain", ["GRP", "OFF"])
        cmds.matchTransform(self.eyebrow_main_grp[0], self.eyebrow_jnts[len(self.eyebrow_jnts)//2], pos=True, rot=True)
        self.local(self.eyebrow_main_ctl, self.eyebrow_main_grp[0])
        cmds.parent(self.eyebrow_main_grp[0], self.controllers_trn)

        self.eyebrow_controllers = []
        self.eyebrows_grps = []

        for i, jnt in enumerate(bezier_cvs):

            if i == 1 or i == (len(bezier_cvs) - 2):

                ctl, grp = curve_tool.controller_creator(f"{self.side}_eyebrow0{i}Tan", ["GRP"])

            else:

                ctl, grp = curve_tool.controller_creator(f"{self.side}_eyebrow0{i}", ["GRP"])
                

            cmds.matchTransform(ctl, jnt, pos=True, rot=True)
            self.local(ctl, grp[0])
            cmds.parent(grp, self.controllers_trn)
            self.eyebrow_controllers.append(ctl)
            self.eyebrows_grps.append(grp)