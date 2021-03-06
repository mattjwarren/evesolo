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


from utility import *
from sql_strings import *
from custom_leaderboards import *	

		

	
def search(request):
	if not request.method=='POST' or ('pilot_name' not in request.POST):
		return render_to_response('evesolo/search.html',context_instance=RequestContext(request))
	
	pilot_name=request.POST['pilot_name'].strip()
	if len(pilot_name)==0:
		return render_to_response('evesolo/search.html',{'error':'Please specify a pilot name, or partial pilot name to search for'},context_instance=RequestContext(request))
	
	if len(pilot_name)<3:
		return render_to_response('evesolo/search.html',{'error':'The text to search for must contain at least 3 characters'},context_instance=RequestContext(request))
	
	
	possible_pilots=Pilot.objects.filter(name__icontains=pilot_name).order_by('name')
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
	if players_pilots==None:
		players_pilots=[]
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
		try:
			api_char_alliance=api_conn.eve.CharacterInfo(characterID=api_char.characterID,userID=key_id,apiKey=key_vCode).alliance
		except AttributeError:
			api_char_alliance=''
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
				return render_to_response('evesolo/add_pilot.html',{'error':'Pilot is already associated to a player.','players':players},context_instance=RequestContext(request))
		

	pilot.api_key='[[%s]]%s' % (key_id,key_vCode)
	pilot.player=player
	pilot.corp=api_char.corporationName
	pilot.alliance=api_char_alliance
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
	highest_kill_id=22999999#12734501
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
				#print 'Malformed kill from API pull'
				continue
			
			if KM.kill_id in seen_kill_ids:
				#do not process dupes seen in pull session (most useful when pulling v.large
				#numbers of kills from a KB
				continue			
			else:
				seen_kill_ids.add(KM.kill_id)
			highest_kill_id=max(highest_kill_id,KM.kill_id)
			#print 'Highest seen killid is',highest_kill_id
			if KM.is_solo_mail():
				losing_pilot_info=get_km_losing_pilot_info(killmail=KM)
				
				#Do we understand the shiptype?
				if not losing_pilot_info['ship']:
					#print "LOSING PILOT IS A WHAT?"
					#LOG THIS SOMEWHERE...
					continue
				
				#Was the winning pilot an NPC?
				winning_pilot_info=get_km_winning_pilot_info(killmail=KM)
				if not winning_pilot_info['ship']:
					non_player_wins+=1
					continue
				
				#Are the players in the same alliance or corp?
				# .. removed:- we dont care in the evesolo boards anymore, settable in private				
				
				
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
					#print 'DISPUTE:: deleting - discovered previous solokill but with many parties on new kill'
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


#secrit point-recalc hook!
@login_required
def recalculate_killpoints(request):
	for kill in Solokill.objects.all():
		Lp=kill.losers_ship.hull_class.fwp_value
		Wp=kill.winners_ship.hull_class.fwp_value
		kill_points=calculate_kill_points(Lp,Wp)
		kill.save()
	return render_to_response('evesolo/profile.html',{'message':'Global killpoint recalculation has completed'},context_instance=RequestContext(request))

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
	context['header_title']='Evesolo All Class Leaderboards'
	context['html_title']=None
	context['verified']=verified
	context['verified_link']='<ul><li><a href="/leaderboards_summary/verified/">Switch to verified kills only</a></li></ul>'
	context['unverified_link']='<ul><li><a href="/leaderboards_summary/">Switch to all kills</a></li></ul>'
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

