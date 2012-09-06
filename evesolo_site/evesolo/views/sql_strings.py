sql_all_class_ranking='''select evesolo_pilot.id,evesolo_pilot.name,sum(evesolo_solokill.points_awarded) as s from evesolo_pilot
		inner join evesolo_solokill on evesolo_solokill.winning_pilot_id=evesolo_pilot.id
		where evesolo_solokill.kill_date>'%s'
		and evesolo_solokill.points_awarded>0.0
		group by evesolo_pilot.id,evesolo_pilot.name
		order by s desc
		limit 10'''

sql_all_class_ranking_custom_points='''select evesolo_pilot.id,evesolo_pilot.name,sum(evesolo_solokill.points_awarded) as s from evesolo_pilot
		inner join evesolo_solokill on evesolo_solokill.winning_pilot_id=evesolo_pilot.id
		inner join evesolo_leaderboardkills on evesolo_solokill.id=evesolo_leaderboardkills.solokill_id
		where evesolo_leaderboardkills.leaderboard_id=%d
		and evesolo_solokill.kill_date>'%s'
		and evesolo_solokill.points_awarded>0.0
		group by evesolo_pilot.id,evesolo_pilot.name
		order by s desc
		limit %d'''

sql_all_class_ranking_custom_kills='''select evesolo_pilot.id,evesolo_pilot.name,count(evesolo_pilot.name) as s from evesolo_pilot
		inner join evesolo_solokill on evesolo_solokill.winning_pilot_id=evesolo_pilot.id
		inner join evesolo_leaderboardkills on evesolo_solokill.id=evesolo_leaderboardkills.solokill_id
		where evesolo_leaderboardkills.leaderboard_id=%d		
		and evesolo_solokill.kill_date>'%s'
		and evesolo_solokill.points_awarded>0.0
		group by evesolo_pilot.id,evesolo_pilot.name
		order by s desc
		limit %d'''


sql_all_class_ranking_nolimit='''select evesolo_pilot.id,evesolo_pilot.name,sum(evesolo_solokill.points_awarded) as s from evesolo_pilot
		inner join evesolo_solokill on evesolo_solokill.winning_pilot_id=evesolo_pilot.id
		where evesolo_solokill.kill_date>'%s'
		and evesolo_solokill.points_awarded>0.0
		group by evesolo_pilot.id, evesolo_pilot.name
		order by s desc
	'''
###
sql_custom_ranking_nolimit_points='''select evesolo_pilot.id,evesolo_pilot.name,sum(evesolo_solokill.points_awarded) as s from evesolo_pilot
		inner join evesolo_solokill on evesolo_solokill.winning_pilot_id=evesolo_pilot.id
		inner join evesolo_leaderboardkills on evesolo_solokill.id=evesolo_leaderboardkills.solokill_id
		where evesolo_leaderboardkills.leaderboard_id=%d
		and evesolo_solokill.kill_date>'%s'
		and evesolo_solokill.points_awarded>0.0
		group by evesolo_pilot.id, evesolo_pilot.name
		order by s desc
		'''
sql_custom_ranking_nolimit_kills='''select evesolo_pilot.id,evesolo_pilot.name,count(evesolo_pilot.name) as s from evesolo_pilot
		inner join evesolo_solokill on evesolo_solokill.winning_pilot_id=evesolo_pilot.id
		inner join evesolo_leaderboardkills on evesolo_solokill.id=evesolo_leaderboardkills.solokill_id
		where evesolo_leaderboardkills.leaderboard_id=%d
		and evesolo_solokill.kill_date>'%s'
		and evesolo_solokill.points_awarded>0.0
		group by evesolo_pilot.id, evesolo_pilot.name
		order by s desc
		'''
sql_custom_ranking_nolimit_damage='''select evesolo_pilot.id,evesolo_pilot.name,sum(evesolo_solokill.damage) as s from evesolo_pilot
		inner join evesolo_solokill on evesolo_solokill.winning_pilot_id=evesolo_pilot.id
		inner join evesolo_leaderboardkills on evesolo_solokill.id=evesolo_leaderboardkills.solokill_id
		where evesolo_leaderboardkills.leaderboard_id=%d
		and evesolo_solokill.kill_date>'%s'
		and evesolo_solokill.points_awarded>0.0
		group by evesolo_pilot.id, evesolo_pilot.name
		order by s desc
		'''
