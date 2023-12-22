import calendar
import datetime
import re
import sys
import csv
import time
import threading
from datetime import datetime

from PyQt6 import QtWidgets, QtCore
from PyQt6.QtCore import QRegularExpression
from PyQt6.QtWidgets import QApplication, QMainWindow, QTableWidget, QTableWidgetItem, QPushButton, QVBoxLayout, \
    QWidget, QHBoxLayout, QLineEdit, QLabel, QDialog, QRadioButton
from PyQt6.QtSql import QSqlDatabase, QSqlQuery, QSqlTableModel
from py122u import nfc

db = QSqlDatabase.addDatabase("QSQLITE")
db.setDatabaseName("employees.db")
db.open()

def NFCRead():
    global status_card
    global last_uid
    global tableWidget
    status_card = 0
    last_uid = 0
    reader = nfc.Reader()
    while True:
        try:
            if status_card == 0:
                reader.connect()

                uid = ''
                for el in list(map(str, reader.get_uid())):
                    uid += el
                last_uid = uid

                db = QSqlDatabase.addDatabase("QSQLITE")
                db.setDatabaseName("employees.db")
                db.open()
                passage = QSqlQuery()
                passage.exec("select * from employees where card_id = '" + str(last_uid) + "'")
                is_card = 0
                while passage.next():
                    time_exp = datetime.strptime(passage.value(11), "%d.%m.%Y %H:%M:%S").timestamp()
                    if time_exp < int(time.time()):
                        reader.led_control(0x05, 0x0A, 0x01, 0x01, 0x01)
                        print(f'Срок действия карты истёк. Срок действия был до {passage.value(11)}. Обратитесь к дежурному охраннику.')
                    else:
                        query_is_checkin = QSqlQuery()
                        query_is_checkin.exec("select card_id from history_passages where card_id = '"+last_uid+"' and check_out = ''")

                        is_check_in = False
                        while query_is_checkin.next():
                            is_check_in = True

                        now = datetime.now()
                        current_time = now.strftime("%d.%m.%Y %H:%M:%S")
                        if is_check_in:
                            query_insert = QSqlQuery()
                            query_insert.exec("update history_passages set check_out = '"+current_time+"' where card_id = '"+last_uid+"'")
                            print(f'{passage.value(1)} {passage.value(2)} {passage.value(3)} покинул территорию в {current_time}')
                        else:
                            query_insert = QSqlQuery()
                            if passage.value(5) == "":
                                rank = "Гость"
                            else:
                                rank = passage.value(5)
                            query_insert.exec("insert into history_passages (card_id, first_name, last_name, middle_name, birth_date, rank, check_in, check_out) values ('" + str(last_uid) + "', '" + passage.value(1) + "', '" + passage.value(2) + "', '" + passage.value(3) + "', '" + passage.value(4) + "', '" + rank + "', '" + current_time + "', '')")
                            print(f'{passage.value(1)} {passage.value(2)} {passage.value(3)} зашёл на территорию в {current_time}')
                    is_card += 1
                if is_card == 0:
                    reader.led_control(0x05, 0x0A, 0x01, 0x01, 0x01)
                    print(f'Карта недействительна')

                time.sleep(1.5)
        except:
            pass
            time.sleep(1)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.tableWidget = QTableWidget()
        self.query = QSqlQuery()
        self.query.exec("create table if not exists history_passages (card_id integer, first_name text, last_name text, middle_name text, birth_date text, rank text, check_in text, check_out text);")
        self.query.exec("create table if not exists employees (card_id integer primary key, first_name text, last_name text, middle_name text, birth_date text, rank text, is_guest boolean, purpose_visit text, phone text, email text, time_issued integer, time_expired integer);")
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Программа КПП охранника')
        self.resize(950, 660)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()
        button_layout = QHBoxLayout()

        button1 = QPushButton('Обновить историю')
        button2 = QPushButton('Список пропусков')
        button_layout.addWidget(button1)
        button_layout.addWidget(button2)

        layout.addLayout(button_layout)

        self.query = QSqlQuery()
        self.query.exec("select * from history_passages")
        arr_results = []
        while self.query.next():
            subarr_resluts = []
            for x in range(8):
                subarr_resluts.append(self.query.value(x))
            arr_results.append(subarr_resluts)
        self.tableWidget.setRowCount(len(arr_results) + 1)
        self.tableWidget.setColumnCount(8)

        self.tableWidget.setItem(0, 0, QTableWidgetItem('ID карты'))
        self.tableWidget.setItem(0, 1, QTableWidgetItem('Фамилия'))
        self.tableWidget.setItem(0, 2, QTableWidgetItem('Имя'))
        self.tableWidget.setItem(0, 3, QTableWidgetItem('Отчество'))
        self.tableWidget.setItem(0, 4, QTableWidgetItem('Дата рождения'))
        self.tableWidget.setItem(0, 5, QTableWidgetItem('Должность'))
        self.tableWidget.setItem(0, 6, QTableWidgetItem('Вход'))
        self.tableWidget.setItem(0, 7, QTableWidgetItem('Выход'))

        for i in range(len(arr_results)):
            rownum = i + 1
            self.tableWidget.setItem(rownum, 0, QTableWidgetItem(str(arr_results[i][0])))
            self.tableWidget.setItem(rownum, 1, QTableWidgetItem(arr_results[i][1]))
            self.tableWidget.setItem(rownum, 2, QTableWidgetItem(arr_results[i][2]))
            self.tableWidget.setItem(rownum, 3, QTableWidgetItem(arr_results[i][3]))
            self.tableWidget.setItem(rownum, 4, QTableWidgetItem(arr_results[i][4]))
            self.tableWidget.setItem(rownum, 5, QTableWidgetItem(arr_results[i][5]))
            self.tableWidget.setItem(rownum, 6, QTableWidgetItem(arr_results[i][6]))
            self.tableWidget.setItem(rownum, 7, QTableWidgetItem(arr_results[i][7]))

        layout.addWidget(self.tableWidget)

        central_widget.setLayout(layout)

        button1.clicked.connect(self.updateListPassages)
        button2.clicked.connect(self.showListEmployees)
        self.show()

    def showListEmployees(self):
        self.ex = ListEmployees()
        self.ex.show()

    def updateListPassages(self):
        db = QSqlDatabase.addDatabase("QSQLITE")
        db.setDatabaseName("employees.db")
        db.open()
        self.query = QSqlQuery()
        self.query.exec("select * from history_passages")
        arr_results = []
        while self.query.next():
            subarr_resluts = []
            for x in range(8):
                subarr_resluts.append(self.query.value(x))
            arr_results.append(subarr_resluts)
        self.tableWidget.setRowCount(len(arr_results) + 1)
        self.tableWidget.setColumnCount(8)

        for i in range(len(arr_results)):
            rownum = i + 1
            self.tableWidget.setItem(rownum, 0, QTableWidgetItem(str(arr_results[i][0])))
            self.tableWidget.setItem(rownum, 1, QTableWidgetItem(arr_results[i][1]))
            self.tableWidget.setItem(rownum, 2, QTableWidgetItem(arr_results[i][2]))
            self.tableWidget.setItem(rownum, 3, QTableWidgetItem(arr_results[i][3]))
            self.tableWidget.setItem(rownum, 4, QTableWidgetItem(arr_results[i][4]))
            self.tableWidget.setItem(rownum, 5, QTableWidgetItem(arr_results[i][5]))
            self.tableWidget.setItem(rownum, 6, QTableWidgetItem(arr_results[i][6]))
            self.tableWidget.setItem(rownum, 7, QTableWidgetItem(arr_results[i][7]))

