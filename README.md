# NetworkPathMap
This is a **network visualization and path analysis tool** built using PyQt6 and Leaflet.js. It allows users to display network nodes, visualize connectivity, compute paths, and interactively analyze circuit data.
![screenshot1](https://github.com/sivenvy/NetworkPathMap/blob/main/NetworkPathMap/screenshots/s1.JPG "gif1")
## Features
- Interactive Map – Displays locations and their connections on a zoomable, draggable map, user can chose map tiles sources from OpenStreetMap or Carto.<br>
- Node-Based and Device-Based Topology – Supports both **location-based** and **device-based** network graphs.<br>
- Path Calculation – Computes all possible paths between selected nodes using DFS.<br>
- Manual Path Design – Allows users to manually select paths and examine circuit details.<br>
- CSV Data Parsing – Reads and filters network circuit data from CSV files.<br>
- Edge and Node Highlighting – Highlights paths and nodes dynamically based on selection.<br>


## Usage

### Interface
- Left Panel: Displays node information and available circuits, **provides node filtering and route calculating operation**.<br>
- Right Panel: Displays an **interactive map** with selectable nodes.<br>
### Graph Modes
- Location-Based Mode (default): Builds topology using site names, useful when designing new physical route.<br>
- Device-Based Mode: Uses equipment serial numbers to ensure **accurate routing design**.<br>
### Path Calculation
1. Select Start & End Points<br>
2. Run Path Calculation (DFS-based)<br>
3. Review & Highlight Routes on the map<br>
### Manual Path Design
1. Enable Manual Path Mode<br>
2. Right-click nodes to construct a custom route<br>
3. Examine available path options<br>
### Protection Path Calculation
- Calculate paths with **different devices/nodes provide working and protection circuit pair** with least cost<br>
### Examine Circuit Detail
- While path is calculated, available circuit will show on item box below segment by segment.<br>
- Select circuit to show circuit detail information.<br>


## Screenshots

### Displays locations and their connections on a zoomable, draggable map.<br>Highlights paths and nodes dynamically based on selection
![screenshot1](https://github.com/sivenvy/NetworkPathMap/blob/main/NetworkPathMap/screenshots/Network%20Path%20Map%202025-02-23%2010-39-21.gif "gif1")
### Path Calculation
![screenshot2](https://github.com/sivenvy/NetworkPathMap/blob/main/NetworkPathMap/screenshots/s2.JPG "gif2")
### Manual Path Design
![screenshot3](https://github.com/sivenvy/NetworkPathMap/blob/main/NetworkPathMap/screenshots/s3.JPG "gif3")
### Working and Protection Path Design
![screenshot4](https://github.com/sivenvy/NetworkPathMap/blob/main/NetworkPathMap/screenshots/s4.JPG "ss1")
### Examine Circuit Detail
![screenshot5](https://github.com/sivenvy/NetworkPathMap/blob/main/NetworkPathMap/screenshots/01.JPG "ss1")

---

## Technologies and Tools Used
This project utilizes the following technologies and tools:

- PyQt6 - A GUI framework for building the interactive interface.
- PyQt6-WebEngine - Enables embedding web content in PyQt6, used for displaying the map.
- [Leaflet.js](https://leafletjs.com/) - A JavaScript mapping library for handling markers, paths, and interactions.
- pandas - Used for reading, filtering, and processing CSV data.
- JavaScript (Frontend) - Works with QWebChannel to enable bidirectional communication between Python and the web interface, handling marker interactions and path visualization.
- [OpenStreetMap](https://www.openstreetmap.org/) - map tiles source and [Carto](https://github.com/gravitystorm/openstreetmap-carto/) style rendering


## License
This project demo is for academic demonstration purposes only.

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
