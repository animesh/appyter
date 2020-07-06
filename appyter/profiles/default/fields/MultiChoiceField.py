from appyter.fields import Field

class MultiChoiceField(Field):
  ''' Represing a multi-selectable combo box.
  The resulting selection is represented with a list of strings that were chosen.

  :param name: (str) A name that will be used to refer to the object as a variable and in the HTML form.
  :param label: (str) A human readable label for the field for the HTML form
  :param description: (Optional[str]) A long human readable description for the field for the HTML form
  :param choices: (Union[List[str], Set[str], Dict[str, str]]) A set of choices that are available for this field or lookup table mapping from choice label to resulting value
  :param default: (float) A default value as an example and for use during prototyping
  :param section: (Optional[str]) The name of a SectionField for which to nest this field under, defaults to a root SectionField
  :param value: (INTERNAL Any) The raw value of the field (from the form for instance)
  :param \**kwargs: Remaining arguments passed down to :class:`appyter.fields.Field`'s constructor.
  '''
  def __init__(self, **kwargs):
    super().__init__(**kwargs)

  @property
  def raw_value(self):
    if type(self.args['value']) == str:
      return [self.args['value']]
    elif type(self.args['value']) == list:
      return self.args['value']
    elif self.args['value'] is None:
      return []
    else:
      return None

  @property
  def value(self):
    if type(self.choices) == dict:
      return [self.choices[v] for v in self.raw_value]
    else:
      assert self.constraint(), '%s[%s] (%s) does not satisfy constraints' % (
        self.field, self.args.get('name', ''), self.raw_value
      )
      return self.raw_value

  def constraint(self):
    return self.raw_value is not None and all(v in self.choices for v in self.raw_value)
