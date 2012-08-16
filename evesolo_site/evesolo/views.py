from django.http import HttpResponse,HttpResponseRedirect
from django.shortcuts import render_to_response
from models import Solokill, Pilot, Player, Ship, Hullclass, Leaderboard, Leaderboardallowedparticipants
from models import Leaderboardallowedships,Leaderboardallowedsystems, Leaderboardinvites,Leaderboardkills

#from evesolo.models import Solokill, Pilot, Player, Ship, Hullclass, Leaderboard, Leaderboardallowedparticipants
#from evesolo.models import Leaderboardallowedships,Leaderboardallowedsystems, Leaderboardinvites



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
			
		api_char=api_conn.account.Characters().characters[0]	
		kills_result=api_conn.char.Killlog(characterID=api_char.characterID).kills
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
	pilot.corp=pilot_info['corp']
	pilot.alliance=pilot_info['alliance']
	pilot.faction=pilot_info['faction']
	save_object(pilot,request)
	return pilot	
	
def get_sql_rows(sql):
	#c=connection.cursor() 
	c=getattr(connection,'cursor')() #//cursor only exists at runtime
	c.execute(sql)
	return c.fetchall()

#def get_or_create_thing(what_kind_of_thing=None,its_name=None):
#	try:
#		the_thing=what_kind_of_thing.objects.get(name=its_name)
#	except what_kind_of_thing.DoesNotExist:
#		the_thing=what_kind_of_thing(name=its_name)
#	return the_thing

def get_or_create_leaderboard(name=None,manager=None):
	try:
		leaderboard=Leaderboard.objects.get(name=name,player=manager)
	except Leaderboard.DoesNotExist:
		leaderboard=Leaderboard(name=name,player=manager)
	return leaderboard

def get_or_create_pilot(name=None):
	try:
		pilot=Pilot.objects.get(name=name)
	except Pilot.DoesNotExist:
		pilot=Pilot(name=name)
	return pilot

def save_object(target,request):
	try:
		target.save()
	except:
		render_to_response('evesolo/error.html',context_instance=RequestContext(request))
		
def testemail(request):
	send_mail('DJANGO TEST','Here is a message, indeed!','yellowalienbaby@gmail.com',['matthew_j_warren@hotmail.com'],fail_silently=False)
	return HttpResponseRedirect(reverse('evesolo.views.latestkills'))
	
def search(request):
	if not request.method=='POST' or ('pilot_name' not in request.POST):
		return render_to_response('evesolo/search.html',context_instance=RequestContext(request))
	
	pilot_name=request.POST['pilot_name'].strip()
	if len(pilot_name)==0:
		return render_to_response('evesolo/search.html',{'error':'Please specify a pilot name, or partial pilot name to search for'},context_instance=RequestContext(request))
	
	if len(pilot_name)<3:
		return render_to_response('evesolo/search.html',{'error':'The text to search for must contain at least 3 characters'},context_instance=RequestContext(request))
	
	
	possible_pilots=Pilot.objects.filter(name__icontains=pilot_name)
	if len(possible_pilots)==0:
		return render_to_response('evesolo/search.html',{'message':'Sorry, no pilots could be found'},context_instance=RequestContext(request))
		
	return render_to_response('evesolo/search.html',{'possible_pilots':possible_pilots},context_instance=RequestContext(request))
	
def register(request):
	if not request.method=='POST' or ( ('username' not in request.POST) or ('email' not in request.POST) or ('password' not in request.POST) or ('password_confirm' not in request.POST) ):
		return render_to_response('evesolo/register.html',context_instance=RequestContext(request))
	
	#check all the input fields, then the user does not exist, then the passwords match, then create the user
	
	username=request.POST['username']
	email=request.POST['email']
	password=request.POST['password']
	password_confirm=request.POST['password_confirm']
	
	if len(username.strip())==0:
		return render_to_response('evesolo/register.html',{'error':'Please supply a username.'},context_instance=RequestContext(request))
		
	if len(email.strip())==0:
		return render_to_response('evesolo/register.html',{'error':'Please supply an email address.'},context_instance=RequestContext(request))
	
	if len(password.strip())==0:
		return render_to_response('evesolo/register.html',{'error':'Please supply a password.'},context_instance=RequestContext(request))
	
	if len(password.strip())==0:
		return render_to_response('evesolo/register.html',{'error':'Please supply a password confirmation.'},context_instance=RequestContext(request))
	
	existing_user=User.objects.filter(username=username)
	
	if len(existing_user)!=0:
		return render_to_response('evesolo/register.html',{'error':'That user already exists, please choose another.'},context_instance=RequestContext(request))
	
	if password==password_confirm:
		try:
			user=User.objects.create_user(username,email,password)
		except:
			return render_to_response('evesolo/register.html',{'error':'There was a problem creating the user, check your details and try again.'},context_instance=RequestContext(request))
		return render_to_response('evesolo/user_created.html',context_instance=RequestContext(request))

def get_profile_context(request):
	context={}
	players=[] #list of 
	user_players=Player.objects.filter(user=request.user)
	for player in user_players:
		player_pilots=Pilot.objects.filter(player=player)
		pilots_ok=[]
		#player pilots
		for pilot in player_pilots:
			key_info=pilot.api_key
			if not key_info:
				ok='No Key'
			else:
				key_tokens=key_info.split(']]')
				key_id=int(key_tokens[0][2:])
				key_vCode=key_tokens[1]
				pilot.vCode_id=key_id
				pilot.vCode=key_vCode
				#authenticate (or not) the key
				cachedAPI=eveapi.EVEAPIConnection(cacheHandler=eveapi_cachehandler.CacheHandler(cache_dir='C:/web/www/evesolo_com/evesolo_site/eve_api_cache'))
				api_conn=cachedAPI.auth(keyID=key_id,vCode=key_vCode)
				try:
					api_char=api_conn.account.Characters().characters[0]
					char_name=api_char.name
				except:
					char_name=None
				if char_name==pilot.name:
					ok='Valid'
				else:
					ok='Invalid'
			pilots_ok.append((pilot,ok))
			
		players.append((player,pilots_ok))
			
	if len(players)==0:
		players=None		
	context['players']=players
	return context

def get_managed_boards_context(request):
	context={}
	player_managed_leaderboards=[]
	user_players=Player.objects.filter(user=request.user)
	pilots_boards=[]
	all_boards=[]
	for player in user_players:
		player_pilots=Pilot.objects.filter(player=player)
		leaderboards=[]
		#player pilots
		for pilot in player_pilots:			
			#grab the boards that the pilot has accepted invites for
			accepted_invites=Leaderboardinvites.objects.filter(pilot=pilot,status='ACCEPTED')
			participating_in_boards=[ inv.leaderboard for inv in accepted_invites ]
			if len(participating_in_boards)!=0:
				all_boards+=participating_in_boards
				pilots_boards.append((pilot,participating_in_boards))
						
		#player managed leaderboards
		player_leaderboards=Leaderboard.objects.filter(player=player)
		for leaderboard in player_leaderboards:
			leaderboards.append(leaderboard)
		if len(leaderboards)!=0:
			player_managed_leaderboards.append( (player,leaderboards) )

	#Player eligible to join leaderboards
	#by default, eligible for all boards that do not have any allowed participants/ships/systems
	eligible_leaderboards=get_sql_rows(sql_public_leaderboards)
	
	#players
	players=Player.objects.filter(user=request.user)
	
	#pilots
	pilots=Pilot.objects.filter(player__user=request.user)
	
	if len(players)==0:
		players=None
	if len(pilots)==0:
		pilots=None
	if len(player_managed_leaderboards)==0:
		player_managed_leaderboards=None
	if len(eligible_leaderboards)==0:
		eligible_leaderboards=None
	if len(pilots_boards)==0:
		pilots_boards=None
		
	
	context['eligible_leaderboards']=eligible_leaderboards
	context['pilots_boards']=pilots_boards
	context['player_managed_leaderboards']=player_managed_leaderboards
	context['players']=players
	context['pilots']=pilots
	return context


@login_required
def manage_boards(request):
	manage_boards_context=get_managed_boards_context(request)
	return render_to_response('evesolo/manage_boards.html',manage_boards_context,context_instance=RequestContext(request))
	

