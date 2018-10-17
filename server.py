import asyncore
import socket
import threading
import json, datetime, time, struct, os, pickle

rooms_list = {}
users_list = {}
logged_list = {}

class ServerManager():

# Input: endereço do servidor, porta do servidor, funções exteriores a serem registadas
# Contexto: É criado o ciclo sobre o qual o servidor irá executar até haver um /exit por parte do utilizador
#           Aquando a inicialização da classe, é criado o canal #Lobby e a informação guardada em ficheiros é recuperada

    def __init__(self, host, port, *outFunctions):

        self.infoRetriever()

        self.room_maker("#Lobby",datetime.datetime.now().strftime("%A %B %d %H:%M:%S"),'public',False, 'Server')

        self.cmd = None
        self.status = None
        self.commandsList = ('exit', 'ping', 'broadcast', 'addRoom', 'msg')

        while (self.cmd != '/exit'):
            try:
                if (self.status == None):
                    self.server = Server(host, port)
                    self.loop_thread = threading.Thread(target=asyncore.loop, name="Asyncore Loop")
                    self.loop_thread.daemon = True
                    self.loop_thread.start()
                    self.server.listen(5)
                    self.status = 'active'
                self.cmd = input("> ")
            except:
                import traceback
                traceback.print_exc()
                print("Error starting server")

            self.command_inspector(self.cmd)

# Contexto: O dicionário que contém os quartos é convertido para outro dicionário que não contém os objectos (clientes)
#           Este novo dicionário é guardado para que possa ser recuperado numa nova sessão

    def room_savior(self):
        try:

            global rooms_list
            rooms_listB = {}

            for rooms in rooms_list.keys():
                room = ''.join(rooms)
                if not room == '#public':
                    date = rooms_list[''.join(rooms)]["date"]
                    status = rooms_list[''.join(rooms)]["status"]
                    mods = rooms_list[''.join(rooms)]["mods"]
                    rooms_listB.update({room :{'date': date, 'status': status, 'mods' : mods}})

                with open('rooms.pickle', 'wb') as handle:
                    pickle.dump(rooms_listB, handle, protocol=pickle.HIGHEST_PROTOCOL)
        except:
            import traceback
            traceback.print_exc()

# Contexto: O dicionário que contém os utilizadores é guardado para que possa ser recuperado numa nova sessão

    def user_savior(self):
        try:
            global users_list

            with open('users.pickle', 'wb') as handle:
                pickle.dump(users_list, handle, protocol=pickle.HIGHEST_PROTOCOL)
        except:
            import traceback
            traceback.print_exc()

# Contexto: Os dicionários de quartos e utilizadores são preenchidos com base em ficheiros externos
#           A cada iteração, o respectivo quarto/utlizador é criado

    def infoRetriever(self):
        global rooms_list
        global users_list

        try:
            with open('rooms.pickle', 'rb') as handle:
                rooms_listB = pickle.load(handle)

                for rooms in rooms_listB.keys():
                    room = ''.join(rooms)
                    date = rooms_listB[room]["date"]
                    status = rooms_listB[room]["status"]
                    modsList = rooms_listB[room]["mods"]

                    self.room_maker(room, date, status, False, modsList)
        except:
            pass

        try:
            with open('users.pickle', 'rb') as handle:
                users_listB = pickle.load(handle)
                for users in users_listB.keys():
                    user = ''.join(users)
                    password = users_listB[user]["password"]
                    exDate = users_listB[user]["expire-date"]

                    self.user_loader(user, password, exDate)
        except:
            pass

