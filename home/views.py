from django.shortcuts import render,redirect
from django.http import HttpResponse, JsonResponse
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.contrib import messages
import re
from .models import userProfile
import uuid

from .forms import ProfileForm
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required 

# # from .utils import send_email_to_client
# from .utils import send_email_to_client
# Create your views here.



from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from .models import userProfile  # Ensure you import your Profile model
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from .models import userProfile  # Your Profile model

def loginpage(request):
    try:
        if request.method == 'POST':
            username = request.POST.get('username')
            password = request.POST.get('password')

            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                
                # Get user's profile
                profile = userProfile.objects.get(user=user)
                request.session['login_success'] = 'Login successful!'

                # Redirect based on role
                role = profile.role.lower()
                if role == 'citizen':
                    return redirect('crime_citizen_dashboard')  
                elif role == 'police':
                    return redirect('police_dashboard')
                elif role == 'sho':  # New role
                    return redirect('sho_dashboard')  # You will create this view
                else:
                    messages.error(request, "Your account role is not recognized.")
                    return render(request, 'login.html')

            else:
                messages.error(request, "Invalid Credentials!")
                return render(request, 'login.html')

    except userProfile.DoesNotExist:
        messages.error(request, "Profile does not exist.")
        return render(request, 'login.html')
    except Exception as e:
        print("Login Error:", e)
    
    return render(request, 'login.html')



import re
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.contrib import messages
from django.http import JsonResponse
from .models import userProfile

def signuppage(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm-password', '')
        # Get role from session rather than POST data
        role = request.session.get('user_role', '').strip()
        
        # If role is not set, show an error
        if not role:
            messages.error(request, "User role is not specified.")
            return render(request, 'signup.html')

        phone = request.POST.get('phone', '').strip() if role.lower() == 'police' else ''

        # Validate uniqueness
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email is already in use.")
            return render(request, 'signup.html')
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username is already taken.")
            return render(request, 'signup.html')

        # Validate password strength and match
        if len(password) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
            return render(request, 'signup.html')
        if not re.search(r'[A-Za-z]', password):
            messages.error(request, "Password must contain at least one letter.")
            return render(request, 'signup.html')
        if not re.search(r'[0-9]', password):
            messages.error(request, "Password must contain at least one number.")
            return render(request, 'signup.html')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            messages.error(request, "Password must contain at least one special character.")
            return render(request, 'signup.html')
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, 'signup.html')

        # Validate phone number (only for police role)
        if role.lower() == 'police':
            if not phone.isdigit():
                messages.error(request, "Phone number must contain only digits.")
                return render(request, 'signup.html')
            if len(phone) != 10:
                messages.error(request, "Phone number must be exactly 10 digits.")
                return render(request, 'signup.html')

        try:
            # Ensure atomic creation of user and profile
            with transaction.atomic():
                user = User.objects.create_user(username=username, email=email, password=password)
                # For police, the account is unapproved until verified; citizens are auto-approved.
                is_approved = False if role.lower() == 'police' else True
                id_card = request.FILES.get('id_card') if role.lower() == 'police' else None

                # Create the user profile
                userProfile.objects.create(
                    user=user,
                    role=role.lower(),  # store in lowercase for consistency
                    is_approved=is_approved,
                    phone=f"+91{phone}" if role.lower() == 'police' else '',
                    id_card=id_card
                )

                # Automatically log in the user after successful signup
                login(request, user)
                messages.success(request, "Account created successfully.")
                return redirect('login')

        except Exception as e:
            print("Signup Error:", e)
            messages.error(request, "An error occurred during signup. Please try again.")

    return render(request, 'signup.html')
       
        

# USERS:

from django.db.models import Count, Avg, F, ExpressionWrapper, fields
from django.shortcuts import render
from django.db.models import Count, Avg, F, ExpressionWrapper, fields
from django.shortcuts import render

from django.db.models import Count, Avg, F, ExpressionWrapper, fields
from django.shortcuts import render

def admin_dashboard(request):
    # ================================
    # 🔹 Optional Access Control
    # ================================
    # if not request.user.is_superuser:
    #     messages.error(request, "Access denied.")
    #     return redirect('login')

    # ================================
    # 🔹 Officers Pending Approval
    # ================================
    pending_officersapproval = userProfile.objects.filter(
        role__iexact='police',
        is_approved=False,
        disapproval_message__isnull=True
    )

    # ================================
    # 🔹 Always load top summary safely
    # ================================
    total_users = User.objects.count()
    total_cases = CrimeReport.objects.count()

    stations_data = []
    pending_officers = []

    # ================================
    # 🔹 Analytics Logic
    # ================================
    try:
        reports = CrimeReport.objects.filter(status="Pending")
        for report in reports:
            report.is_approved = True
            officer = userProfile.objects.filter(
                role='police',
                location=report.address
            ).first()
            if officer:
                report.assigned_officer = officer
            report.save()

        for station in PoliceStation.objects.all():
            reports_station = CrimeReport.objects.filter(station=station)
            total_cases_station = reports_station.count()
            resolved_cases = reports_station.filter(resolution_status="Resolved").count()
            pending_cases = reports_station.filter(resolution_status="Pending").count()

            resolution_rate = (
                round((resolved_cases / total_cases_station) * 100, 2)
                if total_cases_station > 0 else 0
            )

            resolved_reports = reports_station.filter(
                resolved_at__isnull=False,
                reported_at__isnull=False
            )

            avg_resolution_display = "N/A"
            avg_resolution_days_numeric = 0  # 🔹 For sorting later

            if resolved_reports.exists():
                avg_duration = resolved_reports.aggregate(
                    avg_time=Avg(
                        ExpressionWrapper(
                            F('resolved_at') - F('reported_at'),
                            output_field=fields.DurationField()
                        )
                    )
                )['avg_time']

                if avg_duration:
                    total_seconds = avg_duration.total_seconds()
                    days = total_seconds / 86400
                    hours = total_seconds / 3600
                    avg_resolution_days_numeric = round(days, 2)

                    if days >= 1:
                        avg_resolution_display = f"{round(days, 2)} days"
                    else:
                        avg_resolution_display = f"{round(hours, 2)} hours"

            top_crime_type = (
                reports_station.values('crime_type')
                .annotate(count=Count('crime_type'))
                .order_by('-count')
                .first()
            )
            top_crime_type = top_crime_type['crime_type'] if top_crime_type else "N/A"

            stations_data.append({
                'name': station.name,
                'total_cases': total_cases_station,
                'resolved_cases': resolved_cases,
                'pending_cases': pending_cases,
                'resolution_rate': resolution_rate,
                'avg_resolution_display': avg_resolution_display,
                'avg_resolution_days_numeric': avg_resolution_days_numeric,
                'top_crime_type': top_crime_type,
            })

        # 🔹 Sort the list (Descending order by total_cases)
        stations_data.sort(key=lambda x: x['total_cases'], reverse=True)

        pending_officers = userProfile.objects.filter(role='police', is_approved=False)

    except Exception as e:
        print(f"⚠️ Admin dashboard analytics error: {e}")

    # ================================
    # ✅ Render Dashboard
    # ================================
    context = {
        'total_users': total_users,
        'total_cases': total_cases,
        'stations': stations_data,
        'pending_officers': pending_officers,
        'pending_officersapproval': pending_officersapproval,
    }

    return render(request, 'admin_dashboard.html', context)


   

from django.contrib import messages
from django.conf import settings

def admin_login(request):
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        # Check against the predefined admin credentials
        if username == 'Mohit11' and password == 'Mohit11@':
            # Set a session flag for admin login (or you can mark the user as admin in a custom way)
            request.session['is_admin'] = True
            messages.success(request, "Admin login successful.")
            return redirect('admin_dashboard')
        else:
            messages.error(request, "Invalid admin credentials.")
    return render(request, 'admin_login.html')
    
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import userProfile, CrimeReport

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Avg
from datetime import timedelta
from .models import userProfile, CrimeReport, OfficerFeedback
from django.utils import timezone

@login_required
def police_dashboard(request):
    if not request.user.is_authenticated:
        return redirect('login')

    profile = get_object_or_404(userProfile, user=request.user)

    # Ensure that only police users can access this view
    if profile.role.lower() != 'police':
        messages.error(request, "Access denied: You are not a police officer.")
        return redirect('index')

    # Ensure the account is approved
    # if not profile.is_approved:
    #     messages.error(request, "Your police account is not yet approved.")
    #     return redirect('police_dashboard')

    # Get assigned crime reports for the police officer
    assigned_reports = CrimeReport.objects.filter(assigned_officer=profile)

    # --- Count by resolution_status ---
    total_cnt         = assigned_reports.count()
    pending_cnt       = assigned_reports.filter(resolution_status='Pending').count()
    investigating_cnt = assigned_reports.filter(resolution_status='Under Investigation').count()
    resolved_cnt      = assigned_reports.filter(resolution_status='Resolved', resolved_at__isnull=False).count()

    # --- Compute average response time (first_touched_at – assigned_at) ---
    responded = assigned_reports.filter(assigned_at__isnull=False, first_touched_at__isnull=False)
    if responded.exists():
        deltas = [(r.first_touched_at - r.assigned_at).total_seconds() for r in responded]
        avg_secs     = sum(deltas) / len(deltas)
        avg_response = timedelta(seconds=avg_secs)
    else:
        avg_secs     = 0
        avg_response = None

    # --- Compute average officer rating ---
    avg = OfficerFeedback.objects.filter(officer=profile).aggregate(a=Avg('rating'))['a']
    officer_rating = round(avg or 0, 1)
    full_stars      = int(officer_rating)
    partial_percent = int((officer_rating - full_stars) * 100)

    # --- New Metrics ---
    resolution_rate = round((resolved_cnt / total_cnt * 100), 1) if total_cnt else 0

    metrics = {
        'total_cases': total_cnt,
        'case_breakdown': f"{pending_cnt} pending, {investigating_cnt} under investigation, {resolved_cnt} resolved",
        # You can uncomment these once you have Alert & PatrolRoute models implemented
        # 'active_alerts': active_alerts.count(),
        # 'alert_breakdown': f"{critical_alerts} critical, {high_alerts} high priority",
        # 'patrol_routes': patrol_routes.count(),
        # 'high_risk_routes': high_risk_routes,
        'resolution_rate': resolution_rate,
        'resolution_comment': "Above station average" if resolution_rate > 80 else "Below station average",
    }

    context = {
        'is_approved': profile.is_approved,
        'assigned_reports': assigned_reports.exclude(status="Resolved"),
        'officer_profile': profile,
        'performance': {
            'total': total_cnt,
            'pending': pending_cnt,
            'investigating': investigating_cnt,
            'resolved': resolved_cnt,
            'avg_response': avg_response,
            'avg_response_secs': avg_secs,
        },
        'officer_rating': officer_rating,
        'full_stars': full_stars,
        'partial_percent': partial_percent,
        'metrics': metrics,
    }

    return render(request, 'police_dashboard.html', context)

# @login_required
def approve_police(request, user_id):
   
    profile = get_object_or_404(userProfile, user__id=user_id)
    profile.is_approved = True
    profile.save()
    
    messages.success(request, f"Officer <b>{profile.user.username}</b> has been approved.")
    return redirect('admin_dashboard')


from django.http import JsonResponse
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
@csrf_exempt
def disapprove_police(request, user_id):
    if request.method == "POST":
        try:
            officer = get_object_or_404(userProfile, user_id=user_id)

            # Mark officer as disapproved
            officer.is_approved = False
            officer.disapproval_message = "Your registration has been disapproved by the admin."
            officer.delete()

            return JsonResponse({"status": "success", "message": "Officer disapproved successfully!"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})

    return JsonResponse({"status": "error", "message": "Invalid request"}, status=400)



def profile_pg(request):
    profile = request.user.profile  # Assuming there's a one-to-one relationship between User and Profile
    return render(request, 'profile_pg(work).html')
#     Check the user's role and render the corresponding profile page
#     if profile.role == 'client':  # Assuming 'role' is a field in the Profile model
#       return render(request, 'profile_pg(hire).html', {'profile': profile})  # Client profile page
#     elif profile.role == 'freelancer':
#        return render(request, 'profile_pg(work).html', {'profile': profile})  # Freelancer profile page
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

@csrf_exempt
def update_profile(request):
    if request.method == "POST":
        try:
            data = request.POST
            profile = request.user.userprofile

            profile.contact = data.get("contact", profile.contact)
            profile.address = data.get("address", profile.address)
            profile.location = data.get("location", profile.location)
            request.user.first_name = data.get("first_name", request.user.first_name)
            request.user.last_name = data.get("last_name", request.user.last_name)

            # Handle Image Upload
            if 'profile_image' in request.FILES:
                profile.profile_image = request.FILES['profile_image']

            request.user.save()
            profile.save()

            return JsonResponse({
                "status": "success",
                "message": "Profile updated successfully!",
                "profile_image_url": profile.profile_image.url if profile.profile_image else ""
            })
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})
    
    return JsonResponse({"status": "error", "message": "Invalid request"}, status=400)


def user_logout(request):
    logout(request)
    return redirect('login')




def contact_pg(request):
    try:
        # Fetch the user's profile
        profile = Profile.objects.get(user=request.user)  # Assuming you have a one-to-one relationship with User

        # Determine the user's role and set the corresponding template
        if profile.role == 'client':
            profile_template = 'contact_pg(hire).html'  # Template for clients
        elif profile.role == 'freelancer':
            profile_template = 'contact_pg(work).html'  # Template for freelancers
        else:
            profile_template = 'contact_pg.html'  # Default template if no role is assigned
        
        # Render the selected template
        return render(request, profile_template)

    except Profile.DoesNotExist:
        # Handle case where user profile doesn't exist
        return render(request, 'error.html', {'message': 'Profile not found'})  #from django.shortcuts import render, redirect

def index(request):
    return render(request, 'index.html')
    

from django.shortcuts import render
from django.db.models import Q
from .models import userProfile

from django.db.models import Count

from django.db.models import Count, Q

from django.shortcuts import render


def hire(request):
    # Fetch all freelancers (without filters)
    freelancers = Profile.objects.filter(role='freelancer')  # Assuming 'role' is used to differentiate freelancers

    # Fetch applications for each freelancer
    for freelancer in freelancers:
        freelancer.applications = Application.objects.filter(freelancer=freelancer.user)  # Adjust this relationship if needed

    # Client filtering logic for jobs and job applications
    client = request.user
    
    # Get the jobs posted by the current client
    jobs = Job.objects.filter(client=client)
    
    # Get the job applications for the jobs posted by the current client
    job_applications = Application.objects.filter(job__in=jobs)

    # Pass both freelancers and job applications to the template
    context = {
        'freelancers': freelancers,
        'job_applications': job_applications,  # Applications related to the client's jobs
        'jobs': jobs,  # Jobs posted by the client
    }

    return render(request, 'hire.html', context)


def send_email(request):
    if request.method == 'POST':
        # Get form data from the request
        subject = request.POST.get('subject')  # Get the subject from the form
        message = request.POST.get('message')  # Get the message from the form
        from_email = request.POST.get('email')  # Get the sender's email from the form
        recipient_list = ['mohitmekalu@gmail.com']  # Your recipient email
        # Add sender's email to the message
        full_message = f"Message from {from_email}:\n\n{message}"

        try:
            # Send the email
            send_mail(
                subject=subject,  # Subject from the form
                message=full_message,  # Message with sender's email included
                from_email=from_email,  # Email address entered by the user
                recipient_list=recipient_list,  # Where to send the email
                fail_silently=False,  # Raise error if email fails
            )

            # Return success response as JSON for the frontend

        
            return JsonResponse({'message': 'Email sent successfully!'}, status=200)
        except:
            return JsonResponse({'message': 'Failed to send email.'}, status=500)
def forgotpg(request):
    try:
        if request.method == "POST":
            username = request.POST.get("username")
            user_obj = User.objects.filter(username=username).first()
            if not user_obj:
                messages.error(request, "No Username Found with this Username")
                return redirect("forgotpg")

            # Generate a token and update the user's profile
            token = str(uuid.uuid4())
            profile_obj = Profile.objects.filter(user=user_obj).first()
            profile_obj.forgot_password_token = token
            profile_obj.save()

            # Send email to user
            send_email_to_client(user_obj.email, token)
            messages.success(request, "Email has been sent")
            return redirect("forgotpg")
    except Exception as e:
        print(e)
        messages.error(request, "An error occurred. Please try again.")
    return render(request, "forgotpg.html")


def changepg(request, token):
    context = {}
    try:
        # Check if the profile object with the token exists
        profile_obj = userProfile.objects.filter(forgot_password_token=token).first()

        if not profile_obj:
            messages.error(request, "Invalid or expired token.")
            return redirect(f"/changepg/{token}/")  # Redirect to same token URL

        # Optionally, check for token expiration if you have a field like `token_expiry`
        # if profile_obj.token_expiry and profile_obj.token_expiry < timezone.now():
        #     messages.error(request, "Token has expired.")
        #     return redirect("forgot_password")  # Redirect to forgot password if expired
        
        # If the request is POST, process the password change
        if request.method == "POST":
            new_password = request.POST.get("password")
            confirm_password = request.POST.get("confirm_password")
            
            # Check if passwords match
            if new_password != confirm_password:
                messages.error(request, "Passwords do not match.")
                return redirect(f"/changepg/{token}/")

            # Ensure password meets minimum length requirements
            if len(new_password) < 8:
                messages.error(request, "Password should be at least 8 characters long.")
                return redirect(f"/changepg/{token}/")

            # Set the new password for the associated user
            user_obj = profile_obj.user
            user_obj.set_password(new_password)
            user_obj.save()

            # Provide success message and redirect to login page
            messages.success(request, "Password changed successfully. Please log in with your new password.")
            return redirect("login")

    except Profile.DoesNotExist:
        messages.error(request, "Invalid or expired token.")
        return redirect("forgot_password")

    except Exception as e:
        # Log the error and provide a message to the user
        print(f"Error changing password: {e}")
        messages.error(request, "An error occurred. Please try again.")
        return redirect(f"/changepg/{token}/")  # Stay on the same page if there's an error

    # Render the password change page if not a POST request
    return render(request, "changepg.html", context)


def work(request):
    jobs = Job.objects.all()  # Retrieve all available jobs
    return render(request, 'work.html', {'jobs': jobs})


def postjob(request):
    if request.method == "POST":
        form = JobPostForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            job.client = request.user  # Set the client to the logged-in user
            job.save()  # Save the job to the database
            return redirect('hire')  # Redirect to the jobs available page
    else:
        form = JobPostForm()

    return render(request, 'postjob.html', {'form': form})

from django.shortcuts import render, get_object_or_404, redirect

# Assuming you have an ApplicationForm defined

def jobs_available(request):
    jobs = Job.objects.all()  # Fetch all jobs from the database
    return render(request, 'jobs_available.html', {'jobs': jobs})


def apply_job(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    if request.method == 'POST':
        form = ApplicationForm(request.POST)
        if form.is_valid():
            application = form.save(commit=False)
            application.job = job
            application.freelancer = request.user  # This should link the logged-in user
            application.save()
            messages.success(request, "Your application has been submitted successfully.")
            return redirect('jobs_available')  # Redirect after a successful save
    else:
        form = ApplicationForm()
    return render(request, 'apply_job.html', {'form': form, 'job': job})

def submit_application(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    
    if request.method == 'POST':
        cover_letter = request.POST.get('cover_letter')
        
        # Create a new application
        Application.objects.create(job=job, freelancer=request.user, cover_letter=cover_letter)
        
        messages.success(request, "Your application has been submitted successfully.")
        return redirect('jobs_available')  # Redirect to the jobs available page

    return render(request, 'apply_job.html', {'job': job})
def freelancer_profile(request, freelancer_id):
    # Get the profile of the freelancer using the freelancer_id
    freelancer = get_object_or_404(Profile, user_id=freelancer_id)
    
    context = {
        'freelancer': freelancer,
    }
    
    return render(request, 'freelancer_profile.html', context)

def freelancers_listing(request):
    freelancers = Freelancer.objects.all()
    categories = Category.objects.all()  # Fetch categories from the database
    return render(request, 'freelancers_listing.html', {'freelancers': freelancers, 'categories': categories})

def remove_job_application(request, application_id):
    application = get_object_or_404(Application, id=application_id)

    # Make sure the logged-in user owns the job or has permission to delete it
    if application.job.client == request.user:
        application.delete()
        
    # else:
        # messages.error(request, 'You do not have permission to remove this application.')
    return redirect('hire')
from django.shortcuts import render, get_object_or_404


def view_profile(request, id):
    profile = get_object_or_404(Profile, user__id=id)  # Assuming id is the User's id
    return render(request, 'freelancer_profile.html', {'profile': profile})

def notify_freelancer(freelancer_email, job_title):
    subject = 'Job Assignment Notification'
    message = f'You have been assigned to the job: {job_title}.'
    from_email = settings.EMAIL_HOST_USER  # Your email

    send_mail(
        subject,
        message,
        from_email,
        [freelancer_email],
        fail_silently=False,
    )

def assign_job(request, freelancer_id):
    # Ensure this action is only available for POST requests
    if request.method == 'POST':
        # Get the freelancer profile
        freelancer = get_object_or_404(Profile, id=freelancer_id)

        # Here, you might want to associate the job with the freelancer
        # Example: job.freelancer = freelancer (if you have a field for it)
        # job.save()

        # Prepare email
        subject = 'You Have Been Assigned a New Job!'
        client_email = request.user.email 
        message = f"Hello {freelancer.user.username},\n\nWe are pleased to inform you that you have been assigned a new job.\nPlease reach out to the client at {client_email} for more details about the assignment.\n\nBest regards,\nSkillsphere"
        from_email = 'your_email@example.com'  # Replace with your email
        recipient_list = [freelancer.mail]  # Get the email from the profile

        # Send email
        send_mail(subject, message, from_email, recipient_list)

        messages.success(request, 'Job assigned and email notification sent!')
        return redirect('hire')  # Redirect to the appropriate page after assignment


##  DATA VISUALIZZATION ##
from django.shortcuts import render,redirect
from django.http import HttpResponse, JsonResponse
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.contrib import messages
import re
from .models import userProfile
import uuid

from .forms import ProfileForm
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required



# from .utils import send_email_to_client
# from .utils import send_email_to_client
# Create your views here.




def signup_citizen(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm-password')
        
        # Validate email uniqueness
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email is already in use.")
            return render(request, 'signup_citizen.html')
        
        # Validate username uniqueness
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username is already taken.")
            return render(request, 'signup_citizen.html')
        
        # Validate password
        if len(password) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
            return render(request, 'signup_citizen.html')
        if not re.search(r'[A-Za-z]', password):
            messages.error(request, "Password must contain at least one letter.")
            return render(request, 'signup_citizen.html')
        if not re.search(r'[0-9]', password):
            messages.error(request, "Password must contain at least one number.")
            return render(request, 'signup_citizen.html')
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, 'signup_citizen.html')
        
        # Create user and citizen profile
        try:
            user = User.objects.create_user(username=username, email=email, password=password)
            user.save()
            profile = userProfile.objects.create(
                user=user,
                role='citizen',
                is_approved=True  # Citizens are auto-approved
            )
            # No extra fields needed, so no additional save() is required
            login(request, user)
            request.session['login_success'] = 'Account Created Successfully. Please Login to continue'
            return redirect('login')
        except Exception as e:
            print("Citizen Signup Error:", e)
            messages.error(request, "An error occurred during signup. Please try again.")
    
    return render(request, 'signup_citizen.html')

import re
import base64
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, get_user_model
from django.core.files.base import ContentFile
from .models import userProfile, PoliceStation

User = get_user_model()

def signup_police(request):
    stations = PoliceStation.objects.all()

    if request.method == 'POST':
        # ——— Collect form fields ———
        username         = request.POST.get('username')
        email            = request.POST.get('email')
        password         = request.POST.get('password')
        confirm_password = request.POST.get('confirm-password')
        id_card          = request.FILES.get('id_card')
        phone            = request.POST.get('phone', '').strip()
        station_id       = request.POST.get('station', '').strip()  # HTML: name="station"
        badge_id         = request.POST.get('badge_id', '').strip()
        experience_level = request.POST.get('experience_level')
        specialty        = request.POST.get('specialty')
        live_video_b64   = request.POST.get('liveness_video')
        live_frame_b64   = request.POST.get('liveness_frame')

        # ——— Validations ———
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email is already in use.")
            return render(request, 'signup_police.html', {"stations": stations})
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username is already taken.")
            return render(request, 'signup_police.html', {"stations": stations})
        if len(password) < 8 or not re.search(r'[A-Za-z]', password) or not re.search(r'\d', password):
            messages.error(request, "Password must be at least 8 characters and include letters & numbers.")
            return render(request, 'signup_police.html', {"stations": stations})
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, 'signup_police.html', {"stations": stations})
        if not phone.isdigit() or len(phone) != 10:
            messages.error(request, "Phone must be exactly 10 digits.")
            return render(request, 'signup_police.html', {"stations": stations})
        if not station_id:
            messages.error(request, "Please select your police station.")
            return render(request, 'signup_police.html', {"stations": stations})
        if not badge_id:
            messages.error(request, "Badge ID is required.")
            return render(request, 'signup_police.html', {"stations": stations})
        if not experience_level:
            messages.error(request, "Please select your experience level.")
            return render(request, 'signup_police.html', {"stations": stations})
        if not specialty:
            messages.error(request, "Please select your specialty.")
            return render(request, 'signup_police.html', {"stations": stations})
        if not live_video_b64 or not live_frame_b64:
            messages.error(request, "Please record the 3-second liveness video first.")
            return render(request, 'signup_police.html', {"stations": stations})

        try:
            # ——— Get the PoliceStation instance ———
            station_instance = PoliceStation.objects.get(id=station_id)

            # ——— Create User ———
            user = User.objects.create_user(username=username, email=email, password=password)
            user.save()

            # ——— Create Police Profile ———
            profile = userProfile.objects.create(
                user=user,
                role='police',
                phone=f"+91{phone}",
                id_card=id_card,
                station=station_instance,  # ✅ correct instance assigned
                badge_id=badge_id,
                experience_level=experience_level,
                specialty=specialty,
                is_approved=False  # police accounts need admin approval
            )

            # ——— Decode and save liveness video ———
            header, data = live_video_b64.split(';base64,')
            ext = header.split('/')[-1]
            video_data = base64.b64decode(data)
            profile.liveness_video.save(f"{username}_live.{ext}", ContentFile(video_data), save=False)

            # ——— Decode and save liveness frame ———
            header, data = live_frame_b64.split(';base64,')
            ext = header.split('/')[-1]
            img_data = base64.b64decode(data)
            profile.liveness_frame.save(f"{username}_frame.{ext}", ContentFile(img_data), save=False)

            # ——— Final save ———
            profile.save()

            # ——— Auto login + redirect like citizen ———
            login(request, user)
            request.session['login_success'] = 'Account Created Successfully. Please Login to continue'
            return redirect('login')

        except PoliceStation.DoesNotExist:
            messages.error(request, "Invalid police station selected.")
        except Exception as e:
            print("Police Signup Error:", e)
            messages.error(request, "An error occurred during signup. Please try again.")

    return render(request, 'signup_police.html', {"stations": stations})


import re
import base64
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, get_user_model
from django.core.files.base import ContentFile
from .models import userProfile, PoliceStation

User = get_user_model()

def signup_sho(request):
    stations = PoliceStation.objects.all()  # SHO must also be assigned to a station

    if request.method == 'POST':
        # ——— Collect form fields ———
        username         = request.POST.get('username')
        email            = request.POST.get('email')
        password         = request.POST.get('password')
        confirm_password = request.POST.get('confirm-password')
        id_card          = request.FILES.get('id_card')
        phone            = request.POST.get('phone', '').strip()
        station_id       = request.POST.get('station', '').strip()  # HTML: name="station"
        badge_id         = request.POST.get('badge_id', '').strip()
        experience_level = request.POST.get('experience_level')
        specialty        = request.POST.get('specialty')
        
        live_video_b64   = request.POST.get('liveness_video')
        live_frame_b64   = request.POST.get('liveness_frame')

        # ——— Validations ———
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email is already in use.")
            return render(request, 'signup_sho.html', {"stations": stations})
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username is already taken.")
            return render(request, 'signup_sho.html', {"stations": stations})
        if len(password) < 8 or not re.search(r'[A-Za-z]', password) or not re.search(r'\d', password):
            messages.error(request, "Password must be at least 8 characters and include letters & numbers.")
            return render(request, 'signup_sho.html', {"stations": stations})
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, 'signup_sho.html', {"stations": stations})
        if not phone.isdigit() or len(phone) != 10:
            messages.error(request, "Phone must be exactly 10 digits.")
            return render(request, 'signup_sho.html', {"stations": stations})
        if not station_id:
            messages.error(request, "Please select your police station.")
            return render(request, 'signup_sho.html', {"stations": stations})
        if not badge_id:
            messages.error(request, "Badge ID is required.")
            return render(request, 'signup_sho.html', {"stations": stations})
        if not experience_level:
            messages.error(request, "Please select your experience level.")
            return render(request, 'signup_sho.html', {"stations": stations})
        if not specialty:
            messages.error(request, "Please select your specialty.")
            return render(request, 'signup_sho.html', {"stations": stations})
       
        if not live_video_b64 or not live_frame_b64:
            messages.error(request, "Please record the 3-second liveness video first.")
            return render(request, 'signup_sho.html', {"stations": stations})

        try:
            # ——— Get the PoliceStation instance ———
            station_instance = PoliceStation.objects.get(id=station_id)

            # ——— Create User ———
            user = User.objects.create_user(username=username, email=email, password=password)
            user.save()

            # ——— Create SHO Profile ———
            profile = userProfile.objects.create(
                user=user,
                role='sho',
                phone=f"+91{phone}",
                id_card=id_card,
                station=station_instance,
                badge_id=badge_id,
                experience_level=experience_level,
                specialty=specialty,
                
                is_approved=False  # Needs admin approval
            )

            # ——— Decode and save liveness video ———
            header, data = live_video_b64.split(';base64,')
            ext = header.split('/')[-1]
            video_data = base64.b64decode(data)
            profile.liveness_video.save(f"{username}_live.{ext}", ContentFile(video_data), save=False)

            # ——— Decode and save liveness frame ———
            header, data = live_frame_b64.split(';base64,')
            ext = header.split('/')[-1]
            img_data = base64.b64decode(data)
            profile.liveness_frame.save(f"{username}_frame.{ext}", ContentFile(img_data), save=False)

            # ——— Final save ———
            profile.save()

            # ——— Auto login + redirect ———
            login(request, user)
            request.session['login_success'] = 'SHO Account Created Successfully. Please Login to continue'
            return redirect('login')

        except PoliceStation.DoesNotExist:
            messages.error(request, "Invalid police station selected.")
        except Exception as e:
            print("SHO Signup Error:", e)
            messages.error(request, "An error occurred during signup. Please try again.")

    return render(request, 'signup_sho.html', {"stations": stations})


