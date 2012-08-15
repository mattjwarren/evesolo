from evesolo.models import Hullclass, Ship, CCPID
from django.db.utils import IntegrityError
import sys
classes={'hullclass':Hullclass,
		 'ship':Ship}

#infile_name='eve ships classes clean.csv'
#infile_name='typeNames_IDS.csv'
infile_name='typids_types.csv'

		
	


#update_Ship_IDS=True
update_Ship_IDS=False
if update_Ship_IDS:
	ships=Ship.objects.all()
	for ship in ships:
		try:
			ccp=CCPID.objects.get(name=ship.name)
		except CCPID.DoesNotExist:
			print 'NO CCPID FOR NAME',ship.name
		ship.CCPID=ccp
		ship.save()
	print 'Done update ship ids'
	sys.exit()
	






infile=open(infile_name,'r')

lines=infile.readlines()
t=len(lines)
infile.close()
for n,line in enumerate(lines):
	line=line.strip()
	if line.startswith('TABLE'):
		dummy,table=line.split(':')
		continue

	values=line.split(',')
	if table=='hullclass':
		hc=Hullclass()
		hc.name=values[0]
		hc.fwp_value=int(values[1])
		hc.save()
	elif table=='ship':
		s=Ship()
		values=line.split(',')
		hc=Hullclass.objects.get(name=values[2])
		s.name=values[0]
		s.family=values[1]
		s.hull_class=hc
		s.save()
	elif table=='ItemID':
		#SHIPS should be in the DB before ItemID is created from scratch
		i=CCPID()
		i.name=values[0]
		try:
			ship=Ship.objects.get(name=i.name)
			print 'Doing ID for ship:',i.name
			try:
				i.ccp_id=int(values[1])
				i.save()
			except IntegrityError:
				print 'Integrity error for name',values[0]
		except Ship.DoesNotExist:
			pass
	elif table=='ItemTypeID':
		#SHIPS should be in the DB before ItemID is created from scratch
		
		name=values[1].strip()
		try:
			ship=Ship.objects.get(name=name)
			print 'Doing ID for ship:',name
			try:
				i=CCPID.objects.get(name=name)
				i.ccp_type_id=int(values[0])
				i.save()
			except IntegrityError:
				print 'Integrity error for name',values[0]
		except Ship.DoesNotExist:
			pass

print 'Done'
	
