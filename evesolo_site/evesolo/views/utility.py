'''
Created on 23 Aug 2012

@author: matt
'''

from exceptions import Exception

class PilotDoesNotExist(Exception):
    pass

class NoAPIKeyForPilot(Exception):
    pass
    
class IDOrVcodeProblem(Exception):
    pass
    
class APIKeyNotForPilot(Exception):
    pass
    
#from django import forms
#from django.widgets import Textarea
    
class EmptyObject(object):
    pass

def update_attributes_with_keys(something=None,values={}):
    for attribute in values:
        if hasattr(something,attribute):
            old_value=getattr(something,attribute)
            new_value=values[attribute]
            ##check for string representations of integers
            if (type(old_value) is type(1)) and (type(new_value) is type('')):
                try:
                    new_value=int(new_value)
                except ValueError:
                    continue 
            if old_value!=new_value:
                setattr(something,attribute,new_value)