@login_required
def join_board(request):
	#POST request and should ahve 'joining_pilot_name' and
	#								'joining_board_id'
	#otherwise, flip back to profile screen
	if (not request.method=='POST'):
		manage_boards_context=get_managed_boards_context(request)
		return render_to_response('evesolo/manage_boards.html',manage_boards_context,context_instance=RequestContext(request))		
	
	joining_pilot_name=''
	if 'joining_pilot_name' in request.POST:
		joining_pilot_name=request.POST['joining_pilot_name'].strip()

	if len(joining_pilot_name)==0:
		manage_boards_context=get_managed_boards_context(request)
		manage_boards_context['error']='Please give a pilot name.'
		return render_to_response('evesolo/manage_boards.html',manage_boards_context,context_instance=RequestContext(request))

	if not 'joining_board_id' in request.POST:
		manage_boards_context=get_managed_boards_context(request)
		manage_boards_context['error']='Board not found.'
		return render_to_response('evesolo/manage_boards.html',manage_boards_context,context_instance=RequestContext(request))
	
	try:
		joining_board_id=int(request.POST['joining_board_id'])
	except ValueError:
		manage_boards_context=get_managed_boards_context(request)
		manage_boards_context['error']='Board not found.'
		return render_to_response('evesolo/manage_boards.html',manage_boards_context,context_instance=RequestContext(request))
	
	#check pilot is registered to any user players,
	#then the board exists, then make the LEaderboardinvites with status ACCEPTED
	
	#phase2 - Check pilot is in allowed participants
	#and has been invited
	try:
		joining_pilot=Pilot.objects.get(name=joining_pilot_name)
	except Pilot.DoesNotExist:
		manage_boards_context=get_managed_boards_context(request)
		manage_boards_context['error']='Unknown pilot trying to join a Leaderboard.'
		return render_to_response('evesolo/manage_boards.html',manage_boards_context,context_instance=RequestContext(request))

	if joining_pilot.player:
		if joining_pilot.player.user!=request.user:
			manage_boards_context=get_managed_boards_context(request)
			manage_boards_context['error']='You are not associated with that pilot.'
			return render_to_response('evesolo/manage_boards.html',manage_boards_context,context_instance=RequestContext(request))
	else:
		manage_boards_context=get_managed_boards_context(request)
		manage_boards_context['error']='Unknown pilot trying to join a Leaderboard.'
		return render_to_response('evesolo/manage_boards.html',manage_boards_context,context_instance=RequestContext(request))

	try:
		board_to_join=Leaderboard.objects.get(id=joining_board_id)
	except Leaderboard.DoesNotExist:
		manage_boards_context=get_managed_boards_context(request)
		manage_boards_context['error']='Board not found.'
		return render_to_response('evesolo/manage_boards.html',manage_boards_context,context_instance=RequestContext(request))
	
	existing_invites=Leaderboardinvites.objects.filter(leaderboard=board_to_join,pilot=joining_pilot,status='ACCEPTED')
	if len(existing_invites)>0:
		manage_boards_context=get_managed_boards_context(request)
		manage_boards_context['error']='The pilot is already participating in the leaderboard.'
		return render_to_response('evesolo/manage_boards.html',manage_boards_context,context_instance=RequestContext(request))
	
	#Ok. Create invite for Pilot with status='ACCEPTED'
	invite=Leaderboardinvites()
	invite.leaderboard=board_to_join
	invite.status='ACCEPTED'
	invite.pilot=joining_pilot
	
	save_object(invite,request)
	return HttpResponseRedirect(reverse('evesolo.views.manage_boards'))
	
@login_required
def leave_board(request):
	#POST request and should ahve 'resigning_board_id_pilot_id' in format '##:##'
	#otherwise, flip back to profile screen
	if (not request.method=='POST'):
		manage_boards_context=get_managed_boards_context(request)
		manage_boards_context['error']='No POST.'
		return render_to_response('evesolo/manage_boards.html',manage_boards_context,context_instance=RequestContext(request))		
	
	if not 'resigning_board_id_pilot_id' in request.POST:
		manage_boards_context=get_managed_boards_context(request)
		return render_to_response('evesolo/manage_boards.html',manage_boards_context,context_instance=RequestContext(request))

	try:
		resigning_board_id,resigning_pilot_id=request.POST['resigning_board_id_pilot_id'].split(':')
		resigning_board_id=int(resigning_board_id)
		resigning_pilot_id=int(resigning_pilot_id)
	except:
		manage_boards_context=get_managed_boards_context(request)
		return render_to_response('evesolo/manage_boards.html',manage_boards_context,context_instance=RequestContext(request))

	#check pilot is registered to any user players,
	#then the board exists
	
	try:
		resigning_pilot=Pilot.objects.get(id=resigning_pilot_id)
	except Pilot.DoesNotExist:
		manage_boards_context=get_managed_boards_context(request)
		manage_boards_context['error']='Unknown pilot trying to resign from a Leaderboard.'
		return render_to_response('evesolo/manage_boards.html',manage_boards_context,context_instance=RequestContext(request))

	if resigning_pilot.player:
		if resigning_pilot.player.user!=request.user:
			manage_boards_context=get_managed_boards_context(request)
			manage_boards_context['error']='You are not associated with that pilot.'
			return render_to_response('evesolo/manage_boards.html',manage_boards_context,context_instance=RequestContext(request))
	else:
		manage_boards_context=get_managed_boards_context(request)
		manage_boards_context['error']='Unknown pilot trying to resign from a Leaderboard.'
		return render_to_response('evesolo/manage_boards.html',manage_boards_context,context_instance=RequestContext(request))

	try:
		board_to_resign=Leaderboard.objects.get(id=resigning_board_id)
	except Leaderboard.DoesNotExist:
		manage_boards_context=get_managed_boards_context(request)
		manage_boards_context['error']='Board not found.'
		return render_to_response('evesolo/manage_boards.html',manage_boards_context,context_instance=RequestContext(request))
	
	#Ok. Remove ACCEPTED status invite for this board from pilot
	#(Kills remain associated)
	try:
		invite=Leaderboardinvites.objects.get(leaderboard=board_to_resign,pilot=resigning_pilot,status='ACCEPTED')
	except Leaderboardinvites.DoesNotExist:
		manage_boards_context=get_managed_boards_context(request)
		manage_boards_context['error']='Pilot is not participating in that leaderboard.'
		return render_to_response('evesolo/manage_boards.html',manage_boards_context,context_instance=RequestContext(request))

	#Phase2 We currently do not remove the associated kills. This will be a configurable option.
	
	invite.delete()
	return HttpResponseRedirect(reverse('evesolo.views.manage_boards'))
			
@login_required
def board_action(request):
	if request.method!='POST':
		manage_boards_context=get_managed_boards_context(request)
		return render_to_response('evesolo/manage_boards.html',manage_boards_context,context_instance=RequestContext(request))
	
	#hmm, this did work!
	if ('Remove' in request.POST) and (request.POST['Remove']):
		return delete_board(request,request.POST['Remove'])
	elif ('Edit' in request.POST) and (request.POST['Edit']):
		board_id=request.POST['Edit']
		request.POST=None
		request.method='GET'
		return edit_board(request,board_id)
	elif ('Update' in request.POST) and (request.POST['Update']):
		board_id=request.POST['Update']
		return edit_board(request,board_id)
	