# Input: Texto introduzido na shell do servidor
# Contexto: Caso necessário, é possivel fazer broadcast para todos os utilizadores, criar um novo quarto ou
#           enviar uma mensagem pessoal a um utilizador

    def command_inspector(self, input):

        if len(input.split()) >= 2:
            input_split = input.split()
            command = input_split[0]
            param = input_split[1]
        else:
            command = input

        if command[0] == '/' and command[1:] in self.commandsList:
            if (command == '/ping'):
                x = 5
                while (x > 0):
                    print(x)
                    x = x - 1

            elif command == '/broadcast':
                global rooms_list
                for users in rooms_list['#Lobby']['users'].keys():
                    self.server_msg(users, 0, (str(input_split[1:])).strip("['']"), 'broadcast')

            elif command == '/addRoom':
                self.room_maker((str(input_split[1:])).strip("['']"), datetime.datetime.now().strftime("%A %B %d %H:%M:%S"), 'public', True, 'Server')
                self.broadcast_rooms()

            elif command == "/msg":
                for port, name in rooms_list['#Lobby']['users'].items():
                    if name == param:
                        self.out_handler(port, self.jsonMaker_to(datetime.datetime.utcnow().strftime("%H:%M:%S"),'Server',0, (' '.join(input_split[2:])), param, 'personal'))
                        print('Message sent to ' + param + ' > ' + (' '.join(input_split[2:])))

# Input: Recebe os parametros a serem enviados ao cliente
# Output: Devolve o valores em formato json
# Contexto: O jsonMaker_to envia uma mensagem para ser apresentada num quarto especifico;
#           O jsonMaker_generic envia uma mensagem para ser apresentada no quarto activo
#           O jsonMaker responde a uma pergunta por parte do cliente

    def jsonMaker_to(self, time, user, id, message, room, target):
        return json.dumps({"id": id, "jsonrpc": "2.0", "time": time, "user": user, "room" : room, target: message})

    def jsonMaker_generic(self, time, user, id, message, target):
        return json.dumps({"id": id, "jsonrpc": "2.0", "time": time, "user": user, target: message})

    def jsonMaker(self, reason, result, id):
        return json.dumps({"id": id, "jsonrpc": "2.0", reason: result})

# Input: Destino da mensagem; mensagem
# Contexto: Envia para o cliente a mensagem numa estrutura com a sua dimensão para que esta seja lida correctamente

    def out_handler(self, client, message):
        client.send(struct.pack("i", len(message)) + message.encode())

# Input: Nome do quarto; data de criação; status (publico ou privado); necessidade de salvar; moderadores
# Output: Retorna True caso um quarto com o mesmo nome não seja encontrado
# Contexto: É criado um novo quarto com os dados recebidos caso um quarto de nome igual não seja encontrado
#           Se for encontrado, é devolvido False para posteriormente dar indicação ao cliente que já existe um quarto
#           com o mesmo nome. Os moderadores podem ser adicionados de forma singular ou em tuplo

    def room_maker(self, room_name, date, status, need_saving, *mod):
        global rooms_list

        for room in rooms_list.keys():
            if ''.join(room) == room_name:
                return False

        rooms_list.update({room_name: {'users': {}, 'banned_users' : [], 'mods' : [], 'date' : date, 'status' : status}})

        for mods in mod:
            if type(mods) == list:
                for list_tuple in mods:
                    rooms_list[room_name]['mods'].append(list_tuple)
            else:
                rooms_list[room_name]['mods'].append(mods)

        if(need_saving):
            self.room_savior()
        return True

# Contexto: Para os utilizadores no #Lobby (onde obrigatoriamente estão todos os utlizadores), é partilhada uma lista de
#           quartos baseada no *share_rooms*

    def broadcast_rooms(self):
        for users in rooms_list['#Lobby']['users'].keys():
            list = self.share_rooms(users)
            self.out_handler(users, self.jsonMaker('rooms', list, 0))

# Input: Objecto/cliente a ser tido em consideração
# Output: Lista de canais ou o utilizador está presente, é moderador, ou o status do canal é publico

    def share_rooms(self, user):
        try:
            global rooms_list
            user_name = rooms_list['#Lobby']['users'][user]
            temporary_list = []
            for room in rooms_list.keys(): #user in rooms_list[room]['mods'] or
                if user in rooms_list[room]['users'] or user_name in rooms_list[room]['mods'] or rooms_list[room]['status'] == 'public':
                    temporary_list.append(room)
            return list(temporary_list)
        except:
            import traceback
            traceback.print_exc()

