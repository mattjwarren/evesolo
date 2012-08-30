'''
Created on 30 Aug 2012

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


import km_parser
from sql_strings import *
import eveapi_cachehandler
import eveapi

from utility import *

def custom_board_search(request):
    if not request.method=='POST' or ('leaderboard_text' not in request.POST):
        return render_to_response('evesolo/board_search.html',context_instance=RequestContext(request))
    
    leaderboard_text=request.POST['leaderboard_text'].strip()
    if len(leaderboard_text)==0:
        return render_to_response('evesolo/board_search.html',{'error':'Please give some text to search for'},context_instance=RequestContext(request))
    
    if len(leaderboard_text)<3:
        return render_to_response('evesolo/board_search.html',{'error':'The text to search for must contain at least 3 characters'},context_instance=RequestContext(request))
    
    
    possible_leaderboards=Leaderboard.objects.filter(Q(name__icontains=leaderboard_text)|Q(description__icontains=leaderboard_text)).order_by('name')
    if len(possible_leaderboards)==0:
        return render_to_response('evesolo/board_search.html',{'message':'Sorry, no leaderboards could be found'},context_instance=RequestContext(request))
    
    for possible_board in possible_leaderboards:
        number_participating=Leaderboardinvites.objects.filter(leaderboard=possible_board,status='ACCEPTED').count()
        if number_participating==None:
            number_participating=0
        possible_board.participant_count=number_participating

    return render_to_response('evesolo/board_search.html',{'possible_leaderboards':possible_leaderboards},context_instance=RequestContext(request))

def custom_board_stats(request,board_id):
    #calculate   registered pilot #reg / act / max
    #            Total kills
    #            total kill points
    #            total damage done
    #
    #            most active pilot (seen in # fights) tie on damage done
    #            least active pilot
    #            most seen ship
    #            most succesful ship (w/l ratio)
    #            least succesful ship (w/l ratio)>0
    
    try:
        leaderboard=Leaderboard.objects.get(id=board_id)
    except Leaderboard.DoesNotExist:
        return render_to_response('evesolo/latestkills.html',{'error':'Leaderboard not found'},context_instance=RequestContext(request))

    
    registered_pilots_count=Leaderboardinvites.objects.filter(leaderboard=leaderboard,status='ACCEPTED').count()
    pilots_by_activity_rows=get_sql_rows(sql_pilot_leaderboard_fight_counts % leaderboard.id)
    active_pilots_count=len(pilots_by_activity_rows)
    max_pilots=leaderboard.max_participants
    
    kills=Leaderboardkills.objects.filter(leaderboard=leaderboard)
    total_kills=kills.count()
    total_kill_points=sum([ kill.solokill.points_awarded for kill in kills])
    total_damage_done=sum([ kill.solokill.damage for kill in kills])
    
    if len(pilots_by_activity_rows)<5:
        most_active_pilots_rows=pilots_by_activity_rows
    else:
        most_active_pilots_rows=pilots_by_activity_rows[0:5]
        
    most_seen_ships=get_sql_rows(sql_leaderboard_ships_seen_count % leaderboard.id)
    #most_efficient_ships_rows=get_sql_rows(sql_leaderboard_ships_best_wl_ratio % (leaderboard.id,leaderboard.id))
    #least_efficient_ships_rows=get_sql_rows(sql_leaderboard_ships_worst_wl_ratio % (leaderboard.id,leaderboard.id))
    context={}
    context['most_winning_ships']=get_sql_rows(sql_leaderboard_winning_ship_counts % leaderboard.id)
    context['least_winning_ships']=get_sql_rows(sql_leaderboard_losing_ship_counts % leaderboard.id)
    
    context['allowed_alliances']=Leaderboardallowedparticipants.objects.filter(leaderboard=leaderboard,type='ALLIANCE')
    context['allowed_corps']=Leaderboardallowedparticipants.objects.filter(leaderboard=leaderboard,type='CORP')
    context['allowed_pilots']=Leaderboardallowedparticipants.objects.filter(leaderboard=leaderboard,type='PILOT')

    context['allowed_shiptypes']=Leaderboardallowedships.objects.filter(leaderboard=leaderboard,type='CLASS')
    context['allowed_ships']=Leaderboardallowedships.objects.filter(leaderboard=leaderboard,type='SHIP')
    
    if leaderboard.allow_friendly_kills==1:
        context['allow_friendly_kills']='Yes'
    else:
        context['allow_friendly_kills']='No'
    if leaderboard.allow_leaderboard_kills==1:
        context['allow_competitor_kills']='Yes'
    else:
        context['allow_competitor_kills']='No'
    
    context['registered_pilots_count']=registered_pilots_count
    context['active_pilots_count']=active_pilots_count
    context['max_pilots']=max_pilots
    context['total_kills']=total_kills
    context['total_kill_points']=total_kill_points
    context['total_damage_done']=total_damage_done
    context['most_active_pilots_rows']=most_active_pilots_rows
    context['most_seen_ships']=most_seen_ships
    #context['most_efficient_ships_rows']=most_efficient_ships_rows
    #context['least_efficient_ships_rows']=least_efficient_ships_rows
    
    context['leaderboard']=leaderboard
    return render_to_response('evesolo/leaderboard_stats.html',context,context_instance=RequestContext(request))

@login_required
def get_managed_boards_context(request):
    context={}
    player_managed_leaderboards=[]
    user_players=Player.objects.filter(user=request.user)
    pilots_boards=[]
    all_boards=[]
    eligible_boards_by_pilot={}
    
    for player in user_players:
        player_pilots=Pilot.objects.filter(player=player)
        leaderboards=[]
        #player pilots
        for pilot in player_pilots:            
            #grab the boards that the pilot has accepted invites for
            accepted_invites=Leaderboardinvites.objects.filter(pilot=pilot,status='ACCEPTED')
            participating_in_boards=[ inv.leaderboard for inv in accepted_invites ]
            #monkey patch in the number of current participants
            #(monkey patches can make templating smoother)
            #TODO: change this to a property on the model?
            for participating_in_board in participating_in_boards:
                number_participating=Leaderboardinvites.objects.filter(leaderboard=participating_in_board,status='ACCEPTED').count()
                if number_participating==None:
                    number_participating=0
                participating_in_board.participant_count=number_participating
            if len(participating_in_boards)!=0:
                all_boards+=participating_in_boards
                pilots_boards.append((pilot,participating_in_boards))
            #find boards the pilot can join based on restrictions
            alliance_participants=Leaderboardallowedparticipants.objects.filter(type='ALLIANCE',name=pilot.alliance)
            corp_participants=Leaderboardallowedparticipants.objects.filter(type='CORP',name=pilot.corp)
            pilot_participants=Leaderboardallowedparticipants.objects.filter(type='PILOT',name=pilot.name)
            all_participants=list(alliance_participants)+list(corp_participants)+list(pilot_participants)
            all_allowed_boards=[ p.leaderboard for p in all_participants if p.leaderboard not in participating_in_boards ]
            if all_allowed_boards:
                eligible_boards_by_pilot[pilot]=all_allowed_boards
            #monkeypatching
            #TODO: change this to a property on the model?
            for participating_in_board in all_allowed_boards:
                number_participating=Leaderboardinvites.objects.filter(leaderboard=participating_in_board,status='ACCEPTED').count()
                if number_participating==None:
                    number_participating=0
                participating_in_board.participant_count=number_participating
                    
        #player managed leaderboards
        player_leaderboards=Leaderboard.objects.filter(player=player)
        for player_leaderboard in player_leaderboards:
            number_participating=Leaderboardinvites.objects.filter(leaderboard=player_leaderboard,status='ACCEPTED').count()
            if number_participating==None:
                number_participating=0
            player_leaderboard.participant_count=number_participating
            leaderboards.append(player_leaderboard)
        if len(leaderboards)!=0:
            player_managed_leaderboards.append( (player,leaderboards) )

    #Player eligible to join leaderboards
    #by default, eligible for all boards that do not have any allowed participants/ships/systems
    
    #public boards (boards with no restrictions)
    public_leaderboards=get_sql_rows(sql_public_leaderboards)
    
    
    
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
    if len(public_leaderboards)==0:
        public_leaderboards=None
    if len(pilots_boards)==0:
        pilots_boards=None
    if not eligible_boards_by_pilot.keys():
        eligible_boards_by_pilot=None
    
    
    context['eligible_leaderboards']=public_leaderboards
    context['eligible_boards_by_pilot']=eligible_boards_by_pilot
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
    #                                'joining_board_id'
    #otherwise, flip back to profile screen
    if (not request.method=='POST'):
        manage_boards_context=get_managed_boards_context(request)
        return render_to_response('evesolo/manage_boards.html',manage_boards_context,context_instance=RequestContext(request))        

    joining_board_id=None
    if not 'joining_board_id' in request.POST:
        manage_boards_context=get_managed_boards_context(request)
        manage_boards_context['error']='Board not found.'
        return render_to_response('evesolo/manage_boards.html',manage_boards_context,context_instance=RequestContext(request))
    
    joining_pilot_name=''
    if 'joining_pilot_name' in request.POST:
        joining_pilot_name=request.POST['joining_pilot_name'].strip()
    elif ':' in request.POST['joining_board_id']:
        joining_board_id,joining_pilot_name=request.POST['joining_board_id'].split(':')
        joining_board_id.strip()
        joining_pilot_name.strip()
        
    if len(joining_pilot_name)==0:
        manage_boards_context=get_managed_boards_context(request)
        manage_boards_context['error']='Please give a pilot name.'
        return render_to_response('evesolo/manage_boards.html',manage_boards_context,context_instance=RequestContext(request))

    
    try:
        if not joining_board_id:
            joining_board_id=int(request.POST['joining_board_id'])
        else:
            joining_board_id=int(joining_board_id)
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
    
    #check any restrictions if the board has them
    
    allowed_alliances=Leaderboardallowedparticipants.objects.filter(leaderboard=board_to_join,type='ALLIANCE')
    allowed_alliances=[ aa.name for aa in allowed_alliances ]
    in_alliance=joining_pilot.alliance in allowed_alliances
    
    allowed_corps=Leaderboardallowedparticipants.objects.filter(leaderboard=board_to_join,type='CORP')
    allowed_corps=[ aa.name for aa in allowed_corps ]
    in_corp=joining_pilot.corp in allowed_corps

    allowed_pilots=Leaderboardallowedparticipants.objects.filter(leaderboard=board_to_join,type='PILOT')
    allowed_pilots=[ aa.name for aa in allowed_pilots ]
    in_pilots=joining_pilot.name in allowed_pilots
    
    if not (in_alliance or in_corp or in_pilots):
        manage_boards_context=get_managed_boards_context(request)
        manage_boards_context['error']='Pilot has not been invited to board.'
        return render_to_response('evesolo/manage_boards.html',manage_boards_context,context_instance=RequestContext(request))
        
    
    existing_invites=Leaderboardinvites.objects.filter(leaderboard=board_to_join,pilot=joining_pilot,status='ACCEPTED')
    if len(existing_invites)>0:
        manage_boards_context=get_managed_boards_context(request)
        manage_boards_context['error']='Pilot is already competing in board.' % (joining_pilot.name,board_to_join.name)
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

    #end of manage board redirects, setup context for edit_board redirects
    #get corp.alliance.pilot lists
    allowed_alliances=list(Leaderboardallowedparticipants.objects.filter(leaderboard=leaderboard_to_edit,type='ALLIANCE'))
    allowed_corps=list(Leaderboardallowedparticipants.objects.filter(leaderboard=leaderboard_to_edit,type='CORP'))
    allowed_pilots=list(Leaderboardallowedparticipants.objects.filter(leaderboard=leaderboard_to_edit,type='PILOT'))
    
    if allowed_alliances:
        allowed_alliances=''.join([ ap.name+',' for ap in allowed_alliances if ap ])
    if not allowed_alliances: allowed_alliances=''
    if allowed_corps:
        allowed_corps=''.join([ ap.name+',' for ap in allowed_corps  if ap ])
    if not allowed_corps: allowed_corps=''
    if allowed_pilots:
        allowed_pilots=''.join([ ap.name+',' for ap in allowed_pilots  if ap ])
    if not allowed_pilots: allowed_pilots=''
    
    #allowed shipclasses and ships
    allowed_shipclasses=Leaderboardallowedships.objects.filter(leaderboard=leaderboard_to_edit,type='CLASS')
    allowed_ships=Leaderboardallowedships.objects.filter(leaderboard=leaderboard_to_edit,type='SHIP')
    
    if allowed_shipclasses:
        allowed_shipclasses=''.join([sc.name+',' for sc in allowed_shipclasses if sc])
    if not allowed_shipclasses: allowed_shipclasses=''
    if allowed_ships:
        allowed_ships=''.join([sc.name+',' for sc in allowed_ships if sc])
    if not allowed_ships: allowed_ships=''
    
    context=dict()
    context.update(manage_boards_context)
    context['players']=players
#    context={'leaderboard':leaderboard_to_edit}
    context['leaderboard']=leaderboard_to_edit
    context['allowed_alliances']=allowed_alliances
    context['allowed_corps']=allowed_corps
    context['allowed_pilots']=allowed_pilots
    context['allowed_shipclasses']=allowed_shipclasses
    context['allowed_ships']=allowed_ships
    
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
        leaderboard_description=request.POST['leaderboard_description'].strip()
    else:
        leaderboard_description=leaderboard_to_edit.description.strip()
    
    friendly_kills_allowed=False
    if 'allow_friendly_kills' in request.POST:
        friendly_kills_allowed=request.POST['allow_friendly_kills']=='True'
    competitor_kills_allowed=False
    if 'allow_competitor_kills' in request.POST:
        competitor_kills_allowed=request.POST['allow_competitor_kills']=='True'
        
    
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
        
    old_description=leaderboard_to_edit.description.strip()
    new_description=leaderboard_description
    if (old_description!=new_description) and (len(new_description.strip())>3):
        leaderboard_to_edit.description=new_description

    ##friendly/competitor kills
    if friendly_kills_allowed:
        leaderboard_to_edit.allow_friendly_kills=1
    else:
        leaderboard_to_edit.allow_friendly_kills=0
    if competitor_kills_allowed:
        leaderboard_to_edit.allow_leaderboard_kills=1
    else:
        leaderboard_to_edit.allow_leaderboard_kills=0    

    save_object(leaderboard_to_edit,request)
    
    #Now the allowed alliances/corps/pilots
    #first, clear current and then re-set
    alliances=request.POST['allowed_alliances'].split(',')
    corps=request.POST['allowed_corps'].split(',')
    pilots=request.POST['allowed_pilots'].split(',')
    shipclasses=request.POST['allowed_shipclasses'].split(',')
    ships=request.POST['allowed_ships'].split(',')
    Leaderboardallowedships.objects.filter(leaderboard=leaderboard_to_edit).delete()
    #systems...
    Leaderboardallowedparticipants.objects.filter(leaderboard=leaderboard_to_edit).delete()
    for alliance in [ a for a in alliances if a ]:
        lap=Leaderboardallowedparticipants()
        lap.leaderboard=leaderboard_to_edit
        lap.type='ALLIANCE'
        lap.name=alliance.strip()
        lap.save()
    for corp in [ c for c in corps if c ]:
        lap=Leaderboardallowedparticipants()
        lap.leaderboard=leaderboard_to_edit
        lap.type='CORP'
        lap.name=corp.strip()
        lap.save()
    for pilot in [ p for p in pilots if p ]:
        lap=Leaderboardallowedparticipants()
        lap.leaderboard=leaderboard_to_edit
        lap.type='PILOT'
        lap.name=pilot.strip()
        lap.save()
    for shipclass in [s for s in shipclasses if s]:
        las=Leaderboardallowedships()
        las.leaderboard=leaderboard_to_edit
        las.type='CLASS'
        las.name=shipclass.strip()
        las.save()
    for ship in [s for s in ships if s]:
        las=Leaderboardallowedships()
        las.leaderboard=leaderboard_to_edit
        las.type='SHIP'
        las.name=ship.strip()
        las.save()    
    
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

    friendly_kills_allowed=False
    if 'allow_friendly_kills' in request.POST:
        friendly_kills_allowed=request.POST['allow_friendly_kills']=='True'
    competitor_kills_allowed=False
    if 'allow_competitor_kills' in request.POST:
        competitor_kills_allowed=request.POST['allow_competitor_kills']=='True'    
    
    
    #Check the leaderboard is not asociated with another player
    leaderboard=get_or_create_leaderboard(name=leaderboard_name,manager=managing_player)
    #if any of the fields are set, then this leaderbaord already existed
    if leaderboard.description!='':#cheap way to check if was got or created
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
    leaderboard.description=leaderboard_description.strip()
    
    
    ##friendly/competitor kills
    if friendly_kills_allowed:
        leaderboard.allow_friendly_kills=1
    else:
        leaderboard.allow_friendly_kills=0
    if competitor_kills_allowed:
        leaderboard.allow_leaderboard_kills=1
    else:
        leaderboard.allow_leaderboard_kills=0
        
        
    save_object(leaderboard,request)
    
    
    
    #Now the allowed alliances/corps/pilots
    #ship classes/ships
    #/systems
    
    #first, clear current and then re-set
    alliances=request.POST['allowed_alliances'].split(',')
    corps=request.POST['allowed_corps'].split(',')
    pilots=request.POST['allowed_pilots'].split(',')
    shipclasses=request.POST['allowed_shipclasses'].split(',')
    ships=request.POST['allowed_ships'].split(',')
    Leaderboardallowedships.objects.filter(leaderboard=leaderboard).delete()
    Leaderboardallowedparticipants.objects.filter(leaderboard=leaderboard).delete()
    for alliance in [ a for a in alliances if a ]:
        lap=Leaderboardallowedparticipants()
        lap.leaderboard=leaderboard
        lap.type='ALLIANCE'
        lap.name=alliance.strip()
        lap.save()
    for corp in [ c for c in corps if c ]:
        lap=Leaderboardallowedparticipants()
        lap.leaderboard=leaderboard
        lap.type='CORP'
        lap.name=corp.strip()
        lap.save()
    for pilot in [ p for p in pilots if p ]:
        lap=Leaderboardallowedparticipants()
        lap.leaderboard=leaderboard
        lap.type='PILOT'
        lap.name=pilot.strip()
        lap.save()
    for shipclass in shipclasses:
        las=Leaderboardallowedships()
        las.leaderboard=leaderboard
        las.type='CLASS'
        las.name=shipclass.strip()
        las.save()
    for ship in ships:
        las=Leaderboardallowedships()
        las.leaderboard=leaderboard
        las.type='SHIP'
        las.name=ship.strip()
        las.save()
    

    return HttpResponseRedirect(reverse('evesolo.views.manage_boards'))    


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
    
    ranks=leaderboard.ranks
    
    rank_sets=[]
    rank_sets.append( ('All Time',get_sql_rows(sql % (leaderboard_id,'20010101010101',ranks))) )
    rank_sets.append( ('Past Week',get_sql_rows(sql % (leaderboard_id,interval_week,ranks))))
    rank_sets.append( ('Past Month',get_sql_rows(sql % (leaderboard_id,interval_month,ranks))))
    rank_sets.append( ('Past Quarter',get_sql_rows(sql % (leaderboard_id,interval_quarter,ranks))))
    rank_sets.append( ('Past Half Year',get_sql_rows(sql % (leaderboard_id,interval_half,ranks))))
    rank_sets.append( ('Past Year',get_sql_rows(sql % (leaderboard_id,interval_year,ranks))))
    
    context['rank_sets']=rank_sets
    context['header_title']='Leaderboard rankings: %s' % leaderboard.name
    context['html_title']=None
    context['include_verify']=False
    context['leaderboard']=leaderboard
    return render_to_response('evesolo/leaderboard.html',context,context_instance=RequestContext(request))