@login_required	
def edit_board(request,board_id):
	manage_boards_context=get_managed_boards_context(request)
	players=Player.objects.filter(user=request.user)
	
	#check the board exists
	try:
		leaderboard_to_edit=Leaderboard.objects.get(id=board_id)
	except Leaderboard.DoesNotExist:
		manage_boards_context.update({'error':'Board not found.'})
		return render_to_response('evesolo/manage_boards.html',manage_boards_context,context_instance=RequestContext(request))
	
	#check board managed by player
	board_owner=leaderboard_to_edit.player
	if board_owner not in players:
		manage_boards_context.update({'error':'You do not manage that board.'})
		return render_to_response('evesolo/manage_boards.html',manage_boards_context,context_instance=RequestContext(request))

	#end of profile redirects, setup context for edit_board redirects
	allowed_participants=Leaderboardallowedparticipants.objects.filter(leaderboard=leaderboard_to_edit)
	allowed_ships=Leaderboardallowedships.objects.filter(leaderboard=leaderboard_to_edit)
	allowed_systems=Leaderboardallowedsystems.objects.filter(leaderboard=leaderboard_to_edit)
	
	context=dict()
	context['allowed_participants']=allowed_participants
	context['allowed_ships']=allowed_ships
	context['allowed_systems']=allowed_systems
	context['players']=players
	#TODO: Phase 2 add in pilots that are in this board and enable managment of them
	context={'leaderboard':leaderboard_to_edit}
	context.update(manage_boards_context)

	
	#if request has no POST or any bad POST, redirect back to form
	if (not request.method=='POST'):
		return render_to_response('evesolo/edit_leaderboard.html',context,context_instance=RequestContext(request))
	
	#validate & coerce fields
	if 'leaderboard_player_name' in request.POST:
		leaderboard_player_name=request.POST['leaderboard_player_name'].strip()
	else:
		leaderboard_player_name=leaderboard_to_edit.player.name
		
	if 'leaderboard_name' in request.POST:
		leaderboard_name=request.POST['leaderboard_name'].strip()
	else:
		leaderboard_name=leaderboard_to_edit.name
		
	if 'leaderboard_ranks' in request.POST:
		try:
			leaderboard_ranks=int(request.POST['leaderboard_ranks'].strip())
		except ValueError:
			context['error']='Please give the number of ranks to show in the leaderboard.'
			return render_to_response('evesolo/edit_leaderboard.html',context,context_instance=RequestContext(request))
	else:
		leaderboard_ranks=leaderboard_to_edit.ranks
		
	if 'leaderboard_rank_style' in request.POST:
		leaderboard_rank_style=request.POST['leaderboard_rank_style'].upper()
	else:
		leaderboard_rank_style=leaderboard_to_edit.rank_style
		
	if 'leaderboard_max_participants' in request.POST:
		try:
			leaderboard_max_participants=int(request.POST['leaderboard_max_participants'].strip())
		except ValueError:
			context['error']='Please give the max number of participants in the leaderboard.'
			return render_to_response('evesolo/edit_leaderboard.html',context,context_instance=RequestContext(request))
	else:
		leaderboard_max_participants=leaderboard_to_edit.max_participants
		
	if 'leaderboard_description' in request.POST:
		leaderboard_description=request.POST['leaderboard_description'].upper()
	else:
		leaderboard_description=leaderboard_to_edit.description
			
	
	
	#Its a good one, lets make the changes
	old_player=leaderboard_to_edit.player
	try:
		new_player=Player.objects.get(name=leaderboard_player_name)
	except Player.DoesNotExist:
		context['error']='Player does not exist.'
		return render_to_response('evesolo/edit_leaderboard.html',context,context_instance=RequestContext(request))
	#Check new player is owned by user
	if not request.user==new_player.user:
		context['error']='You do not own that player.'
		return render_to_response('evesolo/edit_leaderboard.html',context,context_instance=RequestContext(request))
	if old_player.name!=new_player.name:
		leaderboard_to_edit.player=new_player
	
	
	old_name=leaderboard_to_edit.name
	new_name=leaderboard_name
	if (old_name!=new_name) and (len(new_name)>0):
		leaderboard_to_edit.name=new_name
		
	old_ranks=leaderboard_to_edit.ranks
	new_ranks=leaderboard_ranks	
	if old_ranks!=new_ranks:
		leaderboard_to_edit.ranks=new_ranks
		
	old_rank_style=leaderboard_to_edit.rank_style
	new_rank_style=leaderboard_rank_style
	if (old_rank_style!=new_rank_style):
		if new_rank_style.upper() in valid_ranking_methods:
			leaderboard_to_edit.rank_style=new_rank_style.upper()
	
	old_max_participants=leaderboard_to_edit.max_participants
	new_max_participants=leaderboard_max_participants
	if old_max_participants!=new_max_participants:
		leaderboard_to_edit.max_participants=new_max_participants
		
	old_description=leaderboard_to_edit.description
	new_description=leaderboard_description
	if (old_description!=new_description) and (len(new_description.strip())>3):
		leaderboard_to_edit.description=new_description
		
	save_object(leaderboard_to_edit,request)
	
	return HttpResponseRedirect(reverse('evesolo.views.manage_boards'))
	
		
	
		
@login_required
def delete_board(request,board_id):
	manage_boards_context=get_managed_boards_context(request)
	players=Player.objects.filter(user=request.user)
	
	#check board exists
	try:
		leaderboard_to_delete=Leaderboard.objects.get(id=board_id)
	except Leaderboard.DoesNotExist:
		manage_boards_context.update({'error':'Board not found.'})
		return render_to_response('evesolo/manage_boards.html',manage_boards_context,context_instance=RequestContext(request))
	
	#check board managed by player
	board_owner=leaderboard_to_delete.player
	if board_owner not in players:
		manage_boards_context.update({'error':'You do not manage that board.'})
		return render_to_response('evesolo/manage_boards.html',manage_boards_context,context_instance=RequestContext(request))
	
	#then delete it
	leaderboard_to_delete.delete()
	return HttpResponseRedirect(reverse('evesolo.views.manage_boards'))


valid_ranking_methods=['POINTS','KILLS']
@login_required
def add_leaderboard(request):
	manage_boards_context=get_managed_boards_context(request)
	players=Player.objects.filter(user=request.user)
	if len(players)==0:
		manage_boards_context.update({'error':'You must add a player to your account before you can add a leaderboard to a player.'})
		return render_to_response('evesolo/manage_boards.html',manage_boards_context,context_instance=RequestContext(request))

	if not request.method=='POST' or ('leaderboard_name' not in request.POST):
		return render_to_response('evesolo/add_leaderboard.html',manage_boards_context,context_instance=RequestContext(request))
	
	player_name=request.POST['leaderboard_player_name'].strip()
	if len(player_name)==0:
		manage_boards_context['error']='Please give a player name.'
		return render_to_response('evesolo/add_leaderboard.html',manage_boards_context,context_instance=RequestContext(request))
	try:
		managing_player=Player.objects.get(name=player_name,user=request.user)
	except Player.DoesNotExist:
		manage_boards_context['error']='That player is not associated with your username.'
		return render_to_response('evesolo/add_leaderboard.html',manage_boards_context,context_instance=RequestContext(request))
	
	leaderboard_name=request.POST['leaderboard_name'].strip()
	if len(leaderboard_name)==0:
		manage_boards_context['error']='Please give a name for the leaderboard.'
		return render_to_response('evesolo/add_leaderboard.html',manage_boards_context,context_instance=RequestContext(request))
	
	leaderboard_ranks=request.POST['leaderboard_ranks'].strip()
	not_a_number=False
	try:
		leaderboard_ranks_int=int(leaderboard_ranks)
	except:
		not_a_number=True
	if (len(leaderboard_ranks)==0) or (not_a_number):
		manage_boards_context['error']='Please give the number of ranks to show on the leaderboard'
		return render_to_response('evesolo/add_leaderboard.html',manage_boards_context,context_instance=RequestContext(request))
	
	leaderboard_rank_style=request.POST['leaderboard_style']
	if (len(leaderboard_rank_style)==0) or (leaderboard_rank_style.upper() not in valid_ranking_methods):
		manage_boards_context['error']='Please select a ranking method.'
		return render_to_response('evesolo/add_leaderboard.html',manage_boards_context,context_instance=RequestContext(request))
	
	leaderboard_max_participants=request.POST['leaderboard_max_participants'].strip()
	not_a_number=False
	try:
		leaderboard_max_participants_int=int(leaderboard_max_participants)
	except:
		not_a_number=True
	if (len(leaderboard_max_participants)==0) or (not_a_number):
		manage_boards_context['error']='Please give the maximum number of participants in the leaderboard.'
		return render_to_response('evesolo/add_leaderboard.html',manage_boards_context,context_instance=RequestContext(request))

	leaderboard_description=request.POST['leaderboard_description'].strip()
	if len(leaderboard_description)<3:
		manage_boards_context['error']='Please enter a description (at least 3 characters) for the leaderboard.'
		return render_to_response('evesolo/add_leaderboard.html',manage_boards_context,context_instance=RequestContext(request))

	#Check the leaderboard is not asociated with another player
	leaderboard=get_or_create_leaderboard(name=leaderboard_name,manager=managing_player)
	#if any of the fields are set, then this leaderbaord already existed
	if leaderboard.description!='':
		manage_boards_context['error']='You already manage a board with that name, please choose another'
		return render_to_response('evesolo/add_leaderboard.html',manage_boards_context,context_instance=RequestContext(request))
	save_object(leaderboard,request)
	if leaderboard.player:
		if leaderboard.player.user:
			if not leaderboard.player.user==request.user:
				manage_boards_context['error']='The leaderboard name is already in use, please choose another'
				return render_to_response('evesolo/add_leaderboard.html',manage_boards_context,context_instance=RequestContext(request))		
	leaderboard.name=leaderboard_name
	leaderboard.ranks=leaderboard_ranks_int
	leaderboard.max_participants=leaderboard_max_participants_int
	leaderboard.rank_style=leaderboard_rank_style.upper()
	leaderboard.player=managing_player
	leaderboard.description=leaderboard_description
	save_object(leaderboard,request)
	return HttpResponseRedirect(reverse('evesolo.views.manage_boards'))	

	