###
		
sql_all_class_ranking_interval_nolimit='''select evesolo_pilot.id,evesolo_pilot.name,sum(evesolo_solokill.points_awarded) as s from evesolo_pilot
		inner join evesolo_solokill on evesolo_solokill.winning_pilot_id=evesolo_pilot.id
		where evesolo_solokill.kill_date>='%s'
		and evesolo_solokill.kill_date<'%s'
		and evesolo_solokill.points_awarded>0.0
		group by  evesolo_pilot.id,evesolo_pilot.name
		order by s desc
		'''
##
sql_custom_ranking_interval_nolimit_points='''select evesolo_pilot.id,evesolo_pilot.name,sum(evesolo_solokill.points_awarded) as s from evesolo_pilot
		inner join evesolo_solokill on evesolo_solokill.winning_pilot_id=evesolo_pilot.id
		inner join evesolo_leaderboardkills on evesolo_solokill.id=evesolo_leaderboardkills.solokill_id
		where evesolo_leaderboardkills.leaderboard_id=%d
		and evesolo_solokill.kill_date>='%s'
		and evesolo_solokill.kill_date<'%s'
		and evesolo_solokill.points_awarded>0.0
		group by  evesolo_pilot.id,evesolo_pilot.name
		order by s desc
		'''
sql_custom_ranking_interval_nolimit_damage='''select evesolo_pilot.id,evesolo_pilot.name,sum(evesolo_solokill.damage) as s from evesolo_pilot
		inner join evesolo_solokill on evesolo_solokill.winning_pilot_id=evesolo_pilot.id
		inner join evesolo_leaderboardkills on evesolo_solokill.id=evesolo_leaderboardkills.solokill_id
		where evesolo_leaderboardkills.leaderboard_id=%d
		and evesolo_solokill.kill_date>='%s'
		and evesolo_solokill.kill_date<'%s'
		and evesolo_solokill.points_awarded>0.0
		group by  evesolo_pilot.id,evesolo_pilot.name
		order by s desc
		'''
sql_custom_ranking_interval_nolimit_kills='''select evesolo_pilot.id,evesolo_pilot.name,count(evesolo_pilot.name) as s from evesolo_pilot
		inner join evesolo_solokill on evesolo_solokill.winning_pilot_id=evesolo_pilot.id
		inner join evesolo_leaderboardkills on evesolo_solokill.id=evesolo_leaderboardkills.solokill_id
		where evesolo_leaderboardkills.leaderboard_id=%d
		and evesolo_solokill.kill_date>='%s'
		and evesolo_solokill.kill_date<'%s'
		and evesolo_solokill.points_awarded>0.0
		group by  evesolo_pilot.id,evesolo_pilot.name
		order by s desc
		'''
##
		
sql_all_class_ranking_ver='''select evesolo_pilot.id,evesolo_pilot.name,sum(evesolo_solokill.points_awarded) as s from evesolo_pilot
		inner join evesolo_solokill on evesolo_solokill.winning_pilot_id=evesolo_pilot.id
		where evesolo_solokill.kill_date>'%s'
		and evesolo_solokill.points_awarded>0.0
		and evesolo_solokill.verified=True
		group by  evesolo_pilot.id,evesolo_pilot.name
		order by s desc
		limit 10'''

sql_all_class_ranking_ver_nolimit='''select evesolo_pilot.id,evesolo_pilot.name,sum(evesolo_solokill.points_awarded) as s from evesolo_pilot
		inner join evesolo_solokill on evesolo_solokill.winning_pilot_id=evesolo_pilot.id
		where evesolo_solokill.kill_date>'%s'
		and evesolo_solokill.points_awarded>0.0
		and evesolo_solokill.verified=True
		group by  evesolo_pilot.id,evesolo_pilot.name
		order by s desc'''