class ListEmployees(QMainWindow):
    def __init__(self):
        db = QSqlDatabase.addDatabase("QSQLITE")
        db.setDatabaseName("employees.db")
        db.open()
        super().__init__()
        self.setWindowTitle('Список пропусков')
        self.resize(1370, 660)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()
        header_layout = QHBoxLayout()
        button_update = QPushButton('Обновить список')
        button_add = QPushButton('Добавить пропуск')
        header_layout.addWidget(button_update)
        header_layout.addWidget(button_add)
        layout.addLayout(header_layout)

        self.query = QSqlQuery()
        self.query.exec("select * from employees")
        arr_results = []
        while self.query.next():
            subarr_resluts = []
            for x in range(12):
                subarr_resluts.append(self.query.value(x))
            arr_results.append(subarr_resluts)

        self.tableWidget = QTableWidget()
        self.tableWidget.setRowCount(len(arr_results)+1)
        self.tableWidget.setColumnCount(12)

        self.tableWidget.setItem(0, 0, QTableWidgetItem('ID карты'))
        self.tableWidget.setItem(0, 1, QTableWidgetItem('Фамилия'))
        self.tableWidget.setItem(0, 2, QTableWidgetItem('Имя'))
        self.tableWidget.setItem(0, 3, QTableWidgetItem('Отчество'))
        self.tableWidget.setItem(0, 4, QTableWidgetItem('Дата рождения'))
        self.tableWidget.setItem(0, 5, QTableWidgetItem('Должность'))
        self.tableWidget.setItem(0, 6, QTableWidgetItem('Статус гостя'))
        self.tableWidget.setItem(0, 7, QTableWidgetItem('Цель визита'))
        self.tableWidget.setItem(0, 8, QTableWidgetItem('Номер телефона'))
        self.tableWidget.setItem(0, 9, QTableWidgetItem('Адрес эл. почты'))
        self.tableWidget.setItem(0, 10, QTableWidgetItem('Дата выдачи'))
        self.tableWidget.setItem(0, 11, QTableWidgetItem('Срок действия'))

        for i in range(len(arr_results)):
            rownum = i+1
            if arr_results[i][6] == 1:
                is_guest = "Да"
            else:
                is_guest = "Нет"
            if len(arr_results[i][7]) > 0:
                purpose_visit = arr_results[i][7]
            elif len(arr_results[i][7]) == 0 and arr_results[i][6] == 1:
                purpose_visit = "Не указана"
            else:
                purpose_visit = ""
            self.tableWidget.setItem(rownum, 0, QTableWidgetItem(str(arr_results[i][0])))
            self.tableWidget.setItem(rownum, 1, QTableWidgetItem(arr_results[i][1]))
            self.tableWidget.setItem(rownum, 2, QTableWidgetItem(arr_results[i][2]))
            self.tableWidget.setItem(rownum, 3, QTableWidgetItem(arr_results[i][3]))
            self.tableWidget.setItem(rownum, 4, QTableWidgetItem(arr_results[i][4]))
            self.tableWidget.setItem(rownum, 5, QTableWidgetItem(arr_results[i][5]))
            self.tableWidget.setItem(rownum, 6, QTableWidgetItem(is_guest))
            self.tableWidget.setItem(rownum, 7, QTableWidgetItem(purpose_visit))
            self.tableWidget.setItem(rownum, 8, QTableWidgetItem(arr_results[i][8]))
            self.tableWidget.setItem(rownum, 9, QTableWidgetItem(arr_results[i][9]))
            self.tableWidget.setItem(rownum, 10, QTableWidgetItem(arr_results[i][10]))
            self.tableWidget.setItem(rownum, 11, QTableWidgetItem(arr_results[i][11]))

        layout.addWidget(self.tableWidget)

        central_widget.setLayout(layout)
        button_update.clicked.connect(self.updateEmployees)
        button_add.clicked.connect(self.addEmployees)
        self.show()

    def updateEmployees(self):
        db = QSqlDatabase.addDatabase("QSQLITE")
        db.setDatabaseName("employees.db")
        db.open()
        self.query = QSqlQuery()
        self.query.exec("select * from employees")
        arr_results = []
        while self.query.next():
            subarr_resluts = []
            for x in range(12):
                subarr_resluts.append(self.query.value(x))
            arr_results.append(subarr_resluts)
        self.tableWidget.setRowCount(len(arr_results) + 1)
        self.tableWidget.setColumnCount(12)

        for i in range(len(arr_results)):
            rownum = i+1
            if arr_results[i][6] == 1:
                is_guest = "Да"
            else:
                is_guest = "Нет"
            if len(arr_results[i][7]) > 0:
                purpose_visit = arr_results[i][7]
            elif len(arr_results[i][7]) == 0 and arr_results[i][6] == 1:
                purpose_visit = "Не указана"
            else:
                purpose_visit = ""
            self.tableWidget.setItem(rownum, 0, QTableWidgetItem(str(arr_results[i][0])))
            self.tableWidget.setItem(rownum, 1, QTableWidgetItem(arr_results[i][1]))
            self.tableWidget.setItem(rownum, 2, QTableWidgetItem(arr_results[i][2]))
            self.tableWidget.setItem(rownum, 3, QTableWidgetItem(arr_results[i][3]))
            self.tableWidget.setItem(rownum, 4, QTableWidgetItem(arr_results[i][4]))
            self.tableWidget.setItem(rownum, 5, QTableWidgetItem(arr_results[i][5]))
            self.tableWidget.setItem(rownum, 6, QTableWidgetItem(is_guest))
            self.tableWidget.setItem(rownum, 7, QTableWidgetItem(purpose_visit))
            self.tableWidget.setItem(rownum, 8, QTableWidgetItem(arr_results[i][8]))
            self.tableWidget.setItem(rownum, 9, QTableWidgetItem(arr_results[i][9]))
            self.tableWidget.setItem(rownum, 10, QTableWidgetItem(arr_results[i][10]))
            self.tableWidget.setItem(rownum, 11, QTableWidgetItem(arr_results[i][11]))

    def addEmployees(self):
        self.ex = CreateEmployees()
        self.ex.show()

