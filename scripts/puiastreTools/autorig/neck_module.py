import maya.cmds as cmds
import os

class NeckModule:

    def __init__(self):

        complete_path = os.path.realpath(__file__)
        self.relative_path = complete_path.split("\scripts")[0]
        self.guides_path = os.path.join(self.relative_path, "guides", "neck_guides_v001.guides")
        self.curves_path = os.path.join(self.relative_path, "curves", "neck_ctl.json")

    def make(self):

        pass

    def lock_attrs(self, ctl, attrs):
        
        for attr in attrs:
            cmds.setAttr(f"{ctl}.{attr}", lock=True, keyable=False, channelBox=False)
    