sql_all_class_ranking_interval_ver_nolimit='''select evesolo_pilot.id,evesolo_pilot.name,sum(evesolo_solokill.points_awarded) as s from evesolo_pilot
		inner join evesolo_solokill on evesolo_solokill.winning_pilot_id=evesolo_pilot.id
		where evesolo_solokill.kill_date>='%s'
		and evesolo_solokill.kill_date<'%s'
		and evesolo_solokill.points_awarded>0.0
		and evesolo_solokill.verified=True
		group by  evesolo_pilot.id,evesolo_pilot.name
		order by s desc
		'''
		
		
		
		
sql_ship_ranking='''select evesolo_pilot.id,evesolo_pilot.name,sum(evesolo_solokill.points_awarded) as s from evesolo_pilot
		inner join evesolo_solokill on evesolo_solokill.winning_pilot_id=evesolo_pilot.id
		where evesolo_solokill.kill_date>'%s'
		and evesolo_solokill.points_awarded>0.0
		and evesolo_solokill.winners_ship_id=%d
		group by evesolo_pilot.name
		order by s desc
		limit 10'''

sql_ship_ranking_ver='''select evesolo_pilot.id,evesolo_pilot.name,sum(evesolo_solokill.points_awarded) as s from evesolo_pilot
		inner join evesolo_solokill on evesolo_solokill.winning_pilot_id=evesolo_pilot.id
		where evesolo_solokill.kill_date>'%s'
		and evesolo_solokill.points_awarded>0.0
		and evesolo_solokill.verified=True
		and evesolo_solokill.winners_ship_id=%d
		group by evesolo_pilot.name
		order by s desc
		limit 10'''
		
sql_class_ranking='''select evesolo_pilot.id,evesolo_pilot.name,sum(evesolo_solokill.points_awarded) as s from evesolo_pilot
		inner join evesolo_solokill on evesolo_solokill.winning_pilot_id=evesolo_pilot.id
		inner join evesolo_ship on evesolo_ship.id=evesolo_solokill.winners_ship_id
		inner join evesolo_hullclass on evesolo_hullclass.id=evesolo_ship.hull_class_id
		where evesolo_solokill.kill_date>'%s'
		and evesolo_solokill.points_awarded>0.0
		and evesolo_hullclass.id=%d
		group by evesolo_pilot.name
		order by s desc
		limit 10'''

sql_class_ranking_nolimit='''select evesolo_pilot.id,evesolo_pilot.name,sum(evesolo_solokill.points_awarded) as s from evesolo_pilot
		inner join evesolo_solokill on evesolo_solokill.winning_pilot_id=evesolo_pilot.id
		inner join evesolo_ship on evesolo_ship.id=evesolo_solokill.winners_ship_id
		inner join evesolo_hullclass on evesolo_hullclass.id=evesolo_ship.hull_class_id
		where evesolo_solokill.kill_date>'%s'
		and evesolo_solokill.points_awarded>0.0
		and evesolo_hullclass.id=%d
		group by evesolo_pilot.name
		order by s desc'''

		
sql_class_ranking_ver='''select evesolo_pilot.id,evesolo_pilot.name,sum(evesolo_solokill.points_awarded) as s from evesolo_pilot
		inner join evesolo_solokill on evesolo_solokill.winning_pilot_id=evesolo_pilot.id
		inner join evesolo_ship on evesolo_ship.id=evesolo_solokill.winners_ship_id
		inner join evesolo_hullclass on evesolo_hullclass.id=evesolo_ship.hull_class_id
		where evesolo_solokill.kill_date>'%s'
		and evesolo_solokill.points_awarded>0.0
		and evesolo_solokill.verified=True
		and evesolo_hullclass.id=%d
		group by evesolo_pilot.name
		order by s desc
		limit 10'''
		
		
		
