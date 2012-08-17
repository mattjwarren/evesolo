from django.db import models
import datetime
from django.contrib.auth.models import User


# Create your models here.


class Player(models.Model):
	name=models.CharField(max_length=64,unique=True)
	reg_date=models.DateTimeField('Registered date')
	user=models.ForeignKey(User,null=True)
	def __unicode__(self):
		return self.name

class killboard(models.Model):
	name=models.CharField(max_length=64,unique=True)
	url=models.CharField(max_length=255,unique=True)
	highest_seen_killid=models.IntegerField()
	user=models.ForeignKey(User,null=True)
	active=models.BooleanField()
	
	
class Pilot(models.Model):
	name=models.CharField(max_length=64,unique=True)
	player=models.ForeignKey(Player,null=True)
	corp=models.CharField(max_length=64)
	alliance=models.CharField(max_length=64)
	faction=models.CharField(max_length=64)
	#string of the format [[vCode]]key
	#eve api key for this pilot with killlog access (256)
	api_key=models.CharField(max_length=512,null=True)
	#populated whem KMs pulled via API
	#used to 'scroll-back' through KM's until this
	#ID is seen.
	highest_killID=models.IntegerField(null=True)
	def __unicode__(self):
		return self.name

class Hullclass(models.Model):
	name=models.CharField(max_length=5,unique=True)
	fwp_value=models.IntegerField()
	human_name=models.CharField(max_length=45,unique=True)
	def __unicode__(self):
		return self.name


class CCPID(models.Model):
	name=models.CharField(max_length=128,unique=True)
	ccp_id=models.IntegerField()
	ccp_type_id=models.IntegerField()

	def __unicode__(self):
		return 'ccp_id:'+self.ccp_id.__str__()


class Ship(models.Model):
	name=models.CharField(max_length=128,unique=True)
	family=models.CharField(max_length=64)
	hull_class=models.ForeignKey(Hullclass)
	CCPID=models.ForeignKey(CCPID,null=True)

	def __unicode__(self):
		return self.name

class Solokill(models.Model):
	losing_pilot=models.ForeignKey(Pilot,related_name='losing_pilot')
	winning_pilot=models.ForeignKey(Pilot,related_name='winning_pilot')
	losers_ship=models.ForeignKey(Ship,related_name='losers_ship')
	winners_ship=models.ForeignKey(Ship,related_name='winners_ship')
	points_awarded=models.FloatField()
	damage=models.IntegerField()
	submit_date=models.DateTimeField('Submit date')
	kill_date=models.DateTimeField('Kill date')
	verified=models.BooleanField()
	kill_text=models.CharField(max_length=2048)

	def __unicode__(self):
		kill_datetime=self.kill_date.strftime('%d/%m/%Y %H:%M:%S')
		return kill_datetime+'; '+self.winning_pilot.name+' Vs '+self.losing_pilot.name

#new for equipment tracking
class Item(models.Model):
	name=models.CharField(max_length=128,unique=True)
	
	def __unicode__(self):
		return self.name
	
class Destroyeditems(models.Model):
	solokill=models.ForeignKey(Solokill,null=False)
	item_destroyed=models.ForeignKey(Item,null=False)
	count=models.IntegerField()
	
	def __unicode__(self):
		return 'Destroyed items for solokill: %d' % self.solokill.id
	
class Droppeditems(models.Model):
	solokill=models.ForeignKey(Solokill,null=False)
	item_dropped=models.ForeignKey(Item)
	count=models.IntegerField()

	def __unicode__(self):	
		return 'Dropped items: for solokill: %d' % self.solokill.id
		
#Tables for leaderboard implemetation
class Leaderboard(models.Model):
	name=models.CharField(max_length=64,unique=True)
	ranks=models.IntegerField()
	max_participants=models.IntegerField()
	#rank_style :-  KILLS | POINTS
	rank_style=models.CharField(max_length=14)
	player=models.ForeignKey(Player,null=False)
	description=models.CharField(max_length=512)
	
	def __unicode__(self):
		return '%s managed by player %s' % (self.name, self.player.name)
	
##Phase 2	
class Leaderboardinvites(models.Model):
	leaderboard=models.ForeignKey(Leaderboard,null=False)
	pilot=models.ForeignKey(Pilot,null=False)
	#status :- OPEN | ACCEPTED  (closed / rejected etc.. deletes record)
	status=models.CharField(max_length=14)

	def __unicode__(self):
		return '%s invited to %s' % (self.pilot.name,self.leaderboard.name)

	
class Leaderboardkills(models.Model):
	leaderboard=models.ForeignKey(Leaderboard,null=False)
	solokill=models.ForeignKey(Solokill,null=False)

	def __unicode__(self):
		return 'Solokill id %d in leaderboard %s' % (self.solokill.id,self.leaderboard.name)

##Phase 2	
class Leaderboardgroups(models.Model):
	leaderboard=models.ForeignKey(Leaderboard,null=False)
	name=models.CharField(max_length=64)

	def __unicode__(self):
		return 'Group %s for leaderboard %s' % (self.name,self.leaderboard.name)

##Phase 2			- Join time
class Leaderboardallowedparticipants(models.Model):
	leaderboard=models.ForeignKey(Leaderboard,null=False)
	#type :- CORP | ALLIANCE | PILOT
	type=models.CharField(max_length=14)
	name=models.CharField(max_length=64)

	def __unicode__(self):
		return '%s : %s allowed for leaderboard %s' % (self.type,self.name,self.leaderboard.name)

	
##Phase 2	- Kill Entry Time
class Leaderboardallowedships(models.Model):
	leaderboard=models.ForeignKey(Leaderboard,null=False)
	#type :- CLASS | SHIP
	type=models.CharField(max_length=14)
	name=models.CharField(max_length=64)
	
	def __unicode__(self):
		return '%s : %s allowed in leaderboard %s' % (self.type,self.name,self.leaderboard.name)


##Phase 2	- KillEntry time
class Leaderboardallowedsystems(models.Model):
	leaderboard=models.ForeignKey(Leaderboard,null=False)
	name=models.CharField(max_length=64)
	
	def __unicode__(self):
		return 'SYSTEM %s allowed in leaderboard %s' % (self.name,self.leaderboard.name)

	
##Phase 2	
class Leaderboardgroupmemberships(models.Model):
	leaderboard=models.ForeignKey(Leaderboard,null=False)
	group=models.ForeignKey(Leaderboardgroups,null=False)

	def __unicode__(self):
			return 'Leaderboard %s in group %s' % (self.leaderboard.name,self.group.name)

	
#For pahse2 implementation - also display and edit current registered / invite accepted list





