import sys
from PyQt5.QtWidgets import QWidget, QApplication, QPushButton, QLineEdit, QTextBrowser, QListWidget, QInputDialog, QListWidgetItem, QMessageBox
from PyQt5 import QtGui, QtCore
import os, json, threading, struct
from PyQt5.QtGui import QIcon
import socket, ast, datetime

outputs = {}

SERVER_HOST = '127.0.0.1'
SERVER_PORT = 8000


class App(QWidget):
    def __init__(self):
        super().__init__()

        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((SERVER_HOST, SERVER_PORT))
        self.id = 0

        self.top = 100
        self.left = 100
        self.width = 800
        self.height = 400

        self.userNameDialog()
        self.title = "Super Duper TCP Socket Chat :: " + self.user_name

        self.iniMyUI()

    def room_viewer(self, list):
        global outputs
        self.list_users.clear()
        for elements in list:
            self.list_users.addItem(str(elements))

    def personal_room_maker(self, list):
        global outputs
        for elements in list:
            self.text_output = QTextBrowser(self)
            outputs.update({str(elements): self.text_output})
            self.text_output.setReadOnly(True)
            self.list_rooms.addItem(str(elements))

    def room_maker(self, list):
        global outputs
        self.list_rooms.clear()
        for elements in list:
            if str(elements) not in outputs:
                text_output = QTextBrowser(self)
                text_output.textChanged.connect(self.windows_refresh)
                outputs.update({str(elements): text_output})
                text_output.setVisible(False)

            self.list_rooms.addItem(str(elements))

    def room_change(self, word):
        global outputs
        self.outHandler("welcome", self.user_name, word)
        self.activeRoom = word

    def userNameDialog(self):
        scriptDir = os.path.dirname(os.path.realpath(__file__))
        self.setWindowIcon(QtGui.QIcon(scriptDir + os.path.sep + 'network.png'))
        answer = False
        while not answer == True:

            if answer == False:
                text, ok = QInputDialog.getText(self, 'User information', 'Enter your name:')
                if ok:
                    self.user_name = (str(text))
                    self.outHandler('/nameCheck', self.user_name, '')
                else:
                    sys.exit()

            elif python_obj["result"] == 'password':
                pw, oki = QInputDialog.getText(self, 'User information', 'This name requires a password:')
                if oki:
                    password = (str(pw))
                    self.outHandler('/passCheck', self.user_name, password)
                else:
                    sys.exit()

            size = struct.unpack("i", self.client_socket.recv(struct.calcsize("i")))[0]
            data = ""
            while len(data) < size:
                message = self.client_socket.recv(size - len(data))
                data += message.decode()
                python_obj = json.loads(data.strip())
                answer = python_obj["result"]

                if answer == False:
                    QMessageBox.about(self, "Name already taken!", "Please insert a different name")
                if answer == 'invalid_password':
                    QMessageBox.about(self, "Wrong!", "Please insert a valid password")
                    answer = False

    def closeEvent(self, event):
        reply = QMessageBox.question(self, 'Quit', 'Want to leave Super Duper TCP Socket Chat?', QMessageBox.No | QMessageBox.Yes)
        if reply == QMessageBox.Yes:
            self.outHandler('/exit', '', '')
            event.accept()
        else:
            event.ignore()

    def iniMyUI(self):
        global outputs

        self.setWindowTitle(self.title)
        scriptDir = os.path.dirname(os.path.realpath(__file__))
        self.setWindowIcon(QtGui.QIcon(scriptDir + os.path.sep + 'network.png'))
        self.setFixedSize(self.width, self.height)

        self.commandsList = ('addRoom', 'msg', 'addPriv', 'invite', 'register', 'login', 'delete', 'help')

        self.text_input = QLineEdit(self)
        self.text_input.setPlaceholderText("Message to send")
        self.text_input.setGeometry(200,370,310,20)
        self.text_input.returnPressed.connect(self.input_submit)

        self.btn = QPushButton("Send", self)
        self.btn.setGeometry(520, 370, 80, 20)

        self.my_name = QLineEdit(self)
        self.my_name.textChanged.connect(self.change_window_name)
        self.my_name.setVisible(False)

        self.meme_btn = QPushButton("☺", self)
        self.meme_btn.setGeometry(490, 370, 20, 20)

        self.meme_btn.clicked.connect(self.show_memes)

        self.btn.clicked.connect(self.input_submit)

        self.list_rooms = QListWidget(self)
        self.list_users = QListWidget(self)

        self.list_users.setGeometry(self.width - 190, 10, 180, 350)

        self.text_output = QTextBrowser(self)
        self.text_output.setVisible(False)
        self.generic_output = QTextBrowser(self)

        self.text_output.textChanged.connect(self.windows_refresh)

        outputs.update({'#Lobby': self.text_output})
        self.generic_output.setReadOnly(True)
        self.activeRoom = '#Lobby'

        self.generic_output.setGeometry(200, 10, 400, 350)

        self.list_rooms.setGeometry(10, 10, 180, 350)
        self.list_rooms.itemClicked.connect(self.select_room)

        self.meme_list = QListWidget(self)
        self.meme_list.setVisible(False)
        self.meme_list.itemClicked.connect(self.send_meme)

        self.files = {}
        self.emoticonList = []

        for file in os.listdir(scriptDir + os.path.sep + '\image\emoticons'):
            if file.endswith(".jpg"):
                self.files.update({os.path.join(os.getcwd(), 'image', 'emoticons', file): file})
                self.emoticonList.append(file.strip('.jpg'))

        self.meme_list.setIconSize(QtCore.QSize(60, 60))

        for key, value in self.files.items():
            icon = QIcon(key)
            item = QListWidgetItem(icon, value.strip('.jpg'))
            self.meme_list.addItem(item)

        self.meme_list.setGeometry(490, 220, 180, 150)

        self.list_users.itemClicked.connect(self.windows_refresh)

        thread = threading.Thread(target=self.view_update)
        thread.start()

        self.room_change("#Lobby")
        self.show()

    def view_update(self):
        self.exit = True
        while(self.exit):
            try:
                size = struct.unpack("i", self.client_socket.recv(struct.calcsize("i")))[0]
                data = ""
                while len(data) < size:
                    message = self.client_socket.recv(size - len(data))
                    data += message.decode()
                    python_obj = json.loads(data.strip())

                    if 'admin' in python_obj:
                        self.insert(python_obj['time'], python_obj['user'], python_obj['admin'], python_obj['room'], 1)

                    elif 'message' in python_obj:
                        self.insert(python_obj['time'], python_obj['user'], python_obj['message'], python_obj['room'], 0)

                    elif 'personal' in python_obj:
                        self.insert(python_obj['time'], python_obj['user'], python_obj['personal'], self.activeRoom,2)

                    elif 'broadcast' in python_obj:
                        self.insert(python_obj['time'], python_obj['user'], python_obj['broadcast'],self.activeRoom, 3)

                    elif 'server_msg' in python_obj:
                        self.insert(python_obj['time'], python_obj['user'], python_obj['server_msg'],self.activeRoom, 3)

                    elif 'move_to_room' in python_obj:
                        self.room_change(python_obj['move_to_room'])

                    elif 'rooms' in python_obj:
                        self.listOfRooms = ast.literal_eval(str(python_obj["rooms"]))
                        self.room_maker(self.listOfRooms)

                    elif 'users' in python_obj:
                        self.listOfUsers = ast.literal_eval(str(python_obj["users"]))
                        self.room_viewer(self.listOfUsers)

                    elif 'new_name' in python_obj:
                        self.user_name = python_obj["new_name"]
                        self.my_name.setText("Super Duper TCP Socket Chat :: " + self.user_name)

                    elif 'order_exit' in python_obj:
                        self.exit = False

                    else:
                        pass
            except:
                import traceback
                traceback.print_exc()

            # self.generic_output.moveCursor(QtGui.QTextCursor.End)

    def change_window_name(self, item):
        self.setWindowTitle(self.my_name.text())

    def windows_refresh(self):
        self.generic_output.clear()
        self.generic_output.insertHtml(outputs[self.activeRoom].toHtml())
        self.generic_output.moveCursor(QtGui.QTextCursor.End)

    def send_meme(self, item):
        self.command_inspector(item.text())

    def show_memes(self):
        self.meme_list.setVisible(not self.meme_list.isVisible())

    def select_room(self, item):
        self.room_change(item.text())
        self.generic_output.clear()
        self.generic_output.insertHtml(outputs[self.activeRoom].toHtml())

    def input_submit(self):
        try:
            if self.command_inspector(self.text_input.text()):
                self.generic_output.clear()

            self.text_input.clear()
        except:
            import traceback
            traceback.print_exc()

    def command_inspector(self, input):

        if len(input.split()) >= 2:
            input_split = input.split()
            command = input_split[0]
            second_word = input_split[1]
            all_but_first = (str(input_split[1:])).strip("['']")
            all_but_first_2 = (str(input_split[2:])).strip("['']")

            if command[0] == '/' and command[1:] in self.commandsList:
                if command == '/addRoom' and second_word[0] == '#':
                    self.outHandler(command, all_but_first, self.activeRoom)
                    return True

                if command == '/addPriv' and second_word[0] == '#':
                    self.outHandler(command, all_but_first, self.activeRoom)
                    return True

                if command == '/delete' and second_word[0] == '#':
                    self.outHandler(command, all_but_first, self.activeRoom)
                    return True

                if command == '/invite':
                    self.outHandler(command, all_but_first, self.activeRoom)
                    return False

                if command == '/msg':
                    self.outHandler(command, ' '.join((input_split[2:])), second_word)
                    self.insert(datetime.datetime.now().strftime("%H:%M:%S"), 'to ' + second_word, ' '.join(input_split[2:]), self.activeRoom, 2)
                    return False

                if command == '/register':
                    self.outHandler(command, all_but_first_2, second_word)
                    return False

                if command == '/login':
                    self.outHandler(command, all_but_first_2, second_word)
                    self.room_change(self.activeRoom)
                    return False

        else:
            if input == '/help':
                self.outHandler(input, '', self.activeRoom)
                return False

        self.outHandler("message", input, self.activeRoom)
        return True

    def insert(self, time_stamp, user, string, room, condition):

        global outputs
        colors = ['#000000','#008080','#ea8a00','#b607c6']
        start = ['&lt;','','*','!!']
        closing = ['&gt;','','*','!!']


        if string not in self.emoticonList:
            outputs[room].append(str('<font color="' + colors[condition] + '">[' + time_stamp + '] ' + start[condition] + user + closing[condition] + ' ' + string + '</font>'))

        else:
            outputs[room].append("")
            sentence = string.split()
            outputs[room].append(str('<font color="' + colors[condition] + '">[' + time_stamp + '] ' + start[condition] + user + closing[condition] + ' </font>'))

            for k in range(len(sentence)):
                word = sentence[k]
                matchFound = False
                for emoticon in self.emoticonList[:]:
                    if word == emoticon:
                        matchFound = True
                        outputs[room].append('<br /><img src="image/emoticons/' + word + '.jpg" width="160"/><br>')
                if matchFound == False:
                    outputs[room].insertPlainText(word + " ")

    def outHandler(self, opt, arg, target):
        try:
            self.client_socket.send(self.jsonMaker(opt, arg, target).encode())
            # self.client_socket.send(struct.pack("i", len(self.jsonMaker(opt, arg, target))) + self.jsonMaker(opt, arg, target).encode())
        except:
            import traceback
            traceback.print_exc()
            pass
        return "none"

    # Input: Opção correspondente à função a ser utilizada; Variaveis a serem utilizadas como argumentos na função
    # Output: Mensagem formata em Json a ser enviada ao utilizador

    def jsonMaker(self, opt, arg, target):
        final = {"jsonrpc": "2.0"}
        self.id = self.id + 1
        final.update({"id": self.id, "method": opt, "params": arg, "target": target})
        return json.dumps(final)



if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = App()

    sys.exit(app.exec_())