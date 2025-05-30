# puiastre_tools

**puiastre_tools** is an open-source, modular rigging toolkit for Autodesk Maya, designed to streamline the creation of custom rigs for characters and props. Inspired by frameworks like mGear and autoRigger, it offers a flexible and extensible foundation for riggers and technical artists.

---

## ✨ Features

- **Modular Rigging System** – Build rigs by combining reusable components.
- **Custom Guide Templates** – Define and save guide templates for rapid rig setup.
- **Curve-Based Controls** – Generate animator-friendly controls with customizable shapes.
- **Icon Library** – Access a collection of icons to enhance UI elements.
- **Python-Based Scripts** – Automate rigging tasks with a suite of Python tools.
- **Lightweight and Extensible** – Easily integrate into existing pipelines and extend functionality.

---

## 📁 Project Structure

```
puiastre_tools/
├── build/           # Compiled rig components
├── curves/          # Curve shapes for controls
├── guides/          # Guide templates for rigging
├── icons/           # Icon assets for UI
├── scripts/         # Python scripts for automation
├── puiastre_tools.mod  # Maya module file
├── README.md
├── ROADMAP.md
└── LICENSE
```

---

## 🔧 Installation

1. **Clone the Repository**:

   ```bash
   git clone https://github.com/GuiidoGC/puiastre_tools.git
   ```

2. **Set Up Maya Module**:
   - Copy the `puiastre_tools` folder to your Maya modules directory.
   - Ensure the `puiastre_tools.mod` file is correctly configured to point to the tools' paths.

3. **Restart Maya**:
   - Upon restarting, Maya should recognize the new module and load the tools accordingly.

---

## 🚀 Usage

1. **Access the Tools**:
   - Once loaded, the tools can be accessed via the Maya shelf or through custom menus, depending on your setup.

2. **Create a Rig**:
   - Use the provided guide templates to position guides on your model.
   - Run the build scripts to generate the rig based on the guides.

3. **Customize Controls**:
   - Utilize the curve shapes in the `curves/` directory to create custom control shapes.

4. **Enhance UI**:
   - Incorporate icons from the `icons/` directory to improve the user interface of your rigging tools.

---

## 🛠️ Contributing

Contributions are welcome! To contribute:

1. Fork the Repository:
   - Create your own fork to work on the project.

2. Create a Feature Branch:
   - Develop your feature or fix in a separate branch.

3. Submit a Pull Request:
   - Once your changes are ready, submit a pull request for review.

Please refer to the `CONTRIBUTING.md` file for detailed guidelines.

---

## 📄 License

This project is licensed under the [Apache License 2.0](LICENSE).

---

## 📚 Resources

- [Maya Python API Documentation](https://help.autodesk.com/cloudhelp/2022/ENU/Maya-Tech-Docs/CommandsPython/)
- [mGear Framework](https://www.mgear-framework.com/)
- [autoRigger by leixingyu](https://github.com/leixingyu/autoRigger)
- [GameRig by Arminando](https://github.com/Arminando/GameRig)
- [Pinocchio](https://github.com/stnoh/Pinocchio)
- [Synty → Godot AutoRig Pro Fix](https://github.com/Vortex-Basis-LLC/fix_synty_anim_to_godot_with_autorigpro)
- [AuroraFreir AutoRigger](https://github.com/aurorafreir/Autorigger)

---

## 📞 Contact

For questions, suggestions, or collaborations, please open an issue on the [GitHub repository](https://github.com/GuiidoGC/puiastre_tools/issues).
