'''
Created on 23 Aug 2012

@author: matt
'''
from django.http import HttpResponse,HttpResponseRedirect
from django.shortcuts import render_to_response
#from models import Solokill, Pilot, Player, Ship, Hullclass, Leaderboard, Leaderboardallowedparticipants
#from models import Leaderboardallowedships,Leaderboardallowedsystems, Leaderboardinvites,Leaderboardkills
from django.conf import settings
from evesolo_site.evesolo.models import Solokill, Pilot, Player, Ship, Hullclass, Leaderboard, Leaderboardallowedparticipants
from evesolo_site.evesolo.models import Leaderboardallowedships,Leaderboardallowedsystems, Leaderboardinvites,Leaderboardkills

from django.template import RequestContext
from django.core.urlresolvers import reverse
from django.core.mail import send_mail
from django.db import DatabaseError, connection
from django.db.models import Sum, Q
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.models import User
from django import forms
from django.test.client import Client
from datetime import datetime, timedelta
from pyparsing import ParseException
import urllib


#users / players+pilots / leaderboards / kills
import km_parser
from sql_strings import *
import eveapi_cachehandler
import eveapi

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

def get_or_create_pilot(name=None):
    try:
        pilot=Pilot.objects.get(name=name)
    except Pilot.DoesNotExist:
        pilot=Pilot(name=name)
    return pilot

def update_attributes_with_keys(something=None,values={}):
    for attribute in values:
        if hasattr(something,attribute):
            old_value=getattr(something,attribute)
            new_value=values[attribute]
            ##check for string representations of integers
            if (type(old_value) is int) and (type(new_value) is str):
                try:
                    new_value=int(new_value)
                except ValueError:
                    continue 
            if old_value!=new_value:
                setattr(something,attribute,new_value)
                
                
def get_api_connection_for_pilot(pilot_id=None):
        pilot_id=int(pilot_id)
        try:
            pilot=Pilot.objects.get(pk=pilot_id)
        except Pilot.DoesNotExist:
            raise PilotDoesNotExist('Pilot was not found.')

        key_info=pilot.api_key
        if not key_info:
            raise NoAPIKeyForPilot('No API key found for pilot.')
        
        key_tokens=key_info.split(']]')
        key_id=int(key_tokens[0][2:])
        key_vCode=key_tokens[1]
        pilot.vCode_id=key_id
        pilot.vCode=key_vCode
        
        cachedAPI=eveapi.EVEAPIConnection(cacheHandler=eveapi_cachehandler.CacheHandler(cache_dir=settings.EVE_API_CACHE))
        api_conn=cachedAPI.auth(keyID=key_id,vCode=key_vCode)
        try:
            api_char=api_conn.account.Characters().characters[0]
        except:
            raise IDOrVcodeProblem('There was a problem with the ID/vCode supplied, please try again.')
        
        api_char_name=api_char.name
        if not api_char_name==pilot.name:
            raise APIKeyNotForPilot('The API key given is not for this pilot.')
        return (get_or_create_pilot(name=api_char_name),api_conn)
        
def get_api_mail_block(request,pilot_id=None,killboard_url=None,latest_kill_id=None,error_page=None,bailout_page=None):
    api_conn_exceptions=[PilotDoesNotExist,NoAPIKeyForPilot,IDOrVcodeProblem,APIKeyNotForPilot]
    
    pull_method=pilot_id or killboard_url
    
    print pull_method
    if type(pull_method) is int :
        try:
            pilot,api_conn=get_api_connection_for_pilot(pilot_id=pilot_id)
        except Exception as exception:
            if type(exception) in api_conn_exceptions:
                if type(exception) is PilotDoesNotExist:
                    return HttpResponseRedirect(bailout_page)
                
                return render_to_response(error_page,{'error':exception.__str__()},context_instance=RequestContext(request))
            raise exception
        
        try:
            api_char=api_conn.account.Characters().characters[0]    
            kills_result=api_conn.char.Killlog(characterID=api_char.characterID).kills
        except: #Pokemon
            return render_to_response(error_page,{'error':'An unknown error occurred. Please try again later. If the problem persists, contact yellowalienbaby@gmail.com'},context_instance=RequestContext(request))
        return kills_result
        
        
    if killboard_url:
        print 'PULLIN FROM THA BOARD'
        try:
            if latest_kill_id: killboard_url+='&lastID=%d' % (latest_kill_id+1)
            handle=urllib.urlopen(killboard_url)
            kills_result=eveapi.ParseXML(handle).kills
            handle.close()
        except:
            return render_to_response(error_page,
                                        {'error':'There was a problem retrieving the kills from the killboard'},
                                        context_instance=RequestContext(request))            
        return kills_result
    
    
    