#NOT USED
####def postmail(request):
####	if request.method=='POST':
####		KM=km_parser.EveKillmail()
####		try:
####			KM.parse_killmail_from_copypaste(request.POST['killtext'])
####		except ParseException:
####			return render_to_response('evesolo/newmail.html',
####									  {'error':'We had trouble interpreting that killmail, please check it and try again.'},
####									  context_instance=RequestContext(request))		
####		#ensure is a valid solo mail, if so then create the Solokill object
####		if KM.is_solo_mail():
####			losing_pilot_info=get_km_losing_pilot_info(killmail=KM)
####			winning_pilot_info=get_km_winning_pilot_info(killmail=KM)
####			if (not losing_pilot_info['ship']) or (not winning_pilot_info['ship']):
####				return render_to_response('evesolo/newmail.html',
####						  {'error':'One of the ships on the killmail was of an unknown type.'},
####						  context_instance=RequestContext(request))
####			try:
####				kill_date_time=datetime.strptime(KM.kill_date,'%Y.%m.%d %H:%M:%S')
####			except ValueError:
####				kill_date_time=datetime.strptime(KM.kill_date,'%Y.%m.%d %H:%M')
####			submit_date_time=datetime.now()
####			
####			kill_damage=int(KM.victim['Damage Taken:'])
####			
####			
####			#do either of the pilots exist?
####			#if not, create blank pilot, else get the Pilot record
####			#update and save
####			losing_pilot=update_or_create_pilot(request,losing_pilot_info)
####			winning_pilot=update_or_create_pilot(request,winning_pilot_info)
####
####			#extract the KM lines we are after
####			relevant_km_lines=[]
####			for line in KM.kill_text.split('\n'):
####				if line.startswith('Destroyed items:') or line.startswith('Dropped items:'):
####					break
####				if len(line)!=0:
####					relevant_km_lines.append(line)
####			relevant_km_lines='\n'.join(relevant_km_lines)
####
####			#create the solokill if it does not exist
####			existing_sk=Solokill.objects.filter(losing_pilot=losing_pilot,
####											 winning_pilot=winning_pilot,
####											 kill_date=kill_date_time)
####			if len(existing_sk)!=0:
####				#Killmail already posted
####				return render_to_response('evesolo/newmail.html',
####										  {'kill_id':existing_sk[0].id,
####										  'message':'That kill has already been posted, view it <a href="/kills/%d/">here</a>' % existing_sk[0].id},
####										  context_instance=RequestContext(request))
####			
####			
####			#get the kill_points
####			Lp=losing_pilot_info['ship'].hull_class.fwp_value
####			Wp=winning_pilot_info['ship'].hull_class.fwp_value
####			kill_points=calculate_kill_points(Lp,Wp)
####			
####			#save the kill
####			solokill=Solokill(losing_pilot=losing_pilot,
####									winning_pilot=winning_pilot,
####									losers_ship=losing_pilot_info['ship'],
####									winners_ship=winning_pilot_info['ship'],
####									points_awarded=kill_points,
####									damage=kill_damage,
####									submit_date=submit_date_time,
####									kill_date=kill_date_time,
####									verified=False,
####									kill_text=relevant_km_lines)
####			save_object(solokill,request)
####			
####			return HttpResponseRedirect(reverse('evesolo.views.viewkill',args=(solokill.id,)))
####		else:
####			#Not a Solo kill!
####			return render_to_response('evesolo/newmail.html',
####									  {'error':'The EveSolo killboards only accept solo combat killmails.'},
####									  context_instance=RequestContext(request))
####	return HttpResponseRedirect(reverse('evesolo.views.newmail'))