class CreateEmployees(QMainWindow):
    global last_name_input
    global first_name_input
    global middle_name_input
    global birth_date_input
    global rank_input
    global phone_input
    global email_input
    global expire_date_input
    def __init__(self):
        global status_card
        super().__init__()
        status_card = 1
        self.setWindowTitle('Добавить пропуск')
        self.resize(550, 160)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()

        self.h1_layout = QHBoxLayout()
        self.last_name_text = QLabel("Фамилия")
        self.last_name_input = QLineEdit()
        self.last_name_input.setMaxLength(20)
        self.h1_layout.addWidget(self.last_name_text)
        self.h1_layout.addWidget(self.last_name_input)

        self.h2_layout = QHBoxLayout()
        self.first_name_text = QLabel("Имя")
        self.first_name_input = QLineEdit()
        self.first_name_input.setMaxLength(20)
        self.h2_layout.addWidget(self.first_name_text)
        self.h2_layout.addWidget(self.first_name_input)

        self.h3_layout = QHBoxLayout()
        self.middle_name_text = QLabel("Отчество")
        self.middle_name_input = QLineEdit()
        self.middle_name_input.setMaxLength(20)
        self.h3_layout.addWidget(self.middle_name_text)
        self.h3_layout.addWidget(self.middle_name_input)

        self.h4_layout = QHBoxLayout()
        self.birth_date_text = QLabel("Дата рождения")
        self.birth_date_input = QLineEdit()
        self.birth_date_input.setInputMask('99.99.9999')
        self.h4_layout.addWidget(self.birth_date_text)
        self.h4_layout.addWidget(self.birth_date_input)

        self.radio1 = QRadioButton("Сотрудник", self)
        self.radio2 = QRadioButton("Гость", self)
        self.radio1.setChecked(True)
        self.radio1.toggled.connect(self.selectEmployee)
        self.radio2.toggled.connect(self.selectGuest)

        self.h5_layout = QHBoxLayout()
        self.rank_text = QLabel("Должность")
        self.rank_input = QLineEdit()
        self.rank_input.setMaxLength(20)
        self.h5_layout.addWidget(self.rank_text)
        self.h5_layout.addWidget(self.rank_input)

        self.h6_layout = QHBoxLayout()
        self.phone_text = QLabel("Телефон")
        self.phone_input = QLineEdit()
        self.phone_input.setInputMask('+7 (999) 999 99 99')
        self.h6_layout.addWidget(self.phone_text)
        self.h6_layout.addWidget(self.phone_input)

        self.h7_layout = QHBoxLayout()
        self.email_text = QLabel("Электронная почта")
        self.email_input = QLineEdit()
        self.email_input.setMaxLength(35)
        self.h7_layout.addWidget(self.email_text)
        self.h7_layout.addWidget(self.email_input)

        self.h10_layout = QHBoxLayout()
        self.expire_date_text = QLabel("Срок действия пропуска")
        self.expire_date_input = QLineEdit()
        self.expire_date_input.setInputMask('99.99.9999 99:99')
        self.h10_layout.addWidget(self.expire_date_text)
        self.h10_layout.addWidget(self.expire_date_input)

        self.h11_layout = QHBoxLayout()
        self.purpose_visit_text = QLabel("Цель визита")
        self.purpose_visit_input = QLineEdit()
        self.purpose_visit_input.setMaxLength(60)
        self.h11_layout.addWidget(self.purpose_visit_text)
        self.h11_layout.addWidget(self.purpose_visit_input)
        self.purpose_visit_text.hide()
        self.purpose_visit_input.hide()

        self.h8_layout = QHBoxLayout()
        self.card_text_hint = QLabel("<center>Прислоните карту для записи пропуска</center>")
        self.h8_layout.addWidget(self.card_text_hint)

        self.h9_layout = QHBoxLayout()
        self.button_add = QPushButton('Добавить')
        self.h9_layout.addWidget(self.button_add)

        layout.addLayout(self.h1_layout)
        layout.addLayout(self.h2_layout)
        layout.addLayout(self.h3_layout)
        layout.addLayout(self.h4_layout)
        layout.addWidget(self.radio1)
        layout.addWidget(self.radio2)
        layout.addLayout(self.h5_layout)
        layout.addLayout(self.h6_layout)
        layout.addLayout(self.h7_layout)
        layout.addLayout(self.h11_layout)
        layout.addLayout(self.h10_layout)
        layout.addLayout(self.h8_layout)
        layout.addLayout(self.h9_layout)

        central_widget.setLayout(layout)
        self.button_add.clicked.connect(self.createPass)
        self.show()

    def selectGuest(self):
        self.rank_text.hide()
        self.rank_input.hide()
        self.phone_text.hide()
        self.phone_input.hide()
        self.email_text.hide()
        self.email_input.hide()
        self.purpose_visit_text.show()
        self.purpose_visit_input.show()

    def selectEmployee(self):
        self.rank_text.show()
        self.rank_input.show()
        self.phone_text.show()
        self.phone_input.show()
        self.email_text.show()
        self.email_input.show()
        self.purpose_visit_text.hide()
        self.purpose_visit_input.hide()

    def createPass(self):
        db = QSqlDatabase.addDatabase("QSQLITE")
        db.setDatabaseName("employees.db")
        db.open()
        global last_uid
        global status_card
        status_card = 0
        try:
            lnt = self.last_name_input.text()
            fnt = self.first_name_input.text()
            mnt = self.middle_name_input.text()
            bt = self.birth_date_input.text()
            if self.radio1.isChecked():
                rt = self.rank_input.text()
            else:
                rt = ""
            if self.radio1.isChecked():
                pt = self.phone_input.text()
            else:
                pt = ""
            if self.radio1.isChecked():
                et = self.email_input.text()
            else:
                et = ""
            if self.radio2.isChecked():
                pvt = self.purpose_visit_input.text()
            else:
                pvt = ""
            expt = self.expire_date_input.text()
            now = datetime.now()
            issued_date = now.strftime("%d.%m.%Y %H:%M:%S")
            unix_expire = datetime.strptime(expt, "%d.%m.%Y %H:%M").timestamp()
            unix_birthdate = datetime.strptime(bt, "%d.%m.%Y").timestamp()

            regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'

            self.is_card = QSqlQuery()
            self.is_card.exec("select card_id from employees where card_id = '" + str(last_uid) + "'")
            self.writed_card = 0
            while self.is_card.next():
                self.writed_card += 1

            if len(lnt) > 20 or len(lnt) < 2:
                self.errwin = notifyWindow("Ошибка", "Фамилия должна быть от 2 до 20 символов")
                self.errwin.show()
            elif len(fnt) > 20 or len(fnt) < 2:
                self.errwin = notifyWindow("Ошибка", "Имя должна быть от 2 до 20 символов")
                self.errwin.show()
            elif (len(et) > 40 or len(et) < 5) and self.radio1.isChecked():
                self.errwin = notifyWindow("Ошибка", "Адрес электронной почты должен быть от 5 до 40 символов")
                self.errwin.show()
            elif len(pt) != 18 and self.radio1.isChecked():
                self.errwin = notifyWindow("Ошибка", "Телефон введён неверно")
                self.errwin.show()
            elif (len(et) > 25 or len(et) < 5) and self.radio1.isChecked():
                self.errwin = notifyWindow("Ошибка", "Должность должна быть от 5 до 25 символов")
                self.errwin.show()
            elif unix_expire < int(time.time()):
                self.errwin = notifyWindow("Ошибка", "Срок действия уже истёк")
                self.errwin.show()
            elif unix_birthdate >= int(time.time()):
                self.errwin = notifyWindow("Ошибка", "Человек не может быть из будущего!")
                self.errwin.show()
            elif not(re.fullmatch(regex, et)) and self.radio1.isChecked():
                self.errwin = notifyWindow("Ошибка", "Адрес электронной почти введён некорректно")
                self.errwin.show()
            elif last_uid == 0:
                self.errwin = notifyWindow("Ошибка", "Карта не прислонена")
                self.errwin.show()
            elif self.writed_card > 0:
                self.errwin = notifyWindow("Ошибка", "На эту карту уже записан пропуск")
                self.errwin.show()
            else:
                if self.radio2.isChecked():
                    is_guest = "true"
                else:
                    is_guest = "false"
                self.query = QSqlQuery()
                self.query.exec("insert into employees (card_id, first_name, last_name, middle_name, birth_date, rank, phone, email, time_issued, time_expired, purpose_visit, is_guest) values ('"+str(last_uid)+"', '"+fnt+"', '"+lnt+"', '"+mnt+"', '"+bt+"', '"+rt+"', '"+pt+"', '"+et+"', '"+issued_date+"', '"+expt+":00', '"+pvt+"', "+is_guest+")")
                self.last_name_input.setText("")
                self.last_name_input.setText("")
                self.first_name_input.setText("")
                self.middle_name_input.setText("")
                self.birth_date_input.setText("")
                self.rank_input.setText("")
                self.phone_input.setText("")
                self.email_input.setText("")
                last_uid = 0
                self.notwin = notifyWindow("Сообщение", "Пропуск успешно добавлен")
                self.notwin.show()
        except ValueError:
            self.errwin = notifyWindow("Ошибка", "Дата введена некорректно")
            self.errwin.show()


class notifyWindow(QMainWindow):
    def __init__(self, text_title, text_window):
        super().__init__()
        self.setWindowTitle(text_title)
        self.resize(250, 70)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()
        textwin = QLabel(text_window)
        layout.addWidget(textwin)

        central_widget.setLayout(layout)
        self.show()

def main():
    app = QApplication(sys.argv)
    ex = MainWindow()
    t = threading.Thread(target=NFCRead, args=())
    t.start()
    app.exec()

if __name__ == '__main__':
    main()