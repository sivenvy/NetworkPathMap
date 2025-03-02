from asyncio.windows_events import NULL
from collections import defaultdict
from math import e
from msilib.schema import SelfReg
import sys
import os
import csv
import pandas as pd
 
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QSplitter, QLabel, QTextEdit, QPushButton, QTabWidget, QLineEdit, QCheckBox, QVBoxLayout, QScrollArea, QListWidget, QListWidgetItem, QDialog
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import Qt, pyqtSlot, QObject, QUrl
from PyQt6.QtWebChannel import QWebChannel

import subprocess
import time

# 啟動 HTTP 伺服器（如果已經有運行，則不會影響）
def start_http_server():
    try:
        subprocess.Popen(["python", "-m", "http.server", "8000"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1)  # 等待 1 秒讓伺服器啟動
    except Exception as e:
        print(f"❌ 無法啟動 HTTP 伺服器: {e}")

# 調用函式啟動伺服器
start_http_server()





class PyBridge(QObject):
    def __init__(self, window):
        super().__init__()
        self.window = window  # 將主視窗參考存入，方便更新 UI

    @pyqtSlot(str)
    def logMessage(self, message):
        """接收來自 JavaScript 的 log 訊息並顯示在 log_box 中"""
        self.window.append_log(message)  # 在 log_box 中顯示訊息

    @pyqtSlot(str)
    def sendData(self, name):
        """當地圖標記點被點擊時，更新左側 UI"""
        self.window.update_info(name)
        if self.window.bydevice_checkbox.isChecked():
            self.window.show_node_device(name)
            
        
    @pyqtSlot(str, int)
    def sendNode(self, name, target):
        """接收地圖右鍵選單傳送的標記點"""
        self.window.setNode(name,target)
    

    @pyqtSlot(float, float)
    def sendCoordinates(self, lat, lng):
        """接收地圖點擊的經緯度，顯示在操作區的輸入框中"""
        self.window.update_coordinates(lat, lng)

    @pyqtSlot()
    def addMarker(self):
        #暫時取消使用者編輯地點，棄用
        """將新地點存入 locations.csv，並刷新 UI"""
        name = self.window.name_input.text().strip()
        if name and self.window.coord_display.text():
            lat, lng = self.window.coord_display.text().split(", ")
            lat = float(lat.split(": ")[1])
            lng = float(lng.split(": ")[1])

            # 讀取現有 locations.csv
            try:
                df = pd.read_csv("locations.csv", encoding="utf-8")
            except FileNotFoundError:
                df = pd.DataFrame(columns=["地點", "Lat", "Lng"])  # 若文件不存在，創建新表

            # 確保地點名稱不重複
            if name not in df["地點"].values:
                new_entry = pd.DataFrame([[name, lat, lng]], columns=["地點", "Lat", "Lng"])
                df = pd.concat([df, new_entry], ignore_index=True)
                df.to_csv("locations.csv", index=False, encoding="utf-8")
                print(f"✅ 已新增地點: {name} ({lat}, {lng})")
            else:
                print(f"⚠️ 地點 {name} 已存在，未新增")

            # 刷新 UI
            self.window.refresh_locations()
            
    @pyqtSlot(list)
    def sendEdges(self, edges):
        """傳送邊的端點給 JavaScript"""
        self.window.web_view.page().runJavaScript(f"drawEdges({edges});")
        
        
    @pyqtSlot()
    def clearEdges(self):
        """通知 JavaScript 清除所有已繪製的線條"""
        self.window.web_view.page().runJavaScript("clearEdges();")


class MapApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Map Application")
        self.setGeometry(100, 100, 1200, 800)
        
        # 建立主視窗
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # 分割視窗
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # 左側區域（Tab 介面）
        self.tabs = QTabWidget()
        
        # 第一個 Tab（顯示標記資訊）
        self.tab1 = QWidget()
        self.tab1_layout = QVBoxLayout()
        
        # 在 Tab1 內新增「顯示電路」Checkbox
        self.show_edges_checkbox = QCheckBox("在地圖上顯示電路")
        self.show_edges_checkbox.stateChanged.connect(self.toggle_edges)
        self.tab1_layout.addWidget(self.show_edges_checkbox)


        # **地點資訊（scroll_area）**
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        self.checkbox_layout = QVBoxLayout(scroll_widget)

        scroll_area.setWidget(scroll_widget)
        self.tab1_layout.addWidget(scroll_area)

        
        # 創建純文字區域
        self.info_box = QListWidget()
        self.info_box.setSelectionMode(QListWidget.SelectionMode.SingleSelection)

        # 把勾選框區域和文字區域加入 Tab1
        self.tab1_layout.addWidget(self.info_box)     # 這裡顯示文字
        self.tab1.setLayout(self.tab1_layout)
        self.tabs.addTab(self.tab1, "資訊")
        
        # 讀取 CSV 資料並顯示
        self.location_data = {}
        self.load_location_data()
        
        #--------------#
        #  變數存放區  #
        #--------------#
        self.filtered_ptn_data = pd.DataFrame()  # ✅ 存放篩選後的 PTN 資料
        self.selected_name = None  # ✅ 用來存取點擊的地圖標記名稱
        self.highlighted_node = [] #存放highlighted marker
        self.last_selected_name = None #用來復原highlight的edge
        #self.selected_neighbor = []  # ✅ 存取點擊的地圖標記的相鄰節點
        self.highlighted_edges = [] #存取計算路徑後存於path_list使用者選取的路徑，用來highlight以及顯示可用選實體電路
        self.manual_path_active = False
        self.selected_manual_path = []
        self.graph = {}
        self.device_to_location = {}
        self.location_to_devices = defaultdict(set)

        # 第二個 Tab（按鈕、標記名稱輸入框與顯示座標的輸入框）
        self.tab2 = QWidget()
        self.tab2_layout = QVBoxLayout()        
        
        # 🔹 建立水平佈局
        start_end_layout = QHBoxLayout()
        # 🔹 起點 / 終點 文字方塊
        self.start_label = QLabel("起點:")
        self.start_input = QLineEdit()
        self.start_input.setReadOnly(True)  # 只讀模式
        self.end_label = QLabel("終點:")
        self.end_input = QLineEdit()
        self.end_input.setReadOnly(True)  # 只讀模式
        # 🔹 加入到水平方向佈局
        start_end_layout.addWidget(self.start_label)
        start_end_layout.addWidget(self.start_input)
        start_end_layout.addWidget(self.end_label)
        start_end_layout.addWidget(self.end_input)
        # 🔹 新增到 tab2
        self.tab2_layout.addLayout(start_end_layout)  #  加入主布局
        
        node_device_layout = QHBoxLayout()
        self.A_device_list = QListWidget()
        self.A_device_list.setMaximumHeight(100)
        self.A_device_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)  # 設定只能選一行
        self.A_device_list.itemClicked.connect(self.A_device_selected)  # 點擊事件
        self.A_device_list.setVisible(False)  #  預設隱藏
        self.B_device_list = QListWidget()
        self.B_device_list.setMaximumHeight(100)
        self.B_device_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)  # 設定只能選一行
        self.B_device_list.itemClicked.connect(self.B_device_selected)  # 點擊事件
        self.B_device_list.setVisible(False)  #  預設隱藏
        node_device_layout.addWidget(self.A_device_list)
        node_device_layout.addWidget(self.B_device_list)
        self.tab2_layout.addLayout(node_device_layout)  #  加入主布局
        

        node_device_mode_layout = QHBoxLayout()
        self.bynode_checkbox = QCheckBox("根據機房計算")
        self.bydevice_checkbox = QCheckBox("根據設備計算")
        self.bynode_checkbox.stateChanged.connect(self.disable_bydevice)
        self.bydevice_checkbox.stateChanged.connect(self.disable_bynode)
        self.bynode_checkbox.setChecked(True)
        self.bydevice_checkbox.setChecked(False)
        node_device_mode_layout.addWidget(self.bynode_checkbox)
        node_device_mode_layout.addWidget(self.bydevice_checkbox)
        self.tab2_layout.addLayout(node_device_mode_layout)  #  加入主布局
        
        self.manual_path_checkbox = QCheckBox("手動設計")
        self.manual_path_checkbox.stateChanged.connect(self.toggle_manual_path_mode)
        self.tab2_layout.addWidget(self.manual_path_checkbox)


        self.button_path = QPushButton("計算路由")
        self.tab2_layout.addWidget(self.button_path)
        # 顯示路由區域
        path_list_label_layout = QHBoxLayout()
        self.path_list_label = QLabel("可用路徑")
        self.two_path_checkbox = QCheckBox("計算最佳雙路由")
        path_list_label_layout.addWidget(self.path_list_label)
        path_list_label_layout.addWidget(self.two_path_checkbox)
        self.tab2_layout.addLayout(path_list_label_layout)
        self.path_list = QListWidget()
        self.path_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)  # ✅ 設定只能選一行
        self.path_list.itemClicked.connect(self.on_path_selected)  # ✅ 綁定點擊事件
        self.tab2_layout.addWidget(self.path_list) #  加入主布局
        
        #可用電路資料顯示區
        self.circuit_list_label = QLabel("路徑可用電路")
        self.tab2_layout.addWidget(self.circuit_list_label)
        self.circuit_list = QListWidget()
        self.circuit_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)  # ✅ 設定只能選一行
        self.circuit_list.itemClicked.connect(self.show_circuit_details)  # ✅ 綁定點擊事件
        self.tab2_layout.addWidget(self.circuit_list)

        # 新增標記區
        """
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("輸入標記名稱")
        self.button1 = QPushButton("新增標記")
        self.coord_display = QLineEdit()
        self.coord_display.setReadOnly(True)  # 只讀模式
        self.tab2_layout.addWidget(self.name_input)
        self.tab2_layout.addWidget(self.button1)
        self.tab2_layout.addWidget(self.coord_display)  # 添加座標顯示框
        """
        self.tab2.setLayout(self.tab2_layout)
        self.tabs.addTab(self.tab2, "操作")
        


        
        # 第三個 Tab（顯示JavaScript等log）
        self.tab3 = QWidget()
        self.tab3_layout = QVBoxLayout()
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.tab3_layout.addWidget(self.log_box)
        self.tab3.setLayout(self.tab3_layout)
        self.tabs.addTab(self.tab3, "Log")
        
        splitter.addWidget(self.tabs)
        
        # 右側（顯示地圖）
        self.web_view = QWebEngineView()
        self.load_local_map()
        splitter.addWidget(self.web_view)

        # 設定初始比例
        splitter.setSizes([300, 900])

        # 設置 WebChannel 來與 JavaScript 溝通
        self.channel = QWebChannel()
        self.bridge = PyBridge(self)  # ✅ 把 MapApp 本身傳入 PyBridge
        self.channel.registerObject("pybridge", self.bridge)
        self.web_view.page().setWebChannel(self.channel)

        
        # 按鈕點擊事件
        self.button_path.clicked.connect(self.dfs)
        #self.button1.clicked.connect(self.bridge.addMarker)
        # 建立機房-設備對應
        self.build_lacation_device_list()




    def load_local_map(self):
        """載入本地 HTML 內容"""
        self.web_view.setUrl(QUrl("http://localhost:8000/map.html"))


    def refresh_locations(self):
        #暫時取消使用者編輯地點，棄用
        """重新載入 locations.csv，更新 Checkbox"""
        # 清除現有的 Checkbox
        for i in reversed(range(self.checkbox_layout.count())):
            widget = self.checkbox_layout.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)

        self.location_data.clear()  # 清空原本的地點資料

        # 重新載入地點
        self.load_location_data()

    def toggle_all_checkboxes(self, state):
        """勾選/取消所有地點的 Checkbox"""
        check = state
        #print(check)

        # **確保至少有一個 Checkbox，避免錯誤**
        if not self.location_data:
            return  

        #block_signals = True  # **避免重複觸發 stateChanged**
        for checkbox in self.location_data.keys():
            checkbox.blockSignals(True)  # 暫時停用信號
            checkbox.setChecked(check)   # 設定勾選狀態
            checkbox.blockSignals(False) # 恢復信號
        self.on_checkbox_state_changed()


    def load_location_data(self):
        """讀取 CSV 檔案，並顯示地點資訊（帶「全選」Checkbox）"""
        csv_file = "locations.csv"

        # **清除現有的 Checkbox**
        for i in reversed(range(self.checkbox_layout.count())):
            self.checkbox_layout.itemAt(i).widget().setParent(None)
        
        self.location_data.clear()  # 確保不會重複添加 Checkbox

        # **新增「全選地點」Checkbox**
        self.select_all_checkbox = QCheckBox("全選地點")
        self.select_all_checkbox.stateChanged.connect(self.toggle_all_checkboxes)
        self.checkbox_layout.addWidget(self.select_all_checkbox)

        # **讀取 locations.csv，並顯示地點 Checkbox**
        if os.path.exists(csv_file):
            with open(csv_file, "r", encoding="utf-8") as file:
                reader = csv.reader(file)
                next(reader)  # 跳過標題行
                for row in reader:
                    name, lat, lng = row
                    checkbox = QCheckBox(f"{name} (Lat: {lat}, Lng: {lng})")
                    checkbox.setChecked(False)  # 預設不選中
                    checkbox.stateChanged.connect(self.on_checkbox_state_changed)  # 當狀態改變時觸發
                    self.checkbox_layout.addWidget(checkbox)
                    self.location_data[checkbox] = {'name': name, 'lat': lat, 'lng': lng}
        else:
            self.checkbox_layout.addWidget(QLabel("⚠️ 無法找到 CSV 檔案"))


    def build_lacation_device_list(self):
        
        csv_file = "PTNGES.csv"  # 這是你的 .csv 檔案

        if not os.path.exists(csv_file):
            print("⚠️ 找不到 xxxxptn.csv")
            self.filtered_ptn_data = pd.DataFrame()  # 清空暫存資料
            return  

        # 讀取 CSV
        df = pd.read_csv(csv_file, encoding="utf-8")
        print("Loaded PTN csv")
        for _, row in df.iterrows():
            A, B = row["A地點"], row["B地點"]
            A_dev = row["A設備流水號"]
            B_dev = row["B設備流水號"]

            # ✅ 生成設備節點名稱
            A_node = f"{A}-{A_dev}"
            B_node = f"{B}-{B_dev}"

            # ✅ 設備對應地點記錄
            self.device_to_location[A_node] = A
            self.device_to_location[B_node] = B
            self.location_to_devices[A].add(A_node)
            self.location_to_devices[B].add(B_node)
            print("📌 設備對應機房:", self.device_to_location)


    def on_checkbox_state_changed(self):
        """當勾選框的狀態改變時，通知 JavaScript 新增或移除標記"""
        for checkbox, location in self.location_data.items():
            if checkbox.isChecked():
                # 當勾選框被選中時，通知 JavaScript
                self.web_view.page().runJavaScript(f"addMarker({location['lat']}, {location['lng']}, '{location['name']}');")
            else:
                # 當勾選框被取消選中時，移除標記
                self.web_view.page().runJavaScript(f"removeMarker('{location['name']}');") 
        
        # **重新載入符合的 PTN 資料**
        #若勾選頻繁變動會導致多次重覆讀取PTN.csv,每次讀取都會篩選一次AB地點，cost相當大        
        self.load_selected_ptn_data()
    
    def update_info(self, name):
        """更新左側 UI 顯示資訊，並 Highlight 相鄰地點"""
        self.selected_name = name  # ✅ 儲存標記名稱
        

        #if self.selected_neighbor:# 先復原之前highlight的edge
        for edge in self.highlighted_edges:
            start_node, end_node = edge
            self.change_edges(start_node, end_node )  # ✅ 恢復成預設色
        for node in self.highlighted_node:
            self.change_markers(node)
        self.highlighted_node.clear()
        if self.last_selected_name == name:
            self.last_selected_name = None
            return
            

        # 取得篩選後的結果
        filtered_result = self.filter_ptn_by_selected_name()

        if filtered_result is not None and not filtered_result.empty:
            connected_locations = set(filtered_result["A地點"]).union(set(filtered_result["B地點"]))
            connected_locations.discard(self.selected_name)  # ✅ 移除自己
            result_text = "\n".join(connected_locations)
        else:
            connected_locations = []
            result_text = "⚠️ 無對應的 PTN 資料"

        # ✅ 更新 info_box
        self.info_box.clear()    
        self.info_box.addItem(f"選取的地點:{name}")
        self.info_box.addItem(result_text)
        self.info_box.addItem(f"地點設備清單:")
        devices = sorted(self.location_to_devices[name])
        for device in devices:
            self.info_box.addItem(device)  


        # ✅ 傳送 Highlight 指令到 HTML
                
        self.last_selected_name=name
        self.highlighted_edges.clear()    
        selected_neighbor = list(connected_locations)
        for neighbor in selected_neighbor:
            #node
            self.change_markers(neighbor,"highlightIcon")
            self.highlighted_node.append(neighbor)
            #edge
            self.change_edges(name, neighbor, "red")
            self.highlighted_edges.append((name, neighbor))  #記錄高亮邊
            

    def show_node_device(self, name):
        print(name)
            

    def change_markers(self, node, icon="Default"):
        #icon:"Default", "highlightIcon"
        self.web_view.page().runJavaScript(f"highlightMarkers('{node}', icon='{icon}');")
            

    def setNode(self, name, target):
        """更新操作區顯示的座標資訊"""
        if target == 1 :
            self.start_input.setText(f"{name}")
            self.log_box.append(f"{name}設為起點")
            if self.bydevice_checkbox.isChecked() and name in self.location_to_devices:
                self.A_device_list.clear()
                devices = sorted(self.location_to_devices[name])
                for device in devices:
                    self.A_device_list.addItem(device)  
        elif target == 2 :
            self.end_input.setText(f"{name}")
            self.log_box.append(f"{name}設為終點")
            if self.bydevice_checkbox.isChecked() and name in self.location_to_devices:
                self.B_device_list.clear()
                devices = sorted(self.location_to_devices[name])
                for device in devices:
                    self.B_device_list.addItem(device)  
        elif target == 3 :
            self.addManualPath(name)
            self.log_box.append(f"手動路徑新增:{name}")
            
    def A_device_selected(self, item):
        self.start_input.setText(item.text())
        
    def B_device_selected(self, item):
        self.end_input.setText(item.text())
            
    
    def update_coordinates(self, lat, lng):
        """更新操作區顯示的座標資訊"""
        self.coord_display.setText(f"Lat: {lat}, Lng: {lng}")
        

    
    def load_selected_ptn_data(self):
        """根據使用者勾選的地點，篩選 xxxxptn.csv 內符合的資料"""
        self.selected_locations = [data["name"] for checkbox, data in self.location_data.items() if checkbox.isChecked()]
        self.graph = {}  # 初始化 graph 結構

        if not self.selected_locations:
            print("⚠️ 沒有選取任何地點")
            self.filtered_ptn_data = pd.DataFrame()  # 清空暫存資料
            return  

        csv_file = "PTNGES.csv"  # 這是你的 .csv 檔案

        if not os.path.exists(csv_file):
            print("⚠️ 找不到 xxxxptn.csv")
            self.filtered_ptn_data = pd.DataFrame()  # 清空暫存資料
            return  

        # 讀取 CSV
        df = pd.read_csv(csv_file, encoding="utf-8")
        print("Loaded csv")
        
        #-------------------------------#
        # 在此可新增過濾特定電路資料 df #
        #-------------------------------#
        
        # 篩選 A地點 或 B地點 包含選取的地點
        filtered_df = df[(df["A地點"].isin(self.selected_locations)) | (df["B地點"].isin(self.selected_locations))]

        # 存入程式內供後續使用
        self.filtered_ptn_data = filtered_df
        print(f"✅ 已篩選出 {len(filtered_df)} 筆符合的資料")

        self.build_graph()  # ✅ 建立 graph 結構
        

    def build_graph(self):
        """根據 selected_checkbox 來決定建立機房拓樸 or 設備拓樸"""
        self.graph = {}  # 清空舊 graph
        selected_set = set(self.selected_locations)  # ✅ 加速查詢

        if self.bynode_checkbox.isChecked():
            print("🟢 根據機房計算")
            self.build_graph_by_node(selected_set)
        elif self.bydevice_checkbox.isChecked():
            print("🔵 根據設備計算")
            self.build_graph_by_device(selected_set)

        if self.show_edges_checkbox.isChecked():
            self.toggle_edges()  # ✅ 如果勾選顯示 edge，就更新


    def build_graph_by_node(self, selected_set):
        """根據on_checkbox_state_changed -> load_selected_ptn_data -> filtered_ptn_data 建立 graph"""


        for _, row in self.filtered_ptn_data.iterrows():  # 使用 .iterrows() 正確讀取 DataFrame
            A, B = row["A地點"], row["B地點"]

            #  確保 A 和 B 都在 selected_locations
            if A in selected_set and B in selected_set:
                if A not in self.graph:
                    self.graph[A] = set()
                if B not in self.graph:
                    self.graph[B] = set()

                #  避免重複加入相同的邊
                self.graph[A].add(B)
                self.graph[B].add(A)

        print("Graph 建立完成:", self.graph)  # Debug 用
        if self.show_edges_checkbox.isChecked():
            self.toggle_edges() #若有勾選顯示edge 更新edge
            
            
    def build_graph_by_device(self, selected_set):
        """根據 A設備流水號 - B設備流水號 建立設備拓樸"""
        #self.device_to_location = {}  # ✅ 設備對應機房名稱

        # **確保 graph 初始化**
        self.graph = {}

        for _, row in self.filtered_ptn_data.iterrows():
            A, B = row["A地點"], row["B地點"]
            A_dev = row["A設備流水號"]
            B_dev = row["B設備流水號"]

            # ✅ 生成設備節點名稱
            A_node = f"{A}-{A_dev}"
            B_node = f"{B}-{B_dev}"


            # ✅ 確保 graph 內有這些節點
            if A in selected_set and B in selected_set:
                if A_node not in self.graph:
                    self.graph[A_node] = set()
                if B_node not in self.graph:
                    self.graph[B_node] = set()

                # ✅ 建立雙向連結
                self.graph[A_node].add(B_node)
                self.graph[B_node].add(A_node)

        print("✅ 設備拓樸建立完成:", self.graph)

        if self.show_edges_checkbox.isChecked():
            self.toggle_edges() #若有勾選顯示edge 更新edge
            
    def toggle_edges(self):
        """將所有邊的端點傳送到 JavaScript"""
        if self.show_edges_checkbox.isChecked():
            edges = set()

            for node, neighbors in self.graph.items():
                for neighbor in neighbors:
                    # **如果是設備模式，轉換為機房名稱**
                    node_name = self.device_to_location.get(node, node)  # ✅ 預設回傳 node 本身
                    neighbor_name = self.device_to_location.get(neighbor, neighbor)  

                    edge = tuple(sorted([node_name, neighbor_name]))  
                    edges.add(edge)

            edges_list = [list(edge) for edge in edges]
            print("✅ 傳送邊:", edges_list)
            self.bridge.sendEdges(edges_list)  
        else:
            self.bridge.clearEdges()
            
    def change_edges(self, startNode, endNode, color="lightgray", weight= 2, opacity= 0.7, smoothFactor= 1.5):
        # Default: color: 'lightgray', weight: 2, opacity: 0.7, smoothFactor: 1.5
        self.web_view.page().runJavaScript(f"changeEdge('{startNode}', '{endNode}', '{color}', {weight}, {opacity}, {smoothFactor});")

            
    def filter_ptn_by_selected_name(self):
        """根據 self.selected_name，從 self.filtered_ptn_data 內篩選資料"""
        if self.selected_name is None:
            print("⚠️ 尚未選取地圖上的標記點")
            return pd.DataFrame()

        if self.filtered_ptn_data.empty:
            print("⚠️ 無篩選的 PTN 資料")
            return pd.DataFrame()

        # 篩選符合 selected_name 的資料
        filtered_result = self.filtered_ptn_data[
            (self.filtered_ptn_data["A地點"] == self.selected_name) | 
            (self.filtered_ptn_data["B地點"] == self.selected_name)
        ]

        if filtered_result.empty:
            print(f"⚠️ 找不到 {self.selected_name} 對應的 PTN 資料")
        else:
            print(f"✅ 找到 {len(filtered_result)} 筆符合的 PTN 資料")
        
        return filtered_result  # ✅ 回傳篩選結果
    

    def find_all_paths(self, start, end, path=None, max_depth=10):
        """使用 DFS 找出所有從 start 到 end 的不重複路徑，並限制最大搜尋深度"""
        if path is None:
            path = [start]

        if len(path) > max_depth:  # ✅ 限制搜尋深度
            return []

        if start == end:
            return [path]

        if start not in self.graph:
            return []

        paths = []
        for neighbor in self.graph[start]:
            if neighbor not in path:  # ✅ 確保不走回頭路
                new_paths = self.find_all_paths(neighbor, end, path + [neighbor], max_depth)
                paths.extend(new_paths)

        return paths
    
    def find_two_disjoint_paths(self,all_paths):
        """
        從 `all_paths` 中找出兩條「中間節點不重複」的最佳路徑，使總共經過的節點數最少。
        :param all_paths: list of list (所有找到的路徑)
        :return: (list, list) - 兩條不重複的最佳路徑
        """
        if len(all_paths) < 2:
            print("⚠️ 無法找到兩條不重複的路徑")
            return None, None

        best_pair = None
        min_total_nodes = float("inf")

        # 遍歷所有可能的第一條路徑
        for i in range(len(all_paths)):
            path_1 = all_paths[i]
            core_1 = set(path_1[1:-1])  # 取中間節點（排除起點與終點）

            # 遍歷可能的第二條路徑
            for j in range(i + 1, len(all_paths)):
                path_2 = all_paths[j]
                core_2 = set(path_2[1:-1])  # 取中間節點（排除起點與終點）

                overlap = len(core_1 & core_2)  # 計算中間節點的重疊數量
                total_nodes = len(set(path_1) | set(path_2))  # 計算總節點數（降低成本）

                # ✅ 選擇完全不重複的最佳組合
                if overlap == 0 and total_nodes < min_total_nodes:
                    best_pair = (path_1, path_2)
                    min_total_nodes = total_nodes

        if best_pair:
            print(f"✅ 找到兩條最佳路徑（中間節點不重複）:")
            print(f"  路徑 1: {' → '.join(best_pair[0])}")
            print(f"  路徑 2: {' → '.join(best_pair[1])}")
            return best_pair
        else:
            print("⚠️ 找不到完全不重複的兩條路徑，可能需要放寬條件")
            return None, None
    
    def dfs(self):
        # 執行 DFS 搜尋 A → E 的所有路徑
        all_paths = self.find_all_paths(self.start_input.text(),self.end_input.text())
        sorted_paths = sorted(all_paths, key=len)
        

        self.path_list.clear()  # 清除舊的內容
        # 輸出結果
        if self.two_path_checkbox.isChecked():
            path_1, path_2 = self.find_two_disjoint_paths(all_paths)
            if path_1 and path_2:
                self.path_list.addItem(QListWidgetItem(f"最佳路徑 1: {' → '.join(path_1)}"))
                self.path_list.addItem(QListWidgetItem(f"最佳路徑 2: {' → '.join(path_2)}"))
                self.path_list.addItem(f"其他路徑: ")
            else:
                self.path_list.addItem(f"⚠️ 無法找到完全不重複的兩條路徑")
        for i, path in enumerate(sorted_paths, 1):
            item = QListWidgetItem(f"路徑 {i}: {' → '.join(path)}")
            self.path_list.addItem(item)  # 新增到 QListWidget
            

    def disable_bydevice(self):
        """確保只能勾選其中一個 CheckBox"""
        if self.bynode_checkbox.isChecked():
            self.bydevice_checkbox.setChecked(False)
        self.A_device_list.setVisible(False)
        self.B_device_list.setVisible(False)
        self.load_selected_ptn_data()
            
    def disable_bynode(self):
        if self.bydevice_checkbox.isChecked():
            self.bynode_checkbox.setChecked(False)  
        self.A_device_list.setVisible(True)
        self.B_device_list.setVisible(True)
        self.load_selected_ptn_data()

    def toggle_manual_path_mode(self):
        """開啟或關閉手動路徑模式"""
        self.manual_path_active = Qt.CheckState.Checked
        if self.manual_path_active:
            print("進入手動路徑模式")
            self.manual_path_active = True
            #self.path_list.addItem("手動路徑:")  # 顯示手動模式標題
        else:
            print("關閉手動路徑模式")
            self.manual_path_active = False
            self.selected_manual_path.clear()
            self.path_list.clear()  # 清除手動模式的內容


    
    def addManualPath(self, node):
        """加入手動設計的路徑，並更新唯一顯示的 `path_list` 內容"""
        if not self.manual_path_active:
            print("⚠️ 手動設計模式未開啟，無法加入路徑")
            return

        # **如果是第一個節點，直接設為起點**
        if not self.selected_manual_path:
            self.selected_manual_path = [node]
        else:
            last_node = self.selected_manual_path[-1]

            # **檢查是否有 `edge` 相連**
            if node in self.graph.get(last_node, set()):
                self.selected_manual_path.append(node)
                print(f"✅ 加入手動路徑: {' → '.join(self.selected_manual_path)}")
            
                # **標記該路徑**
                self.change_edges(last_node, node, "blue")
            else:
                print(f"⚠️ {last_node} 和 {node} 之間沒有路徑，無法加入")
                return  # **不更新 UI**

        # **更新 `path_list`，只維持一個 item**
        updated_text = f"手動路徑: {' → '.join(self.selected_manual_path)}"
    
        if self.path_list.count() == 0:
            self.path_list.addItem(updated_text)  # **初次加入**
        else:
            self.path_list.item(0).setText(updated_text)  # **更新唯一 item**
            

    def on_path_selected(self, item):
        """當使用者點選某個路徑時，變更顏色並恢復上次高亮的邊"""
        selected_path = item.text()  # 取得被選中的路徑
        print(f"選取的路徑: {selected_path}")

        # 解析路徑名稱，取得節點列表
        self.path_nodes = selected_path.split(": ")[1].split(" → ")
        if self.bydevice_checkbox.isChecked():
            #self.path_nodes若在此因機房模式做處理後續會遺失設備資料，nodes在此給highlight相關功能使用
            nodes = [self.device_to_location.get(node, node) for node in self.path_nodes]
        else :
            nodes= self.path_nodes
        # 🔹 **先恢復舊的高亮邊為預設顏色**
        # 🔹 **清空已高亮的邊及標記點**
        for edge in self.highlighted_edges:
            start_node, end_node = edge
            self.change_edges(start_node, end_node, "lightgray")  # ✅ 恢復成預設色
        self.highlighted_edges.clear()
        
        for node in self.highlighted_node:
            self.change_markers(node)
        self.highlighted_node.clear()

        # 🔹 **標記新的高亮邊及標記點**
        selected_neighbor=[]
        selected_neighbor.append(nodes[0])
        for i in range(len(nodes) - 1):
            start_node = nodes[i]
            end_node = nodes[i + 1]
            selected_neighbor.append(end_node)
            self.change_edges(start_node, end_node, "red")  # ✅ 標記新路徑
            self.highlighted_edges.append((start_node, end_node))  # ✅ 記錄高亮邊
        #self.web_view.page().runJavaScript(f"highlightMarkers({self.selected_neighbor});")
        for neighbor in selected_neighbor:
            #node
            self.change_markers(neighbor,"highlightIcon")
            self.highlighted_node.append(neighbor)
            

        """當點擊手動路徑時，開始篩選對應的電路"""
        if not self.path_nodes or len(self.path_nodes) < 2:
            print("⚠️ 手動路徑長度不足，無法篩選電路")
            return

        print(f"🔍 開始篩選電路 for {item.text()}")
        self.filter_circuits_by_selected_path()  #  開始篩選
        

    def filter_circuits_by_selected_path(self):
        """根據 `path_list` 內的路徑篩選對應的電路，並分段儲存"""
        if not self.path_nodes or len(self.path_nodes) < 2:
            print("⚠️ 路徑長度不足，無法篩選電路")
            return

        self.selected_circuit_data = {}  # ✅ 用 dict 儲存每段路徑的電路資料

        # 取得所有 (start, end) 邊
        path_edges = [(self.path_nodes[i], self.path_nodes[i + 1]) 
                      for i in range(len(self.path_nodes) - 1)]

        # **判斷是否使用設備模式**
        use_device_mode = self.bydevice_checkbox.isChecked()

        # 逐段篩選電路
        for idx, (start, end) in enumerate(path_edges):
            if use_device_mode:
                # **設備模式：拆分 "地點-設備流水號"**
                start_loc, start_dev = start.split("-")
                end_loc, end_dev = end.split("-")
                print(f"{start_loc},{start_dev}")
                print(f"{end_loc},{end_dev}")
                print(f"------------")
                # **根據 A設備/B設備 進行篩選**
                filtered_circuits = self.filtered_ptn_data[
                    self.filtered_ptn_data.apply(
                        lambda row: ((row["A地點"] == start_loc and str(row["A設備流水號"]) == start_dev and 
                                      row["B地點"] == end_loc and str(row["B設備流水號"]) == end_dev) or
                                     (row["B地點"] == start_loc and str(row["B設備流水號"]) == start_dev and 
                                      row["A地點"] == end_loc and str(row["A設備流水號"]) == end_dev)),
                        axis=1
                    )
                ]
            else:
                # **機房模式：直接根據 A地點/B地點 進行篩選**
                filtered_circuits = self.filtered_ptn_data[
                    self.filtered_ptn_data.apply(
                        lambda row: (row["A地點"], row["B地點"]) == (start, end) or 
                                    (row["B地點"], row["A地點"]) == (start, end),
                        axis=1
                    )
                ]

            # **儲存到 dict（索引對應路徑段）**
            print(filtered_circuits)
            print(f"------------")    
            self.selected_circuit_data[idx] = {
                "edge": f"{start} → {end}",
                "circuits": filtered_circuits
            }

        print(f"✅ 已篩選出 {len(self.selected_circuit_data)} 段電路")
        # ✅ 更新 UI
        self.display_filtered_circuits()

    

    def display_filtered_circuits(self):
        """在 UI 顯示分段電路資訊"""
        self.circuit_list.clear()  # **清空現有列表**

        if not self.selected_circuit_data:
            self.circuit_list.addItem("⚠️ 無可用電路")
            return

        for idx, data in self.selected_circuit_data.items():
            edge = data["edge"]
            circuits = data["circuits"]

            # **顯示段落標題**
            self.circuit_list.addItem(f"🛤 {edge}:")

            # **顯示該段的電路**
            if circuits.empty:
                self.circuit_list.addItem("⚠️ 無可用電路")
            else:
                for _, row in circuits.iterrows():
                    self.circuit_list.addItem(f"  {row['線路名稱']}") 
                    

    def show_circuit_details(self, item):
        """當使用者點選某個電路時，顯示詳細資訊視窗"""
        circuit_name = item.text().strip()  # 取得選擇的電路名稱
        print(f"選擇的電路: {circuit_name}")

        # **在 self.selected_circuit_data 中找到該電路的詳細資訊**
        details = None
        for circuit_data in self.selected_circuit_data.values():
            for _, row in circuit_data["circuits"].iterrows():
                if row["線路名稱"] == circuit_name:  # ✅ 確保對應正確的電路
                    details = row
                    break
            if details is not None:
                break

        if details is None:
            print("⚠️ 找不到對應的電路資訊")
            return

        # **創建新視窗**
        dialog = QDialog(self)
        dialog.setWindowTitle(f"電路詳細資訊 - {circuit_name}")
        dialog.setGeometry(200, 200, 400, 300)  # 設定視窗大小
        layout = QVBoxLayout()

        # **顯示詳細資訊**
        for column in details.index:
            layout.addWidget(QLabel(f"{column}: {details[column]}"))

        # **加入關閉按鈕**
        close_btn = QPushButton("關閉")
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)

        dialog.setLayout(layout)
        dialog.exec()  # **顯示對話框**



    def append_log(self, message):
        """接收來自 JavaScript 的 log 訊息並顯示在 log_box 中"""
        self.log_box.append(message)  # 在 log_box 中顯示訊息

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MapApp()
    window.show()
    sys.exit(app.exec())