@login_required
def add_player(request):
	if not request.method=='POST' or ('player_name' not in request.POST):
		return render_to_response('evesolo/add_player.html',context_instance=RequestContext(request))
	now=datetime.now()
	player_to_add=request.POST['player_name'].strip()
	#deal with empty player name
	if len(player_to_add)==0:
		return render_to_response('evesolo/add_player.html',{'error':'Please supply a player name.'},context_instance=RequestContext(request))
	#see if player exists, if so, error
	existing_player=Player.objects.filter(name=player_to_add)
	if len(existing_player)>0:
		return render_to_response('evesolo/add_player.html',{'error':'That player name already exists, please choose another.'},context_instance=RequestContext(request))
	
	player=Player()
	player.name=player_to_add
	player.reg_date=now
	player.user=request.user
	save_object(player,request)
	return HttpResponseRedirect(reverse('evesolo.views.profile'))


@login_required
def remove_player(request):
	profile_context=get_profile_context(request)
	players_pilots=profile_context['players']
	players=[ p[0] for p in players_pilots ]
	if len(players)==0:
		profile_context['error']='No players available to remove'
		return render_to_response('evesolo/profile.html',profile_context,context_instance=RequestContext(request))

	if not request.method=='POST' or ('player_name' not in request.POST):
		return render_to_response('evesolo/remove_player.html',profile_context,context_instance=RequestContext(request))
	
	#check if player is registered to user, if so, unlink pilots from player and unlink player from user, then delete player
	
	#check name is not 0 length
	player_name=request.POST['player_name'].strip()
	if len(player_name)==0:
		return render_to_response('evesolo/remove_player.html',{'error':'Please supply a player name.','players':players},context_instance=RequestContext(request))
	
	#check player exists
	existing_player=Player.objects.filter(name=player_name)
	if len(existing_player)==0:
		return render_to_response('evesolo/remove_player.html',{'error':'Player does not exist.','players':players},context_instance=RequestContext(request))
	
	player=existing_player[0]
	
	#check player is regsterd to user
	if not player.user==request.user:
		return render_to_response('evesolo/remove_player.html',{'error':'Player is not registered to you.','players':players},context_instance=RequestContext(request))
	
	#unlink player from user
	player.user=None
	
	#get pilots registered to player and unlink them
	pilots=Pilot.objects.filter(player=player)
	for pilot in pilots:
		pilot.player=None
		save_object(pilot,request)
		
	#save unlinked player
	save_object(player,request)
	
	#return to profile
	return HttpResponseRedirect(reverse('evesolo.views.profile'))
		
@login_required
def remove_pilot(request):
	profile_context=get_profile_context(request)
	#pilots is all pilots registered to all players registered to this user
	pilots=Pilot.objects.filter(player__user=request.user)
	if len(pilots)==0:
		profile_context['error']='No pilots available to remove.'
		return render_to_response('evesolo/profile.html',profile_context,context_instance=RequestContext(request))
	
	if not request.method=='POST' or ('pilot_name' not in request.POST):
		return render_to_response('evesolo/remove_pilot.html',{'pilots':pilots},context_instance=RequestContext(request))
	
	#Get pilot, see if is registered to any playerss registerd to this user, if so unlink pilot and save
	
	#check name is not 0 length
	pilot_name=request.POST['pilot_name'].strip()
	if len(pilot_name)==0:
		return render_to_response('evesolo/remove_pilot.html',{'error':'Please supply a pilot name.','pilots':pilots},context_instance=RequestContext(request))
	
	#check pilot exists
	existing_pilot=Pilot.objects.filter(name=pilot_name)
	if len(existing_pilot)==0:
		return render_to_response('evesolo/remove_pilot.html',{'error':'Pilot does not exist.','pilots':pilots},context_instance=RequestContext(request))
	
	pilot=existing_pilot[0]

	#check pilot is registered to a player
	if not pilot.player:
		return render_to_response('evesolo/remove_pilot.html',{'error':'Pilot is not registered to a player.','pilots':pilots},context_instance=RequestContext(request))
		
	#check pilot is registered to a player registered to this user
	if not pilot.player.user==request.user:
		return render_to_response('evesolo/remove_pilot.html',{'error':'Pilot is not registered to any of your players.','pilots':pilots},context_instance=RequestContext(request))
	
	#everything ok so far. unlink pilot from player
	pilot.player=None
	save_object(pilot,request)
	
	#return to profile
	return HttpResponseRedirect(reverse('evesolo.views.profile'))

@login_required
def logout(request):
	auth_logout(request)
	return HttpResponseRedirect(reverse('evesolo.views.latestkills'))

@login_required
def add_pilot(request):
	profile_context=get_profile_context(request)
	players_pilots=profile_context['players']
	players=[ p[0] for p in players_pilots ]
	if len(players)==0:
			return render_to_response('evesolo/profile.html',{'error':'You must add a player for your account before you can add a pilot to a player.'},context_instance=RequestContext(request))

	if request.method!='POST' or ( ('player_name' not in request.POST) or ('pilot_name' not in request.POST) or ('vCode' not in request.POST) or ('ID' not in request.POST) ):
		return render_to_response('evesolo/add_pilot.html',{'players':players},context_instance=RequestContext(request))
	
	player_name=request.POST['player_name'].strip()
	if len(player_name)==0:
		return render_to_response('evesolo/add_pilot.html',{'error':'Please supply a player name.','players':players},context_instance=RequestContext(request))
	
	try:
		player=Player.objects.get(name=player_name,user=request.user)
	except Player.DoesNotExist:
		return render_to_response('evesolo/add_pilot.html',{'error':'Player is not associated with your username.','players':players},context_instance=RequestContext(request))
	
	pilot_name=request.POST['pilot_name'].strip()
	if len(pilot_name)==0:
		return render_to_response('evesolo/add_pilot.html',{'error':'Please supply a pilot name.','players':players},context_instance=RequestContext(request))
	
	#check the given API details are for the given pilot name, if so, add or create pilot, set key details and associate with player
	try:
		key_id=int(request.POST['ID'])
		key_vCode=request.POST['vCode']
		cachedAPI=eveapi.EVEAPIConnection(cacheHandler=eveapi_cachehandler.CacheHandler(cache_dir='C:/web/www/evesolo_com/evesolo_site/eve_api_cache'))
		api_conn=cachedAPI.auth(keyID=key_id,vCode=key_vCode)
		api_char=api_conn.account.Characters().characters[0]
		char_name=api_char.name
	except:
		return render_to_response('evesolo/add_pilot.html',{'error':'There was a problem with the API details provided.','players':players},context_instance=RequestContext(request))
	if char_name!=pilot_name:
		return render_to_response('evesolo/add_pilot.html',{'error':'The API details provided are not for the pilot specified.','players':players},context_instance=RequestContext(request))
	
	#API authenticated, and is for the correct pilot

	#Check the pilot is not asociated with another player
	pilot=get_or_create_pilot(name=pilot_name)
	if pilot.player:
		if pilot.player.user:
			if not pilot.player.user==request.user:
				return render_to_response('evesolo/add_pilot.html',{'error':'Pilot is registered to another users player.','players':players},context_instance=RequestContext(request))
		

	pilot.api_key='[[%s]]%s' % (key_id,key_vCode)
	pilot.player=player
	pilot.corp=''
	pilot.alliance=''
	pilot.faction=''
	save_object(pilot,request)
		
	return HttpResponseRedirect(reverse('evesolo.views.profile'))

def log(msg):
	LOG=False
	if LOG:
		print msg
	

	#'http://kb.pleaseignore.com/?a=idfeed'
#def pull_mails(request,pilot_id=None,killboard_url=None):
#pilot_id and killboard_url to be collected via POST		
@login_required
def pull_mails(request):
	killboard_url=None
	pilot_id=None
	
	if not request.method=='POST':
		return profile(request)
	if not 'pilot_id' in request.POST:
		return profile(request)

	try:
		pilot_id=int(request.POST['pilot_id'])
	except ValueError:
		return profile(request)
		
	if not pilot_id:
		killboard_pull=True
	else:
		killboard_pull=False
		pilot_id=int(pilot_id)
		
	total_mails=0
	non_player_wins=0
	already_posted_verified_mails=0
	disputed_mails=0
	already_posted=0
	posted_mails=0
	posted_kills=[]
	seen_kill_ids=set()
	getting_killmails=True
	now=datetime.now()
	same_corp_kills=0
	same_alliance_kills=0

	#get this from DB
