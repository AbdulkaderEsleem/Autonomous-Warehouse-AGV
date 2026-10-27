# Autonomous Guided Vehicle (AGV) for Warehouse Logistics & Sorting
> **Collaborative Robotics Project | Hardware Prototyping & System Testing**

[[https://img.shields.io/badge/Controller-Raspberry%20Pi%20Pico%20RP2040-red.svg]](https://www.raspberrypi.com/products/raspberry-pi-pico/)
[[https://img.shields.io/badge/Vision-Python%20OpenCV-green.svg]](https://opencv.org/)
[[https://img.shields.io/badge/CAD-SolidWorks-blue.svg]](https://www.solidworks.com/)
[[https://img.shields.io/badge/License-MIT-yellow.svg]](https://opensource.org/licenses/MIT)

## 1. Project Overview
A collaborative proof-of-concept Automated Guided Vehicle (AGV) developed for intralogistics warehouse package sorting. The platform integrates machine vision tag identification with deterministic motor control to execute automated parcel routing.

## 2. My Engineering Contributions & Role
**Role: Mechatronics Assistant & Hardware Testing Contributor**
- **Mechanical Assembly & Fitment:** Assisted in the physical assembly of the differential drive chassis, bracket alignment, and mounting of the 3D-printed sorting diverter.
- **Wiring & Power Harnessing:** Supported low-level circuit wiring, motor driver (H-Bridge) interfacing with the Raspberry Pi Pico, and power distribution isolation.
- **Field Benchmark Testing:** Participated in running systematic sorting validation trials, logging trajectory deviations, and verifying parcel classification consistency across 200 test runs.

## 3. System Architecture (Team Implementation)
- **High-Level Perception:** Host SBC running Python & OpenCV for parcel tag identification using the Raspberry Pi Camera module.
- **Low-Level Actuation:** Dual-core Raspberry Pi Pico (RP2040) managing velocity PID loops and quadrature encoder feedback (1024 CPR).
- **Sorting Mechanism:** Servo-actuated diverter designed to sweep classified parcels into designated sorting zones.

## 4. Hardware Specifications
| Subsystem | Components & Specifications |
| :--- | :--- |
| **Microcontroller** | Raspberry Pi Pico (RP2040 Dual ARM Cortex-M0+) |
| **Vision Sensor** | Raspberry Pi Camera Module v2 |
| **Drivetrain** | Dual geared DC motors with optical encoders |
| **Actuator** | Metal-gear servo mechanical sorting arm |
| **Power Supply** | 3S LiPo battery with buck converters |

## 5. Experimental Results
- Validated parcel diversion accuracy of **98.4%** across testing batches.
- Maintained stable corridor line-following with lateral error within **± 8 mm**.
