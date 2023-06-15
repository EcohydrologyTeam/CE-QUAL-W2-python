import sys
import PyQt5.QtWidgets as qtw
import PyQt5.QtCore as qtc
import numpy as np


class MyTableWidget(qtw.QTableWidget):
    def __init__(self, parent):
        super().__init__(parent)

    def keyPressEvent(self, event):
        if event.key() == qtc.Qt.Key_Enter or event.key() == qtc.Qt.Key_Return:
            current_row = self.currentRow()
            current_column = self.currentColumn()

            if current_row == self.rowCount() - 1 and current_column == self.columnCount() - 1:
                # Wrap around to the top of the next column
                self.setCurrentCell(0, 0)
            elif current_row < self.rowCount() - 1:
                # Move to the next cell down
                self.setCurrentCell(current_row + 1, current_column)
            else:
                # Move to the top of the next column
                self.setCurrentCell(0, current_column + 1)
        else:
            super().keyPressEvent(event)

class MyApp(qtw.QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('PyQt5 Table Multi-Value Copy-Paste Example')
        self.setGeometry(300, 300, 400, 300)

        # Create a menu bar
        menubar = self.menuBar()

        # Create Edit menu
        edit_menu = menubar.addMenu('Edit')

        # Create Copy action
        copy_action = qtw.QAction('Copy', self)
        copy_action.setShortcut('Ctrl+C')
        copy_action.triggered.connect(self.copy_data)
        edit_menu.addAction(copy_action)

        # Create Paste action
        paste_action = qtw.QAction('Paste', self)
        paste_action.setShortcut('Ctrl+V')
        paste_action.triggered.connect(self.paste_data)
        edit_menu.addAction(paste_action)

        # Set the menu bar on the main window
        self.setMenuBar(menubar)

        # Create a table widget
        self.table_widget = MyTableWidget(self)  # Use custom QTableWidget subclass
        self.table_widget.setColumnCount(10)
        self.table_widget.setRowCount(10)

        self.setCentralWidget(self.table_widget)

        self.show()

    def parse_2x2_array(self, string):
        rows = string.split('\n')
        array = [row.split('\t') for row in rows]
        return np.array(array)

    def copy_data(self):
        selected = self.table_widget.selectedRanges()
        if selected:
            s = ''
            for row in range(selected[0].topRow(), selected[0].bottomRow() + 1):
                for col in range(selected[0].leftColumn(), selected[0].rightColumn() + 1):
                    s += str(self.table_widget.item(row, col).text()) + '\t'
                s = s.strip() + '\n'
            s = s.strip()
            qtw.QApplication.clipboard().setText(s)

    def paste_data(self):
        selected = self.table_widget.selectedRanges()
        if selected:
            s = qtw.QApplication.clipboard().text()
            values = self.parse_2x2_array(s)
            nrows, ncols = values.shape

            top_row = selected[0].topRow()
            left_col = selected[0].leftColumn()

            for i, row in enumerate(range(nrows)):
                row = top_row + i
                for j, col in enumerate(range(ncols)):
                    col = left_col + j
                    self.table_widget.setItem(row, col, qtw.QTableWidgetItem(values[i][j]))


if __name__ == '__main__':
    app = qtw.QApplication(sys.argv)
    my_app = MyApp()
    sys.exit(app.exec_())