def choose_pg(request):
    if request.method == 'POST':
        role = request.POST.get('role')
        request.session['user_role'] = role

        if role == 'police':
            return redirect('signup_police')
        elif  role == 'sho':
            return redirect('signup_sho')
        else:
            return redirect('signup_citizen')
    return render(request, 'choose_pg.html')

    
def profile_pg(request):
    profile = request.user.profile  # Assuming there's a one-to-one relationship between User and Profile
    return render(request, 'profile_pg(work).html')
#     Check the user's role and render the corresponding profile page
#     if profile.role == 'client':  # Assuming 'role' is a field in the Profile model
#       return render(request, 'profile_pg(hire).html', {'profile': profile})  # Client profile page
#     elif profile.role == 'freelancer':
#        return render(request, 'profile_pg(work).html', {'profile': profile})  # Freelancer profile page


  # Render the form template
  # Redirect to the respective profile pa

def user_logout(request):
    logout(request)
    return redirect('login')


def contact_pg(request):
    try:
        # Fetch the user's profile
        profile = Profile.objects.get(user=request.user)  # Assuming you have a one-to-one relationship with User

        # Determine the user's role and set the corresponding template
        if profile.role == 'client':
            profile_template = 'contact_pg(hire).html'  # Template for clients
        elif profile.role == 'freelancer':
            profile_template = 'contact_pg(work).html'  # Template for freelancers
        else:
            profile_template = 'contact_pg.html'  # Default template if no role is assigned
        
        # Render the selected template
        return render(request, profile_template)

    except Profile.DoesNotExist:
        # Handle case where user profile doesn't exist
        return render(request, 'error.html', {'message': 'Profile not found'})  #from django.shortcuts import render, redirect


def index(request):
    return render(request, 'index.html')
    

from django.shortcuts import render
from django.db.models import Q
from .models import userProfile
from django.db.models import Count

from django.db.models import Count, Q
from django.shortcuts import render

def hire(request):
    # Fetch all freelancers (without filters)
    freelancers = Profile.objects.filter(role='freelancer')  # Assuming 'role' is used to differentiate freelancers

    # Fetch applications for each freelancer
    for freelancer in freelancers:
        freelancer.applications = Application.objects.filter(freelancer=freelancer.user)  # Adjust this relationship if needed

    # Client filtering logic for jobs and job applications
    client = request.user
    
    # Get the jobs posted by the current client
    jobs = Job.objects.filter(client=client)
    
    # Get the job applications for the jobs posted by the current client
    job_applications = Application.objects.filter(job__in=jobs)

    # Pass both freelancers and job applications to the template
    context = {
        'freelancers': freelancers,
        'job_applications': job_applications,  # Applications related to the client's jobs
        'jobs': jobs,  # Jobs posted by the client
    }

    return render(request, 'hire.html', context)


def send_email(request):
    if request.method == 'POST':
        # Get form data from the request
        subject = request.POST.get('subject')  # Get the subject from the form
        message = request.POST.get('message')  # Get the message from the form
        from_email = request.POST.get('email')  # Get the sender's email from the form
        recipient_list = ['mohitmekalu@gmail.com']  # Your recipient email
        # Add sender's email to the message
        full_message = f"Message from {from_email}:\n\n{message}"

        try:
            # Send the email
            send_mail(
                subject=subject,  # Subject from the form
                message=full_message,  # Message with sender's email included
                from_email=from_email,  # Email address entered by the user
                recipient_list=recipient_list,  # Where to send the email
                fail_silently=False,  # Raise error if email fails
            )

            # Return success response as JSON for the frontend

        
            return JsonResponse({'message': 'Email sent successfully!'}, status=200)
        except:
            return JsonResponse({'message': 'Failed to send email.'}, status=500)
def forgotpg(request):
    try:
        if request.method == "POST":
            username = request.POST.get("username")
            user_obj = User.objects.filter(username=username).first()
            if not user_obj:
                messages.error(request, "No Username Found with this Username")
                return redirect("forgotpg")

            # Generate a token and update the user's profile
            token = str(uuid.uuid4())
            profile_obj = Profile.objects.filter(user=user_obj).first()
            profile_obj.forgot_password_token = token
            profile_obj.save()

            # Send email to user
            send_email_to_client(user_obj.email, token)
            messages.success(request, "Email has been sent")
            return redirect("forgotpg")
    except Exception as e:
        print(e)
        messages.error(request, "An error occurred. Please try again.")
    return render(request, "forgotpg.html")


def changepg(request, token):
    context = {}
    try:
        # Check if the profile object with the token exists
        profile_obj = Profile.objects.filter(forgot_password_token=token).first()

        if not profile_obj:
            messages.error(request, "Invalid or expired token.")
            return redirect(f"/changepg/{token}/")  # Redirect to same token URL

        # Optionally, check for token expiration if you have a field like `token_expiry`
        # if profile_obj.token_expiry and profile_obj.token_expiry < timezone.now():
        #     messages.error(request, "Token has expired.")
        #     return redirect("forgot_password")  # Redirect to forgot password if expired
        
        # If the request is POST, process the password change
        if request.method == "POST":
            new_password = request.POST.get("password")
            confirm_password = request.POST.get("confirm_password")
            
            # Check if passwords match
            if new_password != confirm_password:
                messages.error(request, "Passwords do not match.")
                return redirect(f"/changepg/{token}/")

            # Ensure password meets minimum length requirements
            if len(new_password) < 8:
                messages.error(request, "Password should be at least 8 characters long.")
                return redirect(f"/changepg/{token}/")

            # Set the new password for the associated user
            user_obj = profile_obj.user
            user_obj.set_password(new_password)
            user_obj.save()

            # Provide success message and redirect to login page
            messages.success(request, "Password changed successfully. Please log in with your new password.")
            return redirect("login")

    except Profile.DoesNotExist:
        messages.error(request, "Invalid or expired token.")
        return redirect("forgot_password")

    except Exception as e:
        # Log the error and provide a message to the user
        print(f"Error changing password: {e}")
        messages.error(request, "An error occurred. Please try again.")
        return redirect(f"/changepg/{token}/")  # Stay on the same page if there's an error

    # Render the password change page if not a POST request
    return render(request, "changepg.html", context)


def work(request):
    jobs = Job.objects.all()  # Retrieve all available jobs
    return render(request, 'work.html', {'jobs': jobs})


def postjob(request):
    if request.method == "POST":
        form = JobPostForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            job.client = request.user  # Set the client to the logged-in user
            job.save()  # Save the job to the database
            return redirect('hire')  # Redirect to the jobs available page
    else:
        form = JobPostForm()

    return render(request, 'postjob.html', {'form': form})

from django.shortcuts import render, get_object_or_404, redirect



def jobs_available(request):
    jobs = Job.objects.all()  # Fetch all jobs from the database
    return render(request, 'jobs_available.html', {'jobs': jobs})


