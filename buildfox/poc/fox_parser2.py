
# tired of grako unable parse whitespace correctly
# lets see if it's easy to parse manifest by hand

import re
from pprint import pprint

re_newline_escaped = re.compile("\$+$")
re_comment = re.compile("(?<!\$)\#.*$") # looking for not escaped #
re_identifier = re.compile("[a-zA-Z0-9_.-]+")
re_path = re.compile("(\$\||\$ |\$:|[^ :|\n])+")

class Parser:
	def __init__(self):
		self.filename = "fox_parser_test.ninja"
		with open(self.filename, "r") as f:
			self.lines = f.read().splitlines()

	def parse(self):
		self.line_i = 0
		while self.line_i < len(self.lines):
			self.parse_line()

	def parse_line(self):
		# get line
		if not self.next_line():
			return

		# find first identifier, next actions will be based on it
		self.command = self.read_identifier()
		if self.command == "rule":
			self.read_rule()
		elif self.command == "build":
			self.read_build()
		elif self.command == "default":
			self.read_default()
		elif self.command == "pool":
			self.read_pool()
		elif self.command == "include":
			self.read_include()
		elif self.command == "subninja":
			self.read_subninja()
		elif self.command == "filter":
			pass
		elif self.command == "auto":
			self.read_auto()
		else:
			self.read_assign()

	def read_rule(self):
		rule = self.read_identifier()
		self.read_eol()
		return (rule)

	def read_build(self):
		self.expect_token()
		targets_explicit = []
		targets_implicit = []
		inputs_explicit = []
		inputs_implicit = []
		inputs_order = []

		# read targets explicit
		while self.line_stripped[0] not in ["|", ":"]:
			targets_explicit.append(self.read_path())
			self.expect_token()

		# read targets implicit
		if self.line_stripped[0] == "|":
			self.line_stripped = self.line_stripped[1:].strip()
			self.expect_token()
			while self.line_stripped[0] != ":":
				targets_implicit.append(self.read_path())
				self.expect_token()

		# read rule name
		self.expect_token(":")
		self.line_stripped = self.line_stripped[1:].strip()
		rule = self.read_identifier()

		if self.line_stripped:
			# read inputs explicit
			while self.line_stripped and (self.line_stripped[0] != "|"):
				inputs_explicit.append(self.read_path())

			# read inputs implicit
			if (len(self.line_stripped) >= 2) and (self.line_stripped[0] == "|") and (self.line_stripped[1] != "|"):
				self.line_stripped = self.line_stripped[1:].strip()
				while self.line_stripped and (self.line_stripped[0] != "|"):
					inputs_implicit.append(self.read_path())

			# read inputs order
			if self.line_stripped and (self.line_stripped[0] == "|") and (self.line_stripped[1] == "|"):
				self.line_stripped = self.line_stripped[2:].strip()
				while self.line_stripped:
					inputs_order.append(self.read_path())

		self.read_eol()
		return (targets_explicit, targets_implicit, rule, inputs_explicit, inputs_implicit, inputs_order)

	def read_default(self):
		self.expect_token()
		paths = []
		while self.line_stripped:
			paths.append(self.read_path())
		self.read_eol()
		return (paths)

	def read_pool(self):
		pool = self.read_identifier()
		self.read_eol()
		return (pool)

	def read_include(self):
		return self.read_one_path()

	def read_subninja(self):
		return self.read_one_path()

	def read_one_path(self):
		path = self.read_path()
		self.read_eol()
		return (path)

	def read_auto(self):
		self.expect_token()
		targets = []
		inputs = []

		# read targets
		while self.line_stripped[0] != ":":
			targets.append(self.read_path())
			self.expect_token()

		# read rule name
		self.expect_token(":")
		self.line_stripped = self.line_stripped[1:].strip()
		rule = self.read_identifier()

		# read inputs
		self.expect_token()
		while self.line_stripped:
			inputs.append(self.read_path())
		self.read_eol()
		return (targets, rule, inputs)

	def read_assign(self):
		name = self.command
		self.expect_token("=")
		value = self.line_stripped[1:].strip()
		return (name, value)

	def read_identifier(self):
		identifier = re_identifier.match(self.line_stripped)
		if not identifier:
			raise ValueError("expected token 'identifier' in '%s' (%s:%i)" % (
				self.line_stripped,
				self.filename,
				self.line_num
			))
		self.line_stripped = self.line_stripped[identifier.span()[1]:].strip()
		return identifier.group()

	def expect_token(self, name = ""):
		if name:
			if (not self.line_stripped) or (not self.line_stripped.startswith(name)):
				raise ValueError("expected token '%s' in '%s' (%s:%i)" % (
					name,
					self.line_stripped,
					self.filename,
					self.line_num
				))
		else:
			if not self.line_stripped:
				raise ValueError("expected token(s) in '%s' (%s:%i)" % (
					self.line_stripped,
					self.filename,
					self.line_num
				))

	def read_path(self):
		path = re_path.match(self.line_stripped)
		if not path:
			raise ValueError("expected token 'path' in '%s' (%s:%i)" % (
				self.line_stripped,
				self.filename,
				self.line_num
			))
		self.line_stripped = self.line_stripped[path.span()[1]:].strip()
		return path.group()

	def read_eol(self):
		if self.line_stripped:
			raise ValueError("unexpected token '%s' in '%s' (%s:%i)" % (
				self.line_stripped,
				self.line,
				self.filename,
				self.line_num
			))

	def next_line(self):
		if self.line_i >= len(self.lines):
			return False

		self.line_stripped = ""
		while (not self.line_stripped) and (self.line_i < len(self.lines)):
			self.line = ""
			self.line_num = self.line_i

			# dealing with escaped newlines
			newline_escaped = True
			while newline_escaped and (self.line_i < len(self.lines)):
				self.line += self.lines[self.line_i]
				self.line_i += 1
				newline_escaped = re_newline_escaped.search(self.line)
				if newline_escaped:
					l, r = newline_escaped.span()
					# in some cases we can have $$, $$$$, etc in the end
					# which are escaped $ combinations, and they don't escape newline
					if (r - l) % 2:
						# in case if they do $, $$$, etc, we need to strip last one
						self.line = self.line[:-1]
					else:
						newline_escaped = None

			# line is ready for processing
			self.line_stripped = self.line.strip()

			# skip empty lines
			if not self.line_stripped:
				continue

			# fast strip comment
			if self.line_stripped and self.line_stripped[0] == "#":
				self.line_stripped = ""
				continue

			# slower strip comments
			comment_eol = re_comment.search(self.line_stripped)
			if comment_eol:
				self.line_stripped = self.line_stripped[:comment_eol.span()[0]].strip()

		# if we can't skip empty lines, than just return failure
		if not self.line_stripped:
			return False

		# get whitespace
		self.whitespace = self.line[:self.line.index(self.line_stripped)]
		if "\t" in self.whitespace and " " in self.whitespace:
			raise ValueError("inconsistent whitespace in '%s' (%s:%i)" % (
				self.line,
				self.filename,
				self.line_num
			))
		return True

p = Parser()
p.parse()