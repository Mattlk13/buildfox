# mask file to mask ir

# mask IR is very similar to ninja format
# so we just reuse ninja parser :)

import string
from lib.tool_ninja_parser import ninja_Parser
from lib.mask_ir import IR
from lib.mask_esc import from_esc, from_esc_iter

def from_string(text):
	parser = ninja_Parser(parseinfo = False)
	ast = parser.parse(text, "manifest", trace = False, whitespace = string.whitespace, nameguard = True)
	ir = IR()
	mode = 0

	for expr in ast:
		if "rule" in expr:
			if mode != 0:
				raise ValueError("incorrect order in mask")
			name = expr["rule"]
			vars = {var["assign"]: from_esc(var["value"]) for var in expr["vars"]}
			ir.add_rule(name, vars)
		elif "build" in expr:
			if mode == 0:
				mode = 1
			if mode != 1:
				raise ValueError("incorrect order in mask")
			ir.add_build(
				rule_name = expr["build"],
				targets_explicit	= list(filter(len, from_esc_iter(expr["targets_explicit"]))),
				targets_implicit	= list(filter(len, from_esc_iter(expr["targets_implicit"] or []))),
				inputs_explicit		= list(filter(len, from_esc_iter(expr["inputs_explicit"] or []))),
				inputs_implicit		= list(filter(len, from_esc_iter(expr["inputs_implicit"] or []))),
				inputs_order		= list(filter(len, from_esc_iter(expr["inputs_order"] or [])))
			)
		elif "project" in expr:
			if mode == 1:
				mode = 2
			if mode != 2:
				raise ValueError("incorrect order in mask")
			mode = 2
			name = expr["project"]
			variations = {var["assign"]: list(var["value"]) for var in expr["vars"]}
			ir.add_project(name, variations)

	return ir

def from_file(filename):
	with open(filename, "r") as f:
		return from_string(f.read())
