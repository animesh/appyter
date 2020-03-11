import os
import re
import json
from copy import copy
from flask import Markup
from jupyter_template.context import get_jinja2_env

def build_fields(fields, context={}):
  ''' Build a dictionary of Field instances
  '''
  return {
    field_name: lambda name=None, _field=field, _context=context, **kwargs: _field(
      **dict(kwargs,
        name=name,
        value=_context.get(name),
      )
    )
    for field_name, field in fields.items()
  }

class Field:
  def __init__(self,
      group=None,
      name=None,
      label=None,
      value=None,
      choices=[],
      default=None,
      **kwargs):
    self.args = dict(
      group=group,
      name=name,
      choices=choices,
      label=label,
      default=default,
      value=value if value is not None else default,
      **kwargs,
    )

  def constraint(self):
    ''' Return true if args.value satisfies constraints.
    '''
    return self.args['value'] in self.choices

  def render(self):
    ''' Return a rendered version of the field (form)
    '''
    return Markup(
      get_jinja2_env().get_template(
        self.template
      ).render({
        'this': self
      })
    )

  @property
  def field(self):
    ''' Field name
    '''
    return self.__class__.__name__

  @property
  def template(self):
    ''' Template to use for rendering field
    '''
    return os.path.join('fields', self.field + '.j2')

  @property
  def choices(self):
    ''' Potential values to choose from
    '''
    choices = self.args.get('choices')
    if type(choices) == dict:
      return choices.keys()
    else:
      return choices

  @property
  def raw_value(self):
    ''' Raw value of the field
    '''
    return self.args['value']

  @property
  def value(self):
    ''' Effective value of the field when used
    '''
    choices = self.args.get('choices')
    if type(choices) == dict:
      return choices[self.raw_value]
    else:
      return self.raw_value

  @property
  def safe_value(self):
    ''' Effective value ready to be displayed
    '''
    assert self.constraint(), '%s[%s] (%s) does not satisfy constraints' % (
      self.field, self.args.get('name', ''), self.value
    )
    return Markup(self.value)

  def __str__(self):
    return self.safe_value