#sql_pilot_hullclass_wins_points='''select evesolo_hullclass.human_name,count(*) as c,sum(evesolo_solokill.points_awarded) as p from evesolo_hullclass
#		inner join evesolo_ship on evesolo_ship.hull_class_id=evesolo_hullclass.id
#		inner join evesolo_solokill on evesolo_solokill.winners_ship_id=evesolo_ship.id
#		inner join evesolo_pilot on evesolo_pilot.id=evesolo_solokill.winning_pilot_id
#		where evesolo_pilot.id=%d
#		and evesolo_solokill.points_awarded>0.0
#		group by evesolo_hullclass.name
#		order by c desc,p desc'''
sql_pilot_hullclass_wins_points='''select evesolo_hullclass.human_name,count(*) as c,sum(evesolo_solokill.points_awarded),evesolo_hullclass.id as p from evesolo_hullclass
		inner join evesolo_ship on evesolo_ship.hull_class_id=evesolo_hullclass.id
		inner join evesolo_solokill on evesolo_solokill.winners_ship_id=evesolo_ship.id
		inner join evesolo_pilot on evesolo_pilot.id=evesolo_solokill.winning_pilot_id
		where evesolo_pilot.id=%d
		and evesolo_solokill.points_awarded>0.0
		group by evesolo_hullclass.name
		order by c desc,p desc'''
sql_pilot_hullclass_wins_points_custom='''select evesolo_hullclass.human_name,count(*) as c,sum(evesolo_solokill.points_awarded),evesolo_hullclass.id as p from evesolo_hullclass
		inner join evesolo_ship on evesolo_ship.hull_class_id=evesolo_hullclass.id
		inner join evesolo_solokill on evesolo_solokill.winners_ship_id=evesolo_ship.id
		inner join evesolo_pilot on evesolo_pilot.id=evesolo_solokill.winning_pilot_id
		inner join evesolo_leaderboardkills on evesolo_solokill.id=evesolo_leaderboardkills.solokill_id
		where evesolo_leaderboardkills.leaderboard_id=%d
		and evesolo_pilot.id=%d
		and evesolo_solokill.points_awarded>0.0
		group by evesolo_hullclass.name
		order by c desc,p desc'''

#sql_pilot_ship_wins_points='''select evesolo_ship.name,count(*) as c,sum(evesolo_solokill.points_awarded) as p from evesolo_ship
#		inner join evesolo_solokill on evesolo_solokill.winners_ship_id=evesolo_ship.id
#		inner join evesolo_pilot on evesolo_pilot.id=evesolo_solokill.winning_pilot_id
#		where evesolo_pilot.id=%d
#		and evesolo_solokill.points_awarded>0.0
#		group by evesolo_ship.name
#		order by c desc,p desc'''
sql_pilot_ship_wins_points='''select evesolo_ship.name,count(*) as c,sum(evesolo_solokill.points_awarded),evesolo_ship.id as p from evesolo_ship
		inner join evesolo_solokill on evesolo_solokill.winners_ship_id=evesolo_ship.id
		inner join evesolo_pilot on evesolo_pilot.id=evesolo_solokill.winning_pilot_id
		where evesolo_pilot.id=%d
		and evesolo_solokill.points_awarded>0.0
		group by evesolo_ship.name
		order by c desc,p desc'''
sql_pilot_ship_wins_points_custom='''select evesolo_ship.name,count(*) as c,sum(evesolo_solokill.points_awarded),evesolo_ship.id as p from evesolo_ship
		inner join evesolo_solokill on evesolo_solokill.winners_ship_id=evesolo_ship.id
		inner join evesolo_pilot on evesolo_pilot.id=evesolo_solokill.winning_pilot_id
		inner join evesolo_leaderboardkills on evesolo_solokill.id=evesolo_leaderboardkills.solokill_id
		where evesolo_leaderboardkills.leaderboard_id=%d
		and evesolo_pilot.id=%d
		and evesolo_solokill.points_awarded>0.0
		group by evesolo_ship.name
		order by c desc,p desc'''

