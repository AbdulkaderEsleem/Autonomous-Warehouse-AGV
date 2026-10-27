# Autonomous Guided Vehicle (AGV) for Warehouse Logistics & Sorting
> **Industrial Robotics Project | Embedded Machine Vision & Closed-Loop Actuation**

[[https://img.shields.io/badge/Controller-Raspberry%20Pi%20Pico%20RP2040-red.svg]](https://www.raspberrypi.com/products/raspberry-pi-pico/)
[[https://img.shields.io/badge/Vision-Python%20OpenCV-green.svg]](https://opencv.org/)
[[https://img.shields.io/badge/CAD-SolidWorks-blue.svg]](https://www.solidworks.com/)
[[https://img.shields.io/badge/License-MIT-yellow.svg]](https://opensource.org/licenses/MIT)

## 1. Project Overview
An automated material-handling Automated Guided Vehicle (AGV) engineered for intralogistics distribution centers. The robot autonomously navigates mapped warehouse routes, detects and classifies package tags via machine vision, and executes precise multi-bin sorting routines.

## 2. Distributed Control Architecture
- **High-Level Perception (Host / SBC):**
  - Real-time video processing pipeline in **Python & OpenCV** using the Raspberry Pi Camera module.
  - Detects parcel destinations via color segmentation and marker fiducials at speeds up to 1.2 m/s.
- **Low-Level Deterministic Control (Raspberry Pi Pico RP2040):**
  - Dual-core ARM Cortex-M0+ running closed-loop velocity PID controllers.
  - Quadrature encoder feedback decoding (1024 CPR) for dead-reckoning odometry and PWM motor regulation.

## 3. Mechanical Design & Rapid Prototyping
- **Differential Chassis:** Custom CAD modeled in SolidWorks with drop-down suspension arms for smooth surface contact across floor seams.
- **Sorting Actuator:** 3D-printed PETG diverter mechanism driven by a high-torque metal servo for rapid parcel ejection into sorting bays.

## 4. Hardware Specifications
| Subsystem | Components & Specifications |
| :--- | :--- |
| **Microcontroller** | Raspberry Pi Pico (RP2040 Dual ARM Cortex-M0+) |
| **Vision Sensor** | Raspberry Pi Camera Module v2 (720p @ 30fps) |
| **Drivetrain** | 2x DC Geared Motors with 1024 CPR optical encoders |
| **Motor Drivers** | High-power dual H-Bridge with thermal cutoff protection |
| **Power Distribution** | 3S LiPo battery with isolated step-down buck regulators |

## 5. Performance Benchmarks
- **Sorting Accuracy:** Achieved **98.4%** successful bin routing across 200 consecutive test cycles.
- **Path Deviation:** Lateral tracking error maintained within **± 8 mm** along designated corridors.