#	highest_kill_id=22991713
	highest_kill_id=1
	dupe_limit=20 #maybe maybe not
	log('starting Highest Kill ID is'+str(highest_kill_id))
	while getting_killmails:
		log('Going around the while getting_killmails loop')
		kills=get_api_mail_block(request,pilot_id=pilot_id,
										killboard_url=killboard_url,
										latest_kill_id=highest_kill_id,
										error_page='evesolo/pull_summary.html',
										bailout_page=reverse('evesolo.views.profile'))				
										
		if type(kills) in [HttpResponse,HttpResponseRedirect]:
			return kills

		for kill in kills:
			total_mails+=1

			KM=km_parser.EveKillmail()
			if not KM.parse_killmail_from_eveapi(kill):
				try:
					highest_kill_id=max(highest_kill_id,KM.kill_id)
					print 'Highest seen killid is',highest_kill_id
				except AttributeError:
					pass
				print 'Malformed kill from API pull'
				continue
			
			if KM.kill_id in seen_kill_ids:
				#do not process dupes seen in pull session (most useful when pulling v.large
				#numbers of kills from a KB
				continue			
			else:
				seen_kill_ids.add(KM.kill_id)
			highest_kill_id=max(highest_kill_id,KM.kill_id)
			print 'Highest seen killid is',highest_kill_id
			if KM.is_solo_mail():
				losing_pilot_info=get_km_losing_pilot_info(killmail=KM)
				
				#Do we understand the shiptype?
				if not losing_pilot_info['ship']:
					print "LOSING PILOT IS A WHAT?"
					#LOG THIS SOMEWHERE...
					continue
				
				#Was the winning pilot an NPC?
				winning_pilot_info=get_km_winning_pilot_info(killmail=KM)
				if not winning_pilot_info['ship']:
					non_player_wins+=1
					continue
				
				#Are the players in the same alliance or corp?
				
				##NOTE: This will be togglable when corp/alliance/user leaderboards are implemented
				if winning_pilot_info['corp']==losing_pilot_info['corp']:
					same_corp_kills+=1
					continue
				wining_pilot_alliance=winning_pilot_info['alliance']
				losing_pilot_alliance=losing_pilot_info['alliance']
				if (wining_pilot_alliance not in ['',None]) and (losing_pilot_alliance not in ['',None]):
					if wining_pilot_alliance==losing_pilot_alliance:
						same_alliance_kills+=1
						continue
				
				
				
				#we get dateime object from eveapi not string so ..
				kill_date_time=KM.kill_date
				submit_date_time=datetime.now()
				#already an int from eveapi parsed mails
				kill_damage=KM.victim['Damage Taken:']

				#do either of the pilots exist?
				#if not, create blank pilot, else get the Pilot record
				#update and save losing pilot
				losing_pilot=update_or_create_pilot(request,losing_pilot_info)
				winning_pilot=update_or_create_pilot(request,winning_pilot_info)

				#create the solokill if it does not exist
				existing_sk=Solokill.objects.filter(losing_pilot=losing_pilot,
												 winning_pilot=winning_pilot,
												 kill_date=kill_date_time)

				if len(existing_sk)!=0:
					existing_sk=existing_sk[0]
					#Killmail already posted
					already_posted+=1
					#Set to verified if same pilots and ships, then save
					
					if not existing_sk.verified:
						same_winning_ships=(existing_sk.winners_ship.name==winning_pilot_info['ship'].name)
						same_losing_ships=(existing_sk.losers_ship.name==losing_pilot_info['ship'].name)
						if  same_winning_ships and same_losing_ships:
							if not killboard_pull:
								existing_sk.verified=True
								save_object(existing_sk,request)
								already_posted_verified_mails+=1
							continue
						else:
							#existing mail not verified, and incoming mail different ships
							#if incoming mail is from trusted source: remove old, create new
							#if not trusted: keep old, create new -:- one will be trusted eventually
							disputed_mails+=1
							if killboard_pull:
								print 'DISPUTE:: Previous kill with differing ships found from UNTRUSTED SOURCE'
								#delete the existing_sk and continue with processing the posted mail
								#if its a pilot_id (EVE API) pull
								#otherwise leave as is and continue add new mail. one or 'tother will never become verified.
							else:
								print 'DISPUTE:: Previous kill with differing ships found from API'
								existing_sk.delete()
					else:
						continue
				###
				
				#get the kill_points
				Lp=losing_pilot_info['ship'].hull_class.fwp_value
				Wp=winning_pilot_info['ship'].hull_class.fwp_value
				kill_points=calculate_kill_points(Lp,Wp)

				#save the kill - verified this time as from eveapi
				solokill=Solokill(losing_pilot=losing_pilot,
										winning_pilot=winning_pilot,
										losers_ship=losing_pilot_info['ship'],
										winners_ship=winning_pilot_info['ship'],
										points_awarded=kill_points,
										damage=kill_damage,
										submit_date=submit_date_time,
										kill_date=kill_date_time,
										verified=KM.from_api,
										kill_text='From API')
				save_object(solokill,request)
				posted_mails+=1
				posted_kills.append(solokill)
					
			#IF NOT SOLO MAIL and if from TRUSTED SOURCE
			#SEE IF SOLOKILL EXISTS FOR LOSING PILOT AT THIS EXACT TIME
			#IF DOES, NUKE IT!
			#removes kills people have hand-posted by removing other active parties
			else:
				existing_sk=Solokill.objects.filter(losing_pilot__name=KM.victim['Victim:'],
													kill_date=KM.kill_date)
				if len(existing_sk)!=0:
					print 'DISPUTE:: deleting - discovered previous solokill but with many parties on new kill'
					disputed_mails+=1
					#existing_sk.delete() leave it in only one of the fakes will ever be validated from a real api pull
					#
		else: #end >for kill in kills
			if killboard_pull:
				if len(kills)==0: getting_killmails=not getting_killmails
			else:
				getting_killmails=not getting_killmails
	
	return render_to_response('evesolo/pull_summary.html',{'solo_mails':posted_mails+already_posted,
																'already_posted':already_posted,
																'posted_mails':posted_mails,
																'kill_list':posted_kills,
																'total_mails':total_mails,
																'non_player_wins':non_player_wins,
																'same_corp_kills':same_corp_kills,
																'same_alliance_kills':same_alliance_kills,
																'already_posted_verified_mails':already_posted_verified_mails,
																'disputed_mails':disputed_mails},context_instance=RequestContext(request))

@login_required
def profile(request):
	#get player associated with user if any, and pilots associated with player if any
	profile_context=get_profile_context(request)
	return render_to_response('evesolo/profile.html',profile_context,context_instance=RequestContext(request))

def leaderboards_summary(request,verified=False):
	now=datetime.now()
	interval_week=datetime.strftime(now-timedelta(days=7),'%Y%m%d%H%M%S')
	interval_month=datetime.strftime(now-timedelta(days=31),'%Y%m%d%H%M%S')
	interval_quarter=datetime.strftime(now-timedelta(days=91),'%Y%m%d%H%M%S')
	interval_half=datetime.strftime(now-timedelta(days=182),'%Y%m%d%H%M%S')
	interval_year=datetime.strftime(now-timedelta(days=365),'%Y%m%d%H%M%S')
	
	context={}
	
	if verified:
		sql=sql_all_class_ranking_ver
	else:
		sql=sql_all_class_ranking
		
	rank_sets=[]
	rank_sets.append( ('All Time',get_sql_rows(sql % ('20010101010101'))) )
	rank_sets.append( ('Past Week',get_sql_rows(sql % (interval_week))))
	rank_sets.append( ('Past Month',get_sql_rows(sql % (interval_month))))
	rank_sets.append( ('Past Quarter',get_sql_rows(sql % (interval_quarter))))
	rank_sets.append( ('Past Half Year',get_sql_rows(sql % (interval_half))))
	rank_sets.append( ('Past Year',get_sql_rows(sql % (interval_year))))
	
	context['rank_sets']=rank_sets
	context['header_title']='All Class Leaderboards'
	context['html_title']=None
	context['verified']=verified
	context['verified_link']='<ul><li><a href="/leaderboards_summary/verified/">Switch to verified kills only</a></li></ul>'
	context['unverified_link']='<ul><li><a href="/leaderboards_summary/">Switch to all kills</a></li></ul>'
	return render_to_response('evesolo/leaderboard.html',context,context_instance=RequestContext(request))