sql_pilot_ships_seen_count='''select evesolo_ccpid.ccp_id,evesolo_ship.name,count(*) as c,evesolo_ship.id from evesolo_ship
		inner join evesolo_solokill on (
										 (evesolo_solokill.winners_ship_id=evesolo_ship.id
                                     		and evesolo_solokill.winning_pilot_id=%d
                                     	 )
                                     		or
                                     	 (evesolo_solokill.losers_ship_id=evesolo_ship.id
                                     	    and evesolo_solokill.losing_pilot_id=%d
                                     	 )
                                      )
		inner join evesolo_ccpid on evesolo_ccpid.id=evesolo_ship.CCPID_id
		where evesolo_solokill.points_awarded>0.0
		group by evesolo_ship.name
		order by c desc
		limit 5'''
sql_pilot_ships_seen_count_custom='''select evesolo_ccpid.ccp_id,evesolo_ship.name,count(*) as c,evesolo_ship.id from evesolo_ship
		inner join evesolo_solokill on (
										 (evesolo_solokill.winners_ship_id=evesolo_ship.id
                                     		and evesolo_solokill.winning_pilot_id=%d
                                     	 )
                                     		or
                                     	 (evesolo_solokill.losers_ship_id=evesolo_ship.id
                                     	    and evesolo_solokill.losing_pilot_id=%d
                                     	 )
                                      )
		inner join evesolo_ccpid on evesolo_ccpid.id=evesolo_ship.CCPID_id
		inner join evesolo_leaderboardkills on evesolo_solokill.id=evesolo_leaderboardkills.solokill_id
		where evesolo_leaderboardkills.leaderboard_id=%d
		and evesolo_solokill.points_awarded>0.0
		group by evesolo_ship.name
		order by c desc
		limit 5'''

sql_most_popular_ships='''select evesolo_ccpid.ccp_id,evesolo_ship.name,evesolo_ship.id,count(*) as c from evesolo_ship
    inner join evesolo_solokill on ((evesolo_solokill.winners_ship_id=evesolo_ship.id)
                                    or
                                    (evesolo_solokill.losers_ship_id=evesolo_ship.id))
	inner join evesolo_ccpid on evesolo_ccpid.id=evesolo_ship.CCPID_id
	where evesolo_solokill.points_awarded>0.0
	group by evesolo_ship.name
	order by c desc
	limit 5'''
sql_most_popular_ships_by_class='''select evesolo_ccpid.ccp_id,evesolo_ship.name,evesolo_ship.id,count(*) as c from evesolo_ship
    inner join evesolo_solokill on ((evesolo_solokill.winners_ship_id=evesolo_ship.id)
                                    or
                                    (evesolo_solokill.losers_ship_id=evesolo_ship.id))
	inner join evesolo_ccpid on evesolo_ccpid.id=evesolo_ship.CCPID_id
    inner join evesolo_hullclass on evesolo_hullclass.id=evesolo_ship.hull_class_id
    where evesolo_hullclass.id=%d
	and evesolo_solokill.points_awarded>0.0
	group by evesolo_ship.name
	order by c desc
	limit 5'''
	
sql_ships_most_wins='''select evesolo_ccpid.ccp_id,evesolo_ship.name,evesolo_ship.id,count(*) as c from evesolo_ship
    inner join evesolo_solokill on evesolo_solokill.winners_ship_id=evesolo_ship.id
	inner join evesolo_ccpid on evesolo_ccpid.id=evesolo_ship.CCPID_id
	where evesolo_solokill.points_awarded>0.0
	group by evesolo_ship.name
	order by c desc
	limit 5'''
sql_ships_most_wins_by_class='''select evesolo_ccpid.ccp_id,evesolo_ship.name,evesolo_ship.id,count(*) as c from evesolo_ship
    inner join evesolo_solokill on evesolo_solokill.winners_ship_id=evesolo_ship.id
	inner join evesolo_ccpid on evesolo_ccpid.id=evesolo_ship.CCPID_id
  inner join evesolo_hullclass on evesolo_hullclass.id=evesolo_ship.hull_class_id
  where evesolo_hullclass.id=%d
	and evesolo_solokill.points_awarded>0.0
	group by evesolo_ship.name
	order by c desc
	limit 5'''
	
