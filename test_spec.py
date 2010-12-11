# Copyright (C) 2010, Thomas Leonard
# Visit http://0install.net for details.

from zeroinstall import SafeException
from zeroinstall.injector import model

class TestSpec:
	offline = False

	def __init__(self):
		self.test_iface = None	# The URI of the program being tested

		self.test_ifaces = []	# [Interface] - list of interfaces with specified versions
		self.test_matrix = {}	# {URI: [version]} - versions of each interface to test
		# (test_ifaces is needed because we care about the order)

		self.test_wrapper = None	# Command to execute to perform tests
		self.test_args = []	# Arguments to pass to test script

	# Yield a sequence of set((uri, version)), one for each combination to test
	def get_combos(self, ifaces):
		if not ifaces:
			yield {}
			return
		for version in self.test_matrix[ifaces[0]]:
			for combo in self.get_combos(ifaces[1:]):
				combo[ifaces[0]] = version
				yield combo.copy()

def parse_arguments(options, args):
	spec = TestSpec()

	if options.test_command:
		spec.test_wrapper = options.test_command + ' #'

	spec.offline = options.offline

	if '--' in args:
		i = args.index('--')
		spec.test_args = args[i + 1:]
		args = args[:i]

	iface = None
	for x in args:
		if x[0].isdigit() and iface:
			spec.test_matrix[iface].append(x)
		else:
			assert x not in spec.test_matrix, "Interface %s given twice!" % x
			iface = model.canonical_iface_uri(x)
			spec.test_matrix[iface] = []
			spec.test_ifaces.append(iface)

	# We don't need to specify the version of the interface under test.
	spec.test_iface = spec.test_ifaces[0]
	if not spec.test_matrix[spec.test_iface]:
		del spec.test_matrix[spec.test_iface]
		del spec.test_ifaces[0]
	
	# We do need a version for all the others (else what was the point of listing them?)
	for iface in spec.test_ifaces:
		if not spec.test_matrix[iface]:
			raise SafeException("No versions given for interface %s" % iface)

	return spec
