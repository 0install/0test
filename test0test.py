#!/usr/bin/env python
import sys, tempfile, os, shutil, tempfile, subprocess
from StringIO import StringIO
import unittest
from zeroinstall.support import ro_rmtree, basedir
from zeroinstall.zerostore import Stores

stores = Stores()

my_dir = os.path.abspath(os.path.dirname(__file__))
#sys.path.insert(0, os.path.dirname(my_dir))
#import support
test_bin = os.path.join(my_dir, '0test')

publish_uri = 'http://0install.net/2006/interfaces/0publish'	# The program to test
publish_version = '0.18'

if 'DISPLAY' in os.environ:
	del os.environ['DISPLAY']

# Ensure it's cached now, to avoid extra output during the tests
if subprocess.call(['0launch', '-c', '--download-only', '--not-before=' + publish_version, '--before=' + publish_version + '-post', publish_uri]):
	raise Exception("Failed to download test program")

def test(*args, **kwargs):
	run(*([test_bin] + list(args)), **kwargs)

def run(*args, **kwargs):
	child = subprocess.Popen(args, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
	got, unused = child.communicate()

	expected = kwargs.get('expect', '')
	if expected:
		if expected.lower() not in got.lower():
			raise Exception("Expected '%s', got '%s'" % (expected, got))
	elif got:
		raise Exception("Expected nothing, got '%s'" % got)

# Detect accidental network access
os.environ['http_proxy'] = 'localhost:1111'

for x in ['GNUPGHOME', 'XDG_CONFIG_HOME', 'XDG_CACHE_HOME']:
	if x in os.environ:
		del os.environ[x]
user_cache_dir = os.environ['XDG_CACHE_DIRS'] = basedir.xdg_cache_home

class Test0Test(unittest.TestCase):
	def setUp(self):
		os.chdir('/')

		self.tmpdir = tempfile.mkdtemp(prefix = '0test-test-')

		os.environ['HOME'] = self.tmpdir
		reload(basedir)

		config_dir = basedir.save_config_path('0install.net', 'injector')
		stream = open(os.path.join(config_dir, 'implementation-dirs'), 'w')
		for x in stores.stores:
			stream.write(x.dir + '\n')
		stream.close()

		stream = open(os.path.join(config_dir, 'global'), 'w')
		stream.write('[global]\n'
				'freshness = -1\n'
				'help_with_testing = True\n'
				'network_use = off-line\n')
		stream.close()
	
	def tearDown(self):
		ro_rmtree(self.tmpdir)

	def testVersion(self):
		test('--version', expect = '0test (zero-install)')
		test('--help', expect = 'Usage: 0test')
	
	def test0publish(self):
		test(publish_uri, publish_version, expect = 'None failed')

	def testTestCommand(self):
		test('-t', 'echo $*', publish_uri, publish_version, expect = '/0publish')

	def testCommand(self):
		test('-c', 'run', publish_uri, publish_version, '--', '--version', expect = 'ABSOLUTELY NO WARRANTY')
		test('-c', '', publish_uri, publish_version, '--', '--version', expect = 'No <command> requested and no test command either!')
		test('-c', '', '-t', 'stat $1', publish_uri, publish_version, expect = 'directory')

suite = unittest.makeSuite(Test0Test)
if __name__ == '__main__':
	unittest.main()
