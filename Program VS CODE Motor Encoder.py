import sys
import time
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QGridLayout, QComboBox
)
from PyQt5.QtCore import QTimer
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import serial
import serial.tools.list_ports

class MainWindow(QWidget):
    def _init_(self):
        super()._init_()
        self.setWindowTitle("Motor PID Control")
        self.setGeometry(100, 100, 1200, 800)

        self.serial_connection = None
        self.timer = QTimer(self)
        self.initUI()
        self.init_serial_ports()

    def initUI(self):
        main_layout = QVBoxLayout()

        # PID Control Layout
        pid_layout = QGridLayout()
        pid_layout.addWidget(QLabel("<b>PID Tuning:</b>"), 0, 0, 1, 2)

        pid_layout.addWidget(QLabel("Kp:"), 1, 0)
        self.kp_input = QLineEdit("0.5")
        pid_layout.addWidget(self.kp_input, 1, 1)

        pid_layout.addWidget(QLabel("Ki:"), 2, 0)
        self.ki_input = QLineEdit("0.0001")
        pid_layout.addWidget(self.ki_input, 2, 1)

        pid_layout.addWidget(QLabel("Kd:"), 3, 0)
        self.kd_input = QLineEdit("0")
        pid_layout.addWidget(self.kd_input, 3, 1)

        pid_layout.addWidget(QLabel("Setpoint (RPM):"), 4, 0)
        self.setpoint_input = QLineEdit("50")
        pid_layout.addWidget(self.setpoint_input, 4, 1)

        self.send_button = QPushButton("Send PID and Setpoint")
        self.send_button.clicked.connect(self.send_pid_setpoint)
        pid_layout.addWidget(self.send_button, 5, 0, 1, 2)

        main_layout.addLayout(pid_layout)

        # Serial Connection Layout
        serial_layout = QGridLayout()
        serial_layout.addWidget(QLabel("<b>Serial Connection:</b>"), 0, 0, 1, 2)

        serial_layout.addWidget(QLabel("Port:"), 1, 0)
        self.serial_port_combo = QComboBox()
        serial_layout.addWidget(self.serial_port_combo, 1, 1)

        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.connect_serial)
        serial_layout.addWidget(self.connect_button, 1, 2)

        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.setEnabled(False)
        self.disconnect_button.clicked.connect(self.disconnect_serial)
        serial_layout.addWidget(self.disconnect_button, 1, 3)

        main_layout.addLayout(serial_layout)

        # Plot Area
        self.plot_canvas = PlotCanvas(self, width=10, height=6)
        main_layout.addWidget(self.plot_canvas)

        self.setLayout(main_layout)

    def init_serial_ports(self):
        """Detect and list available serial ports."""
        ports = serial.tools.list_ports.comports()
        self.serial_port_combo.addItems([port.device for port in ports])

    def connect_serial(self):
        """Connect to the selected serial port."""
        port = self.serial_port_combo.currentText()
        if port:
            try:
                self.serial_connection = serial.Serial(port, 9600, timeout=1)
                self.connect_button.setEnabled(False)
                self.disconnect_button.setEnabled(True)
                self.start_graph_update()
            except serial.SerialException as e:
                print(f"Connection failed: {e}")

    def disconnect_serial(self):
        """Disconnect from the serial port."""
        if self.serial_connection:
            self.serial_connection.close()
            self.serial_connection = None
        self.connect_button.setEnabled(True)
        self.disconnect_button.setEnabled(False)
        self.timer.stop()

    def send_pid_setpoint(self):
        """Send PID values and setpoint to Arduino."""
        if self.serial_connection:
            try:
                kp = float(self.kp_input.text())
                ki = float(self.ki_input.text())
                kd = float(self.kd_input.text())
                setpoint = int(self.setpoint_input.text())

                self.serial_connection.write(f"PID:{kp},{ki},{kd}\n".encode())
                self.serial_connection.write(f"SET:{setpoint}\n".encode())
                print(f"Sent PID: Kp={kp}, Ki={ki}, Kd={kd}, Setpoint={setpoint}")

                self.plot_canvas.set_target_setpoint(setpoint)
            except ValueError:
                print("Invalid PID or Setpoint input. Please enter valid numbers.")

    def start_graph_update(self):
        """Start updating the graph."""
        self.timer.timeout.connect(self.update_graph)
        self.timer.start(100)

    def update_graph(self):
        """Read data from Arduino and update the graph."""
        if self.serial_connection and self.serial_connection.in_waiting > 0:
            try:
                data = self.serial_connection.readline().decode().strip()
                if data.startswith("RPM:"):
                    parts = data.split(",")
                    rpm = float(parts[0].split(":")[1])
                    setpoint = float(parts[1].split(":")[1])
                    error = float(parts[2].split(":")[1])
                    self.plot_canvas.update_plot(rpm, setpoint, error)
            except Exception as e:
                print(f"Error reading data: {e}")

class PlotCanvas(FigureCanvas):
    def _init_(self, parent=None, width=10, height=6):
        fig = Figure(figsize=(width, height))
        self.ax = fig.add_subplot(111)
        super()._init_(fig)
        self.setParent(parent)

        self.x_data = []
        self.rpm_data = []
        self.setpoint_data = []
        self.error_data = []

    def update_plot(self, rpm, setpoint, error):
        """Update the plot with new data."""
        self.x_data.append(time.time())
        self.rpm_data.append(rpm)
        self.setpoint_data.append(setpoint)
        self.error_data.append(error)

        if len(self.x_data) > 100:
            self.x_data.pop(0)
            self.rpm_data.pop(0)
            self.setpoint_data.pop(0)
            self.error_data.pop(0)

        self.ax.clear()
        self.ax.plot(self.x_data, self.rpm_data, label="RPM")
        self.ax.plot(self.x_data, self.setpoint_data, label="Setpoint")
        self.ax.plot(self.x_data, self.error_data, label="Error")
        self.ax.legend(loc="upper left")
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("Values")
        self.draw()

    def set_target_setpoint(self, setpoint):
        """Set the target setpoint for the graph."""
        self.setpoint_data = [setpoint] * len(self.x_data)

if _name_ == "_main_":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())