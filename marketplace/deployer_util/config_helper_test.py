# Copyright 2018 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import tempfile
import unittest

import config_helper

SCHEMA = """
properties:
  propertyString:
    type: string
  propertyStringWithDefault:
    type: string
    default: DefaultString
  propertyInt:
    type: int
  propertyIntWithDefault:
    type: int
    default: 3   
  propertyInteger:
    type: integer
  propertyIntegerWithDefault:
    type: integer
    default: 6
  propertyNumber:
    type: number
  propertyNumberWithDefault:
    type: number
    default: 1.0
  propertyBoolean:
    type: boolean
  propertyBooleanWithDefault:
    type: boolean
    default: false
  propertyPassword:
    type: string
    x-google-marketplace:
      type: GENERATED_PASSWORD
      length: 4
required:
- propertyString
- propertyPassword
"""


class ConfigHelperTest(unittest.TestCase):

  def test_load_yaml_file(self):
    with tempfile.NamedTemporaryFile('w') as f:
      f.write(SCHEMA.encode('utf_8'))
      f.flush()

      schema = config_helper.Schema.load_yaml_file(f.name)
      schema_from_str = config_helper.Schema.load_yaml(SCHEMA)
      self.assertEqual(schema.properties, schema_from_str.properties)
      self.assertEqual(schema.required, schema_from_str.required)

  def test_required(self):
    schema = config_helper.Schema.load_yaml(SCHEMA)
    self.assertEqual({'propertyString', 'propertyPassword'},
                     set(schema.required))

  def test_types_and_defaults(self):
    schema = config_helper.Schema.load_yaml(SCHEMA)
    self.assertEqual(
        {'propertyString',
         'propertyStringWithDefault',
         'propertyInt',
         'propertyIntWithDefault',
         'propertyInteger',
         'propertyIntegerWithDefault',
         'propertyNumber',
         'propertyNumberWithDefault',
         'propertyBoolean',
         'propertyBooleanWithDefault',
         'propertyPassword'},
        set(schema.properties))
    self.assertEqual(str,
                     schema.properties['propertyString'].type)
    self.assertIsNone(schema.properties['propertyString'].default)
    self.assertEqual(str,
                     schema.properties['propertyStringWithDefault'].type)
    self.assertEqual('DefaultString',
                     schema.properties['propertyStringWithDefault'].default)
    self.assertEqual(int, schema.properties['propertyInt'].type)
    self.assertIsNone(schema.properties['propertyInt'].default)
    self.assertEqual(int,
                     schema.properties['propertyIntWithDefault'].type)
    self.assertEqual(3,
                     schema.properties['propertyIntWithDefault'].default)
    self.assertEqual(int,
                     schema.properties['propertyInteger'].type)
    self.assertIsNone(schema.properties['propertyInteger'].default)
    self.assertEqual(int,
                     schema.properties['propertyIntegerWithDefault'].type)
    self.assertEqual(6,
                     schema.properties['propertyIntegerWithDefault'].default)
    self.assertEqual(float, schema.properties['propertyNumber'].type)
    self.assertIsNone(schema.properties['propertyNumber'].default)
    self.assertEqual(float,
                     schema.properties['propertyNumberWithDefault'].type)
    self.assertEqual(1.0,
                     schema.properties['propertyNumberWithDefault'].default)
    self.assertEqual(bool,
                     schema.properties['propertyBoolean'].type)
    self.assertIsNone(schema.properties['propertyBoolean'].default)
    self.assertEqual(bool,
                     schema.properties['propertyBooleanWithDefault'].type)
    self.assertEqual(False,
                     schema.properties['propertyBooleanWithDefault'].default)
    self.assertEqual(str, schema.properties['propertyPassword'].type)
    self.assertIsNone(schema.properties['propertyPassword'].default)
    self.assertEqual('GENERATED_PASSWORD',
                     schema.properties['propertyPassword'].xtype)

  def test_password(self):
    schema = config_helper.Schema.load_yaml(
        """
        properties:
          pw:
            type: string
            x-google-marketplace:
              type: GENERATED_PASSWORD
        """)
    self.assertEqual(10, schema.properties['pw'].password.length)
    self.assertEqual(False, schema.properties['pw'].password.include_symbols)
    self.assertEqual(True, schema.properties['pw'].password.base64)

    schema = config_helper.Schema.load_yaml(
        """
        properties:
          pw:
            type: string
            x-google-marketplace:
              type: GENERATED_PASSWORD
              generatedPassword:
                length: 5
                includeSymbols: true
                base64: false
        """)
    self.assertEqual(5, schema.properties['pw'].password.length)
    self.assertEqual(True, schema.properties['pw'].password.include_symbols)
    self.assertEqual(False, schema.properties['pw'].password.base64)

  def test_int_type(self):
    schema = config_helper.Schema.load_yaml(
        """
        properties:
          pi:
            type: int
        """)
    self.assertEqual(5, schema.properties['pi'].str_to_type('5'))

  def test_number_type(self):
    schema = config_helper.Schema.load_yaml(
        """
        properties:
          pn:
            type: number
        """)
    self.assertEqual(5.2, schema.properties['pn'].str_to_type('5.2'))

  def test_invalid_default_type(self):
    self.assertRaises(
        config_helper.InvalidSchema,
        lambda: config_helper.Schema.load_yaml(
            """
            properties:
              pn:
                type: number
                default: abc
            """))

  def test_property_matches_definition(self):
    schema = config_helper.Schema.load_yaml(
        """
        properties:
          propertyInt:
            type: int
          propertyPassword:
            type: string
            x-google-marketplace:
              type: GENERATED_PASSWORD
        """)
    self.assertTrue(schema.properties['propertyInt'].matches_definition(
        {'name': 'propertyInt'}))
    self.assertFalse(schema.properties['propertyInt'].matches_definition(
        {'name': 'propertyPassword'}))
    self.assertTrue(schema.properties['propertyInt'].matches_definition(
        {'type': 'int'}))
    self.assertFalse(schema.properties['propertyInt'].matches_definition(
        {'type': 'string'}))
    self.assertFalse(schema.properties['propertyInt'].matches_definition(
        {'x-google-marketplace': {'type': 'GENERATED_PASSWORD'}}))
    self.assertTrue(schema.properties['propertyPassword'].matches_definition(
        {'x-google-marketplace': {'type': 'GENERATED_PASSWORD'}}))
    self.assertTrue(schema.properties['propertyPassword'].matches_definition(
        {'type': 'string',
         'x-google-marketplace': {
           'type': 'GENERATED_PASSWORD'
         }}))

  def test_defaults_bad_type(self):
    self.assertRaises(
        config_helper.InvalidSchema,
        lambda: config_helper.Schema.load_yaml(
            """
            properties:
              p1:
                type: string
                default: 10
            """))


if __name__ == 'main':
  unittest.main()
