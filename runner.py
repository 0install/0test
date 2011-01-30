# Copyright (C) 2010, Thomas Leonard
# Visit http://0install.net for details.

import os, sys
from zeroinstall.injector import autopolicy, iface_cache, model, run, handler, arch
from reporting import format_combo

class VersionRestriction(model.Restriction):
	def __init__(self, version):
		self.version = version

	def meets_restriction(self, impl):
		return impl.get_version() == self.version

	def __repr__(self):
		return "version = %s" % self.version

class TestingArchitecture(arch.Architecture):
	use = frozenset([None, "testing"])

	def __init__(self, child_arch):
		arch.Architecture.__init__(self, child_arch.os_ranks, child_arch.machine_ranks)
		self.child_arch = child_arch

def _get_implementation_path(impl):
	return impl.local_path or iface_cache.iface_cache.stores.lookup_any(impl.digests)

def run_tests(tested_iface, sels, spec):
	main_command = sels.commands and sels.commands[0]

	root_impl = sels.selections[tested_iface.uri]
	assert root_impl

	if spec.test_wrapper:
		tests_dir = None
		# $1 is the main executable, or the root of the package if there isn't one
		# We have to add the slash because otherwise 0launch interprets the path
		# relative to itself...
		if main_command and main_command.path:
			test_main = "/" + main_command.path
		else:
			test_main = "/"
	else:
		test_main = None

		if main_command.path is None:
			tests_dir = _get_implementation_path(root_impl)
		else:
			main_abs = os.path.join(_get_implementation_path(root_impl), main_command.path)
			if not os.path.exists(main_abs):
				print >>sys.stderr, "Test executable does not exist:", main_abs
				return "skipped"

			tests_dir = os.path.dirname(main_abs)

	child = os.fork()
	if child:
		# We are the parent
		pid, status = os.waitpid(child, 0)
		assert pid == child
		print "Status:", hex(status)
		if status == 0:
			return "passed"
		else:
			return "failed"
	else:
		# We are the child
		try:
			try:
				if spec.test_wrapper is None:
					os.chdir(tests_dir)
				run.execute_selections(sels, spec.test_args, main = test_main, wrapper = spec.test_wrapper)
				os._exit(0)
			except model.SafeException, ex:
				try:
					print >>sys.stderr, unicode(ex)
				except:
					print >>sys.stderr, repr(ex)
			except:
				import traceback
				traceback.print_exc()
		finally:
			sys.stdout.flush()
			sys.stderr.flush()
			os._exit(1)

class Results:
	def __init__(self, spec):
		self.spec = spec
		self.by_combo = {}		# { set((uri, version)) : status }
		self.by_status = {		# status -> [ selections ]
			'passed': [],
			'skipped': [],
			'failed': [],
		}

def run_test_combinations(spec):
	if spec.test_wrapper is None:
		test_command = 'test'
	else:
		test_command = None
	ap = autopolicy.AutoPolicy(spec.test_iface, command = test_command)
	ap.target_arch = TestingArchitecture(ap.target_arch)

	if spec.offline:
		ap.network_use = model.network_offline

	if os.isatty(1):
		ap.handler = handler.ConsoleHandler()

	# Explore all combinations...

	tested_iface = iface_cache.iface_cache.get_interface(spec.test_iface)
	results = Results(spec)
	for combo in spec.get_combos(spec.test_ifaces):
		key = set()
		restrictions = {}
		selections = {}
		for (uri, version) in combo.iteritems():
			iface = iface_cache.iface_cache.get_interface(uri)
			selections[iface] = version
			restrictions[iface] = [VersionRestriction(version)]
			key.add((uri, version))

		ap.solver.extra_restrictions = restrictions
		solve = ap.solve_with_downloads()
		ap.handler.wait_for_blocker(solve)
		if not ap.ready:
			result = 'skipped'
		else:
			selections = {}
			for iface, impl in ap.solver.selections.iteritems():
				if impl:
					version = impl.get_version()
				else:
					impl = None
				selections[iface] = version
			download = ap.download_uncached_implementations()
			if download:
				ap.handler.wait_for_blocker(download)

			tested_impl = ap.implementation[tested_iface]

			print format_combo(selections)

			result = run_tests(tested_iface, ap.solver.selections, spec)

		results.by_status[result].append(selections)
		results.by_combo[frozenset(key)] = (result, selections)
	
	return results