def apply_job(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    if request.method == 'POST':
        form = ApplicationForm(request.POST)
        if form.is_valid():
            application = form.save(commit=False)
            application.job = job
            application.freelancer = request.user  # This should link the logged-in user
            application.save()
            messages.success(request, "Your application has been submitted successfully.")
            return redirect('jobs_available')  # Redirect after a successful save
    else:
        form = ApplicationForm()
    return render(request, 'apply_job.html', {'form': form, 'job': job})

def submit_application(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    
    if request.method == 'POST':
        cover_letter = request.POST.get('cover_letter')
        
        # Create a new application
        Application.objects.create(job=job, freelancer=request.user, cover_letter=cover_letter)
        
        messages.success(request, "Your application has been submitted successfully.")
        return redirect('jobs_available')  # Redirect to the jobs available page

    return render(request, 'apply_job.html', {'job': job})
def freelancer_profile(request, freelancer_id):
    # Get the profile of the freelancer using the freelancer_id
    freelancer = get_object_or_404(Profile, user_id=freelancer_id)
    
    context = {
        'freelancer': freelancer,
    }
    
    return render(request, 'freelancer_profile.html', context)

def freelancers_listing(request):
    freelancers = Freelancer.objects.all()
    categories = Category.objects.all()  # Fetch categories from the database
    return render(request, 'freelancers_listing.html', {'freelancers': freelancers, 'categories': categories})

def remove_job_application(request, application_id):
    application = get_object_or_404(Application, id=application_id)

    # Make sure the logged-in user owns the job or has permission to delete it
    if application.job.client == request.user:
        application.delete()
        
    # else:
        # messages.error(request, 'You do not have permission to remove this application.')
    return redirect('hire')
from django.shortcuts import render, get_object_or_404


def view_profile(request, id):
    profile = get_object_or_404(Profile, user__id=id)  # Assuming id is the User's id
    return render(request, 'freelancer_profile.html', {'profile': profile})

def notify_freelancer(freelancer_email, job_title):
    subject = 'Job Assignment Notification'
    message = f'You have been assigned to the job: {job_title}.'
    from_email = settings.EMAIL_HOST_USER  # Your email

    send_mail(
        subject,
        message,
        from_email,
        [freelancer_email],
        fail_silently=False,
    )

def assign_job(request, freelancer_id):
    # Ensure this action is only available for POST requests
    if request.method == 'POST':
        # Get the freelancer profile
        freelancer = get_object_or_404(Profile, id=freelancer_id)

        # Here, you might want to associate the job with the freelancer
        # Example: job.freelancer = freelancer (if you have a field for it)
        # job.save()

        # Prepare email
        subject = 'You Have Been Assigned a New Job!'
        client_email = request.user.email 
        message = f"Hello {freelancer.user.username},\n\nWe are pleased to inform you that you have been assigned a new job.\nPlease reach out to the client at {client_email} for more details about the assignment.\n\nBest regards,\nSkillsphere"
        from_email = 'your_email@example.com'  # Replace with your email
        recipient_list = [freelancer.mail]  # Get the email from the profile

        # Send email
        send_mail(subject, message, from_email, recipient_list)

        messages.success(request, 'Job assigned and email notification sent!')
        return redirect('hire')  # Redirect to the appropriate page after assignment
                    # *GENERAL USER* #          

##  DATA VISUALIZZATION ##
from django.shortcuts import render
from django.http import JsonResponse
import pandas as pd

# Load dataset once globally
CSV_PATH = 'home/thane_crime_data.csv'
df = pd.read_csv(CSV_PATH)

# Parse Date & Time and extract Year
df["Date & Time"] = pd.to_datetime(df["Date & Time"], errors='coerce')
df["Year"] = df["Date & Time"].dt.year

# Extract unique values for filters
unique_states = sorted(df['State'].dropna().unique())
unique_districts = sorted(df['District'].dropna().unique())
unique_cities = sorted(df['City'].dropna().unique())
unique_crime_types = sorted(df['Crime Type'].dropna().unique())

def crime_chart_by_state(request):
    # Base stats
    total_crimes = len(df)
    solved_cases = df[df['Case Status'].str.lower() == 'solved'].shape[0]
    unsolved_cases = df[df['Case Status'].str.lower() == 'unsolved'].shape[0]

    context = {
        'total_crimes': total_crimes,
        'solved_cases': solved_cases,
        'unsolved_cases': unsolved_cases,
        'states': unique_states,
        'districts': unique_districts,
        'cities': unique_cities,
        'crime_types': unique_crime_types,
    }

    # Drill-down and filter parameters
    level = request.GET.get('level', 'year')  # year, state, district, area, case_status
    year = request.GET.get('year', '')
    gender = request.GET.get('gender', '')
    state = request.GET.get('state', '')
    district = request.GET.get('district', '')
    area = request.GET.get('area', '')

    # Advanced filters
    start_date = request.GET.get('startDate', '')
    end_date = request.GET.get('endDate', '')
    city = request.GET.get('city', '')
    crime_type = request.GET.get('crimeType', '')
    case_status = request.GET.get('caseStatus', '')

    # Create filtered copy
    filtered_df = df.copy()

    # Apply filters sequentially
    if start_date:
        filtered_df = filtered_df[filtered_df["Date & Time"] >= pd.to_datetime(start_date)]
    if end_date:
        filtered_df = filtered_df[filtered_df["Date & Time"] <= pd.to_datetime(end_date)]
    if year:
        filtered_df = filtered_df[filtered_df['Year'] == int(year)]
    if gender:
        filtered_df = filtered_df[filtered_df['Accused Gender'].str.lower() == gender.lower()]
    if state:
        filtered_df = filtered_df[filtered_df['State'].str.lower() == state.lower()]
    if district:
        filtered_df = filtered_df[filtered_df['District'].str.lower() == district.lower()]
    if area:
        filtered_df = filtered_df[filtered_df['Area'].str.lower() == area.lower()]
    if city:
        filtered_df = filtered_df[filtered_df['City'].str.lower() == city.lower()]
    if crime_type:
        crime_type_list = crime_type.split(',')
        filtered_df = filtered_df[filtered_df['Crime Type'].isin(crime_type_list)]
    if case_status:
        case_status_list = case_status.split(',')
        filtered_df = filtered_df[filtered_df['Case Status'].isin(case_status_list)]

    # Prepare drill-down data
    if level == 'year':
        grouped = filtered_df.groupby(['Year', 'Accused Gender']).size().unstack(fill_value=0).reset_index()
        labels = grouped['Year'].astype(str).tolist()
        data = grouped.drop(columns=['Year']).to_dict(orient='list')

    elif level == 'state':
        grouped = filtered_df.groupby(['State', 'Accused Gender']).size().unstack(fill_value=0).reset_index()
        labels = grouped['State'].tolist()
        data = grouped.drop(columns=['State']).to_dict(orient='list')

    elif level == 'district':
        grouped = filtered_df.groupby(['District', 'Accused Gender']).size().unstack(fill_value=0).reset_index()
        labels = grouped['District'].tolist()
        data = grouped.drop(columns=['District']).to_dict(orient='list')

    elif level == 'area':
        grouped = filtered_df.groupby(['Area', 'Accused Gender']).size().unstack(fill_value=0).reset_index()
        labels = grouped['Area'].tolist()
        data = grouped.drop(columns=['Area']).to_dict(orient='list')

    elif level == 'case_status':
        counts = filtered_df['Case Status'].value_counts().to_dict()
        case_data = {
            'ongoing': counts.get('Ongoing', 0),
            'solved': counts.get('Solved', 0),
            'unsolved': counts.get('Unsolved', 0)
        }
        return JsonResponse(case_data)

    # AJAX returns JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'labels': labels, 'data': data})

    # Otherwise render template
    return render(request, 'crime_chart.html', context)

# from django.http import JsonResponse
# import pandas as pd

# def crime_data_api(request):
#     # Load crime data from CSV
#     df = pd.read_csv("home/crime_data.csv")

#     # Ensure lat & lon columns exist
#     if 'Latitude' not in df.columns or 'Longitude' not in df.columns:
#         return JsonResponse({"error": "CSV must contain 'lat' and 'lon' columns"}, status=400)

#     # Group by lat-lon to count crimes at each location
#     crime_density = df.groupby(['Latitude', 'Longitude']).size().reset_index(name='intensity')

#     # Convert to JSON response
#     crime_list = crime_density.to_dict(orient="records")

#     return JsonResponse(crime_list, safe=False)

# 4. Map Analysis View
def map_analysis(request):
    """Renders the map analysis template."""
    return render(request, "map_analysis.html")

from django.shortcuts import render
from django.http import JsonResponse
import pandas as pd

from django.shortcuts import render
from django.http import JsonResponse
import pandas as pd
import os
from django.conf import settings
from django.shortcuts import render
from django.http import JsonResponse
import pandas as pd
import os
from django.conf import settings

def safe_route(request):
    """Render the Safe Route page"""
    return render(request, 'safe_route.html')

def crime_data_api(request):
    """Fetch crime data and return high-crime locations for route safety analysis"""
    
    # Load dataset
    file_path = os.path.join(settings.BASE_DIR, "home/crime_data.csv")
    df = pd.read_csv(file_path)

    # Ensure required columns exist
    required_columns = {'Latitude', 'Longitude', 'Crime Type', 'Case Status', 'FIR Filed'}
    if not required_columns.issubset(df.columns):
        return JsonResponse({"error": "Missing necessary columns in dataset"}, status=400)

    # Define crime risk levels (Higher values = more dangerous)
    crime_risk = {
        "Murder": 0.9, "Assault": 0.8, "Robbery": 0.7,
        "Burglary": 0.6, "Fraud": 0.5, "Harassment": 0.4,
        "Other": 0.3
    }

    # Assign risk level based on Crime Type
    df["Risk_Score"] = df["Crime Type"].map(lambda x: crime_risk.get(x, 0.3))

    # Increase risk for unsolved cases
    df["Risk_Score"] += df["Case Status"].apply(lambda x: 0.2 if x.lower() in ["unsolved", "pending"] else 0)

    # Increase risk if FIR was filed recently (assuming date is in YYYY-MM-DD format)
    df["FIR Filed"] = pd.to_datetime(df["FIR Filed"], errors="coerce")
    recent_threshold = pd.to_datetime("2024-01-01")  # Change based on latest data
    df["Risk_Score"] += df["FIR Filed"].apply(lambda x: 0.1 if pd.notna(x) and x >= recent_threshold else 0)

    # Normalize risk score (0 = safest, 1 = most dangerous)
    df["Risk_Score"] = df["Risk_Score"].clip(0, 1)

    # Mark high-risk locations (Threshold: Risk_Score > 0.6)
    high_crime_areas = df[df["Risk_Score"] > 0.6][["Latitude", "Longitude", "Risk_Score"]]

    # Convert to JSON
    crime_list = high_crime_areas.to_dict(orient="records")
    
    return JsonResponse(crime_list, safe=False)


                            # REPORT CRIME #
@login_required
def crime_report(request):
    stations = PoliceStation.objects.all()
    return render(request, "crime_report.html", {"stations": stations})

# from django.http import JsonResponse
# from django.views.decorators.csrf import csrf_exempt
# from asgiref.sync import async_to_sync
# from channels.layers import get_channel_layer
# from django.conf import settings
# from .models import CrimeReport, CrimePhoto
# from .ml_utils import predict_severity
# from .utils_pkg.deepfake_detector import is_fake_image, is_fake_video

# import os

# MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


# @csrf_exempt
# def verify_evidence(request):
#     """
#     Step 2: Verify uploaded photos/videos using AI deepfake detection.
#     """
#     if request.method != "POST":
#         return JsonResponse({"success": False, "message": "Invalid request!"})

#     try:
#         photos = request.FILES.getlist("photos")
#         video = request.FILES.get("video")

#         # Validate file sizes
#         for media in photos + ([video] if video else []):
#             if media and media.size > MAX_FILE_SIZE:
#                 return JsonResponse({"success": False, "message": f"File '{media.name}' exceeds size limit."})

#         # Check photos
#         for photo in photos:
#             temp_path = os.path.join(settings.MEDIA_ROOT, "temp", photo.name)
#             os.makedirs(os.path.dirname(temp_path), exist_ok=True)
#             with open(temp_path, "wb+") as dest:
#                 for chunk in photo.chunks():
#                     dest.write(chunk)
#             if is_fake_image(temp_path):
#                 return JsonResponse({"success": False, "message": f"❌ Fake/AI-generated photo detected: {photo.name}"})

#         # Check video
#         if video:
#             temp_path = os.path.join(settings.MEDIA_ROOT, "temp", video.name)
#             os.makedirs(os.path.dirname(temp_path), exist_ok=True)
#             with open(temp_path, "wb+") as dest:
#                 for chunk in video.chunks():
#                     dest.write(chunk)
#             if is_fake_video(temp_path):
#                 return JsonResponse({"success": False, "message": f"❌ Fake/AI-generated video detected: {video.name}"})

#         return JsonResponse({"success": True, "message": "✅ All evidence verified as authentic."})

#     except Exception as e:
#         return JsonResponse({"success": False, "message": f"Error: {str(e)}"})


#########Main reportcrime##################


# from django.http import JsonResponse
# from django.views.decorators.csrf import csrf_exempt
# from .models import CrimeReport, CrimePhoto, PoliceStation
# from channels.layers import get_channel_layer
# from asgiref.sync import async_to_sync

# @csrf_exempt
# def report_crime(request):
#     """
#     Step 3: Submit crime report (after evidence verification).
#     Now includes selection of Police Station.
#     """
#     if request.method != "POST":
#         return JsonResponse({"success": False, "message": "Invalid request!"})

#     try:
#         # Extract form data
#         crime_type = request.POST.get("crime_type")
#         description = request.POST.get("description")
#         address = request.POST.get("address", "Unknown")
#         latitude = request.POST.get("latitude")
#         longitude = request.POST.get("longitude")
#         video = request.FILES.get("video")
#         photos = request.FILES.getlist("photos")
#         reported_by = request.user if request.user.is_authenticated else None
#         station_id = request.POST.get("station")

#         # Validate station
#         station = None
#         if station_id:
#             station = PoliceStation.objects.get(id=station_id)

#         # Prevent duplicate reports
#         if CrimeReport.objects.filter(
#             crime_type=crime_type,
#             description=description,
#             address=address,
#             station=station
#         ).exists():
#             return JsonResponse({
#                 "success": False,
#                 "message": "This crime report already exists!"
#             })

#         # Predict severity (existing function)
#         severity_score = predict_severity(crime_type, description, address)

#         # Create new crime report with station
#         crime_report = CrimeReport.objects.create(
#             crime_type=crime_type,
#             description=description,
#             address=address,
#             latitude=latitude,
#             longitude=longitude,
#             video=video,
#             reported_by=reported_by,
#             station=station,       # ✅ link to the selected station
#             severity_score=severity_score,
#             ai_status="Verified"
#         )

#         # Save uploaded photos
#         for photo in photos:
#             CrimePhoto.objects.create(
#                 crime_report=crime_report,
#                 photos=photo
#             )

#         # Broadcast live alert to channels
#         channel_layer = get_channel_layer()
#         async_to_sync(channel_layer.group_send)(
#             "crime_alerts",
#             {"type": "crime_message", "message": f"🚨 New Crime Reported: {crime_type} at {address}"}
#         )

#         return JsonResponse({
#             "success": True,
#             "message": "✅ Crime reported successfully!",
#             "severity_score": severity_score,
#             "report_id": crime_report.id
#         })

#     except PoliceStation.DoesNotExist:
#         return JsonResponse({
#             "success": False,
#             "message": "Selected police station does not exist!"
#         })

#     except Exception as e:
#         return JsonResponse({"success": False, "message": f"Error: {str(e)}"})

 ####Main verification###########
    
# from django.http import JsonResponse
# from django.views.decorators.csrf import csrf_exempt
# from asgiref.sync import async_to_sync
# from channels.layers import get_channel_layer
# from django.conf import settings
# from .models import CrimeReport, CrimePhoto

# from .ml_utils import predict_severity
# # from .utils_pkg.deepfake_detector import is_fake_image, is_fake_video

# import os

# MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


# @csrf_exempt
# def verify_evidence(request):
#     """
#     Step 2: Verify uploaded photos/videos using AI deepfake detection.
#     """
#     if request.method != "POST":
#         return JsonResponse({"success": False, "message": "Invalid request!"})

#     try:
#         photos = request.FILES.getlist("photos")
#         video = request.FILES.get("video")

#         # Validate file sizes
#         for media in photos + ([video] if video else []):
#             if media and media.size > MAX_FILE_SIZE:
#                 return JsonResponse({"success": False, "message": f"File '{media.name}' exceeds size limit."})

#         # Check photos
#         for photo in photos:
#             temp_path = os.path.join(settings.MEDIA_ROOT, "temp", photo.name)
#             os.makedirs(os.path.dirname(temp_path), exist_ok=True)
#             with open(temp_path, "wb+") as dest:
#                 for chunk in photo.chunks():
#                     dest.write(chunk)
#             if is_fake_image(temp_path):
#                 return JsonResponse({"success": False, "message": f"❌ Fake/AI-generated photo detected: {photo.name}"})

#         # Check video
#         if video:
#             temp_path = os.path.join(settings.MEDIA_ROOT, "temp", video.name)
#             os.makedirs(os.path.dirname(temp_path), exist_ok=True)
#             with open(temp_path, "wb+") as dest:
#                 for chunk in video.chunks():
#                     dest.write(chunk)
#             if is_fake_video(temp_path):
#                 return JsonResponse({"success": False, "message": f"❌ Fake/AI-generated video detected: {video.name}"})

#         return JsonResponse({"success": True, "message": "✅ All evidence verified as authentic."})

#     except Exception as e:
#         return JsonResponse({"success": False, "message": f"Error: {str(e)}"})

import json
import os
import io
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.utils import timezone
from django.contrib import messages
 
from .models import (
    CrimeReport, CrimePhoto, PoliceStation,
    userProfile, OfficerFeedback, InvestigationReport,
)
from .forms import OfficerFeedbackForm, InvestigationReportForm
from .evidence_analyzer import analyze_image, analyze_video_basic
from .ml_utils import predict_severity
 
 
# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 · EVIDENCE VERIFICATION  (replaces old verify_evidence)
# ─────────────────────────────────────────────────────────────────────────────
MAX_FILE_SIZE = 50 * 1024 * 1024   # 50 MB
 
@csrf_exempt
def verify_evidence(request):
    """
    Analyse uploaded photos/video for AI-generation signals.
    Returns per-file results so the frontend can show a detailed breakdown.
    Does NOT hard-block suspicious images — flags them so the SHO can decide.
    This mirrors real-world practice: a constable cannot unilaterally reject
    a citizen's report; a supervisor reviews flagged evidence.
    """
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Invalid request method."})
 
    photos = request.FILES.getlist("photos")
    video  = request.FILES.get("video")
 
    if not photos and not video:
        return JsonResponse({"success": False, "message": "No files uploaded."})
 
    photo_results = []
    any_blocked   = False   # only block if HARD evidence of AI (confidence ≥ 0.75)
 
    for photo in photos:
        if photo.size > MAX_FILE_SIZE:
            photo_results.append({
                "filename": photo.name,
                "status": "Blocked",
                "confidence": 1.0,
                "flags": [f"File too large ({photo.size // (1024*1024)} MB)"],
                "recommendation": "Re-upload a smaller image.",
            })
            any_blocked = True
            continue
 
        result = analyze_image(photo)
        photo_results.append({
            "filename":       photo.name,
            "status":         result.status,
            "confidence":     round(result.confidence * 100, 1),
            "flags":          result.flags,
            "recommendation": result.recommendation,
            "detail":         result.detail,
        })
        # Hard-block only high-confidence AI detections
        if result.confidence >= 0.75:
            any_blocked = True
 
    video_result = None
    if video:
        vr = analyze_video_basic(video)
        video_result = vr
        if not vr["ok"]:
            any_blocked = True
 
    # Store results in session so report_crime can persist them to DB
    request.session["evidence_analysis"] = {
        "photos": photo_results,
        "video": video_result,
    }
 
    # Summarise for frontend
    flagged_count  = sum(1 for r in photo_results if r["status"] == "Flagged")
    review_count   = sum(1 for r in photo_results if r["status"] == "Review")
    verified_count = sum(1 for r in photo_results if r["status"] == "Verified")
 
    return JsonResponse({
        "success":       not any_blocked,
        "blocked":       any_blocked,
        "summary": {
            "total":    len(photo_results),
            "verified": verified_count,
            "review":   review_count,
            "flagged":  flagged_count,
        },
        "photo_results": photo_results,
        "video_result":  video_result,
        "message": (
            "🚨 One or more files are strongly suspected to be AI-generated. "
            "Please upload authentic photos taken from your device camera."
        ) if any_blocked else (
            "✅ Evidence accepted. Suspicious items (if any) will be reviewed by the SHO."
            if (review_count or flagged_count) else
            "✅ All evidence verified as authentic."
        ),
    })
 
@csrf_exempt
def report_crime(request):
    """
    Creates CrimeReport + CrimePhoto records.
    Stores per-photo AI analysis results from the earlier verify step.
    """
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Invalid request."})
 
    try:
        crime_type  = request.POST.get("crime_type", "").strip()
        description = request.POST.get("description", "").strip()
        address     = request.POST.get("address", "Unknown").strip()
        latitude    = request.POST.get("latitude")
        longitude   = request.POST.get("longitude")
        station_id  = request.POST.get("station")
        video       = request.FILES.get("video")
        photos      = request.FILES.getlist("photos")
        reported_by = request.user if request.user.is_authenticated else None
 
        if not crime_type or not description:
            return JsonResponse({"success": False, "message": "Crime type and description are required."})
 
        # Station lookup
        station = None
        if station_id:
            try:
                station = PoliceStation.objects.get(id=station_id)
            except PoliceStation.DoesNotExist:
                return JsonResponse({"success": False, "message": "Selected police station does not exist."})
 
        # Duplicate guard
        if CrimeReport.objects.filter(
            crime_type=crime_type, description=description,
            address=address, station=station,
            reported_by=reported_by,
        ).exists():
            return JsonResponse({"success": False, "message": "This report already exists in our system."})
 
        severity_score = predict_severity(crime_type, description, address)
 
        # Retrieve evidence analysis from session
        evidence_analysis = request.session.pop("evidence_analysis", {})
        photo_analyses    = evidence_analysis.get("photos", [])
 
        # Determine overall AI status for the report
        has_flagged = any(p.get("status") == "Flagged" for p in photo_analyses)
        has_review  = any(p.get("status") == "Review"  for p in photo_analyses)
        ai_status   = "Flagged" if has_flagged else ("Review" if has_review else "Verified")
 
        crime_report = CrimeReport.objects.create(
            crime_type=crime_type,
            description=description,
            address=address,
            latitude=latitude   or 0,
            longitude=longitude or 0,
            video=video,
            reported_by=reported_by,
            station=station,
            severity_score=severity_score,
            ai_status=ai_status,
            ai_progress=100,
        )
 
        # Save photos with their individual AI results
        for i, photo in enumerate(photos):
            analysis = photo_analyses[i] if i < len(photo_analyses) else {}
            CrimePhoto.objects.create(
                crime_report=crime_report,
                photos=photo,
                verification_status=analysis.get("status", "Pending"),
                is_ai_generated=(analysis.get("status") == "Flagged"),
                deepfake_suspected=(analysis.get("confidence", 0) >= 50),
                ai_confidence_score=analysis.get("confidence", 0) / 100,
            )
 
        # WebSocket broadcast (existing code kept intact)
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                "crime_alerts",
                {"type": "crime_message",
                 "message": f"🚨 New Crime Reported: {crime_type} at {address}"}
            )
        except Exception:
            pass  # Don't fail the report if WebSocket is unavailable
 
        return JsonResponse({
            "success": True,
            "message": "✅ Crime reported successfully! You can track its status from your dashboard.",
            "severity_score": severity_score,
            "report_id": crime_report.id,
            "ai_status": ai_status,
        })
 
    except Exception as e:
        return JsonResponse({"success": False, "message": f"Unexpected error: {str(e)}"})
 


# @login_required
def admin_report(request):
    reports = CrimeReport.objects.filter(status="Pending")  # Get all pending reports

    for report in reports:
        # Approve each report
        report.is_approved = True

        # Assign a police officer based on the report's address
        officer = userProfile.objects.filter(role='police', location=report.address).first()

        if officer:
            report.assigned_officer = officer
    
        report.save()  # Save each report after assignment

    print("Pending Reports:", reports)  # Print all pending reports for debugging
    return render(request, "admin_report.html", {'reports': reports})

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import CrimeReport

@csrf_exempt
def approve_crime(request, report_id):
    if request.method == "POST":
        report = CrimeReport.objects.get(id=report_id)
        report.status = "Approved"
        report.save()
        return JsonResponse({"message": "Report approved successfully!"})

@csrf_exempt
def reject_crime(request, report_id):
    if request.method == "POST":
        report = CrimeReport.objects.get(id=report_id)
        report.status = "Rejected"
        report.delete()
        return JsonResponse({"message": "Report rejected successfully!"})

@csrf_exempt
def view_evidence(request, report_id):
    if request.method == "GET":
        try:
            report = CrimeReport.objects.get(id=report_id)
            # Get video URL if available
            video_url = report.video.url if report.video else None

            # Get photo URLs; assuming you use CrimePhoto with related_name='photos'
            # Adjust field name as per your model definition.
            photo_urls = [photo.photos.url for photo in report.photos.all()]  # if your field is named 'photos'
            # If you named it 'photo_file', then use: 
            # photo_urls = [photo.photo_file.url for photo in report.photos.all()]

            return JsonResponse({
                "video_url": video_url,
                "photo_urls": photo_urls
            })
        except CrimeReport.DoesNotExist:
            return JsonResponse({"error": "Report not found"}, status=404)
    return JsonResponse({"error": "Invalid request"}, status=400)

from django.shortcuts import render
from django.utils import timezone 

#approved cases(Admin)
# home/views.py

from django.shortcuts import redirect
from django.contrib import messages

def _require_sho(request):
    try:
        profile = request.user.userprofile
        if profile.role != "sho":
            messages.error(request, "Access denied")
            return None, redirect("login")
        return profile, None
    except:
        return None, redirect("login")

from django.utils import timezone
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import CrimeReport, userProfile
from .utils import officer_score
from home.templatetags.custom_filters import station_in_address   # ← import filter here
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone
from .models import CrimeReport, userProfile
 # make sure these exist

from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.contrib import messages
from .models import CrimeReport, userProfile

@login_required
def sho_approved_cases(request):
    """
    Single view that handles every case queue the SHO needs to see:
 
    Tab 1 — Pending Approval   : citizen submitted, SHO must approve/reject
    Tab 2 — Assign Officer     : approved but not yet assigned
    Tab 3 — Awaiting Review    : officer filed investigation report, SHO must sign off
    Tab 4 — Active Cases       : under investigation (monitoring view)
    Tab 5 — Resolved           : closed cases this month
    """
    sho, err = _require_sho(request)
    if err:
        return err
 
    station  = sho.station
    base_qs  = CrimeReport.objects.filter(station=station).select_related(
        "reported_by", "assigned_officer__user", "station"
    ).prefetch_related("photos")
 
    # ── Each queue ────────────────────────────────────────────────────────────
    pending_reports    = base_qs.filter(status="Pending").order_by("-reported_at")
 
    unassigned_reports = base_qs.filter(
        status="Approved", assigned_officer__isnull=True
    ).order_by("-reported_at")
 
    awaiting_inv       = base_qs.filter(
        resolution_status="Awaiting Approval"
    ).order_by("-reported_at")
 
    active_cases       = base_qs.filter(
        resolution_status="Under Investigation"
    ).order_by("-reported_at")
 
    resolved_cases     = base_qs.filter(
        resolution_status="Resolved"
    ).order_by("-resolved_at")[:30]   # last 30
 
    # ── Officers for assignment (scored per-report later in template) ─────────
    officers = userProfile.objects.filter(
        role="police", is_approved=True, station=station
    ).select_related("user")
 
    # Attach scored officer list to each unassigned report
    for rpt in unassigned_reports:
        scored = [(o, officer_score(o, rpt.crime_type)) for o in officers]
        scored.sort(key=lambda x: x[1], reverse=True)
        rpt.scored_officers = scored   # list of (officer, score) tuples
 
    # Attach investigation report to awaiting_inv items
    for rpt in awaiting_inv:
        rpt.inv = getattr(rpt, "investigation_report", None)
 
    # ── Active tab from query string (default = first non-empty queue) ────────
    counts = {
        "pending":    pending_reports.count(),
        "unassigned": unassigned_reports.count(),
        "inv_review": awaiting_inv.count(),
        "active":     active_cases.count(),
        "resolved":   resolved_cases.count(),  # using len since already sliced
    }
 
    # Default: send SHO to the most urgent non-zero tab
    default_tab = "pending"
    for tab in ("pending", "unassigned", "inv_review", "active", "resolved"):
        if counts[tab] > 0:
            default_tab = tab
            break
 
    active_tab = request.GET.get("tab", default_tab)
 
    return render(request, "sho_approved_cases.html", {
        "sho":              sho,
        "station":          station,
        "pending_reports":  pending_reports,
        "unassigned_reports": unassigned_reports,
        "awaiting_inv":     awaiting_inv,
        "active_cases":     active_cases,
        "resolved_cases":   resolved_cases,
        "counts":           counts,
        "active_tab":       active_tab,
    })

# ─────────────────────────────────────────────────────────────────────────────
@login_required
def sho_approve_report(request, report_id):
    """
    SHO approves or rejects a pending citizen crime report.
    Approve → status = "Approved"  (moves to assignment queue)
    Reject  → status = "Rejected"  (citizen notified, report archived)
    """
    sho, err = _require_sho(request)
    if err:
        return err
 
    report   = get_object_or_404(CrimeReport, id=report_id, station=sho.station)
 
    if request.method == "POST":
        decision        = request.POST.get("decision")       # "approve" or "reject"
        rejection_note  = request.POST.get("rejection_note", "").strip()
 
        if decision == "approve":
            report.status = "Approved"
            report.save(update_fields=["status"])
            messages.success(request, f"Report #{report.id} approved — ready for assignment.")
 
        elif decision == "reject":
            report.status = "Rejected"
            # Store rejection reason as an internal note (reusing ai_status field would
            # be wrong — store in description suffix or add a rejection_note field.
            # For now we append to description as a SHO note prefix):
            if rejection_note:
                report.description = f"[SHO Rejection Note: {rejection_note}]\n\n{report.description}"
            report.save(update_fields=["status", "description"])
            messages.warning(request, f"Report #{report.id} rejected.")
 
        else:
            messages.error(request, "Invalid decision.")
 
    return redirect(f"{request.META.get('HTTP_REFERER', '/SHO_dashboard/sho_approved_cases')}?tab=pending")
 
 
# ─────────────────────────────────────────────────────────────────────────────
# SHO ASSIGNS OFFICER  (clean extracted endpoint)
# ─────────────────────────────────────────────────────────────────────────────
@login_required
def sho_assign_officer(request, report_id):
    """
    SHO assigns an officer to an approved, unassigned report.
    Also increments officer's active_case_count.
    """
    sho, err = _require_sho(request)
    if err:
        return err
 
    if request.method == "POST":
        report     = get_object_or_404(CrimeReport, id=report_id, station=sho.station)
        officer_id = request.POST.get("officer_id")
        officer    = get_object_or_404(userProfile, id=officer_id, station=sho.station)
 
        9
 
        # Unassign previous officer if re-assigning
        if report.assigned_officer and report.assigned_officer != officer:
            prev = report.assigned_officer
            if prev.active_case_count > 0:
                prev.active_case_count -= 1
                prev.save(update_fields=["active_case_count"])
 
        report.assigned_officer = officer
        report.assigned_at      = timezone.now()
        report.resolution_status = "Pending"   # officer must accept/start it
        report.save(update_fields=["assigned_officer", "assigned_at", "resolution_status"])
 
        officer.active_case_count += 1
        officer.save(update_fields=["active_case_count"])
 
        messages.success(request, f"Case #{report.id} assigned to Officer {officer.full_name}.")
 
    return redirect(f"/SHO_dashboard/sho_approved_cases?tab=unassigned")
 
    
def live_crime_alerts(request):
    return render(request, 'crime_alerts.html')

def update_report_status(request, report_id):
    """
    Officer changes resolution status.
    Allowed transitions enforced server-side.
    """
    if request.method != "POST":
        return redirect("police_dashboard")
 
    report = get_object_or_404(CrimeReport, id=report_id)
 
    # Auth check
    profile = getattr(request.user, "userprofile", None)
    if not profile or profile.role not in ("police", "sho"):
        messages.error(request, "Unauthorised.")
        return redirect("police_dashboard")
 
    if report.assigned_officer != profile and profile.role != "sho":
        messages.error(request, "You are not assigned to this case.")
        return redirect("police_dashboard")
 
    new_status = request.POST.get("resolution_status")
 
    ALLOWED = {
        "Pending":            ["Under Investigation"],
        "Under Investigation": ["Awaiting Approval"],
        "Awaiting Approval":  [],   # SHO must act; officer cannot self-advance
        "Resolved":           [],
    }
 
    current = report.resolution_status
 
    if new_status not in ALLOWED.get(current, []):
        messages.error(request, f"Cannot move from '{current}' to '{new_status}'.")
        return redirect("police_dashboard")
 
    # Stamp timestamps
    if current == "Pending" and new_status == "Under Investigation":
        if not report.first_touched_at:
            report.first_touched_at = timezone.now()
 
    report.resolution_status = new_status
    report.save(update_fields=["resolution_status", "first_touched_at"])
    messages.success(request, f"Status updated to '{new_status}'.")
    return redirect("police_dashboard")
 
 
@login_required
def submit_investigation(request, report_id):
    """
    Officer files a formal InvestigationReport for SHO review.
    This replaces the "I clicked Resolved" anti-pattern with a real workflow.
    """
    report  = get_object_or_404(CrimeReport, id=report_id)
    profile = get_object_or_404(userProfile, user=request.user)
 
    if report.assigned_officer != profile:
        messages.error(request, "You are not assigned to this case.")
        return redirect("police_dashboard")
 
    # Only allow if under investigation or already awaiting approval (re-submit)
    if report.resolution_status not in ("Under Investigation", "Awaiting Approval"):
        messages.error(request, "Case must be under investigation to file a report.")
        return redirect("police_dashboard")
 
    existing = InvestigationReport.objects.filter(crime_report=report).first()
 
    if request.method == "POST":
        form = InvestigationReportForm(request.POST, instance=existing)
        if form.is_valid():
            inv        = form.save(commit=False)
            inv.crime_report = report
            inv.officer      = profile
            inv.sho_approved = None    # Reset approval on re-submit
            inv.save()
 
            report.resolution_status = "Awaiting Approval"
            report.save(update_fields=["resolution_status"])
 
            messages.success(request, "Investigation report submitted to SHO for review.")
            return redirect("police_dashboard")
    else:
        form = InvestigationReportForm(instance=existing)
 
    return render(request, "submit_investigation.html", {
        "form":   form,
        "report": report,
    })


######main update report status ##
# from django.shortcuts import get_object_or_404, redirect
# from django.utils import timezone
# from django.contrib import messages
# from .models import CrimeReport, InvestigationReport

# def update_report_status(request, report_id):
#     if request.method == "POST":
#         report = get_object_or_404(CrimeReport, id=report_id)

#         # Ensure only police can access
#         if not hasattr(request.user, "userprofile") or request.user.userprofile.role != "police":
#             messages.error(request, "Unauthorized action.")
#             return redirect("police_dashboard")

#         new_status = request.POST.get("resolution_status")

#         # Stamp first touch
#         if report.first_touched_at is None:
#             report.first_touched_at = timezone.now()

#         allowed_transitions = {
#             "Pending": ["Under Investigation"],
#             "Under Investigation": ["Awaiting Approval"],
#             "Awaiting Approval": [],
#             "Resolved": []
            
#         }

#         # Prevent direct resolution
#         if new_status == "Resolved":
#             messages.error(request, "Police cannot directly resolve case. Submit for approval.")
#             return redirect("police_dashboard")

#         # Validate transition
#         if new_status not in allowed_transitions.get(report.resolution_status, []):
#             messages.error(request, "Invalid status transition.")
#             return redirect("police_dashboard")

#         report.resolution_status = new_status
#         report.save(update_fields=["first_touched_at", "resolution_status"])

#         messages.success(request, "Status updated successfully.")

#     return redirect("police_dashboard")


@login_required
def sho_review_investigation(request, report_id):
    """
    SHO approves or rejects an officer's investigation report.
    Approve → resolution_status = Resolved, resolved_at stamped.
    Reject  → resolution_status = Under Investigation (sent back to officer).
    """
    profile = get_object_or_404(userProfile, user=request.user)
    if profile.role != "sho":
        messages.error(request, "Only SHO can review investigation reports.")
        return redirect("sho_approved_cases")
 
    report = get_object_or_404(CrimeReport, id=report_id, station=profile.station)
    inv    = get_object_or_404(InvestigationReport, crime_report=report)
 
    if request.method == "POST":
        decision = request.POST.get("decision")   # "approve" or "reject"
        note     = request.POST.get("note", "").strip()
 
        if decision == "approve":
            inv.sho_approved = True
            inv.reviewed_at  = timezone.now()
            inv.save()
 
            report.resolution_status = "Resolved"
            report.resolved_at       = timezone.now()
            # Decrement officer active case count
            officer = report.assigned_officer
            if officer and officer.active_case_count > 0:
                officer.active_case_count -= 1
                officer.save(update_fields=["active_case_count"])
            report.save(update_fields=["resolution_status", "resolved_at"])
 
            messages.success(request, "Case marked as Resolved.")
 
        elif decision == "reject":
            inv.sho_approved = False
            inv.reviewed_at  = timezone.now()
            # Store SHO feedback in evidence_notes if provided
            if note:
                inv.evidence_notes = (inv.evidence_notes or "") + f"\n\nSHO Feedback: {note}"
            inv.save()
 
            report.resolution_status = "Under Investigation"
            report.save(update_fields=["resolution_status"])
 
            messages.warning(request, "Case returned to officer for further investigation.")
 
        return redirect("sho_approved_cases")
 
    return render(request, "sho_review_investigation.html", {
        "report": report,
        "inv":    inv,
    })
 
@login_required
def officer_case_detail(request, report_id):
    """
    Full case detail page for the assigned officer:
    - All evidence with per-photo AI analysis results
    - Timeline of status changes
    - InvestigationReport form (if not filed yet)
    """
    profile = get_object_or_404(userProfile, user=request.user)
    report  = get_object_or_404(CrimeReport, id=report_id, assigned_officer=profile)
 
    photos     = report.photos.all()
    timeline   = _build_report_timeline(report)
    inv        = getattr(report, "investigation_report", None)
    inv_form   = InvestigationReportForm(instance=inv) if inv else InvestigationReportForm()
 
    return render(request, "officer_case_detail.html", {
        "report":   report,
        "photos":   photos,
        "timeline": timeline,
        "inv":      inv,
        "inv_form": inv_form,
    })

def submit_investigation_report(request, report_id):
    if request.method == "POST":
        report = get_object_or_404(CrimeReport, id=report_id)

        if request.user.userprofile.role != "police":
            return redirect("police_dashboard")

        summary = request.POST.get("summary")
        action_taken = request.POST.get("action_taken")
        evidence_notes = request.POST.get("evidence_notes")

        InvestigationReport.objects.update_or_create(
            crime_report=report,
            defaults={
                "officer": request.user.userprofile,
                "summary": summary,
                "action_taken": action_taken,
                "evidence_notes": evidence_notes,
            }
        )

        report.resolution_status = "Awaiting Approval"
        report.save(update_fields=["resolution_status"])

    return redirect("police_dashboard")

def approve_case_closure(request, report_id):
    if request.method == "POST":
        report = get_object_or_404(CrimeReport, id=report_id)

        if request.user.userprofile.role != "sho":
            return redirect("sho_dashboard")

        if report.resolution_status != "Awaiting Approval":
            return redirect("sho_dashboard")

        investigation = getattr(report, "investigation_report", None)
        if not investigation:
            return redirect("sho_dashboard")

        report.resolution_status = "Resolved"
        report.resolved_at = timezone.now()
        report.save(update_fields=["resolution_status", "resolved_at"])

        investigation.sho_approved = True
        investigation.reviewed_at = timezone.now()
        investigation.save(update_fields=["sho_approved", "reviewed_at"])

    return redirect("sho_dashboard")

def reject_case_closure(request, report_id):
    if request.method == "POST":
        report = get_object_or_404(CrimeReport, id=report_id)

        if request.user.userprofile.role != "sho":
            return redirect("sho_dashboard")

        if report.resolution_status != "Awaiting Approval":
            return redirect("sho_dashboard")

        investigation = getattr(report, "investigation_report", None)
        if investigation:
            investigation.sho_approved = False
            investigation.reviewed_at = timezone.now()
            investigation.save(update_fields=["sho_approved", "reviewed_at"])

        report.resolution_status = "Under Investigation"
        report.save(update_fields=["resolution_status"])

    return redirect("sho_dashboard")


@login_required
def crime_report_status(request):
    """
    Shows citizen their reports with:
    - Full status timeline (audit trail from InvestigationReport + status changes)
    - Assigned officer details
    - AI evidence analysis results
    - Feedback form (only when resolved)
    """
    reports = CrimeReport.objects.filter(
        reported_by=request.user
    ).prefetch_related("photos").select_related("assigned_officer__user", "station")
 
    # Handle feedback POST
    if request.method == "POST":
        report_id = request.POST.get("report_id")
        report    = get_object_or_404(CrimeReport, id=report_id, reported_by=request.user)
        form      = OfficerFeedbackForm(request.POST)
        if form.is_valid():
            fb = form.save(commit=False)
            fb.crime_report = report
            fb.officer      = report.assigned_officer
            fb.save()
            messages.success(request, "Thank you for your feedback!")
        return redirect("crime_report_status")
 
    report_data = []
    for rpt in reports:
        fb   = OfficerFeedback.objects.filter(crime_report=rpt).first()
        form = None
        if rpt.resolution_status == "Resolved" and fb is None and rpt.assigned_officer:
            form = OfficerFeedbackForm()
 
        # Build timeline entries
        timeline = _build_report_timeline(rpt)
 
        # AI evidence summary for this report
        photos = rpt.photos.all()
        evidence_summary = {
            "total":    photos.count(),
            "verified": photos.filter(verification_status="Verified").count(),
            "review":   photos.filter(verification_status="Review").count(),
            "flagged":  photos.filter(verification_status="Flagged").count(),
        }
 
        # Investigation report (if officer filed one)
        inv_report = getattr(rpt, "investigation_report", None)
 
        report_data.append({
            "report":           rpt,
            "form":             form,
            "feedback":         fb,
            "timeline":         timeline,
            "evidence_summary": evidence_summary,
            "investigation":    inv_report,
        })
 
    return render(request, "crime_report_status.html", {"report_data": report_data})
 
 
def _build_report_timeline(report):
    """
    Returns a list of timeline dicts for a report.
    Reconstructed from stored timestamps — no extra model needed.
    """
    entries = []
 
    entries.append({
        "status":      "Submitted",
        "label":       "Report Submitted",
        "description": f"You reported a {report.crime_type} at {report.address}.",
        "timestamp":   report.reported_at,
        "icon":        "📝",
        "color":       "blue",
    })
 
    if report.status == "Approved":
        entries.append({
            "status":      "Approved",
            "label":       "Report Approved",
            "description": "Your report was reviewed and approved by the admin.",
            "timestamp":   None,
            "icon":        "✅",
            "color":       "green",
        })
    elif report.status == "Rejected":
        entries.append({
            "status":      "Rejected",
            "label":       "Report Rejected",
            "description": "Your report was rejected. Contact the station if you believe this is an error.",
            "timestamp":   None,
            "icon":        "❌",
            "color":       "red",
        })
        return entries
 
    if report.assigned_officer:
        entries.append({
            "status":      "Assigned",
            "label":       "Officer Assigned",
            "description": f"Officer {report.assigned_officer.full_name} has been assigned to your case.",
            "timestamp":   report.assigned_at,
            "icon":        "👮",
            "color":       "teal",
        })
 
    if report.first_touched_at:
        entries.append({
            "status":      "Under Investigation",
            "label":       "Investigation Started",
            "description": "The officer has begun working on your case.",
            "timestamp":   report.first_touched_at,
            "icon":        "🔍",
            "color":       "amber",
        })
 
    inv = getattr(report, "investigation_report", None)
    if inv:
        entries.append({
            "status":      "Report Filed",
            "label":       "Investigation Report Filed",
            "description": "The officer has filed a formal investigation report and submitted it for SHO approval.",
            "timestamp":   inv.submitted_at,
            "icon":        "📋",
            "color":       "purple",
        })
        if inv.sho_approved is True:
            entries.append({
                "status":      "SHO Approved",
                "label":       "SHO Approved Resolution",
                "description": "The Station House Officer has reviewed and approved the investigation outcome.",
                "timestamp":   inv.reviewed_at,
                "icon":        "⭐",
                "color":       "green",
            })
        elif inv.sho_approved is False:
            entries.append({
                "status":      "Returned",
                "label":       "Returned for Re-investigation",
                "description": "The SHO has sent this case back to the officer for further action.",
                "timestamp":   inv.reviewed_at,
                "icon":        "↩️",
                "color":       "orange",
            })
 
    if report.resolution_status == "Resolved":
        entries.append({
            "status":      "Resolved",
            "label":       "Case Resolved",
            "description": "Your case has been officially closed.",
            "timestamp":   report.resolved_at,
            "icon":        "🏁",
            "color":       "green",
        })
 
    return entries

########### main crime_report_status ##############
# from django.shortcuts import render, redirect, get_object_or_404
# from .models import CrimeReport, OfficerFeedback
# from .forms import OfficerFeedbackForm
# from django.contrib.auth.decorators import login_required
# #report tracking 

# @login_required
# def crime_report_status(request):
#     # Redirect anonymous
#     if not request.user.is_authenticated:
#         return redirect('login')
        
#     reports = CrimeReport.objects.filter(reported_by=request.user)

#     # handle feedback submission
#     if request.method == 'POST':
#         report_id = request.POST.get('report_id')
#         report = get_object_or_404(CrimeReport, id=report_id, reported_by=request.user)
#         form = OfficerFeedbackForm(request.POST, prefix=str(report.id))
#         if form.is_valid():
#             fb = form.save(commit=False)
#             fb.crime_report = report
#             fb.officer = report.assigned_officer
#             fb.save()
#             return redirect('crime_report_status')

#     # build list of { report, form, feedback }
#     report_data = []
#     for rpt in reports:
#         fb = OfficerFeedback.objects.filter(crime_report=rpt).first()
#         if rpt.resolution_status == "Resolved" and fb is None:
#             form = OfficerFeedbackForm(prefix=str(rpt.id))
#         else:
#             form = None
#         report_data.append({
#             'report': rpt,
#             'form': form,
#             'feedback': fb
#         })

#     return render(request, 'crime_report_status.html', {
#         'report_data': report_data
#     })

from django.http import JsonResponse
from .models import CrimeReport

def get_reports(request):
    reports = CrimeReport.objects.all().values('id', 'crime_type', 'description', 'latitude', 'longitude', 'video', 'status')
    reports_list = list(reports)
    
    # Append full video URL for frontend
    for report in reports_list:
        report['video_url'] = request.build_absolute_uri('/media/' + report['video'])

    return JsonResponse(reports_list, safe=False)

import json
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .models import CrimeReport

@csrf_exempt
def update_status(request, report_id):
    if request.method == 'POST':
        data = json.loads(request.body)
        status = data.get('status')
        
        try:
            report = CrimeReport.objects.get(id=report_id)
            report.status = status
            if astatus == "Solved" and not report.resolved_at:
                report.resolved_at = timezone.now()

            report.save()
            return JsonResponse({'message': f'Report {status} successfully!'})
        except CrimeReport.DoesNotExist:
            return JsonResponse({'error': 'Report not found'}, status=404)


from django.http import JsonResponse
from .models import CrimeReport

def get_approved_reports(request):
    reports = CrimeReport.objects.filter(status='Approved').values('id', 'crime_type', 'description', 'latitude', 'longitude', 'video', 'status')
    reports_list = list(reports)

    # Append full video URL for frontend
    for report in reports_list:
        report['video_url'] = request.build_absolute_uri('/media/' + report['video'])

    return JsonResponse(reports_list, safe=False)


import json
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .models import CrimeReport

@csrf_exempt
def update_case_status(request, report_id):
    if request.method == 'POST':
        data = json.loads(request.body)
        status = data.get('status')
        
        try:
            report = CrimeReport.objects.get(id=report_id, status='Approved')
            report.status = status
            report.save()
            return JsonResponse({'message': f'Case status updated to {status}!'})
        except CrimeReport.DoesNotExist:
            return JsonResponse({'error': 'Case not found'}, status=404)


# from django.http import JsonResponse
# from django.contrib.auth.models import User
# from .models import CrimeReport
# from channels.layers import get_channel_layer
# from asgiref.sync import async_to_sync
# import json

# def assign_case(request):
#     if request.method == "POST":
#         data = json.loads(request.body)
#         report_id = data.get("report_id")
#         officer_id = data.get("officer_id")

#         try:
#             report = CrimeReport.objects.get(id=report_id)
#             officer = User.objects.get(id=officer_id)

#             report.assigned_officer = officer
#             report.status = "In Progress"
#             report.save()

#             # Notify the police officer
#             channel_layer = get_channel_layer()
#             async_to_sync(channel_layer.group_send)(
#                 f"user_{officer_id}",
#                 {
#                     "type": "send_notification",
#                     "message": f"New case assigned: {report.crime_type}",
#                     "type": "warning",
#                 }
#             )

#             return JsonResponse({"message": "Case assigned successfully!"})
#         except CrimeReport.DoesNotExist:
#             return JsonResponse({"message": "Report not found!"}, status=400)
#         except User.DoesNotExist:
#             return JsonResponse({"message": "Officer not found!"}, status=400)

#     return JsonResponse({"message": "Invalid request!"}, status=400)

# import json
# from django.http import JsonResponse
# from django.views.decorators.csrf import csrf_exempt
# from .models import CrimeReport, Notification  # Assuming you have a Notification model

# @csrf_exempt
# def update_status(request):
#     if request.method == "POST":
#         data = json.loads(request.body)
#         report_id = data.get("report_id")
#         new_status = data.get("status")

#         try:
#             report = CrimeReport.objects.get(id=report_id)
#             report.status = new_status
#             report.save()

#             # Save notification for the user
#             Notification.objects.create(
#                 user=report.user, 
#                 message=f"Your report ({report.crime_type}) is now {new_status}"
#             )

#             return JsonResponse({"message": "Case status updated successfully!"})
#         except CrimeReport.DoesNotExist:
#             return JsonResponse({"message": "Report not found!"}, status=400)

#     return JsonResponse({"message": "Invalid request!"}, status=400)
from django.shortcuts import render
import pandas as pd
import json
import os
from django.conf import settings
import requests
import math

def get_color(count, min_count, max_count):
    # Create a color scale from green (low) to red (high)
    if min_count == max_count:
        ratio = 0.5
    else:
        ratio = (count - min_count) / (max_count - min_count)
    
    # Convert to hex color from green to red
    if ratio <= 0.5:
        # Green to Yellow
        r = int(255 * (2 * ratio))
        g = 255
    else:
        # Yellow to Red
        r = 255
        g = int(255 * (2 * (1 - ratio)))
    
    return f'#{r:02x}{g:02x}00'

def get_fixed_coordinates(city, state):
    if state == 'Maharashtra':
        # Fixed coordinates for Mumbai metropolitan cities
        maharashtra_coordinates = {
            'Thane': (19.2183, 72.9781),
            'Navi Mumbai': (19.0330, 73.0297),
            'Kalyan': (19.2403, 73.1305),
            'Dombivli': (19.2190, 73.0930),
            'Vasai': (19.3919, 72.8397),
            'Mira Bhayandar': (19.2952, 72.8547),
            'Bhiwandi': (19.2962, 73.0526)
        }
        return maharashtra_coordinates.get(city, None)
    
    elif state == 'Uttar Pradesh':
        # Fixed coordinates for UP cities with accurate locations
        up_coordinates = {
            'Lucknow': (26.8467, 80.9462),
            'Kanpur': (26.4499, 80.3319),
            'Agra': (27.1767, 78.0081),
            'Varanasi': (25.3176, 82.9739),
            'Prayagraj': (25.4358, 81.8463),
            'Ghaziabad': (28.6692, 77.4538),
            'Noida': (28.5355, 77.3910),
            'Meerut': (28.9845, 77.7064),
            'Bareilly': (28.3670, 79.4304),
            'Aligarh': (27.8974, 78.0880),
            'Moradabad': (28.8387, 78.7733),
            'Saharanpur': (29.9680, 77.5552),
            'Gorakhpur': (26.7606, 83.3732),
            'Faizabad': (26.7732, 82.1442),
            'Jhansi': (25.4484, 78.5685),
            'Muzaffarnagar': (29.4727, 77.7085),
            'Mathura': (27.4924, 77.6737),
            'Barabanki': (26.9320, 81.1932),  # Updated coordinates
            'Malihabad': (26.9242, 80.7089),  # Updated coordinates
            'Kakori': (26.8778, 80.8071),     # Updated coordinates
            'Bakshi Ka Talab': (27.0239, 80.9167),  # Updated coordinates
            'Chinhat': (26.8751, 81.0275),    # Updated coordinates
            'Gosainganj': (26.7758, 81.1203)  # Updated coordinates
        }
        return up_coordinates.get(city, None)
    
    return None

def adjust_overlapping_coordinates(df):
    adjusted_df = df.copy()
    
    # First, apply fixed coordinates for known cities
    for idx, row in adjusted_df.iterrows():
        fixed_coords = get_fixed_coordinates(row['City'], row['State'])
        if fixed_coords:
            adjusted_df.at[idx, 'Latitude'] = fixed_coords[0]
            adjusted_df.at[idx, 'Longitude'] = fixed_coords[1]
    
    # Then handle any remaining overlaps with the circular pattern
    coord_groups = adjusted_df.groupby(['Latitude', 'Longitude'])
    offset = 0.02  # Approximately 2km offset
    
    for (lat, lon), group in coord_groups:
        if len(group) > 1:
            # If there are still multiple cities at these coordinates
            for i, idx in enumerate(group.index):
                if i > 0:  # Skip the first city
                    angle = (360 / len(group)) * i
                    rad_angle = math.radians(angle)
                    lat_offset = offset * math.cos(rad_angle)
                    lon_offset = offset * math.sin(rad_angle)
                    adjusted_df.at[idx, 'Latitude'] = lat + lat_offset
                    adjusted_df.at[idx, 'Longitude'] = lon + lon_offset
    
    return adjusted_df

def crime_map(request):
    try:
        # Read the CSV file
        csv_path = 'home/crime_data.csv'
        df = pd.read_csv(csv_path)
        
        # Print unique cities for UP
        up_cities = df[df['State'] == 'Uttar Pradesh']['City'].unique()
        print("\nUnique cities in Uttar Pradesh:")
        print(sorted(up_cities))
        
        # Calculate state-level crime counts
        state_crime_counts = df.groupby('State').size().reset_index(name='count')
        crime_types_by_state = df.groupby(['State', 'Crime Type']).size().reset_index(name='type_count')
        
        # Calculate city-level crime counts with correct coordinates
        city_crime_counts = df.groupby(['State', 'City']).agg({
            'Latitude': 'first',  # Take the first occurrence of coordinates
            'Longitude': 'first',
        }).reset_index()
        
        # Add count column separately
        city_counts = df.groupby(['State', 'City']).size().reset_index(name='count')
        city_crime_counts = city_crime_counts.merge(city_counts, on=['State', 'City'])
        
        # Adjust coordinates for overlapping cities
        city_crime_counts = adjust_overlapping_coordinates(city_crime_counts)
        
        crime_types_by_city = df.groupby(['State', 'City', 'Crime Type']).size().reset_index(name='type_count')
        
        # Get min and max counts for color scaling (state level)
        state_min_count = state_crime_counts['count'].min()
        state_max_count = state_crime_counts['count'].max()
        
        # Get min and max counts for color scaling (city level)
        city_min_count = city_crime_counts['count'].min()
        city_max_count = city_crime_counts['count'].max()
        
        # Process state data
        state_data = {}
        for _, row in state_crime_counts.iterrows():
            state_name = row['State']
            # Get crime types for this state
            state_crime_types = crime_types_by_state[crime_types_by_state['State'] == state_name]
            crime_types_dict = {}
            for _, type_row in state_crime_types.iterrows():
                crime_types_dict[type_row['Crime Type']] = int(type_row['type_count'])
            
            # Get cities for this state
            state_cities = city_crime_counts[city_crime_counts['State'] == state_name]
            cities_data = []
            
            # Print debug info for UP
            if state_name == 'Uttar Pradesh':
                print("\nProcessing Uttar Pradesh cities:")
            
            for _, city_row in state_cities.iterrows():
                city_name = city_row['City']
                
                if state_name == 'Uttar Pradesh':
                    print(f"City: {city_name}, Lat: {city_row['Latitude']}, Long: {city_row['Longitude']}, Count: {city_row['count']}")
                
                # Get crime types for this city
                city_crime_types = crime_types_by_city[
                    (crime_types_by_city['State'] == state_name) & 
                    (crime_types_by_city['City'] == city_name)
                ]
                city_crime_types_dict = {}
                for _, city_type_row in city_crime_types.iterrows():
                    city_crime_types_dict[city_type_row['Crime Type']] = int(city_type_row['type_count'])
                
                cities_data.append({
                    'name': city_name,
                    'count': int(city_row['count']),
                    'latitude': float(city_row['Latitude']),
                    'longitude': float(city_row['Longitude']),
                    'color': get_color(city_row['count'], city_min_count, city_max_count),
                    'crime_types': city_crime_types_dict
                })
            
            state_data[state_name] = {
                'count': int(row['count']),
                'color': get_color(row['count'], state_min_count, state_max_count),
                'crime_types': crime_types_dict,
                'cities': cities_data
            }
        
        # Get India GeoJSON data
        india_geojson_url = "https://raw.githubusercontent.com/geohacker/india/master/state/india_state.geojson"
        response = requests.get(india_geojson_url)
        india_geojson = response.json()
        
        # Add crime data to GeoJSON properties
        for feature in india_geojson['features']:
            state_name = feature['properties']['NAME_1']
            if state_name in state_data:
                feature['properties']['crime_count'] = state_data[state_name]['count']
                feature['properties']['fill_color'] = state_data[state_name]['color']
                feature['properties']['crime_types'] = state_data[state_name]['crime_types']
                feature['properties']['cities'] = state_data[state_name]['cities']
            else:
                feature['properties']['crime_count'] = 0
                feature['properties']['fill_color'] = '#808080'  # Gray for states with no data
                feature['properties']['crime_types'] = {}
                feature['properties']['cities'] = []
        
        # Convert to JSON string
        map_data = {
            'geojson': india_geojson,
            'state_min_count': int(state_min_count),
            'state_max_count': int(state_max_count),
            'city_min_count': int(city_min_count),
            'city_max_count': int(city_max_count)
        }
        
        return render(request, 'crime_map.html', {
            'map_data': json.dumps(map_data)
        })
    except Exception as e:
        error_message = f"Error loading crime map: {str(e)}"
        print(f"Error: {str(e)}")  # Print error for debugging
        return render(request, "crime_map.html", {"error": error_message})
    
import json
import pandas as pd
from prophet import Prophet
from django.shortcuts import render
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error

def prepare_state_data(df):
    state_data = {}
    states = df['State'].unique().tolist()
    crime_types = df['Crime Type'].unique().tolist()

    for state in states:
        df_s = df[df['State'] == state]
        state_data[state] = {}

        for crime in crime_types:
            sub = df_s[df_s['Crime Type'] == crime]
            if sub.empty:
                continue

            daily = (
                sub.groupby('Date & Time')
                   .size()
                   .reset_index(name='y')
                   .rename(columns={'Date & Time': 'ds'})
            )

            m = Prophet(yearly_seasonality=True, weekly_seasonality=True, daily_seasonality=True)
            m.fit(daily)
            fut = m.make_future_dataframe(periods=365 * 4)
            fc = m.predict(fut)

            hist = daily.set_index('ds').resample('M')['y'].mean()
            yhat = fc.set_index('ds').resample('M')['yhat'].mean().round(0)
            ylow = fc.set_index('ds').resample('M')['yhat_lower'].mean().round(0)
            yhigh = fc.set_index('ds').resample('M')['yhat_upper'].mean().round(0)

            cutoff = pd.Timestamp('2024-12-31')
            h = hist[hist.index <= cutoff]
            f = yhat[yhat.index > cutoff]
            low = ylow[ylow.index > cutoff]
            high = yhigh[yhigh.index > cutoff]

            full_lo = ylow[ylow.index.isin(h.index)]
            full_hi = yhigh[yhigh.index.isin(h.index)]
            anoms = [
                actual if (actual > full_hi.loc[date] or actual < full_lo.loc[date]) else None
                for date, actual in h.items()
            ]
            anoms = anoms + [None] * len(f)

            state_data[state][crime] = {
                'historical': h.round(0).tolist(),
                'forecast': [None] * len(h) + f.tolist(),
                'lower_bound': [None] * len(h) + low.tolist(),
                'upper_bound': [None] * len(h) + high.tolist(),
                'anomalies': anoms,
                'avg_monthly_crimes': float(h.mean()),
                'latest_monthly_pred': float(f.iloc[-1]) if len(f) > 0 else 0.0,
                'monthly_change': float(((f.iloc[-1] - h.mean()) / h.mean() * 100) if len(h) > 0 else 0.0)
            }

    return states, crime_types, state_data

import numpy as np
import json
from django.templatetags.static import static
from django.shortcuts import render
import pandas as pd
from datetime import datetime, timedelta
import os

# Load dataset globally (so it doesn’t reload every request)
CSV_PATH = os.path.join("home", "thane_crime_data.csv")
df = pd.read_csv(CSV_PATH)

# Ensure datetime column is properly parsed
df["Date & Time"] = pd.to_datetime(df["Date & Time"], errors="coerce")

"""
views_predictions.py → paste into home/views.py

Changes:
  1. monthly_crime_predictions : adds ward_predictions_json to context
     so the new template can show trend + crime breakdown per ward
  2. get_ward_suspects          : NEW API endpoint — returns suspect
     records for a given ward name (to be wired to CriminalRecord model)

───────────────────────────────────────────────────────────────────────
STEP-BY-STEP for suspects (the photo gallery in the ward panel):

Right now the suspects come from a JS hardcoded dict (SUSPECT_DB) in
the template. That is fine for a demo. To wire it to your real DB:

1. Create a model (already suggested below — paste into models.py):

    class Suspect(models.Model):
        STATUS = [('wanted','Wanted'),('watch','Watch'),('arrested','Arrested')]
        name        = models.CharField(max_length=120)
        crime_type  = models.CharField(max_length=100)
        status      = models.CharField(max_length=20, choices=STATUS, default='watch')
        age         = models.PositiveIntegerField(null=True, blank=True)
        ward        = models.CharField(max_length=100)   # matches ward lgd_name
        fir_number  = models.CharField(max_length=50, blank=True)
        last_seen   = models.TextField(blank=True)
        photo       = models.ImageField(upload_to='suspects/', blank=True, null=True)
        added_at    = models.DateTimeField(auto_now_add=True)

        def __str__(self):
            return f"{self.name} — {self.ward}"

2. Run migrations:  python manage.py makemigrations && python manage.py migrate

3. The API endpoint below returns JSON for any ward — the template's JS
   can then call it on map click instead of using SUSPECT_DB.
   To enable this: in the template's openWardDetail() function replace:
       const suspects = SUSPECT_DB[wardName] || [];
   with:
       const suspects = await fetch(`/api/suspects/?ward=${encodeURIComponent(wardName)}`)
                              .then(r=>r.json());
   (make the function async first)
───────────────────────────────────────────────────────────────────────
"""

import json, os
from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

from .models import CrimeReport


def monthly_crime_predictions(request):
    """
    Main crime intelligence map view.
    Adds ward_predictions_json so the template can show per-ward
    trend charts and predicted crime breakdowns.
    """
    import pandas as pd

    # ── Static ward scores (for map colouring) ────────────────────
    with open(os.path.join(settings.BASE_DIR, 'static', 'data', 'ward_crime_counts.json')) as f:
        ward_scores_new = json.load(f)

    # ── Detailed ward predictions (trend + crime breakdown) ───────
    json_path = os.path.join(settings.BASE_DIR, 'home', 'ward_predictions.json')
    with open(json_path, 'r') as f:
        ward_predictions = json.load(f)

    # ── CSV-based metrics ─────────────────────────────────────────
    csv_path = os.path.join(settings.BASE_DIR, 'home', 'thane_crime_data.csv')
    df = pd.read_csv(csv_path)
    crimes_by_area = df.groupby("Area")["Crime Type"].count()
    max_c  = crimes_by_area.max() if not crimes_by_area.empty else 1
    min_c  = crimes_by_area.min() if not crimes_by_area.empty else 0
    rng    = max_c - min_c if max_c != min_c else 1
    ward_scores = ((1 - (crimes_by_area - min_c) / rng) * 100).round(2).to_dict()

    safest_area       = max(ward_scores, key=ward_scores.get) if ward_scores else 'N/A'
    safest_area_score = ward_scores.get(safest_area, 0)

    # ── DB metrics ────────────────────────────────────────────────
    total_incidents = CrimeReport.objects.filter(is_deleted=False).count()
    one_week_ago    = timezone.now() - timedelta(days=7)
    recent_incidents = CrimeReport.objects.filter(
        reported_at__gte=one_week_ago, is_deleted=False
    ).count()

    # ── Aggregate metrics from ward_predictions ───────────────────
    avg_safety_score = round(
        sum(w['safety_score'] for w in ward_predictions.values()) / len(ward_predictions), 2
    )
    high_risk_areas = sum(
        1 for w in ward_predictions.values() if w['crime_intensity'] == 'High Risk'
    )
    active_wards   = len(ward_predictions)
    safest_ward    = max(ward_predictions.items(), key=lambda w: w[1]['safety_score'])

    # ── 2026-2028 forecast (if you have it) ───────────────────────
    ward_data = {}
    forecast_path = os.path.join(settings.BASE_DIR, 'static', 'data', 'ward_predictions_2026_2028.json')
    if os.path.exists(forecast_path):
        with open(forecast_path) as f:
            ward_data = json.load(f)

    from django.templatetags.static import static

    context = {
        # For the JS map colouring
        'ward_scores_json':       json.dumps(ward_scores_new),
        # NEW — detailed per-ward data for trend chart + crime bars
        'ward_predictions_json':  json.dumps(ward_predictions),
        # For the forecasting page
        'ward_data_json':         json.dumps(ward_data),
        # Stat cards
        'total_incidents':        total_incidents,
        'recent_incidents':       recent_incidents,
        'avg_safety_score':       avg_safety_score,
        'high_risk_areas':        high_risk_areas,
        'active_wards':           active_wards,
        'safest_ward':            safest_ward,
        'safest_area':            safest_area,
        'safest_area_score':      safest_area_score,
        'ward_geojson':           static('data/thane_wards.json'),
    }
    return render(request, 'monthly_crime_predictions.html', context)


from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Count
from datetime import timedelta
import re
 
from .models import CrimeReport
 
 
def ward_intel_api(request, ward_name):
    """
    Real ward intelligence from your CrimeReport database.
    Matches reports to wards by address text search (since CrimeReport
    doesn't yet have a FK to Ward — add that for better accuracy, see guide).
    """
 
    # ── Build a keyword list from the ward name ─────────────────────
    # Strip common suffixes, split on spaces, use meaningful tokens
    keywords = [
        kw.strip().lower()
        for kw in re.split(r'[\s,/]+', ward_name)
        if len(kw.strip()) > 3
    ]
 
    # ── Base queryset — filter reports whose address mentions the ward ──
    # This is a text search fallback until you add ward FK to CrimeReport
    if keywords:
        from django.db.models import Q
        q = Q()
        for kw in keywords[:3]:   # use top 3 tokens to avoid over-filtering
            q |= Q(address__icontains=kw)
        ward_reports = CrimeReport.objects.filter(q, is_deleted=False)
    else:
        ward_reports = CrimeReport.objects.none()
 
    # ── Recent reports (last 60 days) ────────────────────────────────
    cutoff = timezone.now() - timedelta(days=60)
    recent = ward_reports.filter(reported_at__gte=cutoff).order_by('-reported_at')[:10]
 
    recent_list = []
    for r in recent:
        recent_list.append({
            'id':          r.id,
            'crime_type':  r.crime_type,
            'address':     r.address[:60] if r.address else '',
            'reported_at': r.reported_at.strftime('%d %b %Y, %H:%M'),
            'status':      r.resolution_status,
            'severity':    round(r.severity_score, 1) if r.severity_score else None,
        })
 
    # ── Hourly distribution (8 × 3-hour buckets) ─────────────────────
    # Only from last 180 days for meaningful stats
    six_months_ago = timezone.now() - timedelta(days=180)
    hourly_qs = (
        ward_reports
        .filter(reported_at__gte=six_months_ago)
        .extra(select={'hour': "EXTRACT(HOUR FROM reported_at)"})
        .values('hour')
        .annotate(count=Count('id'))
        .order_by('hour')
    )
 
    # Aggregate into 8 buckets of 3 hours each
    buckets = [0] * 8
    for row in hourly_qs:
        if row['hour'] is not None:
            bucket = int(row['hour']) // 3
            if 0 <= bucket < 8:
                buckets[bucket] += row['count']
 
    # ── Crime type breakdown ──────────────────────────────────────────
    crime_counts = (
        ward_reports
        .values('crime_type')
        .annotate(count=Count('id'))
        .order_by('-count')[:10]
    )
    crime_type_counts = {r['crime_type']: r['count'] for r in crime_counts}
 
    # ── Resolution rate ───────────────────────────────────────────────
    total = ward_reports.count()
    resolved = ward_reports.filter(resolution_status='Resolved').count()
    resolution_rate = round((resolved / total * 100), 1) if total else 0
 
    return JsonResponse({
        'ward':               ward_name,
        'recent_reports':     recent_list,
        'hourly_distribution': buckets,
        'crime_type_counts':  crime_type_counts,
        'total_reports':      total,
        'resolved_reports':   resolved,
        'resolution_rate':    resolution_rate,
        'data_note': (
            'Matched by address text search. '
            'For precise results add ward FK to CrimeReport model.'
        ) if total == 0 else None,
    })
 

# ── Suspect API endpoint ──────────────────────────────────────────────
def get_ward_suspects(request):
    """
    GET /api/suspects/?ward=<ward_name>

    Returns suspect records for the given ward.
    Wire this up once you have the Suspect model populated.
    Returns empty list until then (the template falls back to SUSPECT_DB).
    """
    ward_name = request.GET.get('ward', '').strip()
    if not ward_name:
        return JsonResponse([], safe=False)

   
    from .models import Suspect
    suspects = Suspect.objects.filter(ward__iexact=ward_name)
    data = [{'name': s.name, 'type': s.crime_type, 'status': s.status,
             'age': s.age, 'fir': s.fir_number, 'last_seen': s.last_seen,
             'photo': s.photo.url if s.photo else None} for s in suspects]
    return JsonResponse(data, safe=False)






from django.http import JsonResponse
import json
import os
from django.conf import settings

def wards_geojson(request):
    """
    Serve Thane wards as GeoJSON with crime stats.
    """
    # Path to your exported GeoJSON file
    geojson_path = os.path.join(settings.BASE_DIR, 'static/data/thane_wards.json')

    with open(geojson_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Optionally, add or update properties dynamically here
    for feature in data['features']:
        props = feature['properties']
        # Example: adding dummy dynamic values (replace with real predictions later)
        props['past'] = props.get('past', 100)           # past crimes
        props['predicted'] = props.get('predicted', 120) # predicted crimes
        props['risk'] = props.get('risk', 'Moderate')   # High / Moderate / Low
        props['safety_score'] = props.get('safety_score', 65)


from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .models import CrimeReport  # Replace with your actual model

def delete_crime_report(request, report_id):
    if request.method == "POST":
        report = get_object_or_404(CrimeReport, id=report_id)
        report.delete()
        return JsonResponse({"message": "Crime report deleted successfully"})
    return JsonResponse({"error": "Invalid request"}, status=400)

from datetime import timedelta
import math

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg
from django.shortcuts import render, get_object_or_404, redirect

from .models import userProfile, CrimeReport, OfficerFeedback

from datetime import timedelta
from django.db.models import Avg, Q
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
import math
from .models import userProfile, CrimeReport, OfficerFeedback #, Alert, PatrolRoute  <-------  # adjust imports

@login_required
def police_performance(request):
    # — Fetch this officer’s profile —
    profile = get_object_or_404(userProfile, user=request.user)

    # — Only approved police may proceed —
    if profile.role != 'police':
        messages.error(request, "Access denied: You are not a police officer.")
        return redirect('crime_chart')
    if not profile.is_approved:
        messages.error(request, "Your police account is not yet approved.")
        return redirect('police_dashboard')

    # — All reports assigned to this officer —
    reports = CrimeReport.objects.filter(assigned_officer=profile)

    # — Count by resolution_status —
    total_cnt         = reports.count()
    pending_cnt       = reports.filter(resolution_status='Pending').count()
    investigating_cnt = reports.filter(resolution_status='Under Investigation').count()
    resolved_cnt      = reports.filter(
                            resolution_status='Resolved',
                            resolved_at__isnull=False
                        ).count()

    # — Compute average response time (first_touched_at – assigned_at) —
    responded = reports.filter(
        assigned_at__isnull=False,
        first_touched_at__isnull=False
    )
    if responded.exists():
        deltas = [(r.first_touched_at - r.assigned_at).total_seconds() for r in responded]
        avg_secs     = sum(deltas) / len(deltas)
        avg_response = timedelta(seconds=avg_secs)
    else:
        avg_secs     = 0
        avg_response = None

    # — Compute average officer rating —
    avg = OfficerFeedback.objects.filter(officer=profile).aggregate(a=Avg('rating'))['a']
    officer_rating = round(avg or 0, 1)
    full_stars      = math.floor(officer_rating)
    partial_percent = int((officer_rating - full_stars) * 100)

    # — New Metrics —

    # # Active Alerts (critical + high priority)
    # active_alerts = Alert.objects.filter(
    #     assigned_officer=profile,
    #     status='Active'
    # )
    # critical_alerts = active_alerts.filter(priority='Critical').count()
    # high_alerts     = active_alerts.filter(priority='High').count()

    # # Patrol Routes (high-risk zones today)
    # today = timezone.now().date()
    # # patrol_routes = PatrolRoute.objects.filter(
    # #     officer=profile,
    # #     date=today
    # # )
    # high_risk_routes = patrol_routes.filter(risk_level='High').count()

    # Resolution Rate %
    resolution_rate = round((resolved_cnt / total_cnt * 100), 1) if total_cnt else 0

    context = {
        'officer_profile': profile,
        'performance': {
            'total':              total_cnt,
            'pending':            pending_cnt,
            'investigating':      investigating_cnt,
            'resolved':           resolved_cnt,
            'avg_response':       avg_response,
            'avg_response_secs':  avg_secs,
        },
        'officer_rating':  officer_rating,
        'full_stars':      full_stars,
        'partial_percent': partial_percent,
        # — new metrics —
        'metrics': {
            'total_cases': total_cnt,
            'case_breakdown': f"{pending_cnt} pending, {investigating_cnt} under investigation, {resolved_cnt} resolved",
            # 'active_alerts': active_alerts.count(),
            # 'alert_breakdown': f"{critical_alerts} critical, {high_alerts} high priority",
            # 'patrol_routes': patrol_routes.count(),
            # 'high_risk_routes': high_risk_routes,
            'resolution_rate': resolution_rate,
            'resolution_comment': "Above station average" if resolution_rate > 80 else "Below station average",  # example logic
        }
    }

    return render(request, 'police_performance.html', context)


from django.shortcuts import redirect, get_object_or_404
from .models import CrimeReport  # import your model

def delete_report(request):
    if request.method == 'POST':
        report_id = request.POST.get('report_id')
        report = get_object_or_404(Report, id=report_id)
        report.is_deleted = True  # 👈 soft delete
        report.save()
        return redirect('crime_report_status')
    
    


from datetime import timedelta
from django.db.models import Avg, Q
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
import math
from .models import userProfile, CrimeReport, OfficerFeedback #, Alert, PatrolRoute  <-------  # adjust imports

@login_required
def officer_feedbacks(request):
    profile = get_object_or_404(userProfile, user=request.user)

    # — Only approved police may proceed —
    if profile.role != 'police':
        messages.error(request, "Access denied: You are not a police officer.")
        return redirect('crime_chart')
    if not profile.is_approved:
        messages.error(request, "Your police account is not yet approved.")
        return redirect('police_dashboard')

    # — All reports assigned to this officer —
    reports = CrimeReport.objects.filter(assigned_officer=profile)
    

    officer = request.user.userprofile
    feedbacks = OfficerFeedback.objects.filter(officer=officer).select_related('crime_report')
    
    avg = OfficerFeedback.objects.filter(officer=profile).aggregate(a=Avg('rating'))['a']
    officer_rating = round(avg or 0, 1)
    full_stars      = math.floor(officer_rating)
    partial_percent = int((officer_rating - full_stars) * 100)

    context = {
        'feedbacks': feedbacks,
        'officer_rating':  officer_rating,
        'full_stars':      full_stars,
        'partial_percent': partial_percent,
    }
    return render(request, 'officer_feedbacks.html', context)

import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

@csrf_exempt
def chat_with_bot(request):
    if request.method == "POST":
        data = json.loads(request.body)
        message = data.get("message")
        if not message:
            return JsonResponse({"error": "No message provided"}, status=400)
        
        rasa_response = requests.post(
            "http://localhost:5005/webhooks/rest/webhook",
            json={"sender": "user", "message": message}
        )
        
        if rasa_response.status_code == 200:
            return JsonResponse(rasa_response.json(), safe=False)
        else:
            return JsonResponse({"error": "Failed to reach Rasa"}, status=500)
    return JsonResponse({"error": "Invalid method"}, status=405)


from django.shortcuts import render, get_object_or_404
from .models import CrimeReport, CrimePhoto

def admin_ai_review(request, report_id):
    # Fetch the report
    crime_report = get_object_or_404(CrimeReport, id=report_id)
    photos = CrimePhoto.objects.filter(crime_report=crime_report)

    context = {
        "report": crime_report,
        "photos": photos,
        # These fields are already updated by process_crime_report()
        "weapon_detected": crime_report.weapon_detected,
        "violence_detected": crime_report.violence_detected,
        "deepfake_suspected": crime_report.deepfake_suspected,
        "ai_confidence": crime_report.ai_confidence_score,
    }
    return render(request, "admin_ai_review.html", context)

import json
from django.shortcuts import render
from django.http import HttpResponseBadRequest

def monthly_analytics(request):  
    with open('static/data/ward_predictions_2026_2028.json') as f:
        ward_data = json.load(f)   
    context = {
        "ward_data_json": json.dumps(ward_data),
        
    }
    return render(request, "monthly_analytics.html", context)

from django.shortcuts import render
import pandas as pd
from datetime import datetime, timedelta
import os

# Load dataset globally (so it doesn’t reload every request)
CSV_PATH = os.path.join("home", "thane_crime_data.csv")
df = pd.read_csv(CSV_PATH)

# Ensure datetime column is properly parsed
df["Date & Time"] = pd.to_datetime(df["Date & Time"], errors="coerce")

def crime_citizen_dashboard(request):
    # TODO: Replace with logged-in user's area from Profile
    user_area = "Ghodbunder Road"

    # Crimes grouped by area
    crimes_by_area = df.groupby("Area")["Crime Type"].count()

    # Total crimes in the user’s area
    your_area_crimes = crimes_by_area.get(user_area, 0)

    # Max & Min crimes across all areas (avoid divide by zero)
    max_crimes = crimes_by_area.max() if not crimes_by_area.empty else 1
    min_crimes = crimes_by_area.min() if not crimes_by_area.empty else 0
    crime_range = max_crimes - min_crimes if max_crimes != min_crimes else 1

    # 🟢 Your Area Safety Score (0–100)
    your_area_score = round((1 - (your_area_crimes - min_crimes) / crime_range) * 100, 2)

    # 🟢 Ward Safety Scores
    ward_scores = ((1 - (crimes_by_area - min_crimes) / crime_range) * 100).round(2).to_dict()

    # 🟢 City Average Safety Score (mean of ward scores)
    city_avg_score = round(sum(ward_scores.values()) / len(ward_scores) if ward_scores else 0, 2)

    # 🟢 Safest Area (highest score)
    if ward_scores:
        safest_area = max(ward_scores, key=ward_scores.get)
        safest_area_score = ward_scores[safest_area]
    else:
        safest_area, safest_area_score = "N/A", 0

    # 🟢 Active Alerts (last 7 days)
    # last_7_days = datetime.now() - timedelta(days=7)
    # active_alerts = df[df["Date & Time"] >= last_7_days].shape[0]

    # Pack into context
    context = {
        "your_area": user_area,
        "your_area_score": your_area_score,
        "city_avg_score": city_avg_score,
        "safest_area": safest_area,
        "safest_area_score": safest_area_score,
        # "active_alerts": active_alerts,
        "ward_scores": ward_scores,  # needed for bottom section in HTML
    }
    return render(request, 'crime_citizen_dashboard.html', context)

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone
from .models import userProfile, CrimeReport
from .utils import officer_score
from home.templatetags.custom_filters import station_in_address

from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.contrib import messages
from .models import userProfile, CrimeReport
from django.shortcuts import render
from django.utils import timezone
from datetime import datetime
from .models import userProfile, CrimeReport

from django.http import JsonResponse
from django.db.models import Count
from django.utils.timezone import now
from datetime import timedelta
from .models import NewsIntel


# 🔥 Advanced Pattern Detection (time + location aware)
def detect_patterns():
    last_24h = now() - timedelta(hours=24)

    patterns = (
        NewsIntel.objects
        .filter(created_at__gte=last_24h)
        .values("crime_type", "location")
        .annotate(count=Count("id"))
        .filter(count__gte=2)
        .order_by("-count")
    )

    # Convert to readable intelligence format
    result = []
    for p in patterns:
        result.append({
            "alert": f"{p['crime_type']} cases rising in {p['location']}",
            "crime_type": p["crime_type"],
            "location": p["location"],
            "count": p["count"]
        })

    return result

from django.db.models import Count
from django.utils.timezone import now
from datetime import timedelta
from .models import NewsIntel


# 🔥 Trend Detection (time comparison)
def detect_trends():
    now_time = now()

    last_24h = now_time - timedelta(hours=24)
    prev_24h = now_time - timedelta(hours=48)

    # Current window
    current = (
        NewsIntel.objects
        .filter(created_at__gte=last_24h)
        .values("crime_type", "location")
        .annotate(count=Count("id"))
    )

    # Previous window
    previous = (
        NewsIntel.objects
        .filter(created_at__gte=prev_24h, created_at__lt=last_24h)
        .values("crime_type", "location")
        .annotate(count=Count("id"))
    )

    # Convert previous to lookup dict
    prev_map = {
        (p["crime_type"], p["location"]): p["count"]
        for p in previous
    }

    trends = []

    for c in current:
        key = (c["crime_type"], c["location"])
        current_count = c["count"]
        prev_count = prev_map.get(key, 0)

        if prev_count == 0 and current_count == 1:
            trend = "NEW ⚡"
        elif current_count >= 2 and current_count > prev_count:
            trend = "INCREASING 📈"
        elif current_count < prev_count:
            trend = "DECREASING 📉"
        else:
            trend = "STABLE ➖"

        trends.append({
            "crime_type": c["crime_type"],
            "location": c["location"],
            "current_count": current_count,
            "previous_count": prev_count,
            "trend": trend
        })

    return trends

# 🔥 SHO Alerts API
from django.http import JsonResponse


def sho_alerts(request):
    # 🔥 Priority alerts
    alerts_qs = (
        NewsIntel.objects
        .order_by("-priority_score", "-created_at")[:5]
    )

    alerts = []
    for a in alerts_qs:
        alerts.append({
            "id": a.id,
            "title": a.title,
            "location": a.location,
            "crime_type": a.crime_type,
            "risk_level": a.risk_level,
            "priority_score": a.priority_score,
            "summary": a.summary,
            "suggested_action": a.suggested_action,
            "created_at": a.created_at
        })

    # 🔥 Pattern detection
    patterns = detect_patterns()

    # 🔥 NEW: Trend detection
    trends = detect_trends()

    top_alert = alerts[0] if alerts else None

    return JsonResponse({
        "top_alert": top_alert,
        "top_alerts": alerts,
        "patterns": patterns,
        "trends": trends   # 🔥 NEW FIELD
    })
    
    
def sho_dashboard(request):
    # Get the SHO's profile and assigned station
    sho_profile = userProfile.objects.get(user=request.user)
    station = sho_profile.station

    # Pending reports for this station
    reports = CrimeReport.objects.filter(
        status="Pending",
        station=station
    )

    # Officers under this station
    officers_qs = userProfile.objects.filter(
        station=station,
        role='police',
        is_approved=True
    )
    total_officers = officers_qs.count()
    on_duty = officers_qs.filter(is_on_duty=True).count()
    off_duty = total_officers - on_duty

    top_alerts = NewsIntel.objects.order_by("-priority_score", "-created_at")[:5]
    top_alert = top_alerts.first()

    patterns = detect_patterns()
    trends = detect_trends()
     
    # Prepare officer data for Workload Tracker
    officers = []
    for officer in officers_qs:
        total_cases = CrimeReport.objects.filter(assigned_officer=officer).count()
        resolved_cases = CrimeReport.objects.filter(
            assigned_officer=officer,
            resolution_status="Resolved"
        ).count()
        pending_cases = total_cases - resolved_cases
        officer_resolution_rate = round((resolved_cases / total_cases * 100), 1) if total_cases > 0 else 0

        officers.append({
            'id': officer.id,
            'name': officer.user.get_full_name(),
            'username': officer.user.username,
            'status': 'on_duty' if officer.is_on_duty else 'off_duty',
            'total_cases': total_cases,
            'resolved_cases': resolved_cases,
            'pending_cases': pending_cases,
            'resolution_rate': officer_resolution_rate,
            
        })

    # Optional: Active Cases (total assigned to officers)
    active_cases = sum(o['total_cases'] for o in officers)

    # Station-wide resolution rate (all cases in this station, resolved vs total)
    all_station_cases = CrimeReport.objects.filter(station=station)
    resolved_station_cases = all_station_cases.filter(resolution_status="Resolved").count()
    station_resolution_rate = round((resolved_station_cases / all_station_cases.count() * 100), 1) if all_station_cases.exists() else 0
    

    last_24h = now() - timedelta(hours=24)

    top_news_cards = NewsIntel.objects.filter(
        created_at__gte=last_24h
    ).order_by("-priority_score")[:4]
    
    # Context for template
    context = {
        "officers": officers,
        "total_officers": total_officers,
        "on_duty": on_duty,
        "off_duty": off_duty,
        'reports': reports,
        "active_cases": active_cases,
        "station_resolution_rate": station_resolution_rate,
        "top_alert": top_alert,
        "top_alerts": top_alerts,
        "patterns": patterns,
        "top_news_cards": top_news_cards,
        "trends": trends# New variable for station-wide metric
    }

    return render(request, "sho_police_dashboard.html", context)

from django.shortcuts import get_object_or_404, render
from .models import NewsIntel


def intel_detail(request, id):
    news = get_object_or_404(NewsIntel, id=id)

    return render(request, "intel_detail.html", {
        "news": news
    })

from django.utils import timezone
from datetime import timedelta
from django.db.models import Avg, Count
from .models import CrimeReport, userProfile

import numpy as np
import json
from django.templatetags.static import static
from django.shortcuts import render
import pandas as pd
from datetime import datetime, timedelta
import os

# Load dataset globally (so it doesn’t reload every request)
CSV_PATH = os.path.join("home", "thane_crime_data.csv")
df = pd.read_csv(CSV_PATH)

# Ensure datetime column is properly parsed
df["Date & Time"] = pd.to_datetime(df["Date & Time"], errors="coerce")

def citizen_women_dashboard(request):    # Get user area (assuming userProfile has location or station info)
    user_profile = userProfile.objects.get(user=request.user)
    station = user_profile.station
    now = timezone.now()
    one_week_ago = now - timedelta(days=7)# Filter reports in user's region
    reports = CrimeReport.objects.filter(station=station, is_deleted=False)
    women_df = df[df["Victim Gender"] == "  Female"]
    ward_incidents = women_df.groupby("Area")["Crime Type"].count()
    max_incidents = ward_incidents.max() if not ward_incidents.empty else 1
    min_incidents = ward_incidents.min() if not ward_incidents.empty else 0
    crime_range = max_incidents - min_incidents if max_incidents != min_incidents else 1

    ward_data = {}
    for ward, count in ward_incidents.items():
        ward_safety = round((1 - (count - min_incidents) / crime_range) * 100, 2)
        ward_data[ward] = {
            "crime_count": int(count),
            "safety_score": ward_safety
        }
    # 1️⃣ Safety Score (simplified calculation)
    total_crimes = reports.count()
    women_related_crimes = reports.filter(crime_type__in=[
        "domestic_violence", "assault", "kidnapping"
    ]).count()

    safety_score = max(0, 100 - (women_related_crimes * 10))  # Basic formula

    # 2️⃣ Active SOS Alerts (optional future model)
    active_sos = reports.filter(status="Pending").count()

    # 3️⃣ Average Response Time
    resolved_reports = reports.filter(resolved_at__isnull=False, assigned_at__isnull=False)
    if resolved_reports.exists():
        total_time = sum([(r.resolved_at - r.assigned_at).total_seconds() for r in resolved_reports], 0)
        avg_minutes = total_time / resolved_reports.count() / 60
    else:
        avg_minutes = 0

    # 4️⃣ Police Presence Index
    on_duty_officers = userProfile.objects.filter(station=station, role='police', is_on_duty=True).count()

    # 5️⃣ Recent Crimes
    recent_crimes = reports.filter(reported_at__gte=one_week_ago).count()

    # 6️⃣ Most Common Crime Type
    common_crime = reports.values('crime_type').annotate(total=Count('crime_type')).order_by('-total').first()
    most_common_crime = common_crime['crime_type'] if common_crime else "None"

    # 7️⃣ Pending Investigations
    pending_cases = reports.exclude(resolution_status="Resolved").count()

    context = {
        'safety_score': round(safety_score, 1),
        'active_sos': active_sos,
        'avg_response_time': f"{avg_minutes:.1f} min",
        'on_duty_officers': on_duty_officers,
        'recent_crimes': recent_crimes,
        'most_common_crime': most_common_crime,
        'pending_cases': pending_cases,
        "ward_data": json.dumps(ward_data),  # Pass to JS for map visualization
        "ward_geojson": static("data/thane_wards.json"),
    }



    return render(request, 'citizen_women_dashboard.html',context)

from django.http import JsonResponse
from .models import TrustedContact
from django.contrib.auth.decorators import login_required

@login_required
def add_contact(request):
    if request.method == "POST":
        name = request.POST.get("name")
        phone = request.POST.get("phone")
        TrustedContact.objects.create(user=request.user, name=name, phone_number=phone)
        return JsonResponse({"status": "success"})

@login_required
def remove_contact(request, contact_id):
    TrustedContact.objects.filter(id=contact_id, user=request.user).delete()
    return JsonResponse({"status": "deleted"})

@login_required
def get_contacts(request):
    contacts = TrustedContact.objects.filter(user=request.user).values("id", "name", "phone_number")
    return JsonResponse(list(contacts), safe=False)




# import json
# from django.http import JsonResponse
# from django.conf import settings
# from django.contrib.auth.decorators import login_required
# from twilio.rest import Client
# from .models import TrustedContact


# def send_sos(request):
#     if request.method == "POST":
#         data = json.loads(request.body)
#         latitude = data.get("latitude")
#         longitude = data.get("longitude")
#         user = request.user

#         contacts = TrustedContact.objects.filter(user=user)

#         if not contacts.exists():
#             return JsonResponse({"message": "No trusted contacts found."}, status=400)

#         # Create Twilio client
#         client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

#         alert_message = f"🚨 SOS ALERT 🚨\n{user.username} may be in danger!\nLocation: https://maps.google.com/?q={latitude},{longitude}"

#         for contact in contacts:
#             try:
#                 client.messages.create(
#                     body=alert_message,
#                     from_=settings.TWILIO_PHONE_NUMBER,
#                     to=f"+91{contact.phone_number}"  # prepend country code for India
#   # must be a verified number in trial mode
#                 )
#             except Exception as e:
#                 print(f"Failed to send SMS to {contact.phone_number}: {e}")

#         return JsonResponse({"message": "SOS alerts sent successfully!"})





import requests
from django.conf import settings
from django.shortcuts import render

def crime_news(request):
    query = request.GET.get("q", "crime")  # default search
    url = "https://newsapi.org/v2/everything"

    params = {
        "q": query,
        "language": "en",
        "sortBy": "publishedAt",
        "apiKey": settings.NEWS_API_KEY,
        "pageSize": 20
    }

    response = requests.get(url, params=params)
    data = response.json()

    articles = data.get("articles", [])

    return render(request, "crime_news.html", {"articles": articles, "query": query})

# home/views.py
import os

import pandas as pd
from prophet import Prophet
from sklearn.metrics import mean_absolute_error
from django.shortcuts import render
from django.conf import settings

# =====================================================
# LOAD DATA
# =====================================================
CSV_PATH = os.path.join(settings.BASE_DIR, "home", "monthly_crime_aggregated.csv")

try:
    crime_df = pd.read_csv(CSV_PATH)
    crime_df["month"] = pd.to_datetime(crime_df["month"])
except FileNotFoundError:
    crime_df = pd.DataFrame()
    
def compute_basic_stats(df):
    df = df.copy()
    grouped = df.groupby(["ward", "crime_type"])
    df["months_of_data"] = grouped["month"].transform("count")
    df["avg_crime"] = grouped["crime_count"].transform("mean")

    def risk_level(avg):
        if avg >= 5:
            return "HIGH"
        elif avg >= 2:
            return "MEDIUM"
        else:
            return "LOW"

    def patrol_window(avg):
        # Strategic recommendation, NOT hour prediction
        if avg >= 5:
            return "Late Evening / Night"
        elif avg >= 2:
            return "Evening"
        else:
            return "Daytime"

    df["risk_level"] = df["avg_crime"].apply(risk_level)
    df["peak_window"] = df["avg_crime"].apply(patrol_window)

    return df.drop_duplicates(subset=["ward", "crime_type"])

# =====================================================
# CONFIDENCE (STRICT, SINGLE LABEL)
# =====================================================
def compute_confidence(months, mae):
    if months >= 36 and mae <= 0.2:
        return "HIGH"
    if months >= 18:
        return "MODERATE"
    return "LOW"
# =====================================================
# RECENT TREND
# =====================================================
def compute_recent_spike(df):
    df = df.sort_values("month")

    if df.shape[0] < 6:
        return {"status": "INSUFFICIENT", "label": "⚠️ Limited historical depth"}

    recent_avg = df.tail(3)["crime_count"].mean()
    baseline_avg = df.iloc[:-3]["crime_count"].mean()

    if baseline_avg == 0:
        return {"status": "INSUFFICIENT", "label": "⚠️ No baseline available"}

    change_pct = ((recent_avg - baseline_avg) / baseline_avg) * 100

    if change_pct >= 40:
        return {"status": "SPIKE", "label": "🔴 Recent spike detected"}
    if change_pct >= 15:
        return {"status": "ELEVATED", "label": "🟡 Slight increase observed"}

    return {"status": "NORMAL", "label": "🟢 Normal activity"}

# =====================================================
# STANDARD LIBRARIES
# =====================================================
import os

# =====================================================
# THIRD-PARTY LIBRARIES
# =====================================================
import pandas as pd
from prophet import Prophet
from sklearn.metrics import mean_absolute_error

# =====================================================
# DJANGO IMPORTS
# =====================================================
from django.conf import settings
from django.shortcuts import render


# =====================================================
# DATA LOADING
# =====================================================
BASE_DIR = settings.BASE_DIR

MONTHLY_CSV = os.path.join(BASE_DIR, "home", "monthly_crime_aggregated.csv")
RAW_CSV = os.path.join(BASE_DIR, "home", "thane_crime_data.csv")

try:
    crime_df = pd.read_csv(MONTHLY_CSV)
    crime_df["month"] = pd.to_datetime(crime_df["month"])
except FileNotFoundError:
    crime_df = pd.DataFrame()

try:
    RAW_CRIME_DF = pd.read_csv(RAW_CSV)
except FileNotFoundError:
    RAW_CRIME_DF = pd.DataFrame()


# =====================================================
# CONFIDENCE LOGIC
# =====================================================
def compute_confidence(months: int, mae: float) -> str:
    if months >= 36 and mae <= 0.2:
        return "HIGH"
    if months >= 18:
        return "MODERATE"
    return "LOW"


# =====================================================
# RECENT TREND DETECTION
# =====================================================
def compute_recent_spike(df: pd.DataFrame) -> dict:
    df = df.sort_values("month")

    if df.shape[0] < 6:
        return {"status": "INSUFFICIENT", "label": "⚠️ Limited historical depth"}

    recent_avg = df.tail(3)["crime_count"].mean()
    baseline_avg = df.iloc[:-3]["crime_count"].mean()

    if baseline_avg == 0:
        return {"status": "INSUFFICIENT", "label": "⚠️ No baseline available"}

    change_pct = ((recent_avg - baseline_avg) / baseline_avg) * 100

    if change_pct >= 40:
        return {"status": "SPIKE", "label": "🔴 Recent spike detected"}
    if change_pct >= 15:
        return {"status": "ELEVATED", "label": "🟡 Slight increase observed"}

    return {"status": "NORMAL", "label": "🟢 Normal activity"}


# =====================================================
# TEMPORAL INTELLIGENCE
# =====================================================
def generate_temporal_intelligence(raw_df: pd.DataFrame, total_30d: float):
    if raw_df.empty or total_30d == 0:
        return [], {}, "Unknown", "Insufficient temporal data"

    df = raw_df.copy()
    df["Date & Time"] = pd.to_datetime(df["Date & Time"])
    df["hour"] = df["Date & Time"].dt.hour
    df["weekday"] = df["Date & Time"].dt.weekday
    df["week_of_month"] = df["Date & Time"].dt.day.apply(
        lambda d: (d - 1) // 7 + 1
    )

    # ---------------------------
    # Weekly Distribution
    # ---------------------------
    weekly_ratio = (
        df["week_of_month"]
        .value_counts(normalize=True)
        .reindex([1, 2, 3, 4], fill_value=0)
    )

    weekly_counts = [
        int(round(total_30d * weekly_ratio.get(i, 0))) for i in range(1, 5)
    ]

    diff = int(round(total_30d)) - sum(weekly_counts)
    i = 0
    while diff != 0:
        weekly_counts[i % 4] += 1 if diff > 0 else -1
        diff += -1 if diff > 0 else 1
        i += 1

    weekly = [
        {"week": f"Week {i+1}", "count": weekly_counts[i]}
        for i in range(4)
    ]

    # ---------------------------
    # Hourly Risk
    # ---------------------------
    def hour_bucket(h):
        if h >= 22 or h < 4:
            return "Night (22:00–04:00)"
        if 18 <= h < 22:
            return "Evening (18:00–22:00)"
        return "Daytime"

    df["hour_bucket"] = df["hour"].apply(hour_bucket)
    bucket_ratio = df["hour_bucket"].value_counts(normalize=True)

    def risk_label(p):
        if p >= 0.45:
            return "HIGH"
        if p >= 0.25:
            return "MEDIUM"
        return "LOW"

    hourly_risk = {
        bucket: risk_label(bucket_ratio.get(bucket, 0))
        for bucket in [
            "Night (22:00–04:00)",
            "Evening (18:00–22:00)",
            "Daytime",
        ]
    }

    peak_window = max(
        hourly_risk,
        key=lambda k: ["LOW", "MEDIUM", "HIGH"].index(hourly_risk[k]),
    )

    weekend_ratio = (df["weekday"] >= 5).mean()
    weekend_bias = (
        f"Higher risk observed during weekends (~{int(weekend_ratio * 100)}%)"
    )

    return weekly, hourly_risk, peak_window, weekend_bias


# =====================================================
# OPERATIONAL ACTIONS
# =====================================================
def generate_operational_action(total_cases: float, peak_window: str) -> list:
    if total_cases >= 5:
        return [
            "Increase patrol presence by 1 unit",
            f"Prioritize coverage during {peak_window}",
            "Weekend reinforcement advised",
        ]
    if total_cases >= 2:
        return [
            f"Maintain routine patrol with focus on {peak_window}",
            "No weekday expansion required",
        ]
    return [
        "Routine patrol sufficient",
        "Time-aware vigilance recommended",
    ]


# =====================================================
# CRIME DISTRIBUTION
# =====================================================
def compute_crime_distribution(df: pd.DataFrame, months: int = 12) -> list:
    recent = df.sort_values("month").tail(months)
    grouped = (
        recent.groupby("crime_type")["crime_count"]
        .sum()
        .reset_index()
    )

    total = grouped["crime_count"].sum()
    if total == 0:
        return []

    grouped["percentage"] = (grouped["crime_count"] / total * 100).round(1)
    grouped = grouped.sort_values("crime_count", ascending=False)

    return [
        {
            "crime_type": row["crime_type"],
            "count": int(row["crime_count"]),
            "percentage": row["percentage"],
        }
        for _, row in grouped.iterrows()
    ]


# =====================================================
# FORECAST CORE
# =====================================================
def forecast_and_summarize(df: pd.DataFrame) -> dict:
    df = df.copy()
    df["ds"] = df["month"]
    df["y"] = df["crime_count"]

    months_of_data = df.shape[0]
    avg_monthly = df["y"].mean()

    if months_of_data < 6:
        total_30d = round(avg_monthly, 1)
        confidence = "LOW"
    else:
        train = df.iloc[:-3]
        test = df.iloc[-3:]

        model = Prophet()
        model.fit(train[["ds", "y"]])

        future = model.make_future_dataframe(periods=1, freq="ME")
        forecast = model.predict(future)

        total_30d = round(max(0, forecast.iloc[-1]["yhat"]), 1)
        mae = mean_absolute_error(
            test["y"],
            model.predict(test[["ds"]])["yhat"].clip(lower=0),
        )
        confidence = compute_confidence(months_of_data, mae)

    weekly, hourly_risk, peak_window, weekend_bias = (
        generate_temporal_intelligence(RAW_CRIME_DF, total_30d)
    )
    primary_crime = (
        df.groupby("crime_type")["crime_count"].sum().idxmax()
    )

    return {
        "forecast_summary": {
            "expected_30d": f"{int(total_30d)}–{int(total_30d + 1)} incidents",
            "primary_crime": primary_crime,
            "peak_window": peak_window,
            "confidence": confidence,
            "data_depth": f"{months_of_data} months",
        },
        "weekly_breakdown": weekly,
        "hourly_risk": hourly_risk,
        "weekend_bias": weekend_bias,
        "operational_actions": generate_operational_action(
            total_30d, peak_window
        ),
        "recent_trend": compute_recent_spike(df),
    }


# =====================================================
# VIEWS
# =====================================================
def ward_forecast_view(request, ward_name, crime_type):
    pilot = crime_df[
        (crime_df["ward"] == ward_name)
        & (crime_df["crime_type"] == crime_type)
    ]

    if pilot.empty:
        return render(
            request,
            "error.html",
            {"message": "No data available."},
        )

    summary = forecast_and_summarize(pilot)
    summary.update(
        {
            "ward": ward_name,
            "crime_type": crime_type,
            "crime_distribution": compute_crime_distribution(
                crime_df[crime_df["ward"] == ward_name]
            ),
        }
    )

    return render(
        request,
        "forecast_summary.html",
        {"summary": summary},
    )


def dashboard_view(request):
    df = crime_df.copy()

    selected_ward = request.GET.get("ward")
    selected_crime = request.GET.get("crime_type")
    selected_risk = request.GET.get("risk_level")

    if selected_ward:
        df = df[df["ward"] == selected_ward]
    if selected_crime:
        df = df[df["crime_type"] == selected_crime]

    stats_df = compute_basic_stats(df)

    if selected_risk:
        stats_df = stats_df[stats_df["risk_level"] == selected_risk]

    stats_df["can_forecast"] = stats_df["months_of_data"] >= 5

    panels = [
        {
            "ward": row["ward"],
            "crime_type": row["crime_type"],
            "risk_level": row["risk_level"],
            "peak_window": row["peak_window"],
            "can_forecast": row["can_forecast"],
            "url": f"/forecast/{row['ward']}/{row['crime_type']}/",
        }
        for _, row in stats_df.iterrows()
    ]

    return render(
        request,
        "dashboard.html",
        {
            "panels": panels,
            "wards": sorted(crime_df["ward"].unique()),
            "crime_types": sorted(crime_df["crime_type"].unique()),
            "risk_levels": ["LOW", "MEDIUM", "HIGH"],
            "selected_ward": selected_ward,
            "selected_crime": selected_crime,
            "selected_risk": selected_risk,
        },
    )

# Recommendation part start below this :


# home/views.py
import os
import pandas as pd
from datetime import datetime
from prophet import Prophet
from sklearn.metrics import mean_absolute_error
from django.shortcuts import render
from django.conf import settings

# =====================================================
# LOAD DATASETS (SEPARATED)
# =====================================================

# ---- Monthly Aggregated (Forecasting) ----
MONTHLY_CSV = os.path.join(settings.BASE_DIR, "home", "monthly_crime_aggregated.csv")
try:
    crime_df = pd.read_csv(MONTHLY_CSV)
    crime_df["month"] = pd.to_datetime(crime_df["month"])
except FileNotFoundError:
    crime_df = pd.DataFrame()

# ---- Raw Incident Data (Patrol Intelligence) ----
RAW_CSV = os.path.join(settings.BASE_DIR, "home", "thane_crime_data.csv")
try:
    raw_df = pd.read_csv(RAW_CSV)
    raw_df["Date & Time"] = pd.to_datetime(raw_df["Date & Time"])
    raw_df["hour"] = raw_df["Date & Time"].dt.hour
    raw_df["weekday"] = raw_df["Date & Time"].dt.day_name()
    raw_df["is_weekend"] = raw_df["weekday"].isin(["Saturday", "Sunday"])
except FileNotFoundError:
    raw_df = pd.DataFrame()

# =====================================================
# TIME WINDOW BUCKETS (HUMAN MEANINGFUL)
# =====================================================
TIME_BUCKETS = {
    "Early Morning": range(5, 9),
    "Morning": range(9, 13),
    "Afternoon": range(13, 17),
    "Evening": range(17, 21),
    "Night": list(range(21, 24)) + list(range(0, 5)),
}

def map_time_bucket(hour):
    for label, hours in TIME_BUCKETS.items():
        if hour in hours:
            return label
    return "Unknown"

# =====================================================
# TIME-OF-DAY RISK ANALYSIS
# =====================================================
def compute_time_of_day_risk(df, ward, crime_type):
    subset = df[
        (df["Area"] == ward) &
        (df["Crime Type"] == crime_type)
    ]

    if subset.empty:
        return []

    subset = subset.copy()
    subset["time_bucket"] = subset["hour"].apply(map_time_bucket)

    grouped = (
        subset.groupby("time_bucket")
        .size()
        .reset_index(name="count")
    )

    total = grouped["count"].sum()
    grouped["percentage"] = (grouped["count"] / total * 100).round(1)

    return grouped.sort_values("percentage", ascending=False).to_dict("records")

# =====================================================
# RECENT ACTIVITY SIGNAL (FIX #1)
# =====================================================

import numpy as np

def compute_recent_activity(df, ward, crime_type):
    today = datetime.now()
    subset = df[
        (df["Area"] == ward) & (df["Crime Type"] == crime_type)
    ].copy()

    if subset.empty:
        return {
            "last_48_hours": 0,
            "last_7_days": 0,
            "last_14_days": 0,
            "baseline_14": 0,
            "density_status": "Normal",
            "velocity_status": "Normal",
            "recent_weight": 0,
            "recent_status": "Normal",
        }

    subset["days_ago"] = (today - subset["Date & Time"]).dt.days
    subset["hours_ago"] = (today - subset["Date & Time"]).dt.total_seconds() / 3600

    last_48 = subset[subset["hours_ago"] <= 48].shape[0]
    last_7 = subset[subset["days_ago"] <= 7].shape[0]
    last_14 = subset[subset["days_ago"] <= 14].shape[0]
    baseline_14 = (subset.shape[0] / max(subset["days_ago"].max(), 1)) * 14

    density_status = "High" if last_14 > baseline_14 * 1.3 else "Normal"
    velocity_status = "Elevated" if last_48 >= 3 else "Normal"

    # exponential decay weight
    subset["decay_weight"] = np.exp(-subset["days_ago"] / 7)
    recent_weight = subset["decay_weight"].sum()
    recent_status = "Elevated" if recent_weight >= 3 else "Normal"

    return {
        "last_48_hours": last_48,
        "last_7_days": last_7,
        "last_14_days": last_14,
        "last_30_days": subset[subset["days_ago"] <= 30].shape[0],
        "baseline_14": round(baseline_14, 1),
        "density_status": density_status,
        "velocity_status": velocity_status,
        "recent_weight": round(recent_weight, 2),
        "recent_status": recent_status,
    }


# =====================================================
# PATROL RECOMMENDATION ENGINE (CORE)
# =====================================================
def generate_patrol_recommendation(df, ward, crime_type, mode="summary"):
    time_risk = compute_time_of_day_risk(df, ward, crime_type)
    if not time_risk:
        return None

    top_window = time_risk[0]
    recent_activity = compute_recent_activity(df, ward, crime_type)
    recent = compute_recent_activity(df, ward, crime_type)
    is_weekend = datetime.now().weekday() >= 5
    
    WARD_COL = "Area"          # adjust if your DF uses a different name
    CRIME_COL = "Crime Type"   # adjust if different
    total_cases = df[
        (df[WARD_COL] == ward) &
        (df[CRIME_COL] == crime_type)
    ].shape[0]

    if total_cases >= 36:
        confidence = "HIGH"
    elif total_cases >= 18:
        confidence = "LIMITED"
    else:
        confidence = "LOW"
         
    patrol_risk_score, risk_level = calculate_patrol_risk_score(
    time_concentration=top_window["percentage"],
    recent_weight=recent_activity["recent_weight"],
    total_cases=total_cases,
    density_status=recent["density_status"],
    velocity_status=recent["velocity_status"],
    is_weekend=is_weekend
)
    reasons = []
    if recent["density_status"] == "High":
        reasons.append("High crime density observed in the last 14 days.")

    if recent["velocity_status"] == "Elevated":
        reasons.append(f"{recent['last_48_hours']} incidents reported in the past 48 hours.")

    if is_weekend:
        reasons.append("Weekend time window historically shows higher risk.")

    if mode == "detailed":
        reasons.append(
            f"{top_window['percentage']}% of historical {crime_type} incidents "
            f"in {ward} occur during {top_window['time_bucket']} hours."
        )
        reasons.append(
            f"Recent activity score: {recent_activity['recent_weight']} "
            f"(last 7 days: {recent_activity['last_7_days']} cases)."
        )
    else:
        reasons.append(
            f"Highest concentration during {top_window['time_bucket']} hours."
        )

    return {
        "ward": ward,
        "crime_type": crime_type,
        "recommended_window": top_window["time_bucket"],
        "risk_percentage": top_window["percentage"],
        "reasons": reasons,
        "confidence": confidence,
        "recent_activity": recent_activity,
        "patrol_risk_score": patrol_risk_score,
        "risk_level": risk_level,
        "time_distribution": time_risk
    }



# =====================================================
# MULTI-ZONE TOP 5 RECOMMENDATION
# =====================================================
def get_top_wards(df, crime_type, top_n=5):
    wards = sorted(df["Area"].dropna().unique())
    ward_recs = []

    for ward in wards:
        rec = generate_patrol_recommendation(df, ward, crime_type)
        if rec:
            ward_recs.append(rec)

    # Sort by risk percentage descending
    ward_recs = sorted(ward_recs, key=lambda x: x["risk_percentage"], reverse=True)
    return ward_recs[:top_n]

def calculate_patrol_risk_score(
    time_concentration,   # 0–100 (% of incidents in peak hours)
    recent_weight,        # raw recent activity score
    total_cases,          # ward volume
    density_status,       # "Low" | "Medium" | "High"
    velocity_status,      # "Normal" | "Elevated"
    is_weekend
):
    # -------------------------
    # Core normalization
    # -------------------------
    time_score = time_concentration / 100          # → 0–1
    recent_score = min(recent_weight / 5, 1)       # cap recent spike impact
    volume_factor = min(total_cases / 20, 1)       # damp low-volume noise

    # Core risk (historical reality)
    base_risk = (
        0.55 * time_score +
        0.45 * recent_score
    ) * volume_factor

    # -------------------------
    # Context multipliers
    # -------------------------
    density_multiplier = {
        "Low": 0.95,
        "Medium": 1.0,
        "High": 1.15
    }.get(density_status, 1.0)

    velocity_multiplier = 1.1 if velocity_status == "Elevated" else 1.0
    weekend_multiplier = 1.05 if is_weekend else 1.0

    # Apply multipliers
    adjusted_risk = (
        base_risk *
        density_multiplier *
        velocity_multiplier *
        weekend_multiplier
    )

    # -------------------------
    # Clamp & classify
    # -------------------------
    final_risk = min(adjusted_risk, 1)

    if final_risk >= 0.7:
        risk_level = "HIGH"
    elif final_risk >= 0.4:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    return round(final_risk * 100, 1), risk_level

# =====================================================
# PATROL RECOMMENDATION VIEW (NEW PAGE)
# =====================================================
def patrol_recommendation_view(request):
    ward = request.GET.get("ward")
    crime_type = request.GET.get("crime_type")

    recommendation = None
    time_distribution = []
    top_wards = []

    if ward and crime_type:
        # Existing single-ward logic
        recommendation = generate_patrol_recommendation(
    raw_df, ward, crime_type, mode="detailed"
)

        time_distribution = compute_time_of_day_risk(
            raw_df, ward, crime_type
        )   

    # New multi-zone top 5 wards logic
    if crime_type:
        top_wards = get_top_wards(raw_df, crime_type, top_n=5)

    return render(request, "patrol_recommendations.html", {
        "wards": sorted(raw_df["Area"].dropna().unique()),
        "crime_types": sorted(raw_df["Crime Type"].dropna().unique()),
        "selected_ward": ward,
        "selected_crime": crime_type,
        "recommendation": recommendation,
        "time_distribution": time_distribution,
        "top_wards": top_wards,  # send to template
    })

def synthesize_reason(crime_type, time_bucket, time_pct, recent, is_weekend):
    reasons = []

    # Time dominance
    if time_pct >= 40:
        reasons.append(
            f"{crime_type} incidents historically peak during {time_bucket.lower()} hours."
        )

    # Recent pressure
    if recent["last_7_days"] == 0:
        reasons.append(
            "No incidents reported in the last 7 days, indicating low immediate pressure."
        )
    elif recent["last_7_days"] <= 3:
        reasons.append(
            "Limited recent activity suggests moderate monitoring is sufficient."
        )
    else:
        reasons.append(
            "Spike in recent incidents indicates elevated short-term risk."
        )

    # Weekend modifier
    if is_weekend:
        reasons.append(
            "Weekend patterns may increase opportunistic crime likelihood."
        )

    # Crime-type-aware patrol logic
    if crime_type.lower() == "cybercrime":
        reasons.append(
            "Recommendation favors cyber-cell monitoring over physical patrol presence."
        )

    return " ".join(reasons)




"""
sos_views.py  —  adapted to your actual models (userProfile, Ward, TrustedContact)
"""

import json
import math
from django.http import JsonResponse
from django.views import View
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from .models import SOSAlert, userProfile
from .sos_utils import (
    get_nearest_officers,
    get_ward_from_coordinates,
    build_alert_message,
    notify,
    notify_trusted_contacts,
    schedule_escalation,
    _escalate_to_sho,
    _haversine,
)


@method_decorator(csrf_exempt, name='dispatch')
class SOSTriggerView(View):
    """
    POST /api/sos/trigger/
    Fired after citizen's 10-second countdown completes.
    """

    def post(self, request):
        try:
            data      = json.loads(request.body)
            latitude  = float(data['latitude'])
            longitude = float(data['longitude'])

            # Use logged-in user (assumes session auth / JWT)
            citizen = request.user
            if not citizen.is_authenticated:
                return JsonResponse({'error': 'Login required'}, status=401)

            # 1. Resolve ward from coordinates
            ward = get_ward_from_coordinates(latitude, longitude)

            # 2. Create SOS record
            alert = SOSAlert.objects.create(
                citizen=citizen,
                latitude=latitude,
                longitude=longitude,
                ward=ward,
                status='pending',
            )

            # 3. Notify trusted contacts immediately (parallel concern)
            notify_trusted_contacts(alert, citizen)

            # 4. Find nearest officers
            officers = get_nearest_officers(latitude, longitude, ward, limit=3)

            if not officers:
                _escalate_to_sho(alert, reason="No on-duty officers found in area")
                return JsonResponse({
                    'alert_id': alert.id,
                    'status': 'escalated_to_sho',
                    'message': 'No officers available nearby — SHO has been alerted directly.',
                })

            # 5. Send alerts to officers
            message  = build_alert_message(alert, citizen, ward)
            sent_to  = []

            for officer in officers:
                # userProfile.phone is the field in your model
                phone = officer.phone or officer.contact
                if not phone:
                    continue

                if not phone.startswith('+'):
                    phone = '+91' + phone.lstrip('0')

                notify(phone, message)
                alert.notified_officers.add(officer)

                sent_to.append({
                    'officer_id':   officer.id,
                    'name':         officer.user.get_full_name() or officer.user.username,
                    'distance_km':  round(officer.distance_km, 2),
                    'specialty':    officer.specialty,
                })

            alert.status = 'notified'
            alert.save()

            # 6. Schedule SHO escalation if no acknowledgement in 5 mins
            schedule_escalation(alert.id, delay_minutes=5)

            return JsonResponse({
                'alert_id':        alert.id,
                'status':          'notified',
                'officers_alerted': sent_to,
                'message':         f'{len(sent_to)} officer(s) alerted near your location.',
            })

        except KeyError as e:
            return JsonResponse({'error': f'Missing field: {e}'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class SOSAcknowledgeView(View):
    """
    POST /api/sos/acknowledge/
    Officer taps "I'm responding" on their dashboard.
    Stops escalation from firing, notifies citizen.
    """

    def post(self, request):
        try:
            data      = json.loads(request.body)
            alert_id  = data['alert_id']
            officer_profile = userProfile.objects.get(user=request.user, role='police')

            alert = SOSAlert.objects.get(id=alert_id)

            if alert.status in ('resolved', 'escalated', 'cancelled'):
                return JsonResponse({'message': 'Alert already closed.'})

            alert.status          = 'acknowledged'
            alert.acknowledged_by = officer_profile
            alert.acknowledged_at = timezone.now()
            alert.save()

            # Notify citizen that help is on the way
            eta     = _estimate_eta(officer_profile, alert)
            citizen_phone = _get_citizen_phone(alert.citizen)

            if citizen_phone:
                officer_name = officer_profile.user.get_full_name() or officer_profile.user.username
                sms = (
                    f"Officer {officer_name} is responding to your SOS. "
                    f"ETA approx. {eta} min. Stay safe. Emergency: call 112."
                )
                notify(citizen_phone, sms)

            return JsonResponse({
                'status':  'acknowledged',
                'officer': officer_profile.user.get_full_name(),
                'eta_min': eta,
            })

        except (SOSAlert.DoesNotExist, userProfile.DoesNotExist):
            return JsonResponse({'error': 'Alert or officer not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class SOSCancelView(View):
    """
    POST /api/sos/cancel/
    Citizen cancels during the 10-second countdown.
    alert_id is optional — if not provided, cancels latest pending alert.
    """

    def post(self, request):
        try:
            data = json.loads(request.body)

            if 'alert_id' in data:
                alert = SOSAlert.objects.get(id=data['alert_id'], citizen=request.user)
            else:
                alert = SOSAlert.objects.filter(
                    citizen=request.user, status='pending'
                ).latest('triggered_at')

            if alert.status == 'pending':
                alert.status = 'cancelled'
                alert.save()
                return JsonResponse({'status': 'cancelled'})

            return JsonResponse(
                {'message': 'Alert already sent — cannot cancel.'},
                status=400
            )

        except SOSAlert.DoesNotExist:
            return JsonResponse({'error': 'No pending alert found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class OfficerLocationUpdateView(View):
    """
    POST /api/officer/location/
    Officers ping their GPS every 2–5 minutes from their dashboard.
    This keeps current_latitude/longitude fresh for SOS routing.
    """

    def post(self, request):
        try:
            data     = json.loads(request.body)
            profile  = userProfile.objects.get(user=request.user, role='police')

            profile.current_latitude    = data['latitude']
            profile.current_longitude   = data['longitude']
            profile.last_location_update = timezone.now()

            if 'is_on_duty' in data:
                profile.is_on_duty = data['is_on_duty']

            profile.save(update_fields=[
                'current_latitude', 'current_longitude',
                'last_location_update', 'is_on_duty'
            ])

            return JsonResponse({'status': 'location updated'})

        except userProfile.DoesNotExist:
            return JsonResponse({'error': 'Officer profile not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _estimate_eta(officer_profile, alert):
    """Rough ETA in minutes based on straight-line distance at 30 km/h urban speed."""
    if not officer_profile.current_latitude or not officer_profile.current_longitude:
        return "unknown"
    dist = _haversine(
        float(officer_profile.current_latitude),
        float(officer_profile.current_longitude),
        float(alert.latitude),
        float(alert.longitude),
    )
    return max(1, round((dist / 30) * 60))


def _get_citizen_phone(citizen_user):
    """Get phone from userProfile — your model stores it on the profile."""
    try:
        profile = userProfile.objects.get(user=citizen_user)
        phone = profile.phone or profile.contact
        if phone and not phone.startswith('+'):
            phone = '+91' + phone.lstrip('0')
        return phone
    except userProfile.DoesNotExist:
        return None


import json
import os
import requests
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.shortcuts import render
from groq import Groq


# ── Role-specific system prompts ─────────────────────────────────────────────

SYSTEM_PROMPTS = {
    "citizen": """You are SafetyNet, a public safety assistant for the Thane district police system.
You help citizens understand crime safety, report procedures, and area-specific information.

Guidelines:
- Answer based on Thane district crime context only
- Be empathetic and clear — citizens may be distressed
- If asked about an ongoing emergency, always direct them to dial 100 or SOS
- Do not speculate without data; say "data unavailable for this area" if needed
- Keep responses under 120 words unless the question genuinely requires more
- Never reveal internal police operations or officer identities""",

    "police": """You are SafetyNet, an AI assistant for Thane district police officers.
You help with case analysis, patrol recommendations, report drafting, and crime pattern insights.

Guidelines:
- Be precise and professional
- When summarising cases, use structured format: Incident / Evidence / Status / Recommended Action
- Flag if a case matches known crime patterns in the district
- Reference NCRB categories and IPC sections when relevant
- Keep responses factual and actionable""",

    "sho": """You are SafetyNet, a command-level AI assistant for Station House Officers in Thane district.
You help with officer assignment reasoning, workload analysis, report prioritisation, and district-level insights.

Guidelines:
- Provide executive-level summaries
- When discussing officer assignments, reference specialisation + seniority + workload score
- Highlight anomalies (e.g. underreporting in a ward, officer overload)
- Use NCRB benchmarks when comparing district performance
- Be concise and decision-ready""",
}


# ── Prompt builder ────────────────────────────────────────────────────────────

def build_prompt(user_message: str, role: str, context: dict):
    """
    Returns (system_prompt, enriched_user_message) with injected DB context.
    context dict can include: ward_stats, recent_cases, officer_info, etc.
    """
    system = SYSTEM_PROMPTS.get(role, SYSTEM_PROMPTS["citizen"])

    context_block = ""
    if context.get("ward_stats"):
        context_block += f"\n\nWard Crime Statistics:\n{json.dumps(context['ward_stats'], indent=2)}"
    if context.get("recent_cases"):
        context_block += f"\n\nRecent Cases in Area:\n{json.dumps(context['recent_cases'], indent=2)}"
    if context.get("patrol_data"):
        context_block += f"\n\nPatrol Recommendations:\n{json.dumps(context['patrol_data'], indent=2)}"

    enriched = user_message
    if context_block:
        enriched = f"[Relevant district data:{context_block}]\n\nUser question: {user_message}"

    return system, enriched


# ── Context fetcher (wire to your actual models) ──────────────────────────────

def fetch_context_for_query(user_message, role):
    from home.models import Ward, CrimeReport
    context = {}

    # Detect ward from message
    ward = detect_ward(user_message)
    if ward:
        stats = WardStats.objects.filter(ward_name=ward).values(
            "ward_name", "total_crimes", "top_crime_type", "month"
        )
        context["ward_stats"] = list(stats)

    if role == "police":
        recent = CrimeReport.objects.filter(status="open").order_by("-created_at")[:5].values(
            "id", "crime_type", "location", "status"
        )
        context["recent_cases"] = list(recent)

    return context

# ── Claude API caller ─────────────────────────────────────────────────────────
from groq import Groq
import os

def call_groq(system: str, messages: list, stream: bool = False):
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))


    formatted_messages = []

    if system:
        formatted_messages.append({
            "role": "system",
            "content": system
        })

    for msg in messages:
        formatted_messages.append({
            "role": msg.get("role"),
            "content": msg.get("content")
        })

    if stream:
        return client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=formatted_messages,
            max_tokens=1024,
            temperature=0.2,
            stream=True,
        )
    else:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=formatted_messages,
            max_tokens=1024,
            temperature=0.2,
        )
        return response

# ── Main chat endpoint ────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(["POST"])
def chat(request):
    """
    POST /ai/chat/
    Body: { "message": str, "history": [...], "role": str, "stream": bool }
    """
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    user_message = body.get("message", "").strip()
    history      = body.get("history", [])       # [{"role": "user"|"assistant", "content": str}]
    role         = body.get("role", "citizen")   # citizen | police | sho
    use_stream   = body.get("stream", True)

    if not user_message:
        return JsonResponse({"error": "Message is required"}, status=400)

    context = fetch_context_for_query(user_message, role)
    system_prompt, enriched_message = build_prompt(user_message, role, context)

    messages = history[-10:]  # keep last 10 turns within context window
    messages.append({"role": "user", "content": enriched_message})

    if use_stream:
        return _stream_response(system_prompt, messages)
    return _sync_response(system_prompt, messages)


def _stream_response(system: str, messages: list):
    def event_stream():
        try:
            resp = call_claude(system, messages, stream=True)
            for line in resp.iter_lines():
                if not line:
                    continue
                line = line.decode("utf-8")
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        yield "data: [DONE]\n\n"
                        break
                    try:
                        chunk = json.loads(data)
                        if chunk.get("type") == "content_block_delta":
                            text = chunk["delta"].get("text", "")
                            if text:
                                yield f"data: {json.dumps({'text': text})}\n\n"
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response


def _sync_response(system: str, messages: list):
    try:
        resp = call_claude(system, messages, stream=False)
        data = resp.json()
        reply = data["content"][0]["text"]
        return JsonResponse({"reply": reply})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# ── Page view ─────────────────────────────────────────────────────────────────

def assistant_page(request):
    role = "citizen"
    if request.user.is_authenticated:
        role = getattr(request.user, "role", "citizen")
    return render(request, "chat.html", {"role": role})

from django.http import JsonResponse
from django.core.management import call_command

def sync_news(request):
    call_command('fetch_news_intel')
    return JsonResponse({"status": "updated"})

"""
ADD THESE VIEWS TO YOUR views.py
=================================
These are the new intelligence feature views.
All existing views (sho_dashboard, intel_detail, sho_alerts, sync_news) remain UNCHANGED.
Just paste this block at the bottom of your views.py.
"""

# ─── existing imports you already have ───────────────────────────────────────
# from django.http import JsonResponse
# from django.db.models import Count
# from django.utils.timezone import now
# from datetime import timedelta
# from .models import NewsIntel

# ─── NEW imports to add at top of views.py ───────────────────────────────────
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json as _json


# ══════════════════════════════════════════════════════════════
# NEW VIEW 1 — Intelligence Command Center (full-page)
# GET /intel/
# ══════════════════════════════════════════════════════════════

def intel_center(request):
    """
    The main intelligence command center page.
    Replaces the basic news panel — this is the limelight feature.
    """
    from django.utils.timezone import now
    from datetime import timedelta

    last_24h = now() - timedelta(hours=24)

    # Top priority intel sorted by AI score
    top_intel = NewsIntel.objects.order_by("-priority_score", "-created_at")[:20]

    # Breakdown by crime type for the threat matrix
    threat_matrix = (
        NewsIntel.objects
        .filter(created_at__gte=last_24h)
        .values("crime_type")
        .annotate(count=Count("id"))
        .order_by("-count")[:8]
    )

    # Location hotspots
    hotspots = (
        NewsIntel.objects
        .filter(created_at__gte=last_24h, risk_level__in=["HIGH", "MEDIUM"])
        .values("location")
        .annotate(count=Count("id"))
        .order_by("-count")[:5]
    )

    # Stats
    total_24h   = NewsIntel.objects.filter(created_at__gte=last_24h).count()
    high_risk   = NewsIntel.objects.filter(created_at__gte=last_24h, risk_level="HIGH").count()
    escalating  = NewsIntel.objects.filter(
        created_at__gte=last_24h, threat_escalation="yes"
    ).count()

    context = {
        "top_intel":     top_intel,
        "threat_matrix": list(threat_matrix),
        "hotspots":      list(hotspots),
        "total_24h":     total_24h,
        "high_risk":     high_risk,
        "escalating":    escalating,
    }
    return render(request, "intel_center.html", context)


# ══════════════════════════════════════════════════════════════
# NEW VIEW 2 — AI SITREP API (called by intel_center.html)
# GET /api/intel/sitrep/
# ══════════════════════════════════════════════════════════════

def intel_sitrep(request):
    """
    Returns a fresh AI-generated situation report.
    Called every 60s by the intel center's live ticker.
    """
    from home.services.ai_service import generate_threat_brief

    alerts_qs = NewsIntel.objects.order_by("-priority_score", "-created_at")[:5]
    alerts = [{
        "risk_level":  a.risk_level,
        "crime_type":  a.crime_type,
        "location":    a.location,
        "summary":     a.summary,
    } for a in alerts_qs]

    patterns = detect_patterns()
    trends   = detect_trends()

    sitrep = generate_threat_brief(alerts, patterns, trends)

    return JsonResponse({"sitrep": sitrep})


# ══════════════════════════════════════════════════════════════
# NEW VIEW 3 — ASK INTEL (natural language Q&A)
# POST /api/intel/ask/
# ══════════════════════════════════════════════════════════════

@csrf_exempt
@require_http_methods(["POST"])
def ask_intel(request):
    """
    Officer types a natural language question.
    Groq answers from the live intelligence feed.
    """
    from home.services.ai_service import generate_ask_intel

    try:
        body     = _json.loads(request.body)
        question = body.get("question", "").strip()

        if not question:
            return JsonResponse({"error": "Question required"}, status=400)

        # Pass recent intel as context
        context_alerts = NewsIntel.objects.order_by("-priority_score")[:10]
        answer = generate_ask_intel(question, context_alerts)

        return JsonResponse({
            "answer":   answer,
            "question": question,
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# ══════════════════════════════════════════════════════════════
# NEW VIEW 4 — 48H PREDICTION API
# GET /api/intel/predict/?crime=Robbery&location=Thane
# ══════════════════════════════════════════════════════════════

def intel_predict(request):
    """
    Returns a 48-hour AI threat prediction for a crime/location pair.
    Called when SHO clicks a threat matrix cell.
    """
    from home.services.ai_service import generate_prediction
    from django.utils.timezone import now
    from datetime import timedelta

    crime_type = request.GET.get("crime", "").strip()
    location   = request.GET.get("location", "").strip()

    if not crime_type:
        return JsonResponse({"error": "crime parameter required"}, status=400)

    last_24h = now() - timedelta(hours=24)
    recent_count = NewsIntel.objects.filter(
        crime_type__icontains=crime_type,
        created_at__gte=last_24h,
    ).count()

    prediction = generate_prediction(crime_type, location or "Thane", recent_count)

    return JsonResponse({
        "crime_type":  crime_type,
        "location":    location,
        "recent_24h":  recent_count,
        "prediction":  prediction,
    })


# ══════════════════════════════════════════════════════════════
# NEW VIEW 5 — LIVE INTEL FEED API (polled every 30s)
# GET /api/intel/feed/
# ══════════════════════════════════════════════════════════════

def intel_feed(request):
    """
    Returns latest intel cards for live feed updates.
    Lightweight — no AI call, just DB query.
    """
    from django.utils.timezone import now
    from datetime import timedelta

    last_24h = now() - timedelta(hours=24)

    alerts = NewsIntel.objects.filter(
        risk_level__in=["HIGH", "MEDIUM"]
    ).order_by("-priority_score", "-created_at")[:10]

    total_24h  = NewsIntel.objects.filter(created_at__gte=last_24h).count()
    high_risk  = NewsIntel.objects.filter(created_at__gte=last_24h, risk_level="HIGH").count()
    escalating = NewsIntel.objects.filter(
        created_at__gte=last_24h, threat_escalation="yes"
    ).count()

    return JsonResponse({
        "alerts": [{
            "id":               a.id,
            "title":            a.title,
            "source":           a.source,
            "location":         a.location,
            "crime_type":       a.crime_type,
            "risk_level":       a.risk_level,
            "priority_score":   a.priority_score,
            "summary":          a.summary,
            "insight":          a.insight,
            "suggested_action": a.suggested_action,
            "threat_escalation":getattr(a, "threat_escalation", "no"),
            "image_url":        a.image_url or "",
            "published_at":     a.published_at.isoformat() if a.published_at else "",
            "detail_url":       f"/intel/{a.id}/",
        } for a in alerts],
        "stats": {
            "total_24h":  total_24h,
            "high_risk":  high_risk,
            "escalating": escalating,
        },
        "patterns": detect_patterns(),
        "trends":   detect_trends(),
    })

################################################################################################

# """
# incident_view.py — AI Incident Response Assistant

# POST /api/incident/analyze/
# Body: {
#     "text": "Fight near Kopri bridge, 2 injured",
#     "latitude": 19.2183,   (optional — from browser GPS)
#     "longitude": 72.9781
# }

# Returns structured AI response + nearest officer + map data.
# """

# import json
# import math
# from django.http import JsonResponse
# from django.views import View
# from django.utils import timezone
# from django.utils.decorators import method_decorator
# from django.views.decorators.csrf import csrf_exempt
# from groq import Groq
# from django.conf import settings


# @method_decorator(csrf_exempt, name='dispatch')
# class IncidentAnalyzeView(View):
#     """
#     Core AI incident analysis endpoint.
#     Works for both citizens and police officers.
#     Role is auto-detected from session.
#     """

#     def post(self, request):
#         try:
#             data      = json.loads(request.body)
#             text      = data.get('text', '').strip()
#             latitude  = data.get('latitude')
#             longitude = data.get('longitude')

#             if not text:
#                 return JsonResponse({'error': 'Incident description required'}, status=400)

#             # Detect user role
#             role = 'citizen'
#             user_name = 'Anonymous'
#             if request.user.is_authenticated:
#                 try:
#                     from home.models import userProfile
#                     profile   = userProfile.objects.get(user=request.user)
#                     role      = profile.role or 'citizen'
#                     user_name = request.user.get_full_name() or request.user.username
#                 except Exception:
#                     pass

#             # Get ward context if coordinates provided
#             ward_context = ''
#             ward_name    = None
#             if latitude and longitude:
#                 ward_name, ward_context = _get_ward_context(float(latitude), float(longitude))

#             # Get recent crime pattern context for this ward
#             pattern_context = _get_crime_pattern_context(ward_name)

#             # Call Claude for structured analysis
#             analysis = _analyze_incident(text, role, ward_context, pattern_context)

#             # Find nearest officers if coordinates provided
#             nearest_officers = []
#             nearest_station  = None
#             if latitude and longitude:
#                 nearest_officers = _get_nearest_officers(float(latitude), float(longitude), limit=3)
#                 nearest_station  = _get_nearest_station(float(latitude), float(longitude))

#             # Auto-alert if severity is high/critical and user is citizen
#             alert_sent = False
#             if analysis.get('severity') in ('high', 'critical') and role == 'citizen':
#                 if nearest_officers:
#                     alert_sent = _send_incident_alert(
#                         nearest_officers[:1],
#                         text, analysis, latitude, longitude, user_name
#                     )

#             return JsonResponse({
#                 'status':           'success',
#                 'analysis':         analysis,
#                 'ward':             ward_name,
#                 'nearest_officers': nearest_officers,
#                 'nearest_station':  nearest_station,
#                 'alert_sent':       alert_sent,
#                 'timestamp':        timezone.now().strftime('%H:%M:%S'),
#             })

#         except json.JSONDecodeError:
#             return JsonResponse({'error': 'Invalid JSON'}, status=400)
#         except Exception as e:
#             return JsonResponse({'error': str(e)}, status=500)


# # ──────────────────────────────────────────────────────────────
# # Claude Analysis
# # ──────────────────────────────────────────────────────────────

# def _analyze_incident(text, role, ward_context='', pattern_context=''):
#     """
#     Sends incident text to Claude.
#     Returns structured JSON with severity, actions, predictions.
#     """

#     role_instruction = {
#         'citizen': (
#             "You are an emergency response AI for Thane Police. "
#             "The user is a citizen reporting an incident. "
#             "Use simple, calm, reassuring language. "
#             "Prioritize their safety first."
#         ),
#         'police': (
#             "You are a tactical intelligence AI for Thane Police officers. "
#             "Use precise operational language. "
#             "Focus on deployment, escalation risk, and coordination."
#         ),
#         'sho': (
#             "You are a command intelligence AI for the Station Head Officer. "
#             "Focus on resource allocation, escalation risk, "
#             "and cross-ward coordination."
#         ),
#     }.get(role, 'citizen')

#     prompt = f"""
# {role_instruction}

# {f"Location context: {ward_context}" if ward_context else ""}
# {f"Recent crime patterns: {pattern_context}" if pattern_context else ""}

# A user has reported the following incident:
# "{text}"

# Analyze this incident and respond ONLY with this exact JSON structure:
# {{
#   "crime_type": "assault / theft / accident / fire / medical / disturbance / other",
#   "severity": "low / medium / high / critical",
#   "severity_score": 0-10,
#   "confidence": 0-100,
#   "summary": "one sentence plain summary of the incident",
#   "immediate_actions": [
#     "action 1 for the user right now",
#     "action 2",
#     "action 3"
#   ],
#   "dispatch_recommendation": "what units/resources should be dispatched",
#   "escalation_risk": "low / medium / high",
#   "escalation_reason": "why escalation risk is this level",
#   "safety_tip": "one safety tip specific to this incident type",
#   "estimated_response_time": "X-Y minutes",
#   "emergency_numbers": ["112", "1091"]
# }}

# Be concise. No markdown. Valid JSON only.
# """.strip()

#     client = Groq(api_key=settings.GROQ_API_KEY)

#     response = client.chat.completions.create(
#         model="llama-3.1-8b-instant",  # or mixtral / gemma
#         messages=[
#             {"role": "user", "content": prompt}
#         ],
#         max_tokens=600,
#         temperature=0.2,  # keep low for structured JSON
#     )

#     raw = response.choices[0].message.content.strip()

#     try:
#         return json.loads(raw)
#     except json.JSONDecodeError:
#         # Fallback safe response
#         return {
#             "crime_type":             "other",
#             "severity":               "medium",
#             "severity_score":         5,
#             "confidence":             60,
#             "summary":                text[:100],
#             "immediate_actions":      ["Call 112 immediately", "Stay safe", "Wait for assistance"],
#             "dispatch_recommendation": "Send nearest patrol unit",
#             "escalation_risk":        "medium",
#             "escalation_reason":      "Unable to fully analyze — manual review required",
#             "safety_tip":             "Stay in a safe, visible location",
#             "estimated_response_time": "10-15 minutes",
#             "emergency_numbers":      ["112", "1091"],
#         }


# # ──────────────────────────────────────────────────────────────
# # Ward + Pattern Context
# # ──────────────────────────────────────────────────────────────

# def _get_ward_context(lat, lon):
#     """Returns (ward_name, context_string) for given coordinates."""
#     try:
#         from home.models import Ward
#         wards = Ward.objects.exclude(centroid_latitude=None, centroid_longitude=None)
#         closest, min_dist = None, float('inf')
#         for ward in wards:
#             d = _haversine(lat, lon, float(ward.centroid_latitude), float(ward.centroid_longitude))
#             if d < min_dist:
#                 min_dist = d
#                 closest  = ward
#         if closest:
#             return closest.lgd_name, f"{closest.lgd_name}, {closest.townname}"
#         return None, ''
#     except Exception:
#         return None, ''


# def _get_crime_pattern_context(ward_name):
#     """Returns recent crime pattern string for the ward."""
#     if not ward_name:
#         return ''
#     try:
#         from home.models import CrimeRecord, Ward
#         from django.db.models import Count
#         import datetime
#         ward     = Ward.objects.get(lgd_name=ward_name)
#         cutoff   = timezone.now().date() - datetime.timedelta(days=30)
#         top      = (CrimeRecord.objects
#                     .filter(ward=ward, date_reported__gte=cutoff)
#                     .values('crime_type')
#                     .annotate(c=Count('id'))
#                     .order_by('-c')[:3])
#         if top:
#             crimes = ', '.join(f"{r['crime_type']}({r['c']})" for r in top)
#             return f"Last 30 days in {ward_name}: {crimes}"
#     except Exception:
#         pass
#     return ''


# # ──────────────────────────────────────────────────────────────
# # Nearest Officers + Station
# # ──────────────────────────────────────────────────────────────

# def _get_nearest_officers(lat, lon, limit=3):
#     """Returns nearest on-duty officers as list of dicts."""
#     try:
#         from home.models import userProfile
#         officers = list(userProfile.objects.filter(
#             role='police', is_on_duty=True, is_approved=True,
#         ).exclude(current_latitude=None, current_longitude=None))

#         for o in officers:
#             o._dist = _haversine(lat, lon,
#                                  float(o.current_latitude),
#                                  float(o.current_longitude))

#         officers.sort(key=lambda o: o._dist)
#         return [
#             {
#                 'id':           o.id,
#                 'name':         o.user.get_full_name() or o.user.username,
#                 'specialty':    o.specialty or 'General',
#                 'distance_km':  round(o._dist, 2),
#                 'phone':        o.phone or o.contact or '',
#                 'latitude':     float(o.current_latitude),
#                 'longitude':    float(o.current_longitude),
#             }
#             for o in officers[:limit]
#         ]
#     except Exception:
#         return []


# def _get_nearest_station(lat, lon):
#     """Returns nearest police station as dict."""
#     try:
#         from home.models import PoliceStation
#         stations = list(PoliceStation.objects.all())
#         # PoliceStation may not have coordinates — return first one as fallback
#         if stations:
#             return {'name': stations[0].name, 'address': stations[0].address or ''}
#     except Exception:
#         pass
#     return None


# # ──────────────────────────────────────────────────────────────
# # Auto-Alert
# # ──────────────────────────────────────────────────────────────

# def _send_incident_alert(officers, text, analysis, lat, lon, reporter_name):
#     """Sends SMS alert to nearest officer for high/critical incidents."""
#     try:
#         from home.sos_utils import send_sms
#         maps_link = f"https://maps.google.com/?q={lat},{lon}" if lat and lon else "Location unavailable"
#         severity  = analysis.get('severity', 'unknown').upper()
#         crime     = analysis.get('crime_type', 'incident')

#         message = (
#             f"[{severity} INCIDENT] {crime.title()} reported by {reporter_name}. "
#             f"Location: {maps_link}. "
#             f"Details: {text[:100]}. "
#             f"Action: {analysis.get('dispatch_recommendation', 'Respond immediately')}."
#         )

#         for officer in officers:
#             phone = officer.get('phone', '')
#             if phone:
#                 if not phone.startswith('+'):
#                     phone = '+91' + phone.lstrip('0')
#                 send_sms(phone, message)

#         return True
#     except Exception as e:
#         print(f"[Alert Error] {e}")
#         return False


# def _haversine(lat1, lon1, lat2, lon2):
#     R = 6371
#     dlat = math.radians(lat2 - lat1)
#     dlon = math.radians(lon2 - lon1)
#     a    = (math.sin(dlat/2)**2 +
#             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
#             math.sin(dlon/2)**2)
#     return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

"""

views.py — CrimeCast Complete Views
All 12 view classes merged into one file.
Change 'home' to your actual app name throughout.
"""

# ── Dispatch engine (station-based dispatch) ──────────────────────────────────
from home.dispatch_engine import (          
    resolve_station,
    pick_officer,
    pick_nearest_officer,
    create_real_alert,
    reassign_alert,
    get_sho_for_station,
    _log_timeline,
)

import json
import math
import datetime
from django.http import JsonResponse
from django.views import View
from django.views.generic import TemplateView
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.conf import settings

from home.models import (                   # ← change 'home'
    IncidentAlert, IncidentStatus, IncidentTimeline,
    userProfile,                            # your existing user profile model
)


# ══════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════

CRITICAL_KEYWORDS = [
    "gun", "pistol", "rifle", "shoot", "shooting", "shot",
    "knife", "stabbed", "stabbing", "blade",
    "blood", "bleeding", "unconscious", "not breathing", "no pulse",
    "fire", "burning", "explosion", "bomb",
    "kidnap", "kidnapping", "abduction",
    "rape", "sexual assault",
    "murder", "killing", "dead body", "corpse",
    "overdose", "suicide", "hanging",
    "acid attack", "mob", "riot",
]

HIGH_KEYWORDS = [
    "fight", "assault", "beating", "attack", "hit", "punch",
    "theft", "robbery", "snatching", "stolen",
    "accident", "crash", "collision", "injured", "injury",
    "fainted", "collapsed",
    "domestic violence", "harassment",
    "drug", "narcotics",
]

CRIME_TYPE_KEYWORDS = {
    "assault":   ["fight", "assault", "beating", "attack", "punch", "hit", "stab", "knife", "weapon"],
    "theft":     ["theft", "robbery", "snatching", "stolen", "pickpocket", "chain snatching"],
    "fire":      ["fire", "burning", "smoke", "flames", "explosion"],
    "medical":   ["unconscious", "not breathing", "heart", "collapsed", "fainted", "overdose", "injured"],
    "kidnapping":["kidnap", "abduction", "missing", "taken"],
    "sexual":    ["rape", "sexual assault", "molestation", "harassment"],
    "accident":  ["accident", "crash", "collision", "vehicle"],
    "narcotics": ["drug", "narcotics", "dealer", "smuggling"],
}

LANDMARK_MAP = {
    "kopri":         "Ward No.21",
    "station road":  "Ward No.1",
    "thane station": "Ward No.1",
    "viviana":       "Ward No.15",
    "korum":         "Ward No.8",
    "upvan":         "Ward No.12",
    "hiranandani":   "Ward No.40",
    "ambernath":     "Ward No.35",
    "kalwa":         "Ward No.28",
    "wagle":         "Ward No.16",
    "charai":        "Ward No.3",
    "ghantali":      "Ward No.7",
    "naupada":       "Ward No.5",
}


# ══════════════════════════════════════════════════════════════
# SAFETY RULES OVERRIDE
# ══════════════════════════════════════════════════════════════

def apply_safety_rules(text, ai_output):
    text_lower = text.lower()
    overridden = False

    if any(k in text_lower for k in CRITICAL_KEYWORDS):
        ai_output["severity"]   = "critical"
        ai_output["confidence"] = max(ai_output.get("confidence", 50), 95)
        ai_output["override"]   = True
        overridden = True
    elif any(k in text_lower for k in HIGH_KEYWORDS):
        if ai_output.get("severity") in ("low", "medium"):
            ai_output["severity"]   = "high"
            ai_output["confidence"] = max(ai_output.get("confidence", 50), 85)
            ai_output["override"]   = True
            overridden = True

    detected_type = _detect_crime_type(text_lower)
    if detected_type and ai_output.get("crime_type") in (None, "other", ""):
        ai_output["crime_type"] = detected_type

    ai_output["rule_override"] = overridden
    return ai_output


def _detect_crime_type(text_lower):
    for crime_type, keywords in CRIME_TYPE_KEYWORDS.items():
        if any(k in text_lower for k in keywords):
            return crime_type
    return None


# ══════════════════════════════════════════════════════════════
# SAFETY SCORE ENGINE
# ══════════════════════════════════════════════════════════════

def compute_safety_score(ward_name, crime_type):
    if not ward_name:
        return 5.0
    try:
        from home.models import CrimeRecord   # ← change 'home'
        cutoff = timezone.now().date() - datetime.timedelta(days=30)
        total = CrimeRecord.objects.filter(
            ward__lgd_name=ward_name, date_reported__gte=cutoff
        ).count()
        if total == 0:
            return 3.0
        type_count = CrimeRecord.objects.filter(
            ward__lgd_name=ward_name,
            crime_type__iexact=crime_type,
            date_reported__gte=cutoff,
        ).count()
        volume_score = min(5.0, (total / 20) * 5)
        type_score   = min(5.0, (type_count / max(total, 1)) * 10)
        return min(10.0, round(volume_score + type_score, 2))
    except Exception as e:
        print(f"[Safety Score Error] {e}")
        return 5.0


def compute_time_risk_factor():
    hour = timezone.now().hour
    if 22 <= hour or hour < 5:
        return 1.4, "night"
    elif 5 <= hour < 8:
        return 1.1, "early_morning"
    elif 18 <= hour < 22:
        return 1.2, "evening"
    return 1.0, "day"


# ══════════════════════════════════════════════════════════════
# LOCATION RESOLUTION
# ══════════════════════════════════════════════════════════════

def resolve_location(latitude, longitude, landmark=None):
    if latitude and longitude:
        ward_name, ward_ctx = _get_ward_from_coords(float(latitude), float(longitude))
        return float(latitude), float(longitude), ward_name, ward_ctx, 'gps'
    if landmark:
        ward_name = _ward_from_landmark(landmark)
        return None, None, ward_name, f"Near {landmark}, Thane", 'landmark'
    return None, None, None, '', 'unknown'


def _ward_from_landmark(landmark):
    lm = landmark.lower()
    for key, ward in LANDMARK_MAP.items():
        if key in lm:
            return ward
    return None


def _get_ward_from_coords(lat, lon):
    try:
        from home.models import Ward   # ← change 'home'
        wards = Ward.objects.exclude(centroid_latitude=None, centroid_longitude=None)
        closest, min_dist = None, float('inf')
        for w in wards:
            d = _haversine(lat, lon, float(w.centroid_latitude), float(w.centroid_longitude))
            if d < min_dist:
                min_dist, closest = d, w
        if closest:
            return closest.lgd_name, f"{closest.lgd_name}, {closest.townname}"
    except Exception:
        pass
    return None, ''


# ══════════════════════════════════════════════════════════════
# ESCALATION PREDICTION
# ══════════════════════════════════════════════════════════════

def predict_escalation(text, ward_name, crime_type, time_factor):
    score, reasons = 0, []
    crowd_words   = ["crowd", "gathering", "mob", "people watching", "group", "bystanders"]
    weapon_words  = ["knife", "gun", "rod", "weapon", "armed", "blade"]
    alcohol_words = ["drunk", "drinking", "alcohol", "intoxicated"]

    if any(w in text.lower() for w in crowd_words):
        score += 25; reasons.append("crowd present")
    if any(w in text.lower() for w in weapon_words):
        score += 35; reasons.append("weapon involved")
    if any(w in text.lower() for w in alcohol_words):
        score += 20; reasons.append("intoxication involved")
    if time_factor >= 1.3:
        score += 15; reasons.append("night-time incident")

    high_esc_types = {"assault": 20, "sexual": 25, "kidnapping": 30, "riot": 35}
    score += high_esc_types.get(crime_type, 5)
    if crime_type in high_esc_types:
        reasons.append(f"{crime_type} type")

    if ward_name:
        try:
            from home.models import CrimeRecord   # ← change 'home'
            cutoff = timezone.now().date() - datetime.timedelta(days=30)
            recent = CrimeRecord.objects.filter(
                ward__lgd_name=ward_name, date_reported__gte=cutoff
            ).count()
            if recent > 10:
                score += 10; reasons.append("high-crime ward")
        except Exception:
            pass

    probability = min(95, score)
    reason_str  = ", ".join(reasons) if reasons else "no major escalation indicators"
    return probability, reason_str


# ══════════════════════════════════════════════════════════════
# AI ANALYSIS
# ══════════════════════════════════════════════════════════════

def analyze_with_groq(text, role, location_str, pattern_context,
                      safety_score, time_label, escalation_prob):
    from groq import Groq

    role_inst = {
        'citizen': "You are a calm emergency assistant for Thane Police. Use simple, reassuring language.",
        'police':  "You are a tactical AI for Thane Police officers. Use precise operational language.",
        'sho':     "You are a command AI for the Station Head Officer. Focus on resource allocation.",
    }.get(role, "You are an emergency assistant for Thane Police.")

    prompt = f"""
{role_inst}

Location: {location_str or "Thane, Maharashtra"}
Area safety score: {safety_score}/10 (higher = more dangerous)
Time of day: {time_label}
Escalation probability: {escalation_prob}%
{f"Recent crime patterns: {pattern_context}" if pattern_context else ""}

Incident reported:
"{text}"

Respond ONLY in this exact JSON (no markdown, no extra text):
{{
  "crime_type": "assault/theft/fire/medical/kidnapping/sexual/accident/narcotics/fraud/other",
  "severity": "low/medium/high/critical",
  "severity_score": 1-10,
  "confidence": 0-100,
  "summary": "one sentence factual summary",
  "immediate_actions": ["action 1", "action 2", "action 3"],
  "dispatch_recommendation": "specific units/resources needed",
  "escalation_prediction": "yes/no",
  "escalation_probability": 0-100,
  "escalation_reason": "specific reason based on incident details",
  "safety_tip": "one practical safety tip",
  "estimated_response_time": "X-Y minutes",
  "emergency_numbers": ["112", "1091"]
}}
""".strip()

    try:
        client   = Groq(api_key=settings.GROQ_API_KEY)
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=600,
            temperature=0.2,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except Exception as e:
        print(f"[Groq Error] {e}")
        return _fallback_analysis(text)


def _fallback_analysis(text):
    return {
        "crime_type":              _detect_crime_type(text.lower()) or "other",
        "severity":                "high",
        "severity_score":          7,
        "confidence":              60,
        "summary":                 "Incident requires immediate attention. Manual review recommended.",
        "immediate_actions":       ["Call 112 immediately", "Stay in a safe location", "Do not confront the situation alone"],
        "dispatch_recommendation": "Send nearest patrol unit immediately",
        "escalation_prediction":   "yes",
        "escalation_probability":  70,
        "escalation_reason":       "AI analysis unavailable — defaulting to high alert",
        "safety_tip":              "Stay calm and keep a safe distance",
        "estimated_response_time": "10-15 minutes",
        "emergency_numbers":       ["112", "1091"],
    }


# ══════════════════════════════════════════════════════════════
# PATTERN CONTEXT + HAVERSINE
# ══════════════════════════════════════════════════════════════

def _get_pattern_context(ward_name):
    if not ward_name:
        return ''
    try:
        from home.models import CrimeRecord   # ← change 'home'
        from django.db.models import Count
        cutoff = timezone.now().date() - datetime.timedelta(days=30)
        top = (CrimeRecord.objects
               .filter(ward__lgd_name=ward_name, date_reported__gte=cutoff)
               .values('crime_type').annotate(c=Count('id')).order_by('-c')[:3])
        if top:
            return ', '.join(f"{r['crime_type']}({r['c']})" for r in top)
    except Exception:
        pass
    return ''


def _haversine(lat1, lon1, lat2, lon2):
    R  = 6371
    d1 = math.radians(lat2 - lat1)
    d2 = math.radians(lon2 - lon1)
    a  = (math.sin(d1 / 2) ** 2 +
          math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
          math.sin(d2 / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ══════════════════════════════════════════════════════════════
# VIEW 1 — CITIZEN INCIDENT PAGE
# ══════════════════════════════════════════════════════════════

class CitizenIncidentView(TemplateView):
    """
    GET /incident/
    Serves the citizen reporting page. No login required.
    After submit, JS calls /api/incident/analyze/ and redirects to /incident/track/<id>/
    """
    template_name = 'citizen_incident.html'


# ══════════════════════════════════════════════════════════════
# VIEW 2 — CITIZEN TRACK PAGE
# ══════════════════════════════════════════════════════════════

class CitizenTrackView(TemplateView):
    """
    GET /incident/track/<alert_id>/
    Citizen live-tracking page — polls /api/incident/live/ every 5s.
    """
    template_name = 'citizen_track.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        alert_id = self.kwargs.get('alert_id')
        try:
            alert = IncidentAlert.objects.select_related(
                'assigned_officer__user', 'assigned_officer__station', 'station'
            ).get(id=alert_id)
            ctx['alert']      = alert
            ctx['alert_json'] = json.dumps(alert.to_dict())
        except IncidentAlert.DoesNotExist:
            ctx['alert'] = None
        return ctx


# ══════════════════════════════════════════════════════════════
# VIEW 3 — OFFICER DASHBOARD PAGE
# ══════════════════════════════════════════════════════════════

class OfficerDashboardView(TemplateView):
    """
    GET /officer/dashboard/
    Officer incident management panel — polls /api/incident/officer-alerts/ every 5s.
    """
    template_name = 'officer_dashboard.html'

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            profile = userProfile.objects.select_related('station').get(user=self.request.user)
            ctx['officer'] = profile
        except userProfile.DoesNotExist:
            ctx['officer'] = None
        return ctx


# ══════════════════════════════════════════════════════════════
# VIEW 4 — INCIDENT ANALYZE (AI + dispatch)
# ══════════════════════════════════════════════════════════════

@method_decorator(csrf_exempt, name='dispatch')
class IncidentAnalyzeView(View):
    """
    POST /api/incident/analyze/
    Core endpoint: AI analysis → safety override → station dispatch → alert creation.
    Returns alert_id so citizen JS can redirect to tracking page.
    """

    def post(self, request):
        try:
            data      = json.loads(request.body)
            text      = data.get('text', '').strip()
            latitude  = data.get('latitude')
            longitude = data.get('longitude')
            landmark  = data.get('landmark', '').strip()
            is_panic  = data.get('panic', False)

            if not text:
                if is_panic:
                    text = "Emergency — need immediate help"
                else:
                    return JsonResponse({'error': 'Incident description required'}, status=400)

            # Role detection
            role, user_name = 'citizen', 'Anonymous'
            if request.user.is_authenticated:
                try:
                    p         = userProfile.objects.get(user=request.user)
                    role      = p.role or 'citizen'
                    user_name = request.user.get_full_name() or request.user.username
                except Exception:
                    pass

            # Location
            lat, lon, ward_name, location_str, loc_method = resolve_location(
                latitude, longitude, landmark
            )

            # Time risk
            time_factor, time_label = compute_time_risk_factor()

            # Pattern context from DB
            pattern_context = _get_pattern_context(ward_name)

            # Pre-compute escalation (heuristic — no LLM needed)
            detected_type = _detect_crime_type(text.lower())
            esc_prob, _   = predict_escalation(text, ward_name, detected_type or 'other', time_factor)

            # Pre-compute safety score
            safety_score = compute_safety_score(ward_name, detected_type or 'other')

            # AI analysis
            analysis = analyze_with_groq(
                text, role, location_str, pattern_context,
                safety_score, time_label, esc_prob
            )

            # Safety rules override — always runs last, non-negotiable
            analysis = apply_safety_rules(text, analysis)

            # Inject real data scores
            analysis['area_risk_score']        = safety_score
            analysis['time_risk']              = time_label
            analysis['time_factor']            = time_factor
            analysis['location_method']        = loc_method
            analysis['escalation_probability'] = max(
                analysis.get('escalation_probability', 0), esc_prob
            )

            # Station-based dispatch
            crime_type = analysis.get('crime_type', '')

            officer = pick_nearest_officer(lat, lon, crime_type)

            if officer:
                station = officer.station
            else:
                station = resolve_station(lat=lat, lon=lon)
                officer = pick_officer(station, crime_type)
                

            # 🚨 FALLBACK 1: Any available officer
            if not officer and station:
                from home.models import userProfile
                officer = userProfile.objects.filter(
                    station=station,
                    role='police'
                ).order_by('active_case_count').first()

            # 🚨 FALLBACK 2: SHO (GUARANTEED ASSIGNMENT)
            if not officer and station:
                officer = get_sho_for_station(station)
            
            

            # Create DB alert + send SMS
            alert_id, alert_sent = create_real_alert(
                request, text, analysis, lat, lon,
                ward_name, landmark, station, officer, user_name
            )

            # Officer info for frontend
            officer_info = []
            if officer:
                officer_info = [{
                    'id':          officer.id,
                    'name':        officer.user.get_full_name() or officer.user.username,
                    'specialty':   officer.specialty or 'General',
                    'experience':  getattr(officer, 'experience_level', 'Junior') or 'Junior',
                    'station':     station.name if station else 'Unknown',
                    'phone':       officer.phone or getattr(officer, 'contact', '') or '',
                    'distance_km': 'N/A',
                    'rank_score':  'Assigned by station',
                }]

            nearest_station = {
                'name':    station.name    if station else 'Unknown',
                'address': station.address if station else '',
            } if station else None

            return JsonResponse({
                'status':           'success',
                'analysis':         analysis,
                'alert_id':         alert_id,           # ← JS uses this to redirect
                'ward':             ward_name,
                'station':          station.name if station else None,
                'location_method':  loc_method,
                'nearest_officers': officer_info,
                'nearest_station':  nearest_station,
                'alert_sent':       alert_sent,
                'officer_assigned': (officer.user.get_full_name() if officer else None),
                'timestamp':        timezone.now().strftime('%H:%M:%S'),
            })

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


# ══════════════════════════════════════════════════════════════
# VIEW 5 — OFFICER ACKNOWLEDGE (accept / reject from notification widget)
# ══════════════════════════════════════════════════════════════

@method_decorator(csrf_exempt, name='dispatch')
class IncidentAcknowledgeView(View):
    """POST /api/incident/acknowledge/"""

    def post(self, request):
        try:
            data     = json.loads(request.body)
            alert_id = data.get('alert_id')
            action   = data.get('action')

            if action not in ('accept', 'reject'):
                return JsonResponse({'error': 'action must be accept or reject'}, status=400)

            alert = IncidentAlert.objects.get(id=alert_id)

            if alert.status != IncidentStatus.PENDING:
                return JsonResponse({'message': 'Alert already handled', 'status': alert.status})

            if action == 'accept':
                if alert.assigned_officer and alert.assigned_officer.role == 'sho':
                    alert.status = IncidentStatus.ENROUTE   # ← KEY CHANGE
                else:
                    alert.status = IncidentStatus.ACCEPTED
                alert.accepted_at  = timezone.now()
                alert.responded_at = timezone.now()
                alert.save()
                _log_timeline(alert, IncidentStatus.ACCEPTED, note='Officer accepted via notification.')
                _notify_citizen_status(alert, IncidentStatus.ACCEPTED)
                return JsonResponse({
                    'status':   'accepted',
                    'message':  'You are now assigned to this incident. Navigate to location.',
                    'maps_url': alert.maps_url,
                })
            else:
                alert.status       = IncidentStatus.REJECTED
                alert.responded_at = timezone.now()
                alert.save()
                _log_timeline(alert, IncidentStatus.REJECTED, note='Officer rejected via notification.')
                reassigned = reassign_alert(alert)
                return JsonResponse({
                    'status':     'rejected',
                    'message':    'Alert rejected.',
                    'reassigned': reassigned,
                })

        except IncidentAlert.DoesNotExist:
            return JsonResponse({'error': 'Alert not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


# ══════════════════════════════════════════════════════════════
# VIEW 6 — PENDING ALERTS (polled by officer notification widget)
# ══════════════════════════════════════════════════════════════

class PendingAlertsView(View):
    """GET /api/incident/pending/"""

    def get(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Login required'}, status=401)
        try:
            profile = userProfile.objects.select_related('station').get(user=request.user)

            if profile.role == 'sho':
                alerts = IncidentAlert.objects.filter(
                    station=profile.station,
                    status__in=[
                        IncidentStatus.PENDING,
                        IncidentStatus.ACCEPTED,
                        IncidentStatus.ESCALATED
                    ]
                ).order_by('-created_at')[:20]

            else:
                alerts = IncidentAlert.objects.filter(
                    assigned_officer=profile,
                    status__in=[
                        IncidentStatus.PENDING,
                        IncidentStatus.ACCEPTED
                    ]
                ).order_by('-created_at')[:10]

            result = []
            for a in alerts:
                if a.status == IncidentStatus.PENDING and a.is_expired():
                    a.status = IncidentStatus.REJECTED
                    a.save(update_fields=['status'])
                    _log_timeline(a, IncidentStatus.REJECTED,
                                  note='Auto-expired: no response within 30 seconds')
                    reassign_alert(a)
                    continue
                result.append({
                    **a.to_dict(),
                    'seconds_ago':    a.elapsed_seconds,
                    'sho_escalated':  a.status == IncidentStatus.ESCALATED,
                    'station':        (a.assigned_officer.station.name
                                       if a.assigned_officer and a.assigned_officer.station
                                       else 'Unknown'),
                })

            return JsonResponse({'alerts': result, 'count': len(result)})

        except userProfile.DoesNotExist:
            return JsonResponse({'alerts': [], 'count': 0})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


# ══════════════════════════════════════════════════════════════
# VIEW 7 — RESOLVE + OFFICER FEEDBACK
# ══════════════════════════════════════════════════════════════

@method_decorator(csrf_exempt, name='dispatch')
class ResolveAlertView(View):
    """POST /api/incident/resolve/"""

    def post(self, request):
        try:
            data     = json.loads(request.body)
            alert_id = data.get('alert_id')
            alert    = IncidentAlert.objects.get(id=alert_id)

            alert.status               = IncidentStatus.RESOLVED
            alert.resolved_at          = timezone.now()
            alert.ai_correct           = data.get('ai_correct')
            alert.actual_severity      = data.get('actual_severity', '')
            alert.actual_response_time = data.get('response_time_minutes')
            alert.compute_metrics()

            if alert.assigned_officer:
                alert.assigned_officer.active_case_count = max(
                    0, alert.assigned_officer.active_case_count - 1
                )
                alert.assigned_officer.save(update_fields=['active_case_count'])

            alert.save()
            _log_timeline(alert, IncidentStatus.RESOLVED,
                          actor=request.user if request.user.is_authenticated else None,
                          note=data.get('note', 'Incident resolved.'))
            _notify_citizen_status(alert, IncidentStatus.RESOLVED)

            return JsonResponse({'status': 'resolved', 'message': 'Incident resolved. Feedback recorded.'})

        except IncidentAlert.DoesNotExist:
            return JsonResponse({'error': 'Alert not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


# ══════════════════════════════════════════════════════════════
# VIEW 8 — UPDATE STATUS (officer dashboard action buttons)
# ══════════════════════════════════════════════════════════════

@method_decorator(csrf_exempt, name='dispatch')
class UpdateStatusView(View):
    """POST /api/incident/update-status/"""

    def post(self, request):
        try:
            data       = json.loads(request.body)
            alert_id   = data.get('alert_id')
            new_status = data.get('status', '').strip()
            note       = data.get('note', '').strip()

            if not alert_id or not new_status:
                return JsonResponse({'error': 'alert_id and status are required'}, status=400)

            if new_status not in dict(IncidentStatus.CHOICES):
                return JsonResponse({'error': f'Invalid status: {new_status}'}, status=400)

            alert = IncidentAlert.objects.select_related(
                'assigned_officer__user', 'station'
            ).get(id=alert_id)

            # Auth check
            if request.user.is_authenticated:
                try:
                    profile = userProfile.objects.get(user=request.user)
                    if alert.assigned_officer and alert.assigned_officer.id != profile.id:
                        if not (profile.role == 'sho' and alert.is_escalated):
                            return JsonResponse({'error': 'Not authorised'}, status=403)
                except userProfile.DoesNotExist:
                    return JsonResponse({'error': 'Officer profile not found'}, status=403)

            # Transition validation
            current = alert.status
            if not IncidentStatus.can_transition(current, new_status):
                return JsonResponse({
                    'error':   f'Invalid transition: {current} → {new_status}',
                    'allowed': IncidentStatus.VALID_TRANSITIONS.get(current, []),
                }, status=400)

            alert.status = new_status
            alert.set_status_timestamp(new_status)

            if new_status == IncidentStatus.RESOLVED:
                alert.compute_metrics()
                if alert.assigned_officer:
                    alert.assigned_officer.active_case_count = max(
                        0, alert.assigned_officer.active_case_count - 1
                    )
                    alert.assigned_officer.save(update_fields=['active_case_count'])

            alert.save()

            default_notes = {
                IncidentStatus.ACCEPTED: 'Officer accepted the incident.',
                IncidentStatus.ENROUTE:  'Officer is en route to the location.',
                IncidentStatus.ARRIVED:  'Officer has arrived at the scene.',
                IncidentStatus.RESOLVED: 'Incident has been resolved.',
                IncidentStatus.REJECTED: 'Officer rejected the incident.',
            }
            actor = request.user if request.user.is_authenticated else None
            _log_timeline(alert, new_status, actor=actor,
                          note=note or default_notes.get(new_status, ''))

            if new_status == IncidentStatus.REJECTED:
                reassign_alert(alert)

            _notify_citizen_status(alert, new_status)

            return JsonResponse({
                'status':       'ok',
                'alert':        alert.to_dict(),
                'transitioned': f'{current} → {new_status}',
            })

        except IncidentAlert.DoesNotExist:
            return JsonResponse({'error': 'Alert not found'}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


# ══════════════════════════════════════════════════════════════
# VIEW 9 — LIVE STATUS (citizen tracking page polls this)
# ══════════════════════════════════════════════════════════════

class LiveStatusView(View):
    """GET /api/incident/live/<alert_id>/"""

    def get(self, request, alert_id):
        try:
            alert = IncidentAlert.objects.select_related(
                'assigned_officer__user', 'assigned_officer__station', 'station'
            ).get(id=alert_id)
            return JsonResponse({'ok': True, 'alert': alert.to_dict()})
        except IncidentAlert.DoesNotExist:
            return JsonResponse({'error': 'Alert not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
        
# ============================================================
# ADD THIS VIEW to your views.py
# Place it near the other API views (e.g. after LiveStatusView)
# ============================================================

class OfficerLocationView(View):
    """
    GET /api/incident/officer-location/<alert_id>/

    Returns officer's current GPS coordinates for a given alert.
    Called by citizen tracking page every 5 seconds when status
    is 'enroute' or 'arrived'.

    Response:
    {
        "available": true,
        "latitude": 19.2183,
        "longitude": 72.9781,
        "officer_name": "Rahul Patil",
        "status": "enroute",
        "incident_lat": 19.2200,
        "incident_lon": 72.9800
    }

    Returns available: false when:
    - Status is not enroute/arrived (no point showing map)
    - Officer has no GPS location stored
    - Alert not found
    """

    def get(self, request, alert_id):
        try:
            alert = IncidentAlert.objects.select_related(
                'assigned_officer__user',
            ).get(id=alert_id)

            # Only expose location when officer is actively responding
            if alert.status not in (IncidentStatus.ENROUTE, IncidentStatus.ARRIVED,IncidentStatus.ESCALATED):
                return JsonResponse({'available': False, 'status': alert.status})

            officer = alert.assigned_officer
            if not officer:
                return JsonResponse({'available': False, 'reason': 'no_officer'})

            # Check officer has a recent GPS fix
            o_lat = officer.current_latitude
            o_lon = officer.current_longitude

            if o_lat is None or o_lon is None:
                return JsonResponse({'available': False, 'reason': 'no_gps'})

            return JsonResponse({
                'available':    True,
                'latitude':     float(o_lat),
                'longitude':    float(o_lon),
                'officer_name': officer.user.get_full_name() or officer.user.username,
                'status':       alert.status,
                # Incident location so client can draw the route
                'incident_lat': float(alert.latitude)  if alert.latitude  else None,
                'incident_lon': float(alert.longitude) if alert.longitude else None,
            })

        except IncidentAlert.DoesNotExist:
            return JsonResponse({'available': False, 'reason': 'not_found'}, status=404)
        except Exception as e:
            return JsonResponse({'available': False, 'reason': str(e)}, status=500)


# ══════════════════════════════════════════════════════════════
# VIEW 10 — TIMELINE (citizen tracking page polls this)
# ══════════════════════════════════════════════════════════════

class TimelineView(View):
    """GET /api/incident/timeline/<alert_id>/"""

    def get(self, request, alert_id):
        try:
            alert   = IncidentAlert.objects.get(id=alert_id)
            entries = IncidentTimeline.objects.filter(alert=alert).select_related('actor')
            return JsonResponse({
                'alert_id': alert_id,
                'status':   alert.status,
                'timeline': [e.to_dict() for e in entries],
            })
        except IncidentAlert.DoesNotExist:
            return JsonResponse({'error': 'Alert not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


# ══════════════════════════════════════════════════════════════
# VIEW 11 — OFFICER ALERTS (officer dashboard polls this)
# ══════════════════════════════════════════════════════════════

class OfficerAlertsView(View):
    """GET /api/incident/officer-alerts/"""

    def get(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Login required'}, status=401)

        try:
            profile = userProfile.objects.select_related('station').get(user=request.user)

            if profile.role == 'sho':
                alerts = IncidentAlert.objects.filter(
                    station=profile.station,
                    status__in=[
                        IncidentStatus.PENDING,
                        IncidentStatus.ACCEPTED,
                        IncidentStatus.ENROUTE,
                        IncidentStatus.ARRIVED,
                        IncidentStatus.ESCALATED
                    ]
                ).order_by('-created_at')[:20]

            elif profile.role == 'police':
                alerts = IncidentAlert.objects.filter(
                    assigned_officer=profile,
                    status__in=[
                        IncidentStatus.PENDING,
                        IncidentStatus.ACCEPTED,
                        IncidentStatus.ENROUTE,
                        IncidentStatus.ARRIVED,
                        IncidentStatus.ESCALATED,  # include this
                    ],
                ).order_by('-created_at')[:10]

            else:
                alerts = IncidentAlert.objects.none()
            result = []
            for a in alerts:
                if a.status == IncidentStatus.PENDING and a.is_expired():
                    a.status = IncidentStatus.REJECTED
                    a.save(update_fields=['status'])
                    _log_timeline(a, IncidentStatus.REJECTED,
                                  note='Auto-expired: no officer response within 30 seconds')
                    reassign_alert(a)
                    continue

                result.append({
                    **a.to_dict(),
                    'seconds_ago':           a.elapsed_seconds,
                    'is_expired':            a.is_expired(),
                    'allowed_transitions':   IncidentStatus.VALID_TRANSITIONS.get(a.status, []),
                })
            
            print("==== SHO DASHBOARD DEBUG ====")
            print("Logged in user:", request.user.username)
            print("Station:", profile.station.name)
            print("Total alerts:", IncidentAlert.objects.count())
            print("Matching alerts:", alerts.count())
            print("============================")
            
            return JsonResponse({'alerts': result, 'count': len(result)})

        except userProfile.DoesNotExist:
            return JsonResponse({'alerts': [], 'count': 0})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


# ══════════════════════════════════════════════════════════════
# VIEW 12 — CITIZEN FEEDBACK
# ══════════════════════════════════════════════════════════════

@method_decorator(csrf_exempt, name='dispatch')
class CitizenFeedbackView(View):
    """POST /api/incident/feedback/"""

    def post(self, request):
        try:
            data     = json.loads(request.body)
            alert_id = data.get('alert_id')
            alert    = IncidentAlert.objects.get(id=alert_id)

            if data.get('rating'):
                alert.citizen_rating = min(5, max(1, int(data['rating'])))
            if data.get('feedback_text'):
                alert.citizen_feedback = data['feedback_text'][:500]
            if 'ai_correct' in data:
                alert.ai_correct = bool(data['ai_correct'])
            if data.get('actual_severity'):
                alert.actual_severity = data['actual_severity']

            alert.save()
            return JsonResponse({'status': 'ok', 'message': 'Feedback recorded. Thank you.'})

        except IncidentAlert.DoesNotExist:
            return JsonResponse({'error': 'Alert not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


# ══════════════════════════════════════════════════════════════
# PRIVATE HELPERS
# ══════════════════════════════════════════════════════════════

def _notify_citizen_status(alert, new_status):
    """SMS citizen on key lifecycle transitions."""
    try:
        if not alert.reported_by:
            return
        profile = userProfile.objects.filter(user=alert.reported_by).first()
        phone   = profile.phone if profile else ''
        if not phone:
            return
        if not phone.startswith('+'):
            phone = '+91' + phone.lstrip('0')

        messages = {
            IncidentStatus.ACCEPTED: (
                f"[CrimeCast] Officer {alert.assigned_officer.full_name if alert.assigned_officer else ''} "
                f"has accepted your report #{alert.id}."
            ),
            IncidentStatus.ENROUTE: (
                f"[CrimeCast] Officer is on the way. Stay safe. Report #{alert.id}."
            ),
            IncidentStatus.ARRIVED: (
                f"[CrimeCast] Officer has arrived at the scene. Report #{alert.id}."
            ),
            IncidentStatus.RESOLVED: (
                f"[CrimeCast] Incident #{alert.id} resolved. "
                f"Please rate your experience at your tracking page."
            ),
        }
        msg = messages.get(new_status)
        if not msg:
            return

        from home.sos_utils import send_sms   # ← change 'home'
        send_sms(phone, msg)
    except Exception as e:
        print(f"[_notify_citizen_status] {e}")
        
        
def _analyze_incident(text, role, ward_context='', pattern_context=''):
    """
    Sends incident text to Claude.
    Returns structured JSON with severity, actions, predictions.
    """

    role_instruction = {
        'citizen': (
            "You are an emergency response AI for Thane Police. "
            "The user is a citizen reporting an incident. "
            "Use simple, calm, reassuring language. "
            "Prioritize their safety first."
        ),
        'police': (
            "You are a tactical intelligence AI for Thane Police officers. "
            "Use precise operational language. "
            "Focus on deployment, escalation risk, and coordination."
        ),
        'sho': (
            "You are a command intelligence AI for the Station Head Officer. "
            "Focus on resource allocation, escalation risk, "
            "and cross-ward coordination."
        ),
    }.get(role, 'citizen')

    prompt = f"""
{role_instruction}

{f"Location context: {ward_context}" if ward_context else ""}
{f"Recent crime patterns: {pattern_context}" if pattern_context else ""}

A user has reported the following incident:
"{text}"

Analyze this incident and respond ONLY with this exact JSON structure:
{{
  "crime_type": "assault / theft / accident / fire / medical / disturbance / other",
  "severity": "low / medium / high / critical",
  "severity_score": 0-10,
  "confidence": 0-100,
  "summary": "one sentence plain summary of the incident",
  "immediate_actions": [
    "action 1 for the user right now",
    "action 2",
    "action 3"
  ],
  "dispatch_recommendation": "what units/resources should be dispatched",
  "escalation_risk": "low / medium / high",
  "escalation_reason": "why escalation risk is this level",
  "safety_tip": "one safety tip specific to this incident type",
  "estimated_response_time": "X-Y minutes",
  "emergency_numbers": ["112", "1091"]
}}

Be concise. No markdown. Valid JSON only.
""".strip()

    client = Groq(api_key=settings.GROQ_API_KEY)

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",  # or mixtral / gemma
        messages=[
            {"role": "user", "content": prompt}
        ],
        max_tokens=600,
        temperature=0.2,  # keep low for structured JSON
    )

    raw = response.choices[0].message.content.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Fallback safe response
        return {
            "crime_type":             "other",
            "severity":               "medium",
            "severity_score":         5,
            "confidence":             60,
            "summary":                text[:100],
            "immediate_actions":      ["Call 112 immediately", "Stay safe", "Wait for assistance"],
            "dispatch_recommendation": "Send nearest patrol unit",
            "escalation_risk":        "medium",
            "escalation_reason":      "Unable to fully analyze — manual review required",
            "safety_tip":             "Stay in a safe, visible location",
            "estimated_response_time": "10-15 minutes",
            "emergency_numbers":      ["112", "1091"],
        }

from django.http import JsonResponse
import json
from django.utils import timezone

@csrf_exempt
def update_officer_location(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    try:
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Not authenticated"}, status=403)

        data = json.loads(request.body)

        lat = data.get("latitude")
        lon = data.get("longitude")

        if lat is None or lon is None:
            return JsonResponse({"error": "Missing coordinates"}, status=400)

        from .models import userProfile

        profile = userProfile.objects.get(user=request.user)

        # 🚨 Only police allowed
        if profile.role not in ["police", "sho"]:
            return JsonResponse({"error": "Not allowed"}, status=403)

        profile.current_latitude = lat
        profile.current_longitude = lon
        profile.last_location_update = timezone.now()

        profile.save(update_fields=[
            "current_latitude",
            "current_longitude",
            "last_location_update"
        ])

        return JsonResponse({"status": "ok"})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    
# ── Citizen live location (for officer to see on their map) ──────────────────
@method_decorator(csrf_exempt, name='dispatch')
class CitizenLocationUpdateView(View):
    """
    POST /api/incident/citizen-location/<alert_id>/
    Citizen tracking page posts their GPS here every few seconds.
    Stored on the IncidentAlert itself.
    """
    def post(self, request, alert_id):
        try:
            data = json.loads(request.body)
            lat  = data.get('latitude')
            lon  = data.get('longitude')
            if lat is None or lon is None:
                return JsonResponse({'error': 'Missing coordinates'}, status=400)

            alert = IncidentAlert.objects.get(id=alert_id)
            alert.citizen_latitude  = lat
            alert.citizen_longitude = lon
            alert.save(update_fields=['citizen_latitude', 'citizen_longitude'])
            return JsonResponse({'status': 'ok'})
        except IncidentAlert.DoesNotExist:
            return JsonResponse({'error': 'Not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
        
class CitizenLiveLocationView(View):
    """
    GET /api/incident/citizen-location/<alert_id>/
    Called by officer dashboard every 5s when status is enroute/arrived.
    Returns citizen's last known GPS so officer can see them on their map.
    """
    def get(self, request, alert_id):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Login required'}, status=401)
        try:
            alert = IncidentAlert.objects.get(id=alert_id)
            if alert.status not in (IncidentStatus.ENROUTE, IncidentStatus.ARRIVED):
                return JsonResponse({'available': False})

            c_lat = alert.citizen_latitude
            c_lon = alert.citizen_longitude

            if c_lat is None or c_lon is None:
                # Fall back to the reported incident coordinates
                c_lat = alert.latitude
                c_lon = alert.longitude

            return JsonResponse({
                'available':  True,
                'latitude':   float(c_lat)  if c_lat  else None,
                'longitude':  float(c_lon)  if c_lon  else None,
                'inc_lat':    float(alert.latitude)  if alert.latitude  else None,
                'inc_lon':    float(alert.longitude) if alert.longitude else None,
            })
        except IncidentAlert.DoesNotExist:
            return JsonResponse({'available': False}, status=404)
        except Exception as e:
            return JsonResponse({'available': False, 'reason': str(e)}, status=500)
        
class OfficerTrackView(TemplateView):
    """
    GET /officer/track/<alert_id>/
    Full-screen Ola/Uber style map for officer to navigate to citizen.
    """
    template_name = 'officer_track.html'

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        alert_id = self.kwargs.get('alert_id')
        try:
            alert = IncidentAlert.objects.select_related(
                'assigned_officer__user', 'station'
            ).get(id=alert_id)
            ctx['alert'] = alert
        except IncidentAlert.DoesNotExist:
            ctx['alert'] = None
        return ctx
    
    
"""
ADD THESE VIEWS TO YOUR views.py
=================================
All investigation report views. Paste at bottom of your views.py.
Change 'home' to your app name throughout.
"""

# ─── Additional imports to add at top of views.py ────────────────────────────
# from django.views.decorators.csrf import csrf_exempt   (already in your views)
# from django.views.decorators.http import require_http_methods
# import json as _json  (already present if you followed earlier steps)

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
import json as _json


# ══════════════════════════════════════════════════════════════
# VIEW 1 — OFFICER: Write / Edit Investigation Report
# GET  /investigation/<report_id>/write/
# POST /investigation/<report_id>/write/  (save draft)
# ══════════════════════════════════════════════════════════════

@login_required
def write_investigation(request, report_id):
    """
    Main investigation report writing interface.
    Officer fills 6 structured sections + gets AI assistance.
    """
    from home.models import CrimeReport, InvestigationReport, userProfile

    crime_report = get_object_or_404(CrimeReport, id=report_id)

    # Ensure only the assigned officer can access
    try:
        profile = userProfile.objects.get(user=request.user)
        if crime_report.assigned_officer and crime_report.assigned_officer != profile:
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("You are not assigned to this case.")
    except userProfile.DoesNotExist:
        return redirect('login')

    # Get or create the investigation report
    inv_report, created = InvestigationReport.objects.get_or_create(
        crime_report=crime_report,
        defaults={'officer': profile, 'status': 'draft'}
    )

    if request.method == 'POST':
        # ── Parse form data ──────────────────────────────────────────────────
        inv_report.incident_summary   = request.POST.get('incident_summary', '').strip()
        inv_report.ipc_sections       = request.POST.get('ipc_sections', '').strip()
        inv_report.fir_number         = request.POST.get('fir_number', '').strip()
        inv_report.scene_description  = request.POST.get('scene_description', '').strip()
        inv_report.action_taken       = request.POST.get('action_taken', '').strip()
        inv_report.officer_conclusion = request.POST.get('officer_conclusion', '').strip()
        inv_report.evidence_notes     = request.POST.get('evidence_notes', '').strip()
        inv_report.case_outcome       = request.POST.get('case_outcome', '')
        inv_report.arrest_details     = request.POST.get('arrest_details', '').strip()
        inv_report.forensic_lab       = request.POST.get('forensic_lab', '').strip()

        # Booleans
        inv_report.site_visited      = 'site_visited'      in request.POST
        inv_report.cctv_reviewed     = 'cctv_reviewed'     in request.POST
        inv_report.digital_forensics = 'digital_forensics' in request.POST
        inv_report.arrests_made      = 'arrests_made'      in request.POST
        inv_report.forensic_sent     = 'forensic_sent'     in request.POST
        inv_report.forensic_report_awaited = 'forensic_report_awaited' in request.POST

        # Date/time
        doo = request.POST.get('date_of_occurrence', '')
        too = request.POST.get('time_of_occurrence', '')
        if doo:
            from datetime import date
            try:
                inv_report.date_of_occurrence = date.fromisoformat(doo)
            except ValueError:
                pass
        if too:
            from datetime import time as dtime
            try:
                inv_report.time_of_occurrence = dtime.fromisoformat(too)
            except ValueError:
                pass

        # Witness + evidence JSON from hidden fields
        witnesses_json = request.POST.get('witness_statements_json', '[]')
        evidence_json  = request.POST.get('evidence_items_json', '[]')
        try:
            inv_report.witness_statements = _json.loads(witnesses_json)
            inv_report.witness_count      = len(inv_report.witness_statements)
        except Exception:
            pass
        try:
            inv_report.evidence_items = _json.loads(evidence_json)
        except Exception:
            pass

        # Determine action
        action = request.POST.get('_action', 'save')

        if action == 'submit':
            inv_report.save()
            # Run AI quality check
            from home.services.ai_investigation import analyze_completed_report
            review = analyze_completed_report(inv_report)
            inv_report.ai_risk_assessment = review.get('court_readiness', '')
            inv_report.save(update_fields=['ai_risk_assessment'])
            inv_report.submit()
            # Update CrimeReport status
            crime_report.resolution_status = 'Awaiting Approval'
            crime_report.save(update_fields=['resolution_status'])
            return redirect('investigation_submitted', report_id=report_id)
        else:
            inv_report.save()
            return redirect('write_investigation', report_id=report_id)

    context = {
        'crime_report': crime_report,
        'inv_report':   inv_report,
        'profile':      profile,
        'completion':   inv_report.completion_percent,
        'can_submit':   inv_report.status in ('draft', 'sho_rejected'),
    }
    return render(request, 'investigation_write.html', context)


# ══════════════════════════════════════════════════════════════
# VIEW 2 — OFFICER: Submission confirmation
# GET /investigation/<report_id>/submitted/
# ══════════════════════════════════════════════════════════════

@login_required
def investigation_submitted(request, report_id):
    from home.models import CrimeReport, InvestigationReport
    crime_report = get_object_or_404(CrimeReport, id=report_id)
    try:
        inv_report = crime_report.investigation_report
    except InvestigationReport.DoesNotExist:
        return redirect('write_investigation', report_id=report_id)
    return render(request, 'investigation_submitted.html', {
        'crime_report': crime_report,
        'inv_report':   inv_report,
    })


# ══════════════════════════════════════════════════════════════
# VIEW 3 — SHO: Review Investigation Report
# GET  /investigation/<report_id>/review/
# POST /investigation/<report_id>/review/  (approve / reject)
# ══════════════════════════════════════════════════════════════

@login_required
def review_investigation(request, report_id):
    """
    SHO reads the full report, sees AI quality metrics,
    and approves or returns for revision.
    """
    from home.models import CrimeReport, InvestigationReport, userProfile

    crime_report = get_object_or_404(CrimeReport, id=report_id)

    try:
        inv_report = crime_report.investigation_report
    except InvestigationReport.DoesNotExist:
        return render(request, 'investigation_not_found.html', {'report_id': report_id})

    if request.method == 'POST':
        action   = request.POST.get('action')
        comments = request.POST.get('sho_comments', '').strip()

        if action == 'approve':
            inv_report.approve(reviewer=request.user)
            crime_report.resolution_status = 'Resolved'
            crime_report.resolved_at       = timezone.now()
            crime_report.save(update_fields=['resolution_status', 'resolved_at'])
            return redirect('sho_dashboard')

        elif action == 'reject':
            if not comments:
                comments = "Please revise and resubmit."
            inv_report.reject(reviewer=request.user, comments=comments)
            return redirect('sho_dashboard')

    # Run AI quality analysis on load
    from home.services.ai_investigation import analyze_completed_report
    ai_review = analyze_completed_report(inv_report)

    context = {
        'crime_report': crime_report,
        'inv_report':   inv_report,
        'ai_review':    ai_review,
        'completion':   inv_report.completion_percent,
    }
    return render(request, 'investigation_review.html', context)


# ══════════════════════════════════════════════════════════════
# API 1 — AI DRAFT GENERATOR
# POST /api/investigation/ai-draft/<report_id>/
# ══════════════════════════════════════════════════════════════

@csrf_exempt
def api_ai_draft(request, report_id):
    """
    Officer clicks "AI Draft" — Groq generates a complete first draft.
    Returns JSON to pre-fill the form fields via JS.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    from home.models import CrimeReport
    from home.services.ai_investigation import draft_investigation_report

    crime_report = get_object_or_404(CrimeReport, id=report_id)
    draft = draft_investigation_report(crime_report)

    if not draft:
        return JsonResponse({'error': 'AI draft unavailable. Fill manually.'}, status=500)

    return JsonResponse({'draft': draft})


# ══════════════════════════════════════════════════════════════
# API 2 — WITNESS QUESTION GUIDE
# GET /api/investigation/witness-guide/?crime=assault&n=1
# ══════════════════════════════════════════════════════════════

def api_witness_guide(request):
    """
    Returns 5 AI-generated interview questions for a witness.
    Called when officer clicks "+ Add Witness".
    """
    from home.services.ai_investigation import generate_witness_prompt
    crime_type = request.GET.get('crime', 'general')
    n          = int(request.GET.get('n', 1))
    questions  = generate_witness_prompt(crime_type, n)
    return JsonResponse({'questions': questions})


# ══════════════════════════════════════════════════════════════
# API 3 — AI QUALITY CHECK (called before submit)
# POST /api/investigation/quality-check/<report_id>/
# ══════════════════════════════════════════════════════════════

@csrf_exempt
def api_quality_check(request, report_id):
    """
    Called when officer clicks "Check Report Quality".
    Returns prosecution strength + gaps without saving.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    from home.models import InvestigationReport, CrimeReport
    from home.services.ai_investigation import analyze_completed_report

    crime_report = get_object_or_404(CrimeReport, id=report_id)

    try:
        inv_report = crime_report.investigation_report
    except InvestigationReport.DoesNotExist:
        return JsonResponse({'error': 'Report not found'}, status=404)

    review = analyze_completed_report(inv_report)
    return JsonResponse({'review': review})

