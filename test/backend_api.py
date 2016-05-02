from proxies import ProxyHoldingTestCase
from lib.error import UserError
import unittest

# the API tests assume that all other backend services work properly.

# covered API functions:
#  account
#   account_info
#     no argument
#     logged-in user
#   account_create
#     correct data
#   account_remove

class NoOtherAccountTestCase(ProxyHoldingTestCase):

	def remove_all_other_accounts(self):
		for user in self.proxy_holder.backend_users.user_list():
			if user["name"] != self.proxy_holder.username:
				self.proxy_holder.backend_users.user_remove(user["name"])

	def setUp(self):
		self.remove_all_other_accounts()

	def tearDown(self):
		self.remove_all_other_accounts()

	def test_account_recognition(self):
		"""
		tests whether the correct account is recognized. assumes account_info is correct
		"""
		self.assertEqual(self.proxy_holder.backend_api.account_info()['name'], self.proxy_holder.username)

	def test_account_info(self):
		"""
		tests whether account info is correct
		"""
		self.assertEqual(self.proxy_holder.backend_api.account_info(self.proxy_holder.username),
		                 self.proxy_holder.backend_users.user_info(self.proxy_holder.username))

	def test_account_create(self):
		username = "testuser"
		password = "123"
		organization = self.default_organization_name
		attrs = {
			"realname": "Test User",
			"email": "test@example.com",
			"flags": {"over_quota": True}
		}

		ainf = self.proxy_holder.backend_api.account_create(username, password, organization, attrs)
		self.assertIsNotNone(ainf)
		real_ainf = self.proxy_holder.backend_users.user_info(username)
		self.assertEqual(ainf, real_ainf)

class OtherAccountTestCase(ProxyHoldingTestCase):
	def remove_all_other_accounts(self):
		for user in self.proxy_holder.backend_users.user_list():
			if user["name"] != self.proxy_holder.username:
				self.proxy_holder.backend_users.user_remove(user["name"])

	def setUp(self):
		self.remove_all_other_accounts()

		self.testuser_username = "testuser"
		self.testuser_password = "123"
		self.testuser_organization = self.default_organization_name
		self.testuser_email = "test@example.com"
		self.testuser_attrs = {
			"realname": "Test User",
			"flags": {"over_quota": True}
		}

		self.proxy_holder.backend_users.user_create(self.testuser_username, self.testuser_organization, self.testuser_email, self.testuser_password, self.testuser_attrs)

	def tearDown(self):
		self.remove_all_other_accounts()

	def test_account_remove(self):
		self.proxy_holder.backend_api.account_remove(self.testuser_username)
		try:
			self.proxy_holder.backend_users.user_info(self.testuser_username)
			self.fail("user was not removed")
		except UserError as e:
			if e.code != UserError.ENTITY_DOES_NOT_EXIST:
				self.fail("wrong error code")
		try:
			self.proxy_holder.backend_api.user_info(self.testuser_username)
			self.fail("user is still cached")
		except UserError as e:
			if e.code != UserError.ENTITY_DOES_NOT_EXIST:
				self.fail("wrong error code")


class AuthorizationTestCase(ProxyHoldingTestCase):
	"""
	Tests whether the authorization module works properly.
	"""
	# todo: implement.
	pass



def suite():
	return unittest.TestSuite([
		unittest.TestLoader().loadTestsFromTestCase(NoOtherAccountTestCase),
		unittest.TestLoader().loadTestsFromTestCase(AuthorizationTestCase)
	])