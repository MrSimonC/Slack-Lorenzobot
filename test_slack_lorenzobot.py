from slackclient import SlackClient
import os
import unittest


class TestAPIKey(unittest.TestCase):
    def setUp(self):
        slack_token = os.environ['SLACK_LORENZOBOT']
        self.sc = SlackClient(slack_token)

    def test_api_key_authenticates(self):
        slack_response = self.sc.api_call("auth.test")
        self.assertEqual(slack_response['ok'], True)

