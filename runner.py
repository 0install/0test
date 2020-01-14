# Copyright (C) 2010, Thomas Leonard
# Visit http://0install.net for details.

import os, sys, logging
from zeroinstall.injector import driver, model, run, requirements
from zeroinstall.support import tasks
from reporting import format_combo

class NonlocalRestriction(model.Restriction):
	def meets_restriction(self, impl):
		return impl.local_path is None

	def __str__(self):
		return "nonlocal"

def run_tests(config, tested_iface, sels, spec):
	def _get_implementation_path(impl):
		return impl.local_path or config.iface_cache.stores.lookup_any(impl.digests)

	main_command = sels.commands[0] if sels.commands else None

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
		if main_command is None:
			print("No <command> requested and no test command either!", file=sys.stderr)
			return "skipped"

		test_main = None

		if main_command.path is None:
			tests_dir = _get_implementation_path(root_impl)
		else:
			main_abs = os.path.join(_get_implementation_path(root_impl), main_command.path)
			if not os.path.exists(main_abs):
				print("Test executable does not exist:", main_abs, file=sys.stderr)
				return "skipped"

			tests_dir = os.path.dirname(main_abs)

	child = os.fork()
	if child:
		# We are the parent
		pid, status = os.waitpid(child, 0)
		assert pid == child
		print("Status:", hex(status))
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
			except model.SafeException as ex:
				try:
					print(str(ex), file=sys.stderr)
				except:
					print(repr(ex), file=sys.stderr)
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

def run_test_combinations(config, spec):
	r = requirements.Requirements(spec.test_iface)
	r.command = spec.command

	d = driver.Driver(config = config, requirements = r)
	solver = d.solver

	# Explore all combinations...

	tested_iface = config.iface_cache.get_interface(spec.test_iface)
	results = Results(spec)
	for combo in spec.get_combos(spec.test_ifaces):
		key = set()
		restrictions = {}
		selections = {}
		for (uri, version) in combo.items():
			iface = config.iface_cache.get_interface(uri)
			selections[iface] = version

			if version.startswith('%'):
				if version == '%nonlocal':
					restrictions[iface] = [NonlocalRestriction()]
				else:
					raise model.SafeException("Unknown special '{special}'".format(special = version))
			elif ',' in version:
				not_before, before = [model.parse_version(v) if v != "" else None for v in version.split(',')]
				if (not_before and before) and not_before >= before:
					raise model.SafeException("Low version >= high version in %s!" % version)
				restrictions[iface] = [model.VersionRangeRestriction(before, not_before)]
			else:
				restrictions[iface] = [model.VersionExpressionRestriction(version)]
			key.add((uri, version))

		solver.extra_restrictions = restrictions
		solve = d.solve_with_downloads()
		tasks.wait_for_blocker(solve)
		if not solver.ready:
			logging.info("Can't select combination %s: %s", combo, solver.get_failure_reason())
			result = 'skipped'
			for uri, impl in solver.selections.items():
				if impl is None:
					selections[uri] = selections.get(uri, None) or '?'
				else:
					selections[uri] = impl.get_version()
			if not selections:
				selections = solver.get_failure_reason()
		else:
			selections = {}
			for iface, impl in solver.selections.items():
				if impl:
					version = impl.get_version()
				else:
					impl = None
				selections[iface] = version
			download = d.download_uncached_implementations()
			if download:
				config.handler.wait_for_blocker(download)

			print(format_combo(selections))

			result = run_tests(config, tested_iface, solver.selections, spec)

		results.by_status[result].append(selections)
		results.by_combo[frozenset(key)] = (result, selections)
	
	return results
