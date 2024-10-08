#!/usr/bin/env python3

import socket
import sys
import os
import time
import szasar
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

SERVER = 'localhost'
PORT = 6012
MONITORED_DIRECTORY = '.'
ER_MSG = (
    "Correcto.",
    "Comando desconocido o inesperado.",
    "Usuario desconocido.",
    "Clave de paso o password incorrecto.",
    "Error al crear la lista de ficheros.",
    "El fichero no existe.",
    "Error al bajar el fichero.",
    "Un usuario anonimo no tiene permisos para esta operacion.",
    "El fichero es demasiado grande.",
    "Error al preparar el fichero para subirlo.",
    "Error al subir el fichero.",
    "Error al borrar el fichero.",
    "Error al crear el directorio.",
    "Error al borrar el directorio.",
    "Error al renombrar el directorio.",
    "Error de permisos.",
    "El directorio no existe.",
    "El directorio ya existe."
)

def iserror( message ):
	if( message.startswith( "ER" ) ):
		code = int( message[2:] )
		print( ER_MSG[code] )
		return True
	else:
		return False

def int2bytes( n ):
	if n < 1 << 10:
		return str(n) + " B  "
	elif n < 1 << 20:
		return str(round( n / (1 << 10) ) ) + " KiB"
	elif n < 1 << 30:
		return str(round( n / (1 << 20) ) ) + " MiB"
	else:
		return str(round( n / (1 << 30) ) ) + " GiB"

class FileHandler(FileSystemEventHandler):
    def __init__(self, socket):
        self.socket = socket

    def on_created(self, event):
        if event.is_directory:
            self.create_directory(event.src_path)
        else:
            self.upload_file(event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self.upload_file(event.src_path)

    def on_deleted(self, event):
        if event.is_directory:
            self.delete_directory(event.src_path)
        else:
            self.delete_file(event.src_path)

    def on_moved(self, event):
        if event.is_directory:
            self.rename_directory(event.src_path, event.dest_path)
        else:
            self.delete_file(event.src_path)
            self.upload_file(event.dest_path)

    def upload_file(self, filepath):
        rel_path = os.path.relpath(filepath, MONITORED_DIRECTORY)
        try:
            filesize = os.path.getsize(filepath)
            with open(filepath, "rb") as f:
                filedata = f.read()
        except:
            print(f"No se ha podido acceder al fichero {rel_path}.")
            return

        message = f"{szasar.Command.Upload}{rel_path}?{filesize}\r\n"
        self.socket.sendall(message.encode("ascii"))
        message = szasar.recvline(self.socket).decode("ascii")
        if iserror(message):
            return

        message = f"{szasar.Command.Upload2}\r\n"
        self.socket.sendall(message.encode("ascii"))
        self.socket.sendall(filedata)
        message = szasar.recvline(self.socket).decode("ascii")
        if not iserror(message):
            print(f"El fichero {rel_path} se ha enviado correctamente.")

    def delete_file(self, filepath):
        rel_path = os.path.relpath(filepath, MONITORED_DIRECTORY)
        message = f"{szasar.Command.Delete}{rel_path}\r\n"
        self.socket.sendall(message.encode("ascii"))
        message = szasar.recvline(self.socket).decode("ascii")
        if not iserror(message):
            print(f"El fichero {rel_path} se ha borrado correctamente.")

    def create_directory(self, dirpath):
        rel_path = os.path.relpath(dirpath, MONITORED_DIRECTORY)
        message = f"{szasar.Command.CreateDir}{rel_path}\r\n"
        self.socket.sendall(message.encode("ascii"))
        message = szasar.recvline(self.socket).decode("ascii")
        if not iserror(message):
            print(f"El directorio {rel_path} se ha creado correctamente.")

    def delete_directory(self, dirpath):
        rel_path = os.path.relpath(dirpath, MONITORED_DIRECTORY)
        message = f"{szasar.Command.DeleteDir}{rel_path}\r\n"
        self.socket.sendall(message.encode("ascii"))
        message = szasar.recvline(self.socket).decode("ascii")
        if not iserror(message):
            print(f"El directorio {rel_path} se ha borrado correctamente.")

    def rename_directory(self, src_path, dest_path):
        src_rel_path = os.path.relpath(src_path, MONITORED_DIRECTORY)
        dest_rel_path = os.path.relpath(dest_path, MONITORED_DIRECTORY)
        message = f"{szasar.Command.RenameDir}{src_rel_path}?{dest_rel_path}\r\n"
        self.socket.sendall(message.encode("ascii"))
        message = szasar.recvline(self.socket).decode("ascii")
        if not iserror(message):
            print(f"El directorio {src_rel_path} se ha renombrado a {dest_rel_path} correctamente.")

if __name__ == "__main__":
    if len( sys.argv ) > 3:
        print( "Uso: {} [<servidor> [<puerto>]]".format( sys.argv[0] ) )
        exit( 2 )

    if len( sys.argv ) >= 2:
        SERVER = sys.argv[1]
    if len( sys.argv ) == 3:
        PORT = int( sys.argv[2])
            
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((SERVER, PORT))

    while True:
        user = input( "Introduce el nombre de usuario: " )
        message = "{}{}\r\n".format( szasar.Command.User, user )
        s.sendall( message.encode( "ascii" ) )
        message = szasar.recvline( s ).decode( "ascii" )
        if iserror( message ):
            continue

        password = input( "Introduce la contraseña: " )
        message = "{}{}\r\n".format( szasar.Command.Password, password )
        s.sendall( message.encode( "ascii" ) )
        message = szasar.recvline( s ).decode( "ascii" )
        if not iserror( message ):
            break

    event_handler = FileHandler(s)
    observer = Observer()
    observer.schedule(event_handler, path=MONITORED_DIRECTORY, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

    message = f"{szasar.Command.Exit}\r\n"
    s.sendall(message.encode("ascii"))
    message = szasar.recvline(s).decode("ascii")
    s.close()