import maya.utils as mu
import maya.cmds as cmds
import getpass, os, json


"""
This script sets up the Maya environment by creating command ports and loading the Puiastre Productions UI.
It also executes a deferred command to load the UI after Maya has fully initialized.
"""

def open_vs_code_ports():
    if not cmds.commandPort(":4434", query=True):
        cmds.commandPort(name=":4434")
    if not cmds.commandPort("localhost:7001", query=True):
        cmds.commandPort(name="localhost:7001")

def init_puiastre_ui():
    user = getpass.getuser()
    main_path = "P:/VFX_Project_20/PUIASTRE_PRODUCTIONS/00_Pipeline/puiastre_tools/allowed_users.json"

    if os.path.isdir("P:/VFX_Project_20") is False:
        try:
            import puiastreTools.ui.option_menu as option_menu
            option_menu.puiastre_ui()
        except ImportError as e:
            cmds.warning(f"Could not load Puiastre Productions UI: {e}")
        open_vs_code_ports()
        return
        

    if not os.path.exists(main_path):
        cmds.warning("allowed_users.json not found.")
        return

    with open(main_path, "r") as file:
        allowed_users = json.load(file)

    allowed = None
    for allowed, users in allowed_users.items():
        if user == users:
            allowed = True
            break

    if allowed is None:
        cmds.warning(f"User '{user}' is not authorized to access Puiastre Productions tools.")
        return

    else:
        print(f"User '{user}' is authorized. Loading Puiastre Productions tools.")

        try:
            import puiastreTools.ui.option_menu as option_menu
            option_menu.puiastre_ui()
            print("Puiastre Productions UI loaded successfully.")
        except ImportError as e:
            cmds.warning(f"Could not load Puiastre Productions UI: {e}")
        open_vs_code_ports()

mu.executeDeferred(init_puiastre_ui)

