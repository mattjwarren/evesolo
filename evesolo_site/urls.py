from django.conf.urls.defaults import patterns, include, url
#from evesolo_site import settings
from django.contrib import admin
admin.autodiscover()


urlpatterns = patterns('',
	url(r'^$','evesolo.views.latestkills'),
	
	
	url(r'^newmail/$','evesolo.views.newmail'),
#	url(r'^postmail/$','evesolo.views.postmail'), 
	
	
	url(r'^kills/$','evesolo.views.latestkills'),
	url(r'^kills/(?P<solokill_id>\d+)/$','evesolo.views.viewkill'),
	
	
	url(r'^leaderboards_summary/$','evesolo.views.leaderboards_summary'),
	url(r'^leaderboards_summary/verified/$','evesolo.views.leaderboards_summary',{'verified':True}),
	url(r'^leaderboards_class/(?P<hullclass_id>\d+)/$','evesolo.views.class_leaderboard'),
	url(r'^leaderboards_class/(?P<hullclass_id>\d+)/verified/$','evesolo.views.class_leaderboard',{'verified':True}),
	url(r'^leaderboards_ship/(?P<ship_id>\d+)/$','evesolo.views.ship_leaderboard'),
	url(r'^leaderboards_ship/(?P<ship_id>\d+)/verified/$','evesolo.views.ship_leaderboard',{'verified':True}),
	url(r'^leaderboards/add/$','evesolo.views.add_leaderboard'),
	url(r'^leaderboards_custom/(?P<leaderboard_id>\d+)/$','evesolo.views.leaderboards_summary_custom'),
	url(r'^leaderboards_shipclassindex/$','evesolo.views.ship_boards'),
	url(r'^leaderboard_stats/(?P<board_id>\d+)/','evesolo.views.custom_board_stats'),
	
	url(r'^player/board_action/','evesolo.views.board_action'),
	
	url(r'^ship_stats/$','evesolo.views.ship_stats'),
	
	url(r'^pilot/(?P<pilot_id>\d+)/$','evesolo.views.pilot',{'board_id':None}),
	url(r'^pilot/(?P<pilot_id>\d+)/(?P<board_id>\d+)/$','evesolo.views.pilot'),
	url(r'^pilot/pullmails/$','evesolo.views.pull_mails'),
	url(r'^pilot/join_board/$','evesolo.views.join_board'),
	url(r'^pilot/leave_board/$','evesolo.views.leave_board'),
	
	url(r'^search/$','evesolo.views.search'),
	url(r'^board_search/$','evesolo.views.custom_board_search'),
	
	
	url(r'^accounts/register/$','evesolo.views.register'),									
	url(r'^accounts/login/$', 'django.contrib.auth.views.login',{'template_name': 'evesolo/login.html'}),
	url(r'^accounts/password_reset/$','django.contrib.auth.views.password_reset',
															{'template_name':'evesolo/password_reset.html',
															'email_template_name':'evesolo/password_reset_email.html',
															'post_reset_redirect':'/accounts/post_reset_redirect/',
															'from_email':'yellowalienbaby@gmail.com'}),
															
	url(r'^accounts/post_reset_redirect/$','django.contrib.auth.views.password_reset_done',
															{'template_name':'evesolo/password_reset_done.html'}),
															
	url(r'^accounts/password_reset_confirm/(?P<uidb36>[0-9A-Za-z]+)/(?P<token>.+)/$','django.contrib.auth.views.password_reset_confirm',
															{'template_name':'evesolo/password_reset_confirm.html',
															'post_reset_redirect':'/accounts/password_reset_complete/'}),
															
	url(r'^accounts/password_reset_complete/$','django.contrib.auth.views.password_reset_complete',
															{'template_name':'evesolo/password_reset_complete.html'}),
	
	url(r'^accounts/logout/$','evesolo.views.logout'),									
	url(r'^accounts/profile/$','evesolo.views.profile'),
	url(r'^accounts/add_player/$','evesolo.views.add_player'),
	url(r'^accounts/remove_player/$','evesolo.views.remove_player'),
	url(r'^accounts/add_pilot/$','evesolo.views.add_pilot'),
	url(r'^accounts/remove_pilot/$','evesolo.views.remove_pilot'),
	url(r'^accounts/change_password/$','django.contrib.auth.views.password_change',
									{'post_change_redirect':'/accounts/profile/',
									'template_name':'evesolo/change_password.html'}),
	url(r'^accounts/manage_boards/$','evesolo.views.manage_boards'),
	url(r'^accounts/manage_kills/$','evesolo.views.manage_kills'),
	

	#COMMENT THIS OUT IN PRODUCTION								
	#url(r'^admin/$', include(admin.site.urls)),
	#url(r'^testemail/$','evesolo.views.testemail'),
)
