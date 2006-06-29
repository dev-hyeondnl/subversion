import unittest, os, weakref, tempfile, types

from svn import core, repos, fs, delta, client, wc
from libsvn.core import SubversionException

from trac.versioncontrol.tests.svn_fs import SubversionRepositoryTestSetup, \
  REPOS_PATH
from urllib import pathname2url
from urlparse import urljoin

class SubversionClientTestCase(unittest.TestCase):
  """Test cases for the basic SWIG Subversion client layer"""

  def log_message_func(self, items, pool):
    """ Simple log message provider for unit tests. """
    self.log_message_func_calls += 1
    return "Test log message"

  def log_receiver(self, changed_paths, revision, author, date, message, pool):
    """ Function to recieve log messages retrieved by client.log3(). """
    self.log_message = message
    self.change_author = author
    self.changed_paths = changed_paths

  def setUp(self):
    """Set up authentication and client context"""
    self.client_ctx = client.svn_client_create_context()
    self.client_ctx.log_msg_func2 = client.svn_swig_py_get_commit_log_func
    self.client_ctx.log_msg_baton2 = self.log_message_func
    self.log_message_func_calls = 0
    self.log_message = None
    self.changed_paths = None
    self.change_author = None

    providers = [
       client.svn_client_get_simple_provider(),
       client.svn_client_get_username_provider(),
    ]

    self.client_ctx.auth_baton = core.svn_auth_open(providers)
    self.repos_url = "file://" + pathname2url(REPOS_PATH)

  def info_receiver(self, path, info, pool):
    """Squirrel away the output from 'svn info' so that the unit tests
       can get at them."""
    self.path = path
    self.info = info

  def test_client_ctx_baton_lifetime(self):
    pool = core.Pool()
    temp_client_ctx = client.svn_client_create_context(pool)

    # We keep track of these objects in separate variables here
    # because you can't get a PyObject back out of a PY_AS_VOID field
    test_object1 = lambda *args: "message 1"
    test_object2 = lambda *args: "message 2"
    
    # Verify that the refcount of a Python object is incremented when
    # you insert it into a PY_AS_VOID field.
    temp_client_ctx.log_msg_baton2 = test_object1
    test_object1 = weakref.ref(test_object1)
    self.assertNotEqual(test_object1(), None)

    # Verify that the refcount of the previous Python object is decremented
    # when a PY_AS_VOID field is replaced.
    temp_client_ctx.log_msg_baton2 = test_object2
    self.assertEqual(test_object1(), None)
  
    # Verify that the reference count of the new Python object (which
    # replaced test_object1) was incremented.
    test_object2 = weakref.ref(test_object2)
    self.assertNotEqual(test_object2(), None)

    # Verify that the reference count of test_object2 is decremented when
    # the pool containing temp_client_context is destroyed.
    pool.destroy()
    self.assertEqual(test_object2(), None)

  def test_checkout(self):
    """Test svn_client_checkout2."""

    rev = core.svn_opt_revision_t()
    rev.kind = core.svn_opt_revision_head

    path = os.path.join(tempfile.gettempdir(), 'checkout')

    self.assertRaises(ValueError, client.checkout2, 
                      self.repos_url, path, None, None, True, True, 
                      self.client_ctx)

    client.checkout2(self.repos_url, path, rev, rev, True, True, 
            self.client_ctx)

  def test_info(self):
    """Test svn_client_info on an empty repository"""

    # Run info
    revt = core.svn_opt_revision_t()
    revt.kind = core.svn_opt_revision_head
    client.info(self.repos_url, revt, revt, self.info_receiver,
                False, self.client_ctx)

    # Check output from running info. This also serves to verify that
    # the internal 'info' object is still valid
    self.assertEqual(self.path, os.path.basename(REPOS_PATH))
    self.info.assert_valid()
    self.assertEqual(self.info.URL, self.repos_url)
    self.assertEqual(self.info.repos_root_URL, self.repos_url)

  def test_mkdir_url(self):
    """Test svn_client_mkdir2 on a file:// URL"""
    dir = urljoin(self.repos_url+"/", "dir1")
    
    commit_info = client.mkdir2((dir,), self.client_ctx)
    self.assertEqual(commit_info.revision, 13)
    self.assertEqual(self.log_message_func_calls, 1)

  def test_log3_url(self):
    """Test svn_client_log3 on a file:// URL"""
    dir = urljoin(self.repos_url+"/", "trunk/dir1")

    start = core.svn_opt_revision_t()
    end = core.svn_opt_revision_t()
    core.svn_opt_parse_revision(start, end, "4:0")
    client.log3((dir,), start, start, end, 1, True, False, self.log_receiver,
        self.client_ctx)
    self.assertEqual(self.change_author, "john")
    self.assertEqual(self.log_message, "More directories.")    
    self.assertEqual(len(self.changed_paths), 3)
    for dir in ('/trunk/dir1', '/trunk/dir2', '/trunk/dir3'):
      self.assert_(self.changed_paths.has_key(dir))
      self.assertEqual(self.changed_paths[dir].action, 'A')

  def test_uuid_from_url(self):
    """Test svn_client_uuid_from_url on a file:// URL"""
    self.assert_(isinstance(
                 client.uuid_from_url(self.repos_url, self.client_ctx),
                 types.StringTypes))

  def test_url_from_path(self):
    """Test svn_client_url_from_path for a file:// URL"""
    self.assertEquals(client.url_from_path(self.repos_url), self.repos_url)

    rev = core.svn_opt_revision_t()
    rev.kind = core.svn_opt_revision_head

    path = os.path.join(tempfile.gettempdir(), 'url_from_path')

    client.checkout2(self.repos_url, path, rev, rev, True, True, 
                     self.client_ctx)

    self.assertEquals(client.url_from_path(path), self.repos_url)

  def test_uuid_from_path(self):
    """Test svn_client_uuid_from_path."""
    rev = core.svn_opt_revision_t()
    rev.kind = core.svn_opt_revision_head

    path = os.path.join(tempfile.gettempdir(), 'uuid_from_path')

    client.checkout2(self.repos_url, path, rev, rev, True, True, 
                     self.client_ctx)

    wc_adm = wc.adm_open3(None, path, False, 0, None)

    self.assertEquals(client.uuid_from_path(path, wc_adm, self.client_ctx), 
                      client.uuid_from_url(self.repos_url, self.client_ctx))

    self.assert_(isinstance(client.uuid_from_path(path, wc_adm, 
                            self.client_ctx), types.StringTypes))

  def test_open_ra_session(self):
      """Test svn_client_open_ra_session()."""
      client.open_ra_session(self.repos_url, self.client_ctx)

def suite():
    return unittest.makeSuite(SubversionClientTestCase, 'test',
                              suiteClass=SubversionRepositoryTestSetup)

if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(suite())

