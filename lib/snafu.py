# Snafu: Snake Functions - Main Module

import argparse
import os
import sys
#import pathlib
import ast
import importlib
import importlib.machinery
import types
import inspect
import time
import json
import hashlib
import base64
import glob
import subprocess
import shutil
import threading

class SnafuFunctionSource:
	def __init__(self, source, scan=True):
		self.source = source
		self.size = None
		self.checksum = None
		self.content = None
		if scan:
			self.size = os.stat(source).st_size
			self.content = open(source).read()
			self.checksum = base64.b64encode(hashlib.sha256(bytes(self.content, "utf-8")).digest()).decode("utf-8")

class SnafuImport:
	functiondir = "functions-local"

	def prepare():
		os.makedirs(SnafuImport.functiondir, exist_ok=True)

	def importfunction(funcname, codezip, config, convert=False):
		funcdir = os.path.join(SnafuImport.functiondir, funcname)
		os.makedirs(funcdir, exist_ok=True)
		subprocess.run("cd {} && unzip -q ../{}".format(funcdir, os.path.basename(codezip)), shell=True)
		codefiles = glob.glob(os.path.join(funcdir, "*.py"))
		codefile = codefiles[0]
		oldcodefile = None
		if convert and config["Runtime"] == "python2.7":
			oldcodefile = codefile.replace(".py", ".py2")
			shutil.copyfile(codefile, oldcodefile)
			subprocess.run("2to3 --no-diffs -nw {} 2>/dev/null".format(codefile), shell=True)
			config["Runtime"] = "python3"
		configfile = os.path.join(funcdir, os.path.basename(codefile).split(".")[0] + ".config")
		#filename = config["Handler"].split(".")[0]
		#configfile = "functions-local/{}/{}.config".format(functionname, filename)
		f = open(configfile, "w")
		json.dump(config, f)

		return codefile, configfile, oldcodefile

class SnafuContext:
	def __init__(self):
		self.function_name = None
		self.function_version = None
		self.memory_limit_in_mb = 128

	def get_remaining_time_in_millis(self):
		return 999999