def leaderboards_summary_custom(request,leaderboard_id):
	context={}
	try:
		leaderboard_id=int(leaderboard_id)
	except ValueError:
		context['error']='Unknown leaderboard.'
		return render_to_response('evesolo/leaderboard.html',context,context_instance=RequestContext(request))
	
	try:
		leaderboard=Leaderboard.objects.get(id=leaderboard_id)
	except Leaderboard.DoesNotExist:
		context['error']='Unknown leaderboard.'
		return render_to_response('evesolo/leaderboard.html',context,context_instance=RequestContext(request))

	#Run the leaderbaords summary, but restrict to kills registered to the given leaderboard
	#determine what rank style and use appropriate sql
	now=datetime.now()
	interval_week=datetime.strftime(now-timedelta(days=7),'%Y%m%d%H%M%S')
	interval_month=datetime.strftime(now-timedelta(days=31),'%Y%m%d%H%M%S')
	interval_quarter=datetime.strftime(now-timedelta(days=91),'%Y%m%d%H%M%S')
	interval_half=datetime.strftime(now-timedelta(days=182),'%Y%m%d%H%M%S')
	interval_year=datetime.strftime(now-timedelta(days=365),'%Y%m%d%H%M%S')
	context={}
	
	if leaderboard.rank_style=='POINTS':
		sql=sql_all_class_ranking_custom_points
	else:
		sql=sql_all_class_ranking_custom_kills
		
	rank_sets=[]
	rank_sets.append( ('All Time',get_sql_rows(sql % (leaderboard_id,'20010101010101'))) )
	rank_sets.append( ('Past Week',get_sql_rows(sql % (leaderboard_id,interval_week))))
	rank_sets.append( ('Past Month',get_sql_rows(sql % (leaderboard_id,interval_month))))
	rank_sets.append( ('Past Quarter',get_sql_rows(sql % (leaderboard_id,interval_quarter))))
	rank_sets.append( ('Past Half Year',get_sql_rows(sql % (leaderboard_id,interval_half))))
	rank_sets.append( ('Past Year',get_sql_rows(sql % (leaderboard_id,interval_year))))
	
	context['rank_sets']=rank_sets
	context['header_title']='Leaderboard rankings: %s' % leaderboard.name
	context['html_title']=None
	context['include_verify']=False
	return render_to_response('evesolo/leaderboard.html',context,context_instance=RequestContext(request))

def ship_leaderboard(request,ship_id,verified=False):
	now=datetime.now()
	interval_week=datetime.strftime(now-timedelta(days=7),'%Y%m%d%H%M%S')
	interval_month=datetime.strftime(now-timedelta(days=31),'%Y%m%d%H%M%S')
	interval_quarter=datetime.strftime(now-timedelta(days=91),'%Y%m%d%H%M%S')
	interval_half=datetime.strftime(now-timedelta(days=182),'%Y%m%d%H%M%S')
	interval_year=datetime.strftime(now-timedelta(days=365),'%Y%m%d%H%M%S')
	ship_id=int(ship_id)
	
	try:
		ship=Ship.objects.get(pk=ship_id)
	except Ship.DoesNotExist:
		return render_to_response('evesolo/leaderboard.html',{'error':'Leaderboard cannot be found.'},context_instance=RequestContext(request))

	if verified:
		sql=sql_ship_ranking_ver
	else:
		sql=sql_ship_ranking
	
	context={}
	rank_sets=[]
	rank_sets.append( ('All Time',get_sql_rows(sql % ('20010101010101',ship_id))) )
	rank_sets.append( ('Past Week',get_sql_rows(sql % (interval_week,ship_id))))
	rank_sets.append( ('Past Month',get_sql_rows(sql % (interval_month,ship_id))))
	rank_sets.append( ('Past Quarter',get_sql_rows(sql % (interval_quarter,ship_id))))
	rank_sets.append( ('Past Half Year',get_sql_rows(sql % (interval_half,ship_id))))
	rank_sets.append( ('Past Year',get_sql_rows(sql % (interval_year,ship_id))))
	context['rank_sets']=rank_sets
	context['header_title']=None
	#Waiter, There's HTML in my soup!
	context['html_title']='<center><h1><img src="http://image.eveonline.com/Render/%d_128.png"></img>%s Leaderboards</h1></center>' % (ship.CCPID.ccp_id, ship.name)
	context['verified']=verified
	context['verified_link']='<ul><li><a href="/leaderboards_ship/%d/verified/">Switch to verified kills only</a></li></ul>' % ship_id
	context['unverified_link']='<ul><li><a href="/leaderboards_ship/%d/">Switch to all kills</a></li></ul>' % ship_id
	return render_to_response('evesolo/leaderboard.html',context,context_instance=RequestContext(request))
		
def class_leaderboard(request,hullclass_id,verified=False):
	now=datetime.now()
	interval_week=datetime.strftime(now-timedelta(days=7),'%Y%m%d%H%M%S')
	interval_month=datetime.strftime(now-timedelta(days=31),'%Y%m%d%H%M%S')
	interval_quarter=datetime.strftime(now-timedelta(days=91),'%Y%m%d%H%M%S')
	interval_half=datetime.strftime(now-timedelta(days=182),'%Y%m%d%H%M%S')
	interval_year=datetime.strftime(now-timedelta(days=365),'%Y%m%d%H%M%S')

	hullclass_id=int(hullclass_id)
	try:
		hullclass=Hullclass.objects.get(pk=hullclass_id)
	except Hullclass.DoesNotExist:
		return render_to_response('evesolo/leaderboard.html',{'error':'Leaderboard cannot be found.'},context_instance=RequestContext(request))
	
	if verified:
		sql=sql_class_ranking_ver
	else:
		sql=sql_class_ranking
	
	context={}
	rank_sets=[]
	rank_sets.append( ('All Time',get_sql_rows(sql % ('20010101010101',hullclass_id))))
	rank_sets.append( ('Past Week',get_sql_rows(sql % (interval_week,hullclass_id))))
	rank_sets.append( ('Past Month',get_sql_rows(sql % (interval_month,hullclass_id))))
	rank_sets.append( ('Past Quarter',get_sql_rows(sql % (interval_quarter,hullclass_id))))
	rank_sets.append( ('Past Half Year',get_sql_rows(sql % (interval_half,hullclass_id))))
	rank_sets.append( ('Past Year',get_sql_rows(sql % (interval_year,hullclass_id))))
	context['rank_sets']=rank_sets
	context['header_title']=hullclass.human_name
	context['html_title']=None
	context['verified']=verified
	context['verified_link']='<ul><li><a href="/leaderboards_class/%d/verified/">Switch to verified kills only</a></li></ul>' % hullclass_id
	context['unverified_link']='<ul><li><a href="/leaderboards_class/%d/">Switch to all kills</a></li></ul>' % hullclass_id
	return render_to_response('evesolo/leaderboard.html',context,context_instance=RequestContext(request))
	
def newmail(request):
	return render_to_response('evesolo/newmail.html',context_instance=RequestContext(request))

	
def postmail(request):
	if request.method=='POST':
		KM=km_parser.EveKillmail()
		try:
			KM.parse_killmail_from_copypaste(request.POST['killtext'])
		except ParseException:
			return render_to_response('evesolo/newmail.html',
									  {'error':'We had trouble interpreting that killmail, please check it and try again.'},
									  context_instance=RequestContext(request))		
		#ensure is a valid solo mail, if so then create the Solokill object
		if KM.is_solo_mail():
			losing_pilot_info=get_km_losing_pilot_info(killmail=KM)
			winning_pilot_info=get_km_winning_pilot_info(killmail=KM)
			if (not losing_pilot_info['ship']) or (not winning_pilot_info['ship']):
				return render_to_response('evesolo/newmail.html',
						  {'error':'One of the ships on the killmail was of an unknown type.'},
						  context_instance=RequestContext(request))
			try:
				kill_date_time=datetime.strptime(KM.kill_date,'%Y.%m.%d %H:%M:%S')
			except ValueError:
				kill_date_time=datetime.strptime(KM.kill_date,'%Y.%m.%d %H:%M')
			submit_date_time=datetime.now()
			
			kill_damage=int(KM.victim['Damage Taken:'])
			
			
			#do either of the pilots exist?
			#if not, create blank pilot, else get the Pilot record
			#update and save
			losing_pilot=update_or_create_pilot(request,losing_pilot_info)
			winning_pilot=update_or_create_pilot(request,winning_pilot_info)

			#extract the KM lines we are after
			relevant_km_lines=[]
			for line in KM.kill_text.split('\n'):
				if line.startswith('Destroyed items:') or line.startswith('Dropped items:'):
					break
				if len(line)!=0:
					relevant_km_lines.append(line)
			relevant_km_lines='\n'.join(relevant_km_lines)

			#create the solokill if it does not exist
			existing_sk=Solokill.objects.filter(losing_pilot=losing_pilot,
											 winning_pilot=winning_pilot,
											 kill_date=kill_date_time)
			if len(existing_sk)!=0:
				#Killmail already posted
				return render_to_response('evesolo/newmail.html',
										  {'kill_id':existing_sk[0].id,
										  'message':'That kill has already been posted, view it <a href="/kills/%d/">here</a>' % existing_sk[0].id},
										  context_instance=RequestContext(request))
			
			
			#get the kill_points
			Lp=losing_pilot_info['ship'].hull_class.fwp_value
			Wp=winning_pilot_info['ship'].hull_class.fwp_value
			kill_points=calculate_kill_points(Lp,Wp)
			
			#save the kill
			solokill=Solokill(losing_pilot=losing_pilot,
									winning_pilot=winning_pilot,
									losers_ship=losing_pilot_info['ship'],
									winners_ship=winning_pilot_info['ship'],
									points_awarded=kill_points,
									damage=kill_damage,
									submit_date=submit_date_time,
									kill_date=kill_date_time,
									verified=False,
									kill_text=relevant_km_lines)
			save_object(solokill,request)
			
			return HttpResponseRedirect(reverse('evesolo.views.viewkill',args=(solokill.id,)))
		else:
			#Not a Solo kill!
			return render_to_response('evesolo/newmail.html',
									  {'error':'The EveSolo killboards only accept solo combat killmails.'},
									  context_instance=RequestContext(request))
	return HttpResponseRedirect(reverse('evesolo.views.newmail'))