def latestkills(request,error=None):
	total_pilots=Pilot.objects.count()
	total_kills=Solokill.objects.count()
	total_scoring_kills=Solokill.objects.filter(points_awarded__gt=0).count()
	
	latest_kills=Solokill.objects.exclude(points_awarded=0).order_by('-kill_date')[:10]
	
	latest_submitted_kills=Solokill.objects.exclude(points_awarded=0).order_by('-submit_date')[:10]
	return render_to_response('evesolo/latestkills.html',{'latest_kills':latest_kills,
														  'latest_submitted_kills':latest_submitted_kills,
														  #'message':'Tracking %d pilots with %d kills (%d point-scoring kills)' % (total_pilots,total_kills,total_scoring_kills),
														  'total_pilots':total_pilots,
														  'total_kills':total_kills,
														  'scoring_kills':total_scoring_kills,
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

def pilot(request,pilot_id,board_id,verified=False):
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
	
	accepted_invites=Leaderboardinvites.objects.filter(pilot=pilot,status='ACCEPTED')
	participating_in_boards=[ inv.leaderboard for inv in accepted_invites ]
	if len(participating_in_boards)==0:
		participating_in_boards=None
	leaderboard=None
	if board_id:
		try:
			board_id=int(board_id)
		except ValueError:
			context['error']='The leaderboard is unknown.'
			board_id=None
		if board_id:
			try:
				leaderboard=Leaderboard.objects.get(id=board_id)
			except Leaderboard.DoesNotExist:
				context['error']='The leaderboard is unknown.'
				board_id=None
				
	if not board_id:
		if verified:
			sql=sql_all_class_ranking_ver_nolimit
			sql_interval=sql_all_class_ranking_interval_ver_nolimit
		else:
			sql=sql_all_class_ranking_nolimit
			sql_interval=sql_all_class_ranking_interval_nolimit
	else:
		if leaderboard.rank_style=='KILLS':
			sql=sql_custom_ranking_nolimit_kills
			sql_interval=sql_custom_ranking_interval_nolimit_kills
		elif leaderboard.rank_style=='POINTS':
			sql=sql_custom_ranking_nolimit_points
			sql_interval=sql_custom_ranking_interval_nolimit_points
		elif leaderboard.rank_style=='DAMAGE':
			sql=sql_custom_ranking_nolimit_damage
			sql_interval=sql_custom_ranking_interval_nolimit_damage
			

		
		
	try:
		fmt=('20010101010101')
		if board_id:
			fmt=(board_id,'20010101010101')
		all_time_rank=[ r[0] for r in get_sql_rows(sql % fmt)].index(pilot_id)+1
	except ValueError:
		all_time_rank='-'

		
		
	try:
		fmt=(interval_week)
		if board_id:
			fmt=(board_id,interval_week)
		past_week_rank=[ r[0] for r in get_sql_rows(sql % fmt)].index(pilot_id)+1
	except ValueError:
		past_week_rank='-'
	try:
		fmt=(prev_week_start,interval_week)
		if board_id:
			fmt=(board_id,prev_week_start,interval_week)
		ppast_week_rank=[ r[0] for r in get_sql_rows(sql_interval % fmt)].index(pilot_id)+1
	except:
		ppast_week_rank='-'
	
	
	
	try:
		fmt=(interval_month)
		if board_id:
			fmt=(board_id,interval_month)
		past_month_rank=[ r[0] for r in get_sql_rows(sql % fmt)].index(pilot_id)+1
	except ValueError:
		past_month_rank='-'
	try:
		fmt=(prev_month_start,interval_month)
		if board_id:
			fmt=(board_id,prev_month_start,interval_month)
		ppast_month_rank=[ r[0] for r in get_sql_rows(sql_interval % fmt)].index(pilot_id)+1
	except:
		ppast_month_rank='-'

		
		
	try:
		fmt=(interval_quarter)
		if board_id:
			fmt=(board_id,interval_quarter)
		past_quarter_rank=[ r[0] for r in get_sql_rows(sql % fmt)].index(pilot_id)+1
	except ValueError:
		past_quarter_rank='-'
	try:
		fmt=(prev_quarter_start,interval_quarter)
		if board_id:
			fmt=(board_id,prev_quarter_start,interval_quarter)
		ppast_quarter_rank=[ r[0] for r in get_sql_rows(sql_interval % (prev_quarter_start,interval_quarter))].index(pilot_id)+1
	except:
		ppast_quarter_rank='-'

		
		
		
	try:
		fmt=(interval_half)
		if board_id:
			fmt=(board_id,interval_half)
		past_half_year_rank=[ r[0] for r in get_sql_rows(sql % fmt)].index(pilot_id)+1
	except ValueError:
		past_half_year_rank='-'
	try:
		fmt=(prev_half_start,interval_half)
		if board_id:
			fmt=(board_id,prev_half_start,interval_half)
		ppast_half_year_rank=[ r[0] for r in get_sql_rows(sql_interval % fmt)].index(pilot_id)+1
	except:
		ppast_half_year_rank='-'

		
		
	try:
		fmt=(interval_year)
		if board_id:
			fmt=(board_id,interval_year)
		past_year_rank=[ r[0] for r in get_sql_rows(sql % fmt)].index(pilot_id)+1
	except ValueError:
		past_year_rank='-'
	try:
		fmt=(prev_year_start,interval_year)
		if board_id:
			fmt=(board_id,prev_year_start,interval_year)
		ppast_year_rank=[ r[0] for r in get_sql_rows(sql_interval % (prev_year_start,interval_year))].index(pilot_id)+1
	except:
		ppast_year_rank='-'



	if not board_id:
		all_pilot_scores=Pilot.objects.annotate(total_points=Sum('winning_pilot__points_awarded'))
		all_class=all_pilot_scores.order_by('-total_points','name')
		pilot_points=all_class.get(pk=pilot_id).total_points
	else:
		#calculate total score for leaderbaord
		all_pilot_board_kills=Leaderboardkills.objects.filter(leaderboard=leaderboard,solokill__winning_pilot=pilot)
		if leaderboard.rank_style=='POINTS':
			pilot_points=sum([ apbk.solokill.points_awarded for apbk in all_pilot_board_kills])
		else:
			pilot_points=len(all_pilot_board_kills)
		
	#get pilot w:l ratio
	if not board_id:
		pilot_winkills=Solokill.objects.filter(winning_pilot=pilot)
		pilot_losskills=Solokill.objects.filter(losing_pilot=pilot)
	else:
		pilot_winkills=Leaderboardkills.objects.filter(leaderboard=leaderboard,solokill__winning_pilot=pilot)
		pilot_losskills=Leaderboardkills.objects.filter(leaderboard=leaderboard,solokill__losing_pilot=pilot)
	pilot_wins=len(pilot_winkills)
	pilot_losses=len(pilot_losskills)
	w_l_ratio='%d - %d' % (pilot_wins,pilot_losses)
		
		
	#Class w/most wins
	if not board_id:
		pilot_class_wins=get_sql_rows(sql_pilot_hullclass_wins_points % pilot.id)
	else:
		pilot_class_wins=get_sql_rows(sql_pilot_hullclass_wins_points_custom % (leaderboard.id,pilot.id))

	
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
	if not board_id:
		pilot_ship_wins=get_sql_rows(sql_pilot_ship_wins_points % pilot.id)
	else:
		pilot_ship_wins=get_sql_rows(sql_pilot_ship_wins_points_custom % (leaderboard.id,pilot.id))
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
	if not board_id:
		pilot_favourite_ships=get_sql_rows(sql_pilot_ships_seen_count % (pilot_id,pilot_id))
	else:
		pilot_favourite_ships=get_sql_rows(sql_pilot_ships_seen_count_custom % (pilot_id,pilot_id,leaderboard.id))
	
	#last 10 fights
	if not board_id:
		last_10_fights=Solokill.objects.filter(Q(winning_pilot=pilot)|Q(losing_pilot=pilot)).order_by('-kill_date')[:10] #points_awarded__gt=0
	else:
		last_10_fights_leaderboard_kills=Leaderboardkills.objects.filter(Q(solokill__winning_pilot=pilot)|Q(solokill__losing_pilot=pilot),leaderboard=leaderboard).order_by('-solokill__kill_date')[:10] #,solokill__points_awarded__gt=0
		last_10_fights=[ ltflk.solokill for ltflk in last_10_fights_leaderboard_kills]
	
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
							   'most_seen_ships':pilot_favourite_ships,
							   'participating_in_boards':participating_in_boards,
							   'leaderboard':leaderboard},
							   context_instance=RequestContext(request))


