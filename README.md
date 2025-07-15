# AB-SO-BOT
![3D Files](https://img.shields.io/badge/3D--Printable-STL-blueviolet?logo=print)
![Last Commit](https://img.shields.io/github/last-commit/Mr-C4T/AB-SO-BOT)
![Repo Size](https://img.shields.io/github/repo-size/Mr-C4T/AB-SO-BOT)
![GitHub stars](https://img.shields.io/github/stars/Mr-C4T/AB-SO-BOT?style=social)

**Aluminium Body for Standard Open Arm (SO-ARM100)**

<img src="images/body-render.png" alt="AB-SO-BOT render" width="100%">

## 🔩 Modular Design

AB-SO-BOT is built using a combination of <strong>3D-printed parts</strong> and standard <strong>4040 T-slot aluminium extrusions</strong> to create a customizable and modular body for the <a href="https://github.com/TheRobotStudio/SO-ARM100">SO-ARM100</a> robotic arm designed by TheRobotStudio and HuggingFace.❤️  

<img src="images/AB-SO-DARK.png" alt="AB-SO-BOT Drawing" width="60%">

This modularity allows for easy expansion and adaptation for different robotic applications. From a compact workshop assistant mounted on a camera tripod, to a full humanoid-style bimanual setup using VR controllers teleoperation.

You can find mounting instructions for attaching the so-arm to 4040T profiles in the <a href="https://github.com/TheRobotStudio/SO-ARM100/blob/main/Optional/4040_Base_Mount/README.md">SO-ARM100 repository</a>.

| ![AB-SO-BOT Banner](images/AB-SO-banner.png) |![AB-SO-Render](images/AB-SO-Render.png) |
|:--:|:--:|

## 🤗 Compatible with LeRobot

State-of-the-art AI for real-world robotics  
[![LeRobot Repo](https://img.shields.io/badge/LeRobot-AI-yellow?logo=github)](https://github.com/huggingface/lerobot)

Also check out 🧪 **Phosphobot** for web control (GUI + API) and VR bimanual teleoperation  
[![Phosphobot](https://img.shields.io/badge/Phosphobot-Control-green?logo=github)](https://github.com/phospho-app/phosphobot)

My Huggingface profile (Models & Datasets)  
[![Huggingface](https://img.shields.io/badge/Huggingface-Models-orange?logo=huggingface)](https://huggingface.co/MrC4t)


<p align=" ">
  <a href="https://youtu.be/-x64_-g5ABw?t=606">
    <img src="images/LeRobotHackathonKickOff.png" alt="AB-SO-BOT in LeRobot Hackathon Kickoff" width="60%">
  </a>
  <img src="images/AB-SO.gif" alt="AB-SO-BOT gif" width="36%">
</p>

> 🦾 **_AB-SO-BOT spotted in the 2025 LeRobot Worldwide Hackathon Kickoff video!_**  


## 🧩 3D Parts Overview

AB-SO-BOT is built from modular 3D-printed components, each designed to interface with standard M3/M4 hardware and 4040 aluminum extrusions.

📂 Browse all printable files here: [STL/](./STL/)

## 🦾 4040 Adaptor (Shoulder Mount)

Connects the SO-ARM100 base to 4040 extrusions.
See mounting <a href="https://github.com/TheRobotStudio/SO-ARM100/blob/main/Optional/4040_Base_Mount/README.md">instructions</a> in the SO-ARM100 repo.

The flat version is also available as a STEP file.

📐 [Download STEP file](STEP/SOARM100-4040-Adapter-V2.step)

<table>
  <tr>
    <td align="center" width="50%">
      <strong>4040-Adapter</strong><br>
      <em>Flat version</em><br>
      <a href="STL/SOARM100-4040-Adapter-V2.stl">
        <img src="images/adapter-flat.jpg" height="180px" />
      </a>
    </td>
    <td align="center" width="50%">
      <strong>4040-Adapter-Curved</strong><br>
      <em>Rounded style</em><br>
      <a href="STL/SOARM100-4040-Adapter.stl">
        <img src="images/adapter-curved.jpg" height="180px" />
      </a>
    </td>
  </tr>
</table>

> Requires: M4 screws + wing nuts + T-slot nuts
## 🦴 T-Spine

Links horizontal and vertical extrusions. Also acts as the base for ORP mounting. 
[Open Robotic Platform](https://openroboticplatform.com/designrules)

<table>
  <tr>
    <td align="center" width="50%">
      <strong>TSPINE</strong><br>
      <em>Standard connector</em><br>
      <a href="STL/ABSO-TSPINE.stl">
        <img src="images/tspine.png" height="180px" />
      </a>
    </td>
    <td align="center" width="50%">
      <strong>TSPINE-ORP</strong><br>
      <em>With 4×2 ORP</em><br>
      <a href="STL/ABSO-TSPINE-ORP.stl">
        <img src="images/tspine-orp.png" height="180px" />
      </a>
    </td>
  </tr>
</table>


> Requires: M4 screws + optional M3 hardware (orp version)
## 🧠 Head & Neck

Supports RealSense D435/D435i cameras. Comes in 2 parts: Head and Neck.
      
- <a href="STL/ABSO-NECK.stl">NECK</a>
- <a href="STL/ABSO-HEAD.stl">HEAD</a>


> Requires: M3 screws
## 👂 Ear
Side-mounted panels for USB, RF, or clean finishing. Fully interchangeable.
If you'd like to customize your own panel, the **Blank** version is also available as a STEP file. 

📐 [Download STEP file](STEP/ABSO-EAR-Basic.step)

<table>
  <tr>
    <td align="center" width="25%">
      <strong>SMA</strong><br>
      <a href="STL/ABSO-EAR-SMA.stl">
        <img src="images/head-renderV2.png" height="160"/>
      </a>
    </td>
    <td align="center" width="25%">
      <strong>Blank</strong><br>
      <a href="STL/ABSO-EAR-Basic.stl">
        <img src="images/ear-blank.png" height="160"/>
      </a>
    </td>
    <td align="center" width="25%">
      <strong>USB</strong><br>
      <a href="STL/ABSO-EAR-USB.stl">
        <img src="images/ear.png" height="160"/>
      </a>
    </td>
    <td align="center" width="25%">
      <strong>USB2</strong><br>
      <a href="STL/ABSO-EAR-USB2.stl">
        <img src="images/ear3.png" height="160"/>
      </a>
    </td>
  </tr>
</table>

> Requires: M3 screws

## 🎥 Watch the Demos on YouTube

| Autonomous 3D printing loop | First **AI** inference demo |
|:--:|:--:|
| [![Watch the demo](https://img.youtube.com/vi/gPFcQjBbeOc/hqdefault.jpg)](https://www.youtube.com/watch?v=gPFcQjBbeOc) | [![Watch the demo](https://img.youtube.com/vi/xaGvbCwGXA4/hqdefault.jpg)](https://www.youtube.com/shorts/xaGvbCwGXA4) |

## 🙌 Thanks for Your Support

If this project is useful or inspiring to you, feel free to give it a ⭐ so others can discover it too.  
You're more than welcome to ask questions, share ideas for improvement, or show off what you’ve built!

<p align=" ">
      <img src="https://api.star-history.com/svg?repos=Mr-C4T/AB-SO-BOT&type=Date" alt="Star History Chart" width="60%" />
      <img src="images/ABSO-TRIPOD.png" alt="ABSO Tripod" width="36%" />
</p>
