from exceptions import Exception

class PilotDoesNotExist(Exception):
	pass

class NoAPIKeyForPilot(Exception):
	pass
	
class IDOrVcodeProblem(Exception):
	pass
	
class APIKeyNotForPilot(Exception):
	pass
from django.http import HttpResponse,HttpResponseRedirect
from django.shortcuts import render_to_response
from evesolo.models import Solokill, Pilot, Player, Ship, Hullclass
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
import km_parser
from sql_strings import *
import eveapi_cachehandler
import eveapi

def get_api_connection_for_pilot(pilot_id=None):
		pilot_id=int(pilot_id)
		try:
			pilot=Pilot.objects.get(pk=pilot_id)
		except Pilot.DoesNotExist:
			raise PilotDoesNotExist('Pilot was not found.')

		key_info=pilot.api_key
		if not key_info:
			raise NoAPIKeyFoundForPilot('No API key found for pilot.')
		
		key_tokens=key_info.split(']]')
		key_id=int(key_tokens[0][2:])
		key_vCode=key_tokens[1]
		pilot.vCode_id=key_id
		pilot.vCode=key_vCode
		
		cachedAPI=eveapi.EVEAPIConnection(cacheHandler=eveapi_cachehandler.CacheHandler(cache_dir='C:/web/www/evesolo_com/evesolo_site/eve_api_cache'))
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
	if type(pull_method) is int :
		try:
			pilot,api_conn=get_api_conection_for_pilot(request,pilot_id=pilot_id,error_page=error_page)
		except exception, error:
			if exception in api_conn_exceptions:
				if type(exception) is PilotDoesNotExist:
					return HttpResponseRedirect(bailout_page)
				
				return render_to_response(error_page,{'error':error},context_instance=RequestContext(request))
			raise exception(error)
			
		api_char=api_conn.account.Characters().characters[0]	
		kills_result=api_conn.char.Killlog(characterID=api_char.characterID).kills
		return kills_result
		
		
	if killboard_url:
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
	try:
		losing_pilot_info[ship]=Ship.objects.get(CCPID__ccp_type_id=losing_pilot_info['ship_ccpid'])
	except Ship.DoesNotExist:
		losing_pilot['ship']=None
	return losing_pilot_info



def get_km_winning_pilot_info(killmail=None):
	winning_pilot['raw']=KM.involved_parties[KM.involved_parties.keys()[0]]
	winning_pilot['name']=winning_pilot_raw['Name:']
	winning_pilot['corp']=winning_pilot_raw['Corp:']
	winning_pilot['alliance']=winning_pilot_raw['Alliance:']
	winning_pilot['faction']=winning_pilot_raw['Faction:']
	winning_pilot['ship_ccpid']=winning_pilot_raw['Ship:']
	try:
		winning_pilot['ship']=Ship.objects.get(CCPID__ccp_type_id=winning_pilot['ship_ccpid'])
	except Ship.DoesNotExist:
		winning_pilot_info['ship']=None
	return winning_ship_info


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

def update_or_create_pilot(pilot_info)
	pilot=get_or_create_pilot(name=pilot_info['name'])
	pilot.corp=pilot_info['corp']
	pilot.alliance=pilot_info['alliance']
	pilot.faction=pilot_info['faction']
	save_object(pilot,request)
	return pilot