def ship_boards(request):
	ctr=0
	nav_set=[] #[ ( ('text','link'),('textN','linkN'),... ),...x5 ]
	texts_links=[]
	for hull_id in range(3,19):
		hullclass=Hullclass.objects.get(pk=hull_id)
		class_name=hullclass.human_name
		texts_links.append( (class_name,hullclass.id) )
		ctr+=1
		if ctr==5:
			nav_set.append(texts_links)
			texts_links=[]
			ctr=0
	
	ctr=0
	nav_set_ship=[]
	all_ships=Ship.objects.all().order_by('name')
	names_ids=[]
	for ship in all_ships:
		names_ids.append( (ship.name,ship.id))
		ctr+=1
		if ctr==5:
			nav_set_ship.append(names_ids)
			names_ids=[]
			ctr=0
			
	context={}
	context['nav_set']=nav_set
	context['ship_set']=nav_set_ship
	return render_to_response('evesolo/ship_boards.html',
							context,
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
	kill_list=Solokill.objects.filter(winning_pilot__player__user=request.user,kill_date__gt=interval_sixweeks,points_awarded__gt=0).order_by('-kill_date')
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
		
		player_pilots=Pilot.objects.filter(player__user=request.user)

		#get set of all ships allowed (all, or just classes and names given) in the board for checking kills
		ships_allowed_in_board=[]
		allowed_classes=Leaderboardallowedships.objects.filter(type='CLASS')
		allowed_names=Leaderboardallowedships.objects.filter(type='SHIP')
		for allowed_class in allowed_classes:
			class_ships=Ship.objects.filter(hull_class__human_name=allowed_class.name)
			ships_allowed_in_board+=[ cs.name for cs in class_ships ]
		ships_allowed_in_board+=[ an.name for an in allowed_names ]


		ship_restrictions=0
		bad_pilots=0
		added_count=0
		not_invited=0
		not_allowed_competitor=0
		not_allowed_friendly=0
		already_entered=0
		kills_not_verified=0
		not_allowed_general=0
		too_old=0
		for solokill_id in solokills_to_add:
			try:
				solokill_id=int(solokill_id)
				solokill=Solokill.objects.get(id=solokill_id)
			except Solokill.DoesNotExist:
				continue

			#if solokill isnt verified, say no
			if not solokill.verified:
				kills_not_verified+=1
				continue
			#if its too old bye bye
			if solokill.kill_date<board_to_enter.start_date:
				too_old+=1
				continue
			#is the kill restricted by shiptype or shipclass
			if ships_allowed_in_board:
				if solokill.winners_ship.name not in ships_allowed_in_board:
					ship_restrictions+=1
					continue

			pilot_to_add=solokill.winning_pilot
			#check it belongs to the correct pilot .. a pilot the user owns
			#TODO: NOT a good check - need to tie to specific pilot ((last filtered by pilot..)
			if pilot_to_add not in player_pilots:
				bad_pilots+=1
				continue
			
			
			pilot_invite=Leaderboardinvites.objects.filter(leaderboard=board_to_enter,pilot=pilot_to_add,status="ACCEPTED").count()
			if pilot_invite==0:
				not_invited+=1
				continue
			
			
			#is kill leaderboard restricted by Friends / competitors?
			friendly_allowed=board_to_enter.allow_friendly_kills
			competitor_allowed=board_to_enter.allow_leaderboard_kills
			outsider_allowed=board_to_enter.allow_outsider_kills
			
			losing_pilot=solokill.losing_pilot
			looser_alliance=losing_pilot.alliance
			looser_corp=losing_pilot.corp
			if (not looser_alliance) and (not pilot_to_add.alliance):
				looser_friendly= looser_corp==pilot_to_add.corp
			else:
				looser_friendly=(looser_alliance==pilot_to_add.alliance) or (looser_corp==pilot_to_add.corp)
			looser_competitor=Leaderboardinvites.objects.filter(leaderboard=board_to_enter,pilot=losing_pilot).count()>0
			looser_general=not looser_competitor
			
			
			#if looser is a competitor, and competitors are not allowed, then refuse regardless sof friendly status
			if (looser_competitor) and (not competitor_allowed):
				not_allowed_competitor+=1
				continue
			if (looser_friendly) and (not friendly_allowed):
				not_allowed_friendly+=1
				continue
			if (looser_general) and (not outsider_allowed):
				not_allowed_general+=1
				continue
			
			#does the kill already exist
			try:
				Leaderboardkills.objects.get(leaderboard=board_to_enter,solokill=solokill)
				#
				already_entered+=1
			except Leaderboardkills.DoesNotExist:
				leaderboard_kill=Leaderboardkills(leaderboard=board_to_enter,solokill=solokill)
				save_object(leaderboard_kill,request)
				added_count+=1










			
			
		error_list=[]
		not_allowed=not_allowed_competitor+not_allowed_friendly+already_entered+kills_not_verified+too_old+not_invited+ship_restrictions+bad_pilots+not_allowed_general
		
		context['message']=[]
		if not_allowed==0:
			context['message']='All kills succesfully entered.'
		elif not_allowed>0:
			if not_allowed_competitor:
				error_list.append('%d Refused, competitor kills not allowed.' % not_allowed_competitor)
			if ship_restrictions:
				error_list.append('%d Refused, winning shiptype does not qualify for the leaderboard.' % ship_restrictions)
			if bad_pilots:
				error_list.append('%d Refused, bad pilot.' % bad_pilots)

			if not_allowed_friendly:
				error_list.append('%d Refused, friendly kills not allowed.' % not_allowed_friendly)
			if not_invited>0:
				error_list.append('%d Refused, pilot not competing in board.' % not_invited)
			if already_entered>0:
				error_list.append('%d Refused, kills already entered into board.' % already_entered)
			if kills_not_verified>0:
				error_list.append('%d Refused, not verified.' % kills_not_verified)
			if too_old>0:
				error_list.append('%d Refused, kills are too old.' % too_old)
			if not_allowed_general>0:
				error_list.append('%d Refused, General kills not allowed.' % not_allowed_general)
			if added_count:
				context['message'].append('...%d Succesfully entered.') % added_count
			context['error']='</br>'.join(error_list)
		return render_to_response('evesolo/manage_kills.html',context,context_instance=RequestContext(request))

	return render_to_response('evesolo/manage_kills.html',context,context_instance=RequestContext(request))
