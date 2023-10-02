import sys
import sqlite3
import cv2
import easyocr
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel, QLineEdit, QVBoxLayout, QWidget, QRadioButton, QTextEdit
from datetime import datetime

class ParkirApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.title = 'Sistem Parkir'
        self.width = 400
        self.height = 400
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(100, 100, self.width, self.height)

        self.manual_radio = QRadioButton('Isi Manual', self)
        self.manual_radio.move(20, 20)
        self.manual_radio.setChecked(True)
        self.manual_radio.clicked.connect(self.select_manual)
        
        self.camera_radio = QRadioButton('Ambil Gambar dari Kamera', self)
        self.camera_radio.move(20, 50)
        self.camera_radio.clicked.connect(self.select_camera)

        self.label = QLabel('Nomor Plat Kendaraan:', self)
        self.label.move(20, 90)

        self.textbox = QLineEdit(self)
        self.textbox.move(180, 90)
        self.textbox.resize(150, 30)

        self.enter_button = QPushButton('Masuk', self)
        self.enter_button.move(20, 140)
        self.enter_button.clicked.connect(self.masuk_parkir)  # Perbaiki fungsi yang terhubung

        self.exit_button = QPushButton('Keluar', self)
        self.exit_button.move(180, 140)
        self.exit_button.clicked.connect(self.keluar_parkir)  # Perbaiki fungsi yang terhubung

        self.status_label = QLabel('', self)
        self.status_label.move(20, 180)
        self.status_label.resize(300, 30)

        self.keterangan_label = QLabel('Keterangan Waktu:', self)
        self.keterangan_label.move(20, 220)

        self.keterangan_textbox = QTextEdit(self)
        self.keterangan_textbox.move(180, 220)
        self.keterangan_textbox.resize(150, 60)

        self.data_label = QLabel('Data Parkir:', self)
        self.data_label.move(20, 300)

        self.data_textbox = QTextEdit(self)
        self.data_textbox.move(20, 330)
        self.data_textbox.resize(340, 60)
        self.data_textbox.setReadOnly(True)

        # Inisialisasi kamera
        self.capture = None
        self.camera_selected = False

        # Inisialisasi waktu masuk dan waktu keluar
        self.waktu_masuk = None
        self.waktu_keluar = None

        # Biaya parkir per jam
        self.biaya_pertama = 3000  # Rp 3.000 untuk satu jam pertama
        self.biaya_berikutnya = 2000  # Rp 2.000 untuk setiap jam berikutnya

        # Buat database SQLite
        self.create_database()

    def select_manual(self):
        self.camera_selected = False

    def select_camera(self):
        self.camera_selected = True

        # Buka kamera
        self.capture = cv2.VideoCapture(0)
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    def create_database(self):
        connection = sqlite3.connect("parkir.db")
        cursor = connection.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS parkir (
                            nomor_plat TEXT,
                            waktu_masuk DATETIME,
                            waktu_keluar DATETIME,
                            biaya INTEGER,
                            keterangan TEXT
                        )''')
        connection.commit()
        connection.close()

    def masuk_parkir(self):
        nomor_plat = self.textbox.text()
        if nomor_plat:
            connection = sqlite3.connect("parkir.db")
            cursor = connection.cursor()

            self.waktu_masuk = datetime.now()  # Catat waktu masuk saat ini
            keterangan = self.waktu_masuk.strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("INSERT INTO parkir (nomor_plat, waktu_masuk, keterangan) VALUES (?, ?, ?)",
                           (nomor_plat, self.waktu_masuk, keterangan))
            connection.commit()
            connection.close()

            self.status_label.setText(f"Kendaraan dengan nomor plat {nomor_plat} masuk parkir.")
            self.keterangan_textbox.setPlainText(keterangan)
        else:
            self.status_label.setText("Masukkan nomor plat kendaraan!")

    def ambil_nomor_plat(self, frame):
        reader = easyocr.Reader(['en'])  # Anda dapat mengganti 'en' dengan bahasa yang sesuai
        result = reader.readtext(frame)
        nomor_plat = ""

        for detection in result:
            text, _, _, _ = detection
            nomor_plat += text + " "

        return nomor_plat.strip()

    def capture_frame(self):
        if self.capture is not None:
            ret, frame = self.capture.read()
            if ret:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                nomor_plat = self.ambil_nomor_plat(gray)
                self.textbox.setText(nomor_plat)

    def keluar_parkir(self):
        nomor_plat = self.textbox.text()
        if nomor_plat and self.waktu_masuk:
            connection = sqlite3.connect("parkir.db")
            cursor = connection.cursor()
            cursor.execute("SELECT waktu_masuk FROM parkir WHERE nomor_plat = ? AND waktu_keluar IS NULL",
                           (nomor_plat,))
            result = cursor.fetchone()

            if result:
                try:
                    self.waktu_keluar = datetime.now()
                    # Sesuaikan format waktu masuk yang ada di database
                    waktu_masuk_db = datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S.%f")
                    selisih_waktu = self.waktu_keluar - waktu_masuk_db
                    durasi_jam = selisih_waktu.seconds / 3600

                    biaya = self.biaya_pertama + (self.biaya_berikutnya * (durasi_jam - 1))
                    if durasi_jam <= 1:
                        biaya = self.biaya_pertama

                    keterangan = f"{selisih_waktu.days} hari {int(durasi_jam)} jam {selisih_waktu.seconds // 60 % 60} menit {selisih_waktu.seconds % 60} detik"
                    cursor.execute("UPDATE parkir SET waktu_keluar = ?, biaya = ?, keterangan = ? WHERE nomor_plat = ? AND waktu_masuk = ?",
                                   (self.waktu_keluar, biaya, keterangan, nomor_plat, waktu_masuk_db.strftime("%Y-%m-%d %H:%M:%S.%f")))
                    connection.commit()
                    connection.close()

                    self.status_label.setText(f"Kendaraan dengan nomor plat {nomor_plat} keluar parkir. Biaya parkir: Rp {biaya}")
                    self.keterangan_textbox.setPlainText(keterangan)
                except ValueError as e:
                    self.status_label.setText(f"Kesalahan dalam mengonversi waktu masuk: {str(e)}")
                    print(f"Kesalahan dalam mengonversi waktu masuk: {str(e)}")
            else:
                self.status_label.setText(f"Kendaraan dengan nomor plat {nomor_plat} tidak ditemukan dalam database atau sudah keluar parkir.")
        else:
            self.status_label.setText("Masukkan nomor plat kendaraan!")

    def display_data(self):
        connection = sqlite3.connect("parkir.db")
        cursor = connection.cursor()
        cursor.execute("SELECT nomor_plat, waktu_masuk, waktu_keluar, biaya, keterangan FROM parkir")
        data = cursor.fetchall()
        connection.close()

        self.data_textbox.clear()
        for entry in data:
            nomor_plat, waktu_masuk, waktu_keluar, biaya, keterangan = entry
            if waktu_keluar:
                self.data_textbox.append(f"Nomor Plat: {nomor_plat}\nWaktu Masuk: {waktu_masuk}\nWaktu Keluar: {waktu_keluar}\nDurasi Parkir: {keterangan}\nBiaya Parkir: Rp {biaya}\n")
            else:
                self.data_textbox.append(f"Nomor Plat: {nomor_plat}\nWaktu Masuk: {waktu_masuk}\nBelum Keluar\n")

    def closeEvent(self, event):
        if self.capture is not None:
            self.capture.release()
        event.accept()

def main():
    app = QApplication(sys.argv)
    window = ParkirApp()
    window.show()

    while True:
        if window.camera_selected and window.capture.isOpened():
            window.capture_frame()

        window.display_data()
        app.processEvents()

if __name__ == '__main__':
    main()
    