# Input: Utilizador a ser adicionado a um canal
# Contexto: Caso o utilizador não esteja já no canal, o mesmo é adicionado e os utlizadores lá presentes são avisados *server_joined*(menos
#           o utilizador que entrou), desta forma é possivel evitar que um utilizador que alterne entre canais esteja sempre
#           a sair e entrar. caso o *add_type* seja private, o utilizador em questão é avisado que tem agora um novo quarto.

    def add_to_room(self, room_name, user_name, user_ip, add_type):
        global rooms_list

        if user_ip not in rooms_list[room_name]['users']:
            rooms_list[room_name]['users'].update({user_ip : user_name})

            if add_type == 'private':
                self.out_handler(user_ip, self.jsonMaker('rooms', self.share_rooms(user_ip), 2))
                self.server_msg(user_ip, 0, (" You've been invited to join " + room_name), 'server_msg')
                self.share_users_in_room(room_name)

            room_type = rooms_list[room_name]['status']
            self.out_handler(user_ip, self.jsonMaker_to(datetime.datetime.now().strftime("%H:%M:%S"), '***', 0, ' Now talking in ' + room_type + ' channel ' + room_name, room_name, 'admin'))
            self.clean_old_users(room_name)

            for users in rooms_list[room_name]['users'].keys():
                if not users == user_ip:
                    self.server_joined(users, user_name, room_name)

            self.out_handler(user_ip, self.jsonMaker_to(datetime.datetime.now().strftime("%H:%M:%S"), '***', 0, ' Set by ' + str(rooms_list[room_name]['mods'][0]).strip("{:'}") + ' on ' + rooms_list[room_name]['date'], room_name, 'admin'))

# Input: Quarto a ser apagado
# Contexto: Caso o quarto exista, o mesmo será apagado

    def delete_room(self, room_name):
        global rooms_list
        if room_name in rooms_list:
            del rooms_list[room_name]

# Input: Quarto a ser tido em consideração
# Contexto: Para os utilizadores no quarto de input, é partilhada uma lista de utilizadores baseada no *share_users*

    def share_users_in_room(self, room):
        global rooms_list
        self.clean_old_users(room)

        for users in rooms_list[room]['users'].keys():
            try:
                self.out_handler(users, self.jsonMaker('users', self.share_users(room), 0))
            except:
                pass

# Input: Quarto a ser tido em consideração
# Output: Lista de utilizadores em quarto

    def share_users(self, room):
        try:
            global rooms_list
            return list(rooms_list[room]['users'].values())
        except:
            import traceback
            traceback.print_exc()

# Input: Quarto a ser tido em consideração
# Contexto: Para evitar que seja feita uma lista de utilizador num canal, constituida por utilizadores já desconectados,
#           é testada a conexão do utilizador e o mesmo é descartado caso a conexão apresente problemas

    def clean_old_users(self, room):
        global rooms_list
        no_longer_avaliable = []
        for exceptions in rooms_list[room]['users'].keys():
            if not (exceptions.connected):
                no_longer_avaliable.append(exceptions)

        for remove_this in no_longer_avaliable:
            rooms_list[room]['users'].pop(remove_this)

# Input: Nome do utilizador a ser actualizado; Ip do utilizador
# Output: Nome do utilizador antes de ser feito o update
# Contexto: Caso um utilizador Y seja autenticado com o nome X, os valores no dicionário tem de ser actualizados. Esta
#           actualização é realizada com base no Ip

    def switch_user_name(self,user_name, user_ip):
        global rooms_list
        for rooms in rooms_list.keys():
            for ip, userName in rooms_list[rooms]['users'].items():
                if ip == user_ip:
                    name_to_return = userName
                    rooms_list[rooms]['users'].update({user_ip: user_name})
        return name_to_return

# Input: Utilizador de destino; nome do utilizador que se juntou ao canal; nome do canal
# Contexto: Se um novo utilizador se junta ao canal X, os restantes utilizadores recebem uma mensagem da sua presença

    def server_joined(self, user_ip, user_name, room_name):
        self.out_handler(user_ip, self.jsonMaker_to(datetime.datetime.now().strftime("%H:%M:%S"), '',0,  user_name + ' has joined the channel', room_name, 'admin'))