class Snafu:
	def __init__(self, quiet=False):
		self.functions = {}
		self.quiet = quiet
		self.connectormods = []
		self.interactive = False

	def info(self, s):
		if self.quiet and not self.interactive:
			return

		col_on = "\x1b[32m\x1b[1m"
		col_off = "\x1b[0m"

		timestamp = time.time()
		callid = threading.get_ident()

		print(col_on + "[{:.3f}][{}][{}]".format(timestamp, callid, s) + col_off)

	def execute(self, funcname, **kwargs):
		sourcename = None
		if "." in funcname:
			sourcename, funcnamepart = funcname.split(".")
		if funcname in self.functions:
			funcs = self.functions[funcname]
		else:
			print("Error: {} is not a function.".format(funcname), file=sys.stderr)
			return
		#if not sourcename:
		#	if len(funcs) == 1:
		#		func = list(funcs.values())[0]
		#	else:
		#		print("Error: {} is ambiguous; qualifiers: {}.".format(funcname, list(funcs.keys())), file=sys.stderr)
		#		return
		#else:
		#	if sourcename in funcs:
		#		func = funcs[sourcename]
		#	else:
		#		print("Error: {}.{} is not a function.".format(sourcename, funcname), file=sys.stderr)
		#		return

		func, config, sourceinfos = funcs
		self.info("function:{}".format(funcname))
		if config:
			if "Environment" in config:
				self.info("config:environment")
				envvars = config["Environment"]["Variables"]
				for envvar in envvars:
					os.environ[envvar] = envvars[envvar]

		args = inspect.getargspec(func)
		wantedargs = args[0]
		funcargs = []
		for wantedarg in wantedargs:
			if wantedarg in kwargs:
				funcargs.append(kwargs[wantedarg])
			elif wantedarg == "context":
				# only for convention==lambda?
				ctx = SnafuContext()
				ctx.function_name = funcname
				funcargs.append(ctx)
			else:
				if self.interactive:
					if os.isatty(sys.stdin.fileno()):
						data = input("Data for argument {} needed:".format(wantedarg))
					else:
						data = sys.stdin.read()
					funcargs.append(data)
				else:
					print("Data for argument {} needed but not supplied.".format(wantedarg))
					return

		stime = time.time()
		try:
			res = func(*funcargs)
			success = True
		except:
			self.info("exception!")
			res = None
			success = False
		self.info("result:{}".format(res))
		dtime = (time.time() - stime) * 1000
		self.info("time:{:1.3f}ms".format(dtime))
		# FIXME: this part must become mt-safe through a protected section
		f = open("snafu.csv", "a")
		print("{},{},{:1.3f},{}".format(sourcename or "", funcname, dtime, success), file=f)
		f.close()
		return res

	def connect(self, connectors):
		if not self.quiet:
			for connector in connectors:
				print("+ connector:", connector)
				if connector == "cli":
					self.interactive = True

		connectormods = []
		for connector in connectors:
			mod = importlib.import_module("connectors." + connector)
			connectormods.append(mod)

		for connectormod in connectormods:
			if "init" in dir(connectormod):
				connectormod.init(self.execute)

		self.connectormods = connectormods

		while True:
			for connectormod in connectormods:
				handled = False
				if "request" in dir(connectormod):
					f = connectormod.request()
					res = self.execute(f)
					connectormod.reply(res)
					handled = True
			if not handled:
				time.sleep(5)

	def activatefile(self, source, convention):
		sourceinfos = None
		try:
			sourceinfos = SnafuFunctionSource(source)
			sourcecode = sourceinfos.content
		except:
			print("Warning: {} is not parseable, skipping.".format(source), file=sys.stderr)
			return
		if not self.quiet:
			print("» module:", source)
		handler = None
		config = None
		configname = source.split(".")[0] + ".config"
		if os.path.isfile(configname):
			if not self.quiet:
				print("  config:", configname)
			config = json.load(open(configname))
			if config:
				if "Handler" in config:
					handler = config["Handler"]
		sourcetree = ast.parse(sourcecode)
		loader = importlib.machinery.SourceFileLoader(os.path.basename(source), source)
		mod = types.ModuleType(loader.name)
		loader.exec_module(mod)
		sourcename = os.path.basename(source).split(".")[0]
		for node in ast.walk(sourcetree):
			if type(node) == ast.FunctionDef:
				if not handler:
					handlername = "lambda_handler"
					handlerbase = sourcename
				else:
					handlerbase, handlername = handler.split(".")
				if convention != "lambda" or (node.name == handlername and sourcename == handlerbase):
					funcname = sourcename + "." + node.name
					if config and "FunctionName" in config and convention == "lambda":
						funcname = config["FunctionName"]
					if not self.quiet:
						print("  function: {}".format(funcname))
					func = getattr(mod, node.name)
					#if not node.name in self.functions:
					#	self.functions[node.name] = {}
					#self.functions[node.name][sourcename] = (func, config, sourceinfos)
					self.functions[funcname] = (func, config, sourceinfos)
				else:
					if not self.quiet:
						print("  skip function {}.{}".format(sourcename, node.name))

	def activate(self, sources, convention):
		for source in sources:
			if os.path.isfile(source):
				if source.endswith(".py"):
					self.activatefile(source, convention)
			elif os.path.isdir(source):
				#p = pathlib.Path(source)
				entries = [os.path.join(source, entry.name) for entry in os.scandir(source) if not entry.name.startswith(".")]
				self.activate(entries, convention)
			else:
				print("Warning: {} is not readable, skipping.".format(source), file=sys.stderr)

class SnafuRunner:
	def __init__(self):
		parser = argparse.ArgumentParser(description="Snake Functions as a Service")
		parser.add_argument("-c", "--convention", help="method call convention", choices=["any", "lambda"], default="any")
		parser.add_argument("-C", "--connector", help="function connectors", choices=["cli", "web", "messaging", "filesystem"], default=["cli"], nargs="+")
		parser.add_argument("-x", "--execute", help="execute a single function")
		parser.add_argument("-q", "--quiet", help="operate in quiet mode", action="store_true")
		parser.add_argument("file", nargs="*", help="source file(s) or directories to activate; uses './functions' by default")
		args = parser.parse_args()

		if not args.file:
			args.file.append("functions")
			args.file.append("functions-local")

		snafu = Snafu(args.quiet)
		snafu.activate(args.file, args.convention)
		if args.execute:
			snafu.execute(args.execute)
		else:
			try:
				snafu.connect(args.connector)
			except:
				print("Terminated.")
