"""Application entry point — UI shell only until design + Supabase are ready."""

import sys

from PySide6.QtWidgets import QApplication, QLabel, QMainWindow


class PlaceholderWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Payra")
        self.setMinimumSize(960, 640)
        label = QLabel("Payra — UI design coming next")
        label.setStyleSheet("font-size: 18px; padding: 24px;")
        self.setCentralWidget(label)


def main() -> int:
    app = QApplication(sys.argv)
    window = PlaceholderWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