sql_ships_most_losses='''select evesolo_ccpid.ccp_id,evesolo_ship.name,evesolo_ship.id,count(*) as c from evesolo_ship
    inner join evesolo_solokill on evesolo_solokill.losers_ship_id=evesolo_ship.id
	inner join evesolo_ccpid on evesolo_ccpid.id=evesolo_ship.CCPID_id
	where evesolo_solokill.points_awarded>0.0
	group by evesolo_ship.name
	order by c desc
	limit 5'''
sql_ships_most_losses_by_class='''select evesolo_ccpid.ccp_id,evesolo_ship.name,evesolo_ship.id,count(*) as c from evesolo_ship
    inner join evesolo_solokill on evesolo_solokill.losers_ship_id=evesolo_ship.id
	inner join evesolo_ccpid on evesolo_ccpid.id=evesolo_ship.CCPID_id
    inner join evesolo_hullclass on evesolo_hullclass.id=evesolo_ship.hull_class_id
	where evesolo_hullclass.id=%d
	and evesolo_solokill.points_awarded>0.0
	group by evesolo_ship.name
	order by c desc
	limit 5'''
	



#NOTE - Includes _ALL_ ships even those with only 1 kill (Unlike the generic eve-board query)
####sql_leaderboard_ships_best_wl_ratio='''select  evesolo_ccpid.ccp_id,evesolo_ship.name as shipname,evesolo_ship.id,
####        (select if(count(*)>0,count(*),null)
####        from evesolo_ship
####        inner join evesolo_solokill on evesolo_solokill.winners_ship_id=evesolo_ship.id
####        inner join evesolo_leaderboardkills on evesolo_leaderboardkills.solokill_id=evesolo_solokill.id
####        where evesolo_solokill.points_awarded>0.0
####        and evesolo_leaderboardkills.leaderboard_id=%d
####        and evesolo_ship.name=shipname
####        ) 
####    /   
####        (select if(count(*)>0,count(*),null)
####        from evesolo_ship
####        inner join evesolo_solokill on evesolo_solokill.losers_ship_id=evesolo_ship.id
####		inner join evesolo_leaderboardkills on evesolo_leaderboardkills.solokill_id=evesolo_solokill.id
####        where evesolo_solokill.points_awarded>0.0
####		and evesolo_leaderboardkills.leaderboard_id=%d
####        and evesolo_ship.name=shipname
####        ) wl_ratio
####  from evesolo_ship
####  inner join evesolo_ccpid on evesolo_ccpid.id=evesolo_ship.CCPID_id  
####	group by evesolo_ship.name
####  having wl_ratio>0
####	order by wl_ratio desc
####	limit 5'''
####sql_leaderboard_ships_worst_wl_ratio='''select  evesolo_ccpid.ccp_id,evesolo_ship.name as shipname,evesolo_ship.id,
####        (select if(count(*)>0,count(*),null)
####        from evesolo_ship
####        inner join evesolo_solokill on evesolo_solokill.winners_ship_id=evesolo_ship.id
####        inner join evesolo_leaderboardkills on evesolo_leaderboardkills.solokill_id=evesolo_solokill.id
####        where evesolo_solokill.points_awarded>0.0
####        and evesolo_leaderboardkills.leaderboard_id=%d
####        and evesolo_ship.name=shipname
####        ) 
####    /   
####        (select if(count(*)>0,count(*),null)
####        from evesolo_ship
####        inner join evesolo_solokill on evesolo_solokill.losers_ship_id=evesolo_ship.id
####		inner join evesolo_leaderboardkills on evesolo_leaderboardkills.solokill_id=evesolo_solokill.id
####        where evesolo_solokill.points_awarded>0.0
####		and evesolo_leaderboardkills.leaderboard_id=%d
####        and evesolo_ship.name=shipname
####        ) wl_ratio
####  from evesolo_ship
####  inner join evesolo_ccpid on evesolo_ccpid.id=evesolo_ship.CCPID_id  
####	group by evesolo_ship.name
####  having wl_ratio>0
####	order by wl_ratio asc
####	limit 5'''
sql_ships_best_wl_ratio='''select  evesolo_ccpid.ccp_id,evesolo_ship.name as shipname,evesolo_ship.id,
        (select if(count(*)>10,count(*),null)
        from evesolo_ship
        inner join evesolo_solokill on evesolo_solokill.winners_ship_id=evesolo_ship.id
        where evesolo_solokill.points_awarded>0.0
        and evesolo_ship.name=shipname
        ) 
    /   
        (select if(count(*)>10,count(*),null)
        from evesolo_ship
        inner join evesolo_solokill on evesolo_solokill.losers_ship_id=evesolo_ship.id
        where evesolo_solokill.points_awarded>0.0
        and evesolo_ship.name=shipname
        ) wl_ratio
  from evesolo_ship
  inner join evesolo_ccpid on evesolo_ccpid.id=evesolo_ship.CCPID_id
	group by evesolo_ship.name
  having wl_ratio>0
	order by wl_ratio desc
	limit 5'''