def get_km_losing_pilot_info(killmail=None):
    losing_pilot_info={}
    losing_pilot_info['name']=killmail.victim['Victim:']
    losing_pilot_info['corp']=killmail.victim['Corp:']
    losing_pilot_info['alliance']=killmail.victim['Alliance:']
    losing_pilot_info['faction']=killmail.victim['Faction:']
    losing_pilot_info['ship_ccpid']=killmail.victim['Destroyed:']
    if type(losing_pilot_info['ship_ccpid']) is int:
        try:
            losing_pilot_info['ship']=Ship.objects.get(CCPID__ccp_type_id=losing_pilot_info['ship_ccpid'])
        except Ship.DoesNotExist:
            losing_pilot_info['ship']=None
    else:
        try:
            losing_pilot_info['ship']=Ship.objects.get(name=losing_pilot_info['ship_ccpid'])
        except Ship.DoesNotExist:
            losing_pilot_info['ship']=None
    return losing_pilot_info

def get_km_winning_pilot_info(killmail=None):
    winning_party=killmail.involved_parties[killmail.involved_parties.keys()[0]]
    winning_pilot_info={}
    winning_pilot_info['name']=winning_party['Name:']
    winning_pilot_info['corp']=winning_party['Corp:']
    winning_pilot_info['alliance']=winning_party['Alliance:']
    winning_pilot_info['faction']=winning_party['Faction:']
    winning_pilot_info['ship_ccpid']=winning_party['Ship:']
    if type(winning_pilot_info['ship_ccpid']) is int:
        try:
            winning_pilot_info['ship']=Ship.objects.get(CCPID__ccp_type_id=winning_pilot_info['ship_ccpid'])
        except Ship.DoesNotExist:
            winning_pilot_info['ship']=None
    else:
        try:
            winning_pilot_info['ship']=Ship.objects.get(name=winning_pilot_info['ship_ccpid'])
        except Ship.DoesNotExist:
            winning_pilot_info['ship']=None
    
    return winning_pilot_info

def calculate_kill_points(Lp,Wp):
    #Lp and Wp are ship hullclass fwp values for Loser and Winner
    if Lp==0 and Wp==0:
        kill_points=1
    elif Lp==0:
        kill_points=0
    elif Wp==Lp:
        kill_points=1
    elif Wp<Lp:
        kill_points=(Lp-Wp)+1
    elif Wp>Lp:
        kill_points=round(1.0/-((Lp-Wp)-1),2)
    return kill_points

def update_or_create_pilot(request,pilot_info):
    pilot=get_or_create_pilot(name=pilot_info['name'])
    if not pilot.api_key:
        pilot.corp=pilot_info['corp']
        pilot.alliance=pilot_info['alliance']
        pilot.faction=pilot_info['faction']
        save_object(pilot,request)
    return pilot    
    
def get_sql_rows(sql,as_instances=False):
    #c=connection.cursor() 
    c=getattr(connection,'cursor')() #//cursor only exists at runtime
    c.execute(sql)
    all_rows=c.fetchall()
    if not as_instances:
        return all_rows
    #TODO: return eligible rowsets as model instances
         

#def get_or_create_thing(what_kind_of_thing=None,its_name=None):
#    try:
#        the_thing=what_kind_of_thing.objects.get(name=its_name)
#    except what_kind_of_thing.DoesNotExist:
#        the_thing=what_kind_of_thing(name=its_name)
#    return the_thing

def get_or_create_leaderboard(name=None,manager=None):
    try:
        leaderboard=Leaderboard.objects.get(name=name,player=manager)
    except Leaderboard.DoesNotExist:
        leaderboard=Leaderboard(name=name,player=manager)
    return leaderboard



def save_object(target,request):
    try:
        target.save()
    except:
        render_to_response('evesolo/error.html',context_instance=RequestContext(request))
        
def testemail(request):
    send_mail('DJANGO TEST','Here is a message, indeed!','yellowalienbaby@gmail.com',['matthew_j_warren@hotmail.com'],fail_silently=False)
    return HttpResponseRedirect(reverse('evesolo.views.latestkills'))