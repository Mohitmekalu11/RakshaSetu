"""
URL configuration for Skillsphere project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from home import views
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.urls import path, include


urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', views.loginpage, name='login'), 
    path('admin_login/', views.admin_login, name='admin_login'),
    path('signup_citizen/', views.signup_citizen, name="signup_citizen"),
    path('signup_police/', views.signup_police, name="signup_police"),
    path('signup_sho/', views.signup_sho, name="signup_sho"),
    path('update_profile/', views.update_profile, name='update_profile'),
    path("choose_pg/", views.choose_pg, name="choose_pg"),
    # USERS:
    path('chatbot/', include('chatbot.urls')),
    path('copilot/', include('safety_copilot.urls')),
    path("raksha-copilot/", include('safety_copilot.urls')), 
    
    
    path('admin_dashboard/', views.admin_dashboard, name='admin_dashboard'), 
    path('approve_police/<int:user_id>/', views.approve_police, name='approve_police'),
    path("disapprove_police/<int:user_id>/", views.disapprove_police, name="disapprove_police"),
    path('police_dashboard/', views.police_dashboard, name='police_dashboard'), 
    path('police_performance/', views.police_performance, name='police_performance'),
    path('Citezens_dashboard/', views.crime_chart_by_state, name='crime_chart'),
    path('Analysis/', views.map_analysis, name='map_analysis'),
    path('crime-data-api/', views.crime_data_api, name='crime_data_api'),
    
    # path('crime_heatmap/', views.crime_heatmap, name='crime_heatmap'),
    # path('crime_timeline/', views.crime_timeline, name='crime_timeline'),
    path('safe_route/', views.safe_route, name='safe_route'),
    
    path('add_contact/', views.add_contact, name='add_contact'),
    path('remove_contact/<int:contact_id>/', views.remove_contact, name='remove_contact'),
    path('get_contacts/', views.get_contacts, name='get_contacts'),
    # path('send_sos/', views.send_sos, name='send_sos'),
   
    path('api/incident/citizen-location/<int:alert_id>/',
     views.CitizenLocationUpdateView.as_view(),  # POST from citizen
     name='citizen_location_update'),

     path('api/incident/citizen-location-read/<int:alert_id>/',
          views.CitizenLiveLocationView.as_view(),  # GET from officerc
          name='citizen_location_read'),
     
     path('officer/track/<int:alert_id>/',
     views.OfficerTrackView.as_view(),
     name='officer_track'),
     
     
     
    path('incident/',
         
         views.CitizenIncidentView.as_view(),
         name='citizen_incident'),
 
    # 2. After submit → JS redirects here automatically
    path('incident/track/<int:alert_id>/',
         views.CitizenTrackView.as_view(),
         name='citizen_track'),
 
    # ══════════════════════════════════════════════════════════
    # OFFICER / POLICE FLOW
    # ══════════════════════════════════════════════════════════
 
    # Officer dashboard — see + manage assigned alerts
    path('officer/dashboard/',
         views.OfficerDashboardView.as_view(),
         name='officer_dashboard'),
 
    # Police / SHO tactical incident console
    path('dispatch/',
         TemplateView.as_view(template_name='police_incident.html'),
         name='police_incident'),
 
    # Officer notification popup (embed in any page with {% include %})
    path('officer-alerts/',
         TemplateView.as_view(template_name='officer_notification_widget.html'),
         name='officer_alerts_page'),
 
    # ══════════════════════════════════════════════════════════
    # INCIDENT ANALYSIS API
    # ══════════════════════════════════════════════════════════
 
    # Called by citizen_incident.html on submit
    path('api/incident/analyze/',
         views.IncidentAnalyzeView.as_view(),
         name='incident_analyze'),
 
    # ══════════════════════════════════════════════════════════
    # LIFECYCLE APIs (used by citizen_track.html + officer_dashboard.html)
    # ══════════════════════════════════════════════════════════
 
    # Citizen polls this every 5s for live status + officer info
    path('api/incident/live/<int:alert_id>/',
         views.LiveStatusView.as_view(),
         name='incident_live'),
 
    # Citizen polls this every 5s for timeline history
    path('api/incident/timeline/<int:alert_id>/',
         views.TimelineView.as_view(),
         name='incident_timeline'),
 
    # Officer dashboard polls this every 5s for assigned alerts
    path('api/incident/officer-alerts/',
         views.OfficerAlertsView.as_view(),
         name='officer_alerts_api'),
 
    # Officer taps Accept / En Route / Arrived / Resolve
    path('api/incident/update-status/',
         views.UpdateStatusView.as_view(),
         name='incident_update_status'),
 
    # Officer notification widget polls this every 15s
    path('api/incident/pending/',
         views.PendingAlertsView.as_view(),
         name='incident_pending'),
 
    # Officer accept / reject a dispatched alert (notification widget)
    path('api/incident/acknowledge/',
         views.IncidentAcknowledgeView.as_view(),
         name='incident_acknowledge'),
 
    # Citizen submits star rating + feedback after resolution
    path('api/incident/feedback/',
         views.CitizenFeedbackView.as_view(),
         name='incident_feedback'),
 
    # Officer marks resolved + posts AI accuracy feedback
    path('api/incident/resolve/',
         views.ResolveAlertView.as_view(),
         name='incident_resolve'),
    
    path("api/officer/update-location/", views.update_officer_location, name="update_officer_location"),
     
    path('api/incident/officer-location/<int:alert_id>/',
     views.OfficerLocationView.as_view(),
     name='officer_location'),
    
    
     
    path("chat/", views.chat, name="chat"),
    path("ai/", views.assistant_page, name="page"),
    path("sho-alerts/", views.sho_alerts, name="sho_alerts"),
    path("intel_detail/<int:id>/", views.intel_detail, name="intel_detail"),
    
    
     path("SHO_dashboard/intel/",                views.intel_center,  name="intel_center"),
     path("api/intel/sitrep/",     views.intel_sitrep,  name="intel_sitrep"),
     path("api/intel/ask/",        views.ask_intel,     name="ask_intel"),
     path("api/intel/predict/",    views.intel_predict, name="intel_predict"),
     path("api/intel/feed/",       views.intel_feed,    name="intel_feed"),
     
    
    # REPORT CRIME #
    path('Citizens_Safety_dashboard/', views.crime_citizen_dashboard, name='crime_citizen_dashboard'),
    path('Citezens_dashboard/crime_report/', views.crime_report, name='crime_report'),
    path("api/report_crime/", views.report_crime, name="report_crime"),
    path('api/get_reports/', views.get_reports, name='get_reports'),
    path('api/update_status/<int:report_id>/', views.update_status, name='update_status'),
    path('api/get_approved_reports/', views.get_approved_reports, name='get_approved_reports'),
    path('api/update_case_status/<int:report_id>/',views.update_case_status, name='update_case_status'),
    path('Citezens_dashboard/crime_report_status/', views.crime_report_status, name='crime_report_status'),
    #delete case report 
    path('delete_report/', views.delete_report, name='delete_report'),
    
    ##AI Detection
    path("verify_evidence/", views.verify_evidence, name="verify_evidence"),
   
    path("sync-news/", views.sync_news, name="sync_news"),
    # Admin approval
    
    path('admin_dashboard/admin_report/', views.admin_report, name='admin_report'),
    path('approve-crime/<int:report_id>/', views.approve_crime, name='approve_crime'),
    path('reject-crime/<int:report_id>/', views.reject_crime, name='reject_crime'),
    path('view-evidence/<int:report_id>/', views.view_evidence, name='view_evidence'),
    path('SHO_dashboard/sho_approved_cases', views.sho_approved_cases, name='sho_approved_cases'),
    
    path('delete-crime/<int:report_id>/', views.delete_crime_report, name='delete-crime'),
    

    ###new ####
    
    path(
    'case/<int:report_id>/detail/',
    views.officer_case_detail,
    name='officer_case_detail'
     ),
     path(
     'case/<int:report_id>/investigate/',
     views.submit_investigation,
     name='submit_investigation'
     ),
     path(
     'SHO_dashboard/review-investigation/<int:report_id>/',
     views.sho_review_investigation,
     name='sho_review_investigation'
     ),
     
      path(
        'SHO_dashboard/approve-report/<int:report_id>/',
        views.sho_approve_report,
        name='sho_approve_report'
    ),
 
    # SHO assigns officer to an approved report
    path(
        'assign-officer/<int:report_id>/',
        views.sho_assign_officer,
        name='sho_assign_officer'
    ),
 
     # from home import views
 
  path('investigation/<int:report_id>/write/',     views.write_investigation,     name='write_investigation'),
  path('investigation/<int:report_id>/submitted/', views.investigation_submitted,  name='investigation_submitted'),
  path('investigation/<int:report_id>/review/',    views.review_investigation,     name='review_investigation'),

  path('api/investigation/ai-draft/<int:report_id>/', views.api_ai_draft,      name='api_ai_draft'),
  path('api/investigation/witness-guide/',            views.api_witness_guide,  name='api_witness_guide'),
  path('api/investigation/quality-check/<int:report_id>/', views.api_quality_check, name='api_quality_check'),
 
 
 
 

 
 
 
 # ── URL to add ────────────────────────────────────────────────────────
# In urls.py add:
  path('api/suspects/', views.get_ward_suspects, name='get_ward_suspects'),


    # Citizen triggers SOS
    path('api/sos/trigger/',     views.SOSTriggerView.as_view(),    name='sos_trigger'),
    # Officer acknowledges
    path('api/sos/acknowledge/', views.SOSAcknowledgeView.as_view(), name='sos_acknowledge'),
    # Citizen cancels during countdown
    path('api/sos/cancel/',      views.SOSCancelView.as_view(),     name='sos_cancel'),
    # Officer pings GPS (call every 2-5 mins from dashboard)
    path('api/officer/location/', views.OfficerLocationUpdateView.as_view(), name='officer_location'),
    
    

    # viewPredictions(PoLice) 
    
     path('api/ward-intel/<str:ward_name>/', views.ward_intel_api, name='ward_intel_api'),
    path('api/wards/', views.wards_geojson, name='wards-geojson'),

    path('monthly_crime_predictions', views.monthly_crime_predictions, name='monthly_crime_predictions'),
    path('monthly_analytics/', views.monthly_analytics, name='monthly_analytics'),
    #Police update status
    path('update-report-status/<int:report_id>/', views.update_report_status, name='update_report_status'),
    
    #police feedback
    path('officer-feedbacks/', views.officer_feedbacks, name='officer_feedbacks'),
    
    #map
    path('Citezens_dashboard/crime_map', views.crime_map, name='crime_map'),
    
    #chatbot 
    path('api/chat/', views.chat_with_bot, name='chat_with_bot'),

# SHO Dashboard

path('SHO_dashboard/', views.sho_dashboard, name='sho_dashboard'),
path('Women_dashboard/', views.citizen_women_dashboard, name='citizen_women_dashboard'),



path("news/", views.crime_news, name="crime_news"),



    path('dashboard/', views.dashboard_view, name='dashboard'),
  path('forecast/<str:ward_name>/<str:crime_type>/', views.ward_forecast_view, name='ward_forecast'),
  path("police/patrol-recommendation/", views.patrol_recommendation_view,name='patrol_recommendations'),


    
   
#     path('hire/', views.hire, name="hire"),
    
#     path('work/', views.work, name="work"),
path('load-fixtures/', views.load_fixtures, name='load_fixtures'),
 
 
    path('', views.index, name="index"),
    path('contact_pg/', views.contact_pg, name="contact_pg"),
    path('forgotpg/', views.forgotpg, name="forgotpg"),
    path('changepg/<uuid:token>/', views.changepg, name="changepg"),
    path('send-email/', views.send_email, name='send_email'),
    path('profile_pg/', views.profile_pg, name='profile_pg'),
#     path('freelancers_listing/', views.freelancers_listing, name='freelancers_listing'),
    path('profile_pg/update/', views.update_profile, name='update_profile'),
    path('profile/update/', views.update_profile, name='update_profile'),
#     path('postjob/', views.postjob, name='postjob'),
#     path('jobs-available/', views.jobs_available, name='jobs_available'),
#     path('apply/<int:job_id>/', views.apply_job, name='apply_job'),
#     path('jobs/<int:job_id>/apply/', views.apply_job, name='apply_job'),
# 	path('freelancer/<int:id>/', views.view_profile, name='view_profile'),
#     path('freelancer/<int:freelancer_id>/', views.freelancer_profile, name='freelancer_profile'),
#     path('submit_application/<int:job_id>/', views.submit_application, name='submit_application'),
# 	path('remove-application/<int:application_id>/', views.remove_job_application, name='remove_job_application'),
#     path('assign_job/<int:freelancer_id>/', views.assign_job, name='assign_job'),
#     path('payment/<int:freelancer_id>/', views.payment_process, name='payment_process'),
#     path('payment/success/', views.payment_success, name='payment_success'),

]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)