# Input: Utilizador de destino; id; mensagem; tipo de mensagem
# Contexto: Função que sintetiza o envio de uma mensagem a um utilizador

    def server_msg(self, target, id, msg, reason):
        self.out_handler(target, self.jsonMaker_generic(datetime.datetime.now().strftime("%H:%M:%S"), '***', id, msg, reason))

# Input: Nome do utilizador antes de um update ao nome; Nome do utilizado após update
# Contexto: Anuncia canais onde utilizador X está presente, que o seu novo nome agora é Y

    def broadcast_where_user_is(self, old_name, new_name):
        global rooms_list

        for room in rooms_list.keys():
            if new_name in rooms_list[room]['users'].values():
                for userIp in rooms_list[room]['users'].keys():
                    self.out_handler(userIp,self.jsonMaker_to(datetime.datetime.now().strftime("%H:%M:%S"), '', 0, old_name + ' is now known as ' + new_name , room,'admin'))

# Input: Nome do utilizador
# Output: Retorna socket do utilizador com base no nome dado

    def ip_finder(self, user_name):
        global rooms_list
        userIp = 1
        for ip, name in rooms_list['#Lobby']['users'].items():
            if name == user_name:
                userIp = ip
        return userIp

# Input: Nome do utilizador; password; data de expiração
# Contexto: Utilizador é adicionado com base em ficheiro externo

    def user_loader(self, user_name, password, date):
        global users_list
        users_list.update({user_name : {'password' : password, 'expire-date' : date}})

# Input: Nome do utilizador; password; data de expiração
# Contexto: Utilizador é adicionado com base num novo registo

    def user_maker(self, user_name, password, *need_saving):
        global users_list
        users_list.update({user_name : {'password' : password, 'expire-date' : datetime.datetime.now() + datetime.timedelta(days=7)}})

        if (need_saving):
            self.user_savior()

# Input: Nome do utilizador; password
# Output: Retorna True caso o utilizador/password correspondam

    def verify_user(self, username, password):
        global users_list
        for users in users_list:
            if(''.join(users) == username and users_list[users]['password'] == password):
                return True
        return False

# Input: Nome do utilizador;
# Output: Retorna True caso o utilizador esteja logado

    def is_user_logged(self, username):
        global logged_list
        for users in logged_list:
            if ''.join(users) == username:
                return True
        return False

# Input: Nome do utilizador;
# Contexto: Utilizador é adicionado à lista de utilizadores logados e o tempo de expiração do nome é renovado

    def log_user(self, username):
        global logged_list
        logged_list.update({ username : {'date' : datetime.datetime.now().strftime("%A %B %d %H:%M:%S")}})