def latestkills(request,error=None):
	latest_kills=Solokill.objects.exclude(points_awarded=0).order_by('-kill_date')[:10]
	
	latest_submitted_kills=Solokill.objects.exclude(points_awarded=0).order_by('-submit_date')[:10]
	return render_to_response('evesolo/latestkills.html',{'latest_kills':latest_kills,
														  'latest_submitted_kills':latest_submitted_kills,
														  'error':error},
														  context_instance=RequestContext(request))

def viewkill(request,solokill_id):
	solokill_id=int(solokill_id)
	try:
		sk=Solokill.objects.get(pk=solokill_id)
	except Solokill.DoesNotExist:
		return render_to_response('evesolo/viewkill.html',{'error':'The kill details were not found.'},context_instance=RequestContext(request))
	if sk.verified==False:
		sk.verified='Not Verified'
	else:
		sk.verified='Verified'
	return render_to_response('evesolo/viewkill.html',{'kill':sk},context_instance=RequestContext(request))

def pilot(request,pilot_id,verified=False):
	#get allclass alltime rank/points
	pilot_id=int(pilot_id)
	try:
		pilot=Pilot.objects.get(pk=pilot_id)
	except Pilot.DoesNotExist:
		return render_to_response('evesolo/pilot_summary.html',{'error':'Sorry, that pilot could not be found'},context_instance=RequestContext(request))
		
#Get rank positions in week/month/quart/half/year leaderboards
	now=datetime.now()
	interval_week=datetime.strftime(now-timedelta(days=7),'%Y%m%d%H%M%S')
	prev_week_start=datetime.strftime(now-timedelta(days=14),'%Y%m%d%H%M%S')
	interval_month=datetime.strftime(now-timedelta(days=31),'%Y%m%d%H%M%S')
	prev_month_start=datetime.strftime(now-timedelta(days=62),'%Y%m%d%H%M%S')
	interval_quarter=datetime.strftime(now-timedelta(days=91),'%Y%m%d%H%M%S')
	prev_quarter_start=datetime.strftime(now-timedelta(days=182),'%Y%m%d%H%M%S')
	interval_half=datetime.strftime(now-timedelta(days=182),'%Y%m%d%H%M%S')
	prev_half_start=datetime.strftime(now-timedelta(days=364),'%Y%m%d%H%M%S')
	interval_year=datetime.strftime(now-timedelta(days=365),'%Y%m%d%H%M%S')
	prev_year_start=datetime.strftime(now-timedelta(days=730),'%Y%m%d%H%M%S')
	
	context={}
	
	if verified:
		sql=sql_all_class_ranking_ver_nolimit
		sql_interval=sql_all_class_ranking_interval_ver_nolimit
	else:
		sql=sql_all_class_ranking_nolimit
		sql_interval=sql_all_class_ranking_interval_nolimit

		
		
	try:
		all_time_rank=[ r[0] for r in get_sql_rows(sql % ('20010101010101'))].index(pilot_id)+1
	except ValueError:
		all_time_rank='-'

		
		
	try:
		past_week_rank=[ r[0] for r in get_sql_rows(sql % (interval_week))].index(pilot_id)+1
	except ValueError:
		past_week_rank='-'
	try:
		ppast_week_rank=[ r[0] for r in get_sql_rows(sql_interval % (prev_week_start,interval_week))].index(pilot_id)+1
	except:
		ppast_week_rank='-'
	
	
	
	try:
		past_month_rank=[ r[0] for r in get_sql_rows(sql % (interval_month))].index(pilot_id)+1
	except ValueError:
		past_month_rank='-'
	try:
		ppast_month_rank=[ r[0] for r in get_sql_rows(sql_interval % (prev_month_start,interval_month))].index(pilot_id)+1
	except:
		ppast_month_rank='-'

		
		
	try:
		past_quarter_rank=[ r[0] for r in get_sql_rows(sql % (interval_quarter))].index(pilot_id)+1
	except ValueError:
		past_quarter_rank='-'
	try:
		ppast_quarter_rank=[ r[0] for r in get_sql_rows(sql_interval % (prev_quarter_start,interval_quarter))].index(pilot_id)+1
	except:
		ppast_quarter_rank='-'

		
		
		
	try:
		past_half_year_rank=[ r[0] for r in get_sql_rows(sql % (interval_half))].index(pilot_id)+1
	except ValueError:
		past_half_year_rank='-'
	try:
		ppast_half_year_rank=[ r[0] for r in get_sql_rows(sql_interval % (prev_half_start,interval_half))].index(pilot_id)+1
	except:
		ppast_half_year_rank='-'

		
		
	try:
		past_year_rank=[ r[0] for r in get_sql_rows(sql % (interval_year))].index(pilot_id)+1
	except ValueError:
		past_year_rank='-'
	try:
		ppast_year_rank=[ r[0] for r in get_sql_rows(sql_interval % (prev_year_start,interval_year))].index(pilot_id)+1
	except:
		ppast_year_rank='-'



		
	all_pilot_scores=Pilot.objects.annotate(total_points=Sum('winning_pilot__points_awarded'))
	all_class=all_pilot_scores.order_by('-total_points','name')
	pilot_points=all_class.get(pk=pilot_id).total_points

	#get pilot w:l ratio
	pilot_winkills=Solokill.objects.filter(winning_pilot=pilot)
	pilot_losskills=Solokill.objects.filter(losing_pilot=pilot)
	pilot_wins=len(pilot_winkills)
	pilot_losses=len(pilot_losskills)
	w_l_ratio='%d - %d' % (pilot_wins,pilot_losses)
	#Class w/most wins
	pilot_class_wins=get_sql_rows(sql_pilot_hullclass_wins_points % pilot.id)
	if len(pilot_class_wins)!=0: #####
		pilot_best_class=pilot_class_wins[0][0]
		pilot_best_class_wins=pilot_class_wins[0][1]
		pilot_best_class_wins_points=pilot_class_wins[0][2]
		pilot_best_class_id=pilot_class_wins[0][3]
	else:
		pilot_best_class='No Wins'
		pilot_best_class_wins=0
		pilot_best_class_wins_points=0
		pilot_best_class_id=0

	#Ship w/most wins
	pilot_ship_wins=get_sql_rows(sql_pilot_ship_wins_points % pilot.id)
	if len(pilot_ship_wins)!=0: ####
		pilot_best_ship=pilot_ship_wins[0][0]
		best_ship_obj=Ship.objects.get(name=pilot_best_ship)
		pilot_best_ship_wins=pilot_ship_wins[0][1]
		pilot_best_ship_wins_points=pilot_ship_wins[0][2]
		pilot_best_ship_id=pilot_ship_wins[0][3]
	else:
		pilot_best_ship='No Wins'
		pilot_best_ship_wins=0
		pilot_best_ship_wins_points=0
		pilot_best_ship_id=0
		
	#favourite ship
	pilot_favourite_ships=get_sql_rows(sql_pilot_ships_seen_count % (pilot_id,pilot_id))
	
	
	#last 10 fights
	last_10_fights=Solokill.objects.filter(Q(winning_pilot=pilot)|Q(losing_pilot=pilot)).order_by('-kill_date')[:10]
	
	
