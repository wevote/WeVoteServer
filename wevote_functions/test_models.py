# wevote_functions/test_models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.test import TestCase
from .models import positive_value_exists


class WeVoteFunctionsTestsModels(TestCase):

    # def setUp(self):

    def test_positive_value_exists(self):
        """
        Try out several values to make sure the We Vote function 'positive_value_exists' returns the expected value
        :return:
        """
        #######################################
        # Test for True
        value_to_test = 1
        self.assertEqual(positive_value_exists(value_to_test), True,
                         "Testing value: {value_to_test}, True expected".format(value_to_test=value_to_test))

        value_to_test = 100
        self.assertEqual(positive_value_exists(value_to_test), True,
                         "Testing value: {value_to_test}, True expected".format(value_to_test=value_to_test))

        value_to_test = 'hello'
        self.assertEqual(positive_value_exists(value_to_test), True,
                         "Testing value: {value_to_test}, True expected".format(value_to_test=value_to_test))

        value_to_test = True
        self.assertEqual(positive_value_exists(value_to_test), True,
                         "Testing value: {value_to_test}, True expected".format(value_to_test=value_to_test))

        value_to_test = {
            'success': True
        }
        self.assertEqual(positive_value_exists(value_to_test), True,
                         "Testing value: {value_to_test}, True expected".format(value_to_test=value_to_test))

        value_to_test = [
            'success'
        ]
        self.assertEqual(positive_value_exists(value_to_test), True,
                         "Testing value: {value_to_test}, True expected".format(value_to_test=value_to_test))

        #######################################
        # Test for False
        value_to_test = 0
        self.assertEqual(positive_value_exists(value_to_test), False,
                         "Testing value: {value_to_test}, False expected".format(value_to_test=value_to_test))

        value_to_test = -1
        self.assertEqual(positive_value_exists(value_to_test), False,
                         "Testing value: {value_to_test}, False expected".format(value_to_test=value_to_test))

        value_to_test = ''
        self.assertEqual(positive_value_exists(value_to_test), False,
                         "Testing value: {value_to_test}, False expected".format(value_to_test=value_to_test))

        value_to_test = '0'
        self.assertEqual(positive_value_exists(value_to_test), False,
                         "Testing value: {value_to_test}, False expected".format(value_to_test=value_to_test))

        value_to_test = False
        self.assertEqual(positive_value_exists(value_to_test), False,
                         "Testing value: {value_to_test}, False expected".format(value_to_test=value_to_test))

        value_to_test = {}
        self.assertEqual(positive_value_exists(value_to_test), False,
                         "Testing value: {value_to_test}, False expected".format(value_to_test=value_to_test))

        value_to_test = []
        self.assertEqual(positive_value_exists(value_to_test), False,
                         "Testing value: {value_to_test}, False expected".format(value_to_test=value_to_test))