sql_ships_best_wl_ratio_by_class='''select  evesolo_ccpid.ccp_id,evesolo_ship.name as shipname,evesolo_ship.id,
        (select if(count(*)>10,count(*),null)
        from evesolo_ship
        inner join evesolo_solokill on evesolo_solokill.winners_ship_id=evesolo_ship.id
        where evesolo_solokill.points_awarded>0.0
        and evesolo_ship.name=shipname
        ) 
    /   
        (select if(count(*)>10,count(*),null)
        from evesolo_ship
        inner join evesolo_solokill on evesolo_solokill.losers_ship_id=evesolo_ship.id
        where evesolo_solokill.points_awarded>0.0
        and evesolo_ship.name=shipname
        ) wl_ratio
  from evesolo_ship
  inner join evesolo_ccpid on evesolo_ccpid.id=evesolo_ship.CCPID_id
  inner join evesolo_hullclass on evesolo_hullclass.id=evesolo_ship.hull_class_id
  where evesolo_hullclass.id=%d
	group by evesolo_ship.name
  having wl_ratio>0
	order by wl_ratio desc
	limit 5'''
	
sql_ships_worst_wl_ratio='''select  evesolo_ccpid.ccp_id,evesolo_ship.name as shipname,evesolo_ship.id,
        (select if(count(*)>10,count(*),null)
        from evesolo_ship
        inner join evesolo_solokill on evesolo_solokill.winners_ship_id=evesolo_ship.id
        where evesolo_solokill.points_awarded>0.0
        and evesolo_ship.name=shipname
        ) 
    /   
        (select if(count(*)>10,count(*),null)
        from evesolo_ship
        inner join evesolo_solokill on evesolo_solokill.losers_ship_id=evesolo_ship.id
        where evesolo_solokill.points_awarded>0.0
        and evesolo_ship.name=shipname
        ) wl_ratio
  from evesolo_ship
  inner join evesolo_ccpid on evesolo_ccpid.id=evesolo_ship.CCPID_id
	group by evesolo_ship.name
  having wl_ratio>0
	order by wl_ratio asc
	limit 5'''
sql_ships_worst_wl_ratio_by_class='''select  evesolo_ccpid.ccp_id,evesolo_ship.name as shipname,evesolo_ship.id,
        (select if(count(*)>10,count(*),null)
        from evesolo_ship
        inner join evesolo_solokill on evesolo_solokill.winners_ship_id=evesolo_ship.id
        where evesolo_solokill.points_awarded>0.0
        and evesolo_ship.name=shipname
        ) 
    /   
        (select if(count(*)>10,count(*),null)
        from evesolo_ship
        inner join evesolo_solokill on evesolo_solokill.losers_ship_id=evesolo_ship.id
        where evesolo_solokill.points_awarded>0.0
        and evesolo_ship.name=shipname
        ) wl_ratio
  from evesolo_ship
  inner join evesolo_ccpid on evesolo_ccpid.id=evesolo_ship.CCPID_id
  inner join evesolo_hullclass on evesolo_hullclass.id=evesolo_ship.hull_class_id
  where evesolo_hullclass.id=%d
	group by evesolo_ship.name
  having wl_ratio>0
	order by wl_ratio asc
	limit 5'''