#	all_time_rank=[ r[0] for r in get_sql_rows(sql % ('20010101010101'))].index(pilot_id)+1
#	past_week_rank=[ r[0] for r in get_sql_rows(sql % (interval_week))].index(pilot_id)+1
#	past_month_rank=[ r[0] for r in get_sql_rows(sql % (interval_month))].index(pilot_id)+1
#	past_quarter_rank=[ r[0] for r in get_sql_rows(sql % (interval_quarter))].index(pilot_id)+1
#	past_half_year_rank=[ r[0] for r in get_sql_rows(sql % (interval_half))].index(pilot_id)+1
#	past_year_rank=[ r[0] for r in get_sql_rows(sql % (interval_year))].index(pilot_id)+1

	return render_to_response('evesolo/pilot_summary.html',
							  {'rank':all_time_rank,
							   'past_week_rank':past_week_rank,
							   'past_month_rank':past_month_rank,
							   'past_quarter_rank':past_quarter_rank,
							   'past_half_year_rank':past_half_year_rank,
							   'past_year_rank':past_year_rank,
							   'ppast_week_rank':ppast_week_rank,
							   'ppast_month_rank':ppast_month_rank,
							   'ppast_quarter_rank':ppast_quarter_rank,
							   'ppast_half_year_rank':ppast_half_year_rank,
							   'ppast_year_rank':ppast_year_rank,
							   'points':pilot_points,
							   'pilot':pilot,
							   'winloss':w_l_ratio,
							   'bestclass':pilot_best_class,
							   'bestclasswins':pilot_best_class_wins,
							   'bestclasswinspoints':pilot_best_class_wins_points,
							   'bestclassid':pilot_best_class_id,
							   'bestship':pilot_best_ship,
							   'bestshipwins':pilot_best_ship_wins,
							   'bestshipwinspoints':pilot_best_ship_wins_points,
							   'bestshipid':pilot_best_ship_id,
							   'latest_kills':last_10_fights,
							   'most_seen_ships':pilot_favourite_ships},
							   context_instance=RequestContext(request))


def ship_stats(request):

	#OVERALL
	rank_sets=[]
	#[ (class_name,most_pop,most_wins,most_losses,best_wl,worst_wl
	ctr=0
	nav_set=[] #[ ( ('text','link'),('textN','linkN'),... ),...x5 ]
	texts_links=[]
	for hull_id in range(3,19):
		class_name=Hullclass.objects.get(pk=hull_id).human_name
		texts_links.append( (class_name,class_name) )
		ctr+=1
		if ctr==5:
			nav_set.append(texts_links)
			texts_links=[]
			ctr=0
		most_pop=get_sql_rows(sql_most_popular_ships_by_class % hull_id)
		most_wins=get_sql_rows(sql_ships_most_wins_by_class % hull_id)
		most_losses=get_sql_rows(sql_ships_most_losses_by_class % hull_id)
		best_wl=get_sql_rows(sql_ships_best_wl_ratio_by_class % hull_id)
		worst_wl=get_sql_rows(sql_ships_worst_wl_ratio_by_class % hull_id)
		rank_sets.append( (class_name,[('Most Popular',most_pop,'Wins + Losses'),
									('Most Wins',most_wins,'Wins'),
									('Most Losses',most_losses,'Losses'),
									('Best Win:Loss Ratio',best_wl,'Win/Loss'),
									('Worst Win:Loss Ratio',worst_wl,'Win/Loss')]) )
		
	return render_to_response('evesolo/ship_stats.html',
							{'rank_sets':rank_sets,
							'nav_set':nav_set},
							context_instance=RequestContext(request))
	

def get_manage_kills_context(request):
	now=datetime.now()
	interval_sixweeks=datetime.date(now-timedelta(days=360))#42

	manage_kills_context={}
	#Player pilots
	pilots=Pilot.objects.filter(player__user=request.user)
	if len(pilots)==0:
		pilots=None
	manage_kills_context['pilots']=pilots
	
	#winning_kills
	kill_list=Solokill.objects.filter(winning_pilot__player__user=request.user,kill_date__gt=interval_sixweeks).order_by('-kill_date')
	#kill_list=Solokill.objects.all() ##
	manage_kills_context['kill_list']=[ kill for kill in kill_list if kill.verified ]
	
	#leadrboards
	leaderboards=[]
	for pilot in pilots:
		pilot_accepted_invites=Leaderboardinvites.objects.filter(pilot=pilot,status='ACCEPTED')
		leaderboards+=[invite.leaderboard for invite in pilot_accepted_invites]
	manage_kills_context['leaderboards']=list(set(leaderboards))
	return manage_kills_context
		

@login_required
def manage_kills(request):
	context=get_manage_kills_context(request)
	if request.method!='POST':
		return render_to_response('evesolo/manage_kills.html',context,context_instance=RequestContext(request))
	
		
	#Find out what function triggered the POST
	if ('pilot_filter' in request.POST) and (request.POST['pilot_filter']):
		if request.POST['filter_by_pilot']=='ALL':
			return render_to_response('evesolo/manage_kills.html',context,context_instance=RequestContext(request))
		
		try:
			filter_by_pilot_id=int(request.POST['filter_by_pilot'])
		except ValueError:
			
			context['error']='Unknown pilot.'
			return render_to_response('evesolo/manage_kills.html',context,context_instance=RequestContext(request))
		try:
			filter_by_pilot=Pilot.objects.get(id=filter_by_pilot_id)
		except Pilot.DoesNotExist:
			context['error']='Unknown pilot.'
			return render_to_response('evesolo/manage_kills.html',context,context_instance=RequestContext(request))
		kill_list=context['kill_list']
		context['kill_list']=[kill for kill in kill_list if kill.winning_pilot==filter_by_pilot]
		
		#leaderboards filter
		pilot_accepted_invites=Leaderboardinvites.objects.filter(pilot=filter_by_pilot,status='ACCEPTED')
		leaderboards=[invite.leaderboard for invite in pilot_accepted_invites]
		context['leaderboards']=leaderboards
		return render_to_response('evesolo/manage_kills.html',context,context_instance=RequestContext(request))
	
	elif ('enter_kills' in request.POST) and (request.POST['enter_kills']):
		if not 'solokills_to_add' in request.POST:
			return render_to_response('evesolo/manage_kills.html',context,context_instance=RequestContext(request))
		
		solokills_to_add=request.POST.getlist('solokills_to_add')
		if not solokills_to_add:
			return render_to_response('evesolo/manage_kills.html',context,context_instance=RequestContext(request))
		
		if not 'enter_into_leaderboard' in request.POST:
			return render_to_response('evesolo/manage_kills.html',context,context_instance=RequestContext(request))
		
		try:
			board_to_enter_id=int(request.POST['enter_into_leaderboard'])
		except ValueError:
			return render_to_response('evesolo/manage_kills.html',context,context_instance=RequestContext(request))
		
		try:
			board_to_enter=Leaderboard.objects.get(id=board_to_enter_id)
		except Leaderboard.DoesNotExist:
			context['error']='Board not found'
			return render_to_response('evesolo/manage_kills.html',context,context_instance=RequestContext(request))
		
		if board_to_enter not in context['leaderboards']:
			context['error']='Board not found'
			return render_to_response('evesolo/manage_kills.html',context,context_instance=RequestContext(request))
		
		added_count=0
		for solokill_id in solokills_to_add:
			try:
				solokill_id=int(solokill_id)
				solokill=Solokill.objects.get(id=solokill_id)
			except Solokill.DoesNotExist:
				continue
			
			pilot_to_add=solokill.winning_pilot
					
			pilot_invite=Leaderboardinvites.objects.filter(leaderboard=board_to_enter,pilot=pilot_to_add,status="ACCEPTED").count()
			if pilot_invite==0:
				continue
			try:
				Leaderboardkills.objects.get(leaderboard=board_to_enter,solokill=solokill)
			except Leaderboardkills.DoesNotExist:
				leaderboard_kill=Leaderboardkills(leaderboard=board_to_enter,solokill=solokill)
				save_object(leaderboard_kill,request)
				added_count+=1
		if added_count==0:
			context['error']='No new leaderboard entries were made.'
		else:
			context['message']='%d of %d entries made.' % (added_count,len(solokills_to_add))
		return render_to_response('evesolo/manage_kills.html',context,context_instance=RequestContext(request))

	return render_to_response('evesolo/manage_kills.html',context,context_instance=RequestContext(request))

		 
		 
		 