import maya.cmds as cmds
import puiastreTools.tools.curve_tool as curve_tool
from puiastreTools.utils import guides_manager
from puiastreTools.utils import data_export
from importlib import reload
reload(data_export)


class SpikesModule(object):
    
    def __init__(self):

        data_exporter = data_export.DataExport()

        self.modules_grp = data_exporter.get_data("basic_structure", "modules_GRP")
        self.skel_grp = data_exporter.get_data("basic_structure", "skel_GRP")
        self.masterWalk_ctl = data_exporter.get_data("basic_structure", "masterWalk_CTL")

    def make(self):

        """
        Create the spikes module
        
        """

        self.side = "C"

        self.module_trn = cmds.createNode("transform", name=f"{self.side}_spikesModule_GRP", ss=True, parent=self.modules_grp)
        self.controllers_trn = cmds.createNode("transform", name=f"{self.side}_spikesControllers_GRP", ss=True, parent=self.masterWalk_ctl)
        self.skinning_trn = cmds.createNode("transform", name=f"{self.side}_spikesSkinning_GRP", ss=True, parent=self.skel_grp)


        for side in ["L", "R"]:
            self.guides_import(side)
            self.spike(side, self.upper_spike[0])
            self.spike(side, self.lateral_spike[0])
    
    def guides_import(self, side):

        """
        Import all the spikes joints that exist in the guides file.
        
        """

        self.upper_spike = guides_manager.guide_import(joint_name=f"{side}_upperSpike_JNT", all_descendents=True)
        self.lateral_spike = guides_manager.guide_import(joint_name=f"{side}_lateralSpike_JNT", all_descendents=True)
        cmds.parent(self.upper_spike[0], self.lateral_spike[0], self.module_trn)
    
    def lock_attrs(self, ctl, attrs):
        
        for attr in attrs:
            cmds.setAttr(f"{ctl}.{attr}", lock=True, keyable=False, channelBox=False)

    def spike_build(self):

        self.attrs_ctl, self.attrs_grp = curve_tool.controller_creator(f"{self.side}_spikeAttributes", ["GRP"])
        cmds.move(0, 250, 0, self.attrs_grp, r=True)
        self.lock_attrs(self.attrs_ctl, ["translateX", "translateY", "translateZ", "rotateX", "rotateY", "rotateZ", "scaleX", "scaleY", "scaleZ", "visibility"])
        cmds.addAttr(self.attrs_ctl, ln="Envelope", at="float", dv=0, maxValue=1, minValue=0, keyable=True)
        cmds.addAttr(self.attrs_ctl, ln="Amplitude", at="float", dv=0.1, keyable=True)
        cmds.addAttr(self.attrs_ctl, ln="Wave", at="float", dv=0, keyable=True)
        cmds.addAttr(self.attrs_ctl, ln="Dropoff", at="float", dv=0, keyable=True)

    def spike(self, side, spike_joint):

        
        name = spike_joint.split("_")[1]
        self.spike_joints = cmds.listRelatives(spike_joint, type="joint", allDescendents=True)
        self.spike_joints.reverse() 
        match_jnt = spike_joint
        print(match_jnt)


        self.spike_transform = cmds.createNode("transform", n=f"{side}_{name}Module_GRP", p=self.module_trn)
        cmds.parent(match_jnt, self.spike_transform)

        # Get the positions of the end joints
        end_jnts = []
        end_jnts_pos = []
        

        for i, jnts in enumerate(self.spike_joints):

            if i <= 17:
                jnt = cmds.listRelatives(jnts, c=True)[0]
                end_jnts_pos.append(cmds.xform(jnt, q=True, ws=True, t=True))
                end_jnts.append(jnt)
                self.spike_joints.remove(jnt)

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
        joints_grp = cmds.createNode("transform", n=f"{side}_{name}Joints_GRP", p=self.spike_transform)
        hdls_transform = cmds.createNode("transform", n=f"{side}_{name}Handles_GRP", p=self.spike_transform)
        for i, jnt in enumerate(self.spike_joints):
            ik_hdl = cmds.ikHandle(sj=jnt, ee=end_jnts[i], sol="ikSCsolver", n=f"{side}_{name}0{i}Ik_HDL")
            cmds.parent(ik_hdl[0], hdls_transform)
            cmds.pointConstraint(locators[i], ik_hdl[0], mo=True)
            cmds.setAttr(f"{jnt}.radius", 5)
            cmds.parent(jnt, joints_grp)

        # Add a Sine handle to the curve
        # Do the handle local
        curve_duplicate = cmds.duplicate(curve, n=f"{side}_{name}Sine_CRV")[0]
        sine_hdl = cmds.nonLinear(curve_duplicate, type="sine", n=f"{side}_{name}Sine_")
        cmds.parent(sine_hdl[1], self.spike_transform)
        cmds.rotate(90, 0, 0, sine_hdl[1], ws=True)
        local_bs = cmds.blendShape(curve_duplicate, curve, n=f"{side}_{name}SineLocal_BS", origin="world")


        # Create a controller for the curve and the sine handle
        self.ctl, self.grp = curve_tool.controller_creator(f"{side}_{name}", ["GRP"])
        cmds.parent(self.grp, self.controllers_trn)
        cmds.matchTransform(self.grp, match_jnt, pos=True, rot=True, scl=False)
        self.lock_attrs(self.ctl, ["translateX", "translateY", "translateZ", "rotateX", "rotateY", "rotateZ", "scaleX", "scaleY", "scaleZ", "visibility"])
        cmds.addAttr(self.ctl, ln="Envelope", at="float", dv=0, maxValue=1, minValue=0, keyable=True)
        cmds.addAttr(self.ctl, ln="Amplitude", at="float", dv=0.1, keyable=True)
        cmds.addAttr(self.ctl, ln="Wave", at="float", dv=0, keyable=True)
        cmds.addAttr(self.ctl, ln="Offset", at="float", dv=0, keyable=True)
        cmds.addAttr(self.ctl, ln="Dropoff", at="float", dv=0, keyable=True)
        cmds.connectAttr(f"{self.ctl}.Envelope", f"{local_bs[0]}.{curve_duplicate}")
        cmds.connectAttr(f"{self.ctl}.Amplitude", f"{sine_hdl[0]}.amplitude")
        cmds.connectAttr(f"{self.ctl}.Wave", f"{sine_hdl[0]}.wavelength")
        cmds.connectAttr(f"{self.ctl}.Offset", f"{sine_hdl[0]}.offset")
        cmds.connectAttr(f"{self.ctl}.Dropoff", f"{sine_hdl[0]}.dropoff")
        

        for i, jnt in enumerate(end_jnts):
            cmds.select(clear=True)
            skin_joint = cmds.joint(n=jnt.replace("_JNT", "Skinning_JNT"))
            cmds.connectAttr(f"{jnt}.worldMatrix[0]", f"{skin_joint}.offsetParentMatrix")
            cmds.parent(skin_joint, self.skinning_trn)
            cmds.setAttr(f"{skin_joint}.radius", 5)

        cmds.delete(match_jnt)