class EchoHandler(asyncore.dispatcher, ServerManager):
    def handle_read(self):
        self.notificationsList = ["notification", "update"]

        try:
            msg = self.recv(1024).decode()
            if msg:
                python_obj = json.loads(msg)
                print("Message received from %s" % repr(self.addr))
                print(python_obj)

        # try:
        #     size = struct.unpack("i", self.recv(struct.calcsize("i")))[0]
        #     data = ""
        #     while len(data) < size:
        #         message = self.recv(size - len(data))
        #         data += message.decode()
        #         python_obj = json.loads(data.strip())

                if python_obj["method"] == "welcome":

                    self.add_to_room(python_obj["target"], python_obj["params"], self, 'public')
                    self.out_handler(self, self.jsonMaker('rooms', self.share_rooms(self), python_obj["id"]))
                    self.share_users_in_room(python_obj["target"])

                elif python_obj["method"] == "/register":

                    if(python_obj["params"] == ''):
                        self.server_msg(self, python_obj["id"], (' Username cannot be registered without a password '), 'server_msg')
                    else:
                        if(self.check_if_name_exists(python_obj["target"],self) and self.check_name_expiration_date(python_obj["target"],self)):
                            if(self.check_if_user_exists(python_obj["target"])):
                                self.server_msg(self, python_obj["id"],(' Username registered successfully '), 'server_msg')
                            else:
                                self.server_msg(self, python_obj["id"], (' Username updated successfully '),'server_msg')
                            self.user_maker(python_obj["target"], python_obj["params"], True)
                        else:
                            self.server_msg(self, python_obj["id"], (' Username is already being used '), 'server_msg')

                elif python_obj["method"] == "/login":

                    if (self.verify_user(python_obj["target"], python_obj["params"])):
                        self.log_user(python_obj["target"])
                        self.server_msg(self, python_obj["id"], (' Logged in successfully '), 'server_msg')
                        self.broadcast_where_user_is(self.switch_user_name(python_obj["target"],self), python_obj["target"])
                        self.out_handler(self,self.jsonMaker('new_name', python_obj["target"],python_obj["id"]))
                    else:
                        self.server_msg(self, python_obj["id"], (' Invalid credentials '), 'server_msg')

                elif python_obj["method"] == "/addRoom" or python_obj["method"] == "/addPriv":

                    if self.is_user_logged(rooms_list['#Lobby']['users'][self]):
                        if python_obj["method"] == "/addRoom":
                            room_type = 'public'
                        else:
                            room_type = 'private'

                        if(self.room_maker(python_obj["params"],datetime.datetime.now().strftime("%A %B %d %H:%M:%S"),room_type,True, rooms_list['#Lobby']['users'][self],'Server')):
                            self.broadcast_rooms()
                            self.add_to_room(python_obj["params"], rooms_list['#Lobby']['users'][self], self, room_type)
                            self.out_handler(self, self.jsonMaker('move_to_room', python_obj["params"], python_obj["id"]))

                            self.share_users_in_room(python_obj["params"])
                            self.server_msg(self, python_obj["id"], (' New room successfully created '), 'server_msg')
                        else:
                            self.server_msg(self, python_obj["id"], (' Room name is already being used '), 'server_msg')
                    else:
                        self.server_msg(self, python_obj["id"], (' You need to be logged to make a new room '), 'server_msg')

                elif python_obj["method"] == "/invite":

                    if self.check_mod(self, python_obj["target"]):
                        self.add_to_room(python_obj["target"], python_obj["params"], self.ip_finder(python_obj["params"]), 'private')
                        self.server_msg(self, python_obj["id"], (python_obj["params"] + ' invited with success '),'server_msg')
                    else:
                        self.server_msg(self, python_obj["id"], (' Only a room moderator can invite '),'server_msg')

                elif python_obj["method"] == "/delete":

                    if self.room_exists(python_obj["params"]):
                        if self.check_mod(self, python_obj["params"]):
                            self.delete_room(python_obj["params"])
                            self.broadcast_rooms()
                            self.out_handler(self, self.jsonMaker('move_to_room', '#Lobby', python_obj["id"]))
                            self.server_msg(self, python_obj["id"], (python_obj["params"] + ' deleted with success'), 'server_msg')
                            self.room_savior()
                        else:
                            self.server_msg(self, python_obj["id"], (' Only a room moderator can delete channels '), 'server_msg')
                    else:
                        self.server_msg(self, python_obj["id"], (' Room not found '),'server_msg')


                elif python_obj["method"] == "/nameCheck":

                    if not self.check_if_user_exists(python_obj["params"]):
                        self.out_handler(self, self.jsonMaker('result', 'password', python_obj["id"]))
                    elif self.check_if_name_exists(python_obj["params"], self):
                        self.out_handler(self, self.jsonMaker('result', True, python_obj["id"]))
                    else:
                        self.out_handler(self, self.jsonMaker('result', False, python_obj["id"]))

                elif python_obj["method"] == "/passCheck":

                    if (self.verify_user(python_obj["params"], python_obj["target"])):
                        self.log_user(python_obj["params"])
                        self.out_handler(self, self.jsonMaker('result', True, python_obj["id"]))
                        self.server_msg(self, python_obj["id"], (' Logged in successfully '), 'server_msg')
                    else:
                        self.out_handler(self, self.jsonMaker('result', 'invalid_password', python_obj["id"]))

                elif python_obj["method"] == "/msg":

                    user_found = False
                    for port, name in rooms_list['#Lobby']['users'].items():
                        if name == python_obj["target"]:
                            self.out_handler(port,self.jsonMaker_generic(datetime.datetime.utcnow().strftime("%H:%M:%S"),rooms_list['#Lobby']['users'][self],python_obj["id"],python_obj["target"],'personal'))
                            user_found = True

                    if user_found == False:
                        self.server_msg(self, python_obj["id"], ('No such nick: ' + python_obj["target"]),'server_msg')

                elif python_obj["method"] == "/help":

                    self.out_handler(self, self.jsonMaker_to(datetime.datetime.now().strftime("%H:%M:%S"), '***', python_obj["id"], ('<p>The following commands are avaliable:</p>/register (userName) (userPassword)<br/>/login (userName) (userPassword)<p>- You can re-register your username to update the password -</p>/addRoom (#roomName)<br/>/addPriv (#roomName)<p>- You need to be logged to make a new room -</p>/invite (userName)<br/>/delete (#roomName)<p>- You need to a mod to invite or delete -</p>/msg (userName) (message)'),python_obj["target"], 'admin'))

                elif python_obj["method"] == "/exit":
                    self.out_handler(self, self.jsonMaker('order_exit', True, python_obj["id"]))
                    self.close()

                else:
                    if python_obj["method"] in self.notificationsList:
                        print("notification received")
                    else:
                        print("Message received from %s" % repr(self.addr))

                        try:
                            for users in rooms_list[python_obj["target"]]['users'].keys():
                                self.out_handler(users, self.jsonMaker_to(datetime.datetime.utcnow().strftime("%H:%M:%S"),rooms_list[python_obj["target"]]['users'][self], python_obj["id"],python_obj["params"], python_obj["target"],'message'))

                        except:
                            print("ops")

        except:
            import traceback
            traceback.print_exc()
            print("Something went wrong\nA team of highly trained monkeys has been dispatched")