sql_public_leaderboards='''select evesolo_leaderboard.id as leaderboardid, evesolo_leaderboard.name,evesolo_leaderboard.ranks,
		(select count(*) from evesolo_leaderboardinvites
		where evesolo_leaderboardinvites.leaderboard_id=leaderboardid
		and evesolo_leaderboardinvites.status='ACCEPTED'
		),
		evesolo_leaderboard.max_participants,evesolo_leaderboard.rank_style,evesolo_player.name,evesolo_leaderboard.description
		from evesolo_leaderboard
		inner join evesolo_player on evesolo_player.id=evesolo_leaderboard.player_id
		where evesolo_leaderboard.id not in
		(select distinct evesolo_leaderboard.id from evesolo_leaderboard
		inner join evesolo_leaderboardallowedparticipants on evesolo_leaderboardallowedparticipants.leaderboard_id=evesolo_leaderboard.id)
		'''
		

sql_pilot_leaderboard_fight_counts=''' select evesolo_pilot.id, evesolo_pilot.name, count(*) as c from evesolo_pilot
inner join evesolo_solokill on (
										 (evesolo_solokill.winning_pilot_id=evesolo_pilot.id
                                     	 )
                                     		or
                                     	 (evesolo_solokill.losing_pilot_id=evesolo_pilot.id
                                     	 )
                                )
inner join evesolo_leaderboardkills on evesolo_leaderboardkills.solokill_id=evesolo_solokill.id
inner join evesolo_leaderboardinvites on evesolo_pilot.id=evesolo_leaderboardinvites.pilot_id
where
evesolo_leaderboardkills.leaderboard_id=%d
and evesolo_solokill.points_awarded>0
and evesolo_leaderboardinvites.status='ACCEPTED'
group by evesolo_pilot.name
order by c desc
'''

sql_leaderboard_ships_seen_count='''select evesolo_ccpid.ccp_id,evesolo_ship.name,count(*) as c,evesolo_ship.id from evesolo_ship
		inner join evesolo_solokill on (
										 (evesolo_solokill.winners_ship_id=evesolo_ship.id
                                     	 )
                                     		or
                                     	 (evesolo_solokill.losers_ship_id=evesolo_ship.id
                                     	 )
                                      )
		inner join evesolo_ccpid on evesolo_ccpid.id=evesolo_ship.CCPID_id
		inner join evesolo_leaderboardkills on evesolo_solokill.id=evesolo_leaderboardkills.solokill_id
		where evesolo_leaderboardkills.leaderboard_id=%d
		and evesolo_solokill.points_awarded>0.0
		group by evesolo_ship.name
		order by c desc
		limit 5'''

sql_leaderboard_winning_ship_counts='''select evesolo_ccpid.ccp_id,evesolo_ship.name,count(*) as c,evesolo_ship.id from evesolo_ship
		inner join evesolo_solokill on evesolo_solokill.winners_ship_id=evesolo_ship.id
		inner join evesolo_ccpid on evesolo_ccpid.id=evesolo_ship.CCPID_id
		inner join evesolo_leaderboardkills on evesolo_solokill.id=evesolo_leaderboardkills.solokill_id
		where evesolo_leaderboardkills.leaderboard_id=%d
		and evesolo_solokill.points_awarded>0.0
		group by evesolo_ship.name
		order by c desc
		limit 5'''
		
sql_leaderboard_losing_ship_counts='''select evesolo_ccpid.ccp_id,evesolo_ship.name,count(*) as c,evesolo_ship.id from evesolo_ship
		inner join evesolo_solokill on evesolo_solokill.losers_ship_id=evesolo_ship.id
		inner join evesolo_ccpid on evesolo_ccpid.id=evesolo_ship.CCPID_id
		inner join evesolo_leaderboardkills on evesolo_solokill.id=evesolo_leaderboardkills.solokill_id
		where evesolo_leaderboardkills.leaderboard_id=%d
		and evesolo_solokill.points_awarded>0.0
		group by evesolo_ship.name
		order by c desc
		limit 5'''