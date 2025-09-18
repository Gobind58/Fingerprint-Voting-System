import sys
from PyQt5 import QtWidgets, QtCore
import db
from fingerprint import FingerprintSensor

class LoginView(QtWidgets.QWidget):
    def __init__(self, sensor: FingerprintSensor):
        super().__init__()
        self.sensor = sensor
        self.setWindowTitle("Fingerprint Voting System — Login")
        self.port = QtWidgets.QLineEdit("COM3")  # or /dev/ttyUSB0
        self.connect_btn = QtWidgets.QPushButton("Connect Sensor")
        self.scan_btn = QtWidgets.QPushButton("Scan Finger")
        self.status = QtWidgets.QLabel("Not connected")

        lay = QtWidgets.QVBoxLayout(self)
        lay.addWidget(QtWidgets.QLabel("Sensor Port:"))
        lay.addWidget(self.port)
        lay.addWidget(self.connect_btn)
        lay.addWidget(self.scan_btn)
        lay.addWidget(self.status)

        self.connect_btn.clicked.connect(self.connect_sensor)
        self.scan_btn.clicked.connect(self.scan)

    def connect_sensor(self):
        try:
            self.sensor.connect(self.port.text())
            count = self.sensor.get_template_count()
            self.status.setText(f"Connected. Templates: {count}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", str(e))

    def scan(self):
        if not self.sensor.fp:
            QtWidgets.QMessageBox.warning(self, "Warning", "Connect sensor first")
            return
        self.status.setText("Waiting for finger...")
        QtWidgets.QApplication.processEvents()
        try:
            match = None
            while match is None:
                QtWidgets.QApplication.processEvents()
                match = self.sensor.search()
            user = db.get_user_by_finger(match)
            if not user:
                QtWidgets.QMessageBox.information(self, "Unknown", f"No user linked to finger ID {match}")
                return
            user_id, name, is_admin = user
            if is_admin:
                self.open_admin()
            else:
                self.open_voter(user_id, name)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", str(e))

    def open_admin(self):
        self.aw = AdminView(self.sensor)
        self.aw.show()

    def open_voter(self, user_id, name):
        self.vw = VoterView(user_id, name)
        self.vw.show()

class VoterView(QtWidgets.QWidget):
    def __init__(self, user_id, name):
        super().__init__()
        self.user_id = user_id
        self.setWindowTitle(f"Welcome {name} — Cast Your Vote")
        self.party_group = QtWidgets.QButtonGroup(self)
        self.vote_btn = QtWidgets.QPushButton("Cast Vote")
        self.status = QtWidgets.QLabel("")
        lay = QtWidgets.QVBoxLayout(self)
        lay.addWidget(QtWidgets.QLabel("Select a party:"))
        for pid, pname in db.list_parties():
            rb = QtWidgets.QRadioButton(pname)
            self.party_group.addButton(rb, pid)
            lay.addWidget(rb)
        lay.addWidget(self.vote_btn)
        lay.addWidget(self.status)
        self.vote_btn.clicked.connect(self.cast_vote)

    def cast_vote(self):
        pid = self.party_group.checkedId()
        if pid == -1:
            QtWidgets.QMessageBox.information(self, "Info", "Please select a party")
            return
        ok = db.vote_once(self.user_id, pid)
        if ok:
            self.status.setText("Vote recorded. Thank you!")
            self.vote_btn.setEnabled(False)
        else:
            self.status.setText("You have already voted or an error occurred.")

class AdminView(QtWidgets.QTabWidget):
    def __init__(self, sensor: FingerprintSensor):
        super().__init__()
        self.sensor = sensor
        self.setWindowTitle("Admin — Manage Election")
        self.parties_tab = self.build_parties_tab()
        self.users_tab = self.build_users_tab()
        self.results_tab = self.build_results_tab()
        self.addTab(self.parties_tab, "Parties")
        self.addTab(self.users_tab, "Users")
        self.addTab(self.results_tab, "Results")

    def build_parties_tab(self):
        w = QtWidgets.QWidget()
        self.party_list = QtWidgets.QListWidget()
        self.party_name = QtWidgets.QLineEdit()
        add_btn = QtWidgets.QPushButton("Add")
        upd_btn = QtWidgets.QPushButton("Rename")
        del_btn = QtWidgets.QPushButton("Delete")
        refresh_btn = QtWidgets.QPushButton("Refresh")

        lay = QtWidgets.QVBoxLayout(w)
        lay.addWidget(self.party_list)
        form = QtWidgets.QHBoxLayout()
        form.addWidget(self.party_name)
        form.addWidget(add_btn); form.addWidget(upd_btn); form.addWidget(del_btn); form.addWidget(refresh_btn)
        lay.addLayout(form)

        add_btn.clicked.connect(self.add_party)
        upd_btn.clicked.connect(self.update_party)
        del_btn.clicked.connect(self.delete_party)
        refresh_btn.clicked.connect(self.load_parties)
        self.load_parties()
        return w

    def load_parties(self):
        self.party_list.clear()
        for pid, pname in db.list_parties():
            item = QtWidgets.QListWidgetItem(pname)
            item.setData(QtCore.Qt.UserRole, pid)
            self.party_list.addItem(item)

    def add_party(self):
        name = self.party_name.text().strip()
        if not name: return
        try:
            db.add_party(name)
            self.load_parties()
            self.party_name.clear()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", str(e))

    def update_party(self):
        item = self.party_list.currentItem()
        if not item: return
        pid = item.data(QtCore.Qt.UserRole)
        new = self.party_name.text().strip()
        if not new: return
        db.update_party(pid, new)
        self.load_parties()
        self.party_name.clear()

    def delete_party(self):
        item = self.party_list.currentItem()
        if not item: return
        pid = item.data(QtCore.Qt.UserRole)
        db.delete_party(pid)
        self.load_parties()

    def build_users_tab(self):
        w = QtWidgets.QWidget()
        name = QtWidgets.QLineEdit(); name.setPlaceholderText("User name")
        is_admin = QtWidgets.QCheckBox("Admin")
        pos = QtWidgets.QSpinBox(); pos.setRange(0, 1000); pos.setPrefix("Template #")
        enroll_btn = QtWidgets.QPushButton("Enroll + Save")
        del_btn = QtWidgets.QPushButton("Delete User + Template")
        info = QtWidgets.QLabel("Connect sensor in Login screen first. Template slots depend on sensor.")

        lay = QtWidgets.QFormLayout(w)
        lay.addRow("Name:", name)
        lay.addRow("", is_admin)
        lay.addRow("Template Position:", pos)
        lay.addRow("", enroll_btn)
        lay.addRow("Delete by Template Position:", del_btn)
        lay.addRow("", info)

        def do_enroll():
            try:
                stored = self.sensor.enroll(pos.value())
                db.create_user(name.text().strip(), stored, 1 if is_admin.isChecked() else 0)
                QtWidgets.QMessageBox.information(w, "Success", f"Enrolled at {stored} and saved.")
            except Exception as e:
                QtWidgets.QMessageBox.critical(w, "Error", str(e))

        def do_delete():
            try:
                self.sensor.delete(pos.value())
                db.delete_user_by_finger(pos.value())
                QtWidgets.QMessageBox.information(w, "Deleted", "Template and user removed.")
            except Exception as e:
                QtWidgets.QMessageBox.critical(w, "Error", str(e))

        enroll_btn.clicked.connect(do_enroll)
        del_btn.clicked.connect(do_delete)
        return w

    def build_results_tab(self):
        w = QtWidgets.QWidget()
        self.results_table = QtWidgets.QTableWidget(0, 2)
        self.results_table.setHorizontalHeaderLabels(["Party", "Votes"])
        refresh = QtWidgets.QPushButton("Refresh")
        export = QtWidgets.QPushButton("Export CSV")
        lay = QtWidgets.QVBoxLayout(w)
        lay.addWidget(self.results_table)
        row = QtWidgets.QHBoxLayout()
        row.addWidget(refresh); row.addWidget(export)
        lay.addLayout(row)

        def load():
            data = db.get_results()
            self.results_table.setRowCount(0)
            for name, votes in data:
                r = self.results_table.rowCount()
                self.results_table.insertRow(r)
                self.results_table.setItem(r, 0, QtWidgets.QTableWidgetItem(str(name)))
                self.results_table.setItem(r, 1, QtWidgets.QTableWidgetItem(str(votes)))

        def export_csv():
            path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save CSV", "results.csv", "CSV Files (*.csv)")
            if not path: return
            data = db.get_results()
            import csv
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Party", "Votes"])
                writer.writerows(data)
            QtWidgets.QMessageBox.information(w, "Saved", "Exported results.")

        refresh.clicked.connect(load)
        export.clicked.connect(export_csv)
        load()
        return w

def main():
    db.init_db()
    app = QtWidgets.QApplication(sys.argv)
    sensor = FingerprintSensor()
    win = LoginView(sensor)
    win.resize(420, 360)
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