# Input: Nome do canal;
# Output: Retorna True se o nome existir na lista de quartos

    def room_exists(self, room_name):
        if room_name in rooms_list:
            return True

# Input: Nome do utilizado; Ip do utilizador
# Contexto: Verifica se o nome que está a ser registado pertence a outra conta já adicionada. Caso positivo, é verificado
#           se a conta do nome pretendido já expirou. A excepção corresponde a ele mesmo

    def check_name_expiration_date(self, name, *exception):
        global users_list

        if self.ip_finder(name) == exception[0]:
            return True

        for names in users_list.keys():
            if name == names:

                if datetime.datetime.now() > users_list[names]['expire-date']:
                    return True
                else:
                    return False
        return True

# Input: Nome do utilizador
# Output: Retorna True se conta não existe

    def check_if_user_exists(self, name):
        global users_list
        for names in users_list.keys():
            if name == names:
                return False
        return True

# Input: Nome do utilizador
# Output: Retorna True se nome não existe ou pertencer à excepção (ele mesmo)

    def check_if_name_exists(self, name, *exception):
        global rooms_list

        if self.ip_finder(name) == exception[0]:
            return True

        for room in rooms_list.keys():
            if name in rooms_list[room]['users'].values():
                return False

        return True

# Input: Nome do utilizador; Quarto a considerar
# Contexto: Retorna True utilizador for moderador no canal

    def check_mod(self, user, room):
        if self.room_exists(room):
            user_name = rooms_list['#Lobby']['users'][user]
            for users in rooms_list[room]['mods']:
                if users == user_name:
                    return True

# Input: asyncore.dispatcher
# Contexto: Inicialização do servidor

class Server(asyncore.dispatcher):

    # Input: endereço do servidor, porta do servidor

    def __init__(self, host, port):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind((host, port))
        self.listen(5)
        print('Server up and running on %s:%s' % (host, port))

    def handle_accept(self):
        pair = self.accept()
        if pair is not None:
            sock, addr = pair
            print('New client connect from %s' % repr(addr))
            handler = EchoHandler(sock)

server = ServerManager('0.0.0.0', int('8000'))