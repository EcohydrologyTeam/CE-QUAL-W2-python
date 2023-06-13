import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QMessageBox


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Message Dialog Example")
        self.setGeometry(100, 100, 300, 200)

        button = QPushButton("Open Dialog", self)
        button.clicked.connect(self.show_message_dialog)
        button.move(100, 80)

    def show_message_dialog(self):
        message_box = QMessageBox()
        message_box.setWindowTitle("Message Dialog")
        message_box.setText("Hello, World!")
        message_box.exec_()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
