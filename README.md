# NetworkPathMap
This is a network visualization and path analysis tool built using PyQt6 and Leaflet.js. It allows users to display network nodes, visualize connectivity, compute paths, and interactively analyze circuit data.

## Features
✔ Interactive Map – Displays locations and their connections on a zoomable, draggable map.<br>
✔ Node-Based and Device-Based Topology – Supports both location-based and device-based network graphs.<br>
✔ Path Calculation – Computes all possible paths between selected nodes using DFS.<br>
✔ Manual Path Design – Allows users to manually select paths and examine circuit details.<br>
✔ CSV Data Parsing – Reads and filters network circuit data from CSV files.<br>
✔ Edge and Node Highlighting – Highlights paths and nodes dynamically based on selection.<br>


## Usage

### Map Interface
- Left Panel: Displays node information and available circuits.<br>
- Right Panel: Displays an interactive map with selectable nodes.<br>
- Context Menu: Right-click on a node to set it as Start or End.<br>
### Graph Modes
- Location-Based Mode (default): Builds topology using site names.<br>
- Device-Based Mode: Uses equipment serial numbers to ensure accurate routing.<br>
### Path Calculation
1. Select Start & End Points<br>
2. Run Path Calculation (DFS-based)<br>
3. Review & Highlight Routes on the map<br>
### Manual Path Design
1. Enable Manual Path Mode<br>
2. Right-click nodes to construct a custom route<br>
3. Examine available path options<br>
### Examine Circuit Detail
- While path is calculated, available circuit will show on item box below segment by segment.<br>
- Select circuit to show circuit detail information.<br>
## Screenshots

TESTIMG

---

## License
This project is for academic demonstration purposes. Do not use it for commercial or proprietary applications.

---
## **Installation**  

### **1. Clone the repository**  
```sh
git clone https://github.com/sivenvy/NetworkPathMap.git
cd NetworkPathMap
```
### **2. Install dependencies**
Ensure you have Python 3.9+ installed, then run:
```sh
pip install -r requirements.txt
```
### **3. Run the application**
Ensure you have Python 3.9+ installed, then run:
```sh
python NetworkPathMap.py
```
