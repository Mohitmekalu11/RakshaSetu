from django.db import models
from django.contrib.auth.models import User

class PoliceStation(models.Model):
    name = models.CharField(max_length=255, unique=True)
    address = models.TextField(blank=True, null=True)
    phone    = models.CharField(max_length=20, blank=True)
    wards    = models.TextField(blank=True, help_text="Comma-separated ward names this station covers")
    latitude  = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
 
    class Meta:
        ordering = ['name']
 
    def __str__(self):
        return self.name
 
    def covers_ward(self, ward):
        if not ward or not self.wards_covered:
            return False

        ward = str(ward).strip()
        covered = [w.strip() for w in self.wards_covered.split(',')]

        return ward in covered

    

class userProfile(models.Model):
    ROLE_CHOICES = [
        
        ('user', 'User'),
        ('police', 'Police'),
        ('sho', 'SHO'),
    ]
   
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    forgot_password_token = models.CharField(max_length=255, blank=True, null=True)
    bio = models.TextField(max_length=500, blank=True)
    about = models.TextField(blank=True, null=True)
    contact = models.CharField(max_length=10, blank=True, null=True)
    mail = models.EmailField(blank=True, null=True)
    
    current_latitude   = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    current_longitude  = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    last_location_update = models.DateTimeField(null=True, blank=True)
    active_case_count  = models.PositiveIntegerField(default=0)
    # inside userProfile model
    is_on_duty = models.BooleanField(default=True)


    SPECIALTY_CHOICES = (
        ('Cyber Crime', 'Cyber Crime'),
        ('Theft', 'Theft'),
        ('Assault', 'Assault'),
        ('Fraud', 'Fraud'),
        ('Narcotics', 'Narcotics'),
        ('Other', 'Other'),
    )

    EXPERIENCE_CHOICES = (
        ('Junior', 'Junior'),
        ('Senior', 'Senior'),
        ('Inspector', 'Inspector'),
    )
 
    address = models.TextField(blank=True, null=True)

    location = models.CharField(max_length=30, blank=True)
    profile_image = models.ImageField(upload_to='profile_images/', blank=True)

    role = models.CharField(max_length=10, choices=ROLE_CHOICES, null=True, blank=True)

    # Police-specific fields
    badge_id = models.CharField(max_length=50, blank=True, null=True)
    station = models.ForeignKey(PoliceStation, on_delete=models.SET_NULL, null=True, blank=True)

    SENIORITY_CHOICES = [
    ('constable', 'Constable'),
    ('head_constable', 'Head Constable'),
    ('asi', 'ASI'),
    ('si', 'Sub Inspector'),
    ('inspector', 'Inspector'),
    ('dsp', 'DSP'),
    ]

    seniority = models.CharField(
        max_length=30,
        choices=SENIORITY_CHOICES,
        blank=True,
        null=True
    )

        
    experience_level = models.CharField(max_length=20, choices=EXPERIENCE_CHOICES, blank=True, null=True)
    specialty = models.CharField(max_length=50, choices=SPECIALTY_CHOICES, blank=True, null=True)

    rank = models.CharField(max_length=50, blank=True, null=True)

    is_approved = models.BooleanField(default=True)  # Default True for citizens; for police, you'll set this to False.
    disapproval_message = models.TextField(blank=True, null=True)
    
    
    
    # Extra fields for police registration (optional for citizens)
    phone = models.CharField(max_length=10, blank=True, null=True)
    id_card = models.ImageField(upload_to='id_cards/', blank=True,null=True)
    
    liveness_video  = models.FileField(upload_to='liveness_videos/', blank=True, null=True)
    liveness_frame  = models.ImageField(upload_to='liveness_frames/', blank=True, null=True)
    
    

    def __str__(self):
        return f"{self.user.username} ({self.role})"
    
    class Meta:
        ordering = ['seniority', 'user__first_name']
 
    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.get_role_display()})"
 
    @property
    def full_name(self):
        return self.user.get_full_name() or self.user.username
    
    @property
    def is_available(self):
        return (
            self.role == 'police' and
            self.is_on_duty and
            self.is_approved and
            self.active_case_count < 3
        )




from django.db import models
from django.contrib.auth.models import User


class CrimeReport(models.Model):
    crime_type = models.CharField(max_length=255)
    description = models.TextField()
    address = models.CharField(max_length=255, default="Unknown")
    latitude = models.DecimalField(max_digits=9, decimal_places=6)  
    longitude = models.DecimalField(max_digits=9, decimal_places=6)  
    video = models.FileField(upload_to='crime_videos/', blank=True, null=True)
    reported_at = models.DateTimeField(auto_now_add=True)
    reported_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    resolved_at = models.DateTimeField(null=True, blank=True)
    assigned_at = models.DateTimeField(null=True, blank=True) 
    first_touched_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When officer first opened or updated this report"
    )
    
    # Workflow fields
    status = models.CharField(
        max_length=20,
        choices=[
            ("Pending", "Pending"),
            ("Approved", "Approved"),
            ("Rejected", "Rejected")
        ],
        default="Pending"
    )
    resolution_status = models.CharField(
            max_length=30,
            choices=[
                ("Pending", "Pending"),
                ("Under Investigation", "Under Investigation"),
                ("Awaiting Approval", "Awaiting Approval"),
                ("Resolved", "Resolved"),
            ],
            default="Pending",
    )

    
    assigned_officer = models.ForeignKey(
        'userProfile', null=True, blank=True, on_delete=models.SET_NULL
    )
    station = models.ForeignKey(
        PoliceStation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="crime_reports"
    )
    severity_score = models.FloatField(null=True, blank=True) 
    is_deleted = models.BooleanField(default=False) 

    ai_status = models.CharField(max_length=50, default="Pending")
    ai_progress = models.IntegerField(default=0) 
    def __str__(self):
        return f"{self.crime_type} - {self.address}"

# class InvestigationReport(models.Model):
#     crime_report = models.OneToOneField(
#         CrimeReport,
#         on_delete=models.CASCADE,
#         related_name="investigation_report"
#     )

#     officer = models.ForeignKey(
#         'userProfile',
#         on_delete=models.SET_NULL,
#         null=True,
#         blank=True
#     )

#     summary = models.TextField()
#     action_taken = models.TextField()
#     evidence_notes = models.TextField()

#     submitted_at = models.DateTimeField(auto_now_add=True)

#     sho_approved = models.BooleanField(null=True)
#     reviewed_at = models.DateTimeField(null=True, blank=True)

#     def __str__(self):
#         return f"Investigation Report for Case {self.crime_report.id}"

# """
# ADD/REPLACE InvestigationReport in your models.py
# ==================================================
# This replaces your existing InvestigationReport model.
# Run: python manage.py makemigrations && python manage.py migrate
# """

from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User


class InvestigationReport(models.Model):

    STATUS_CHOICES = [
        ('draft',           'Draft'),
        ('submitted',       'Submitted for Review'),
        ('sho_approved',    'SHO Approved'),
        ('sho_rejected',    'Returned for Revision'),
        ('court_ready',     'Court-Ready'),
    ]

    crime_report = models.OneToOneField(
        'CrimeReport', on_delete=models.CASCADE, related_name='investigation_report'
    )
    officer = models.ForeignKey(
        'userProfile', on_delete=models.SET_NULL, null=True, blank=True
    )

    # ── Status ───────────────────────────────────────────────────────────────
    status     = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    version    = models.PositiveIntegerField(default=1)   # increments on each revision

    # ── SECTION 1: Incident Overview (AI pre-filled from CrimeReport) ────────
    incident_summary      = models.TextField(help_text="Factual account: who, what, where, when",null=True)
    ipc_sections          = models.CharField(
        max_length=300, blank=True,
        help_text="Comma-separated IPC sections e.g. 302, 376, 420"
    )
    fir_number            = models.CharField(max_length=50, blank=True)
    date_of_occurrence    = models.DateField(null=True, blank=True)
    time_of_occurrence    = models.TimeField(null=True, blank=True)
    scene_description     = models.TextField(blank=True, help_text="Physical description of the crime scene")

    # ── SECTION 2: Investigation Actions ─────────────────────────────────────
    action_taken          = models.TextField(help_text="Chronological list of every action: visits, interviews, arrests")
    site_visited          = models.BooleanField(default=False)
    site_visited_at       = models.DateTimeField(null=True, blank=True)
    cctv_reviewed         = models.BooleanField(default=False)
    digital_forensics     = models.BooleanField(default=False)
    arrests_made          = models.BooleanField(default=False)
    arrest_details        = models.TextField(blank=True, help_text="Name, age, address, charges for each arrested person")

    # ── SECTION 3: Witness Statements ────────────────────────────────────────
    witness_count         = models.PositiveSmallIntegerField(default=0)
    witness_statements    = models.JSONField(
        default=list, blank=True,
        help_text="[{name, age, contact, statement_summary, recorded_at}]"
    )

    # ── SECTION 4: Evidence Chain-of-Custody ─────────────────────────────────
    evidence_notes        = models.TextField(blank=True)
    evidence_items        = models.JSONField(
        default=list, blank=True,
        help_text="[{item_no, description, collection_date, custody_officer, location}]"
    )
    forensic_sent         = models.BooleanField(default=False)
    forensic_lab          = models.CharField(max_length=100, blank=True)
    forensic_report_awaited = models.BooleanField(default=False)

    # ── SECTION 5: AI Intelligence Layer ────────────────────────────────────
    ai_case_summary       = models.TextField(blank=True, help_text="Groq-generated case narrative")
    ai_suggested_sections = models.CharField(max_length=300, blank=True, help_text="AI-suggested IPC sections")
    ai_risk_assessment    = models.TextField(blank=True, help_text="AI assessment: likelihood of conviction, missing evidence")
    ai_next_steps         = models.TextField(blank=True, help_text="AI-recommended next investigation steps")
    ai_generated_at       = models.DateTimeField(null=True, blank=True)

    # ── SECTION 6: Closure & SHO Review ─────────────────────────────────────
    officer_conclusion    = models.TextField(blank=True, help_text="Officer's final conclusion and recommendation")
    case_outcome          = models.CharField(
        max_length=30, blank=True,
        choices=[
            ('chargesheet_filed', 'Chargesheet Filed'),
            ('closure_report',    'Closure Report'),
            ('referred_to_court', 'Referred to Court'),
            ('further_investigation', 'Further Investigation Required'),
            ('pending_forensics', 'Pending Forensics'),
        ]
    )

    sho_approved          = models.BooleanField(null=True)
    sho_comments          = models.TextField(blank=True, help_text="SHO revision instructions or approval notes")
    reviewed_at           = models.DateTimeField(null=True, blank=True)
    reviewed_by           = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_reports'
    )

    # ── Timestamps ────────────────────────────────────────────────────────────
    submitted_at          = models.DateTimeField(null=True, blank=True)
    created_at            = models.DateTimeField(auto_now_add=True,null=True)
    updated_at            = models.DateTimeField(auto_now=True,null=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"Investigation Report — Case #{self.crime_report_id} v{self.version} [{self.status}]"

    def submit(self):
        self.status       = 'submitted'
        self.submitted_at = timezone.now()
        self.save(update_fields=['status', 'submitted_at'])

    def approve(self, reviewer):
        self.status       = 'sho_approved'
        self.sho_approved = True
        self.reviewed_at  = timezone.now()
        self.reviewed_by  = reviewer
        self.save(update_fields=['status', 'sho_approved', 'reviewed_at', 'reviewed_by'])
        # Also mark the CrimeReport resolution status
        self.crime_report.resolution_status = 'Awaiting Approval'
        self.crime_report.save(update_fields=['resolution_status'])

    def reject(self, reviewer, comments):
        self.status       = 'sho_rejected'
        self.sho_approved = False
        self.sho_comments = comments
        self.reviewed_at  = timezone.now()
        self.reviewed_by  = reviewer
        self.version     += 1
        self.save(update_fields=['status', 'sho_approved', 'sho_comments', 'reviewed_at', 'reviewed_by', 'version'])

    @property
    def completion_percent(self):
        """Returns 0–100 showing how complete the report is."""
        checks = [
            bool(self.incident_summary),
            bool(self.action_taken),
            bool(self.ipc_sections),
            bool(self.fir_number),
            bool(self.date_of_occurrence),
            bool(self.scene_description),
            self.witness_count > 0 or bool(self.witness_statements),
            bool(self.evidence_notes) or bool(self.evidence_items),
            bool(self.officer_conclusion),
            bool(self.case_outcome),
        ]
        return int(sum(checks) / len(checks) * 100)

class CrimePhoto(models.Model):
    crime_report = models.ForeignKey(
        CrimeReport, on_delete=models.CASCADE, related_name='photos'
    )
    photos = models.ImageField(upload_to='photos/')

    # 🔹 AI / Deepfake Detection Fields for photos
    is_ai_generated = models.BooleanField(default=False, help_text="True if detected as AI-generated")
    verification_status = models.CharField(
        max_length=20,
        choices=[
            ("Pending", "Pending"),
            ("Verified", "Verified"),
            ("Flagged", "Flagged")
        ],
        default="Pending"
    )
    deepfake_suspected = models.BooleanField(default=False)
    weapon_detected = models.BooleanField(default=False)
    violence_detected = models.BooleanField(default=False)
    ai_confidence_score = models.FloatField(
        null=True, blank=True, help_text="0.0 to 1.0 probability score"
    )

    def __str__(self):
        return f"Photo for Report ID {self.crime_report.id}"


class OfficerFeedback(models.Model):
    crime_report = models.OneToOneField(CrimeReport, on_delete=models.CASCADE)
    officer = models.ForeignKey(userProfile, on_delete=models.CASCADE, limit_choices_to={'role': 'police'})
    rating = models.PositiveSmallIntegerField()  # 1 to 5 stars
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback for {self.officer.user.username} - {self.rating} stars"

# app/models.py
from django.db import models

class Ward(models.Model):
    lgd_name = models.CharField(max_length=100, unique=True)  # e.g., "Ward No.28"
    lgd_code = models.IntegerField(null=True, blank=True)
    townname = models.CharField(max_length=100, default="Thane")
    state = models.CharField(max_length=50, default="Maharashtra")
    st_area = models.FloatField(null=True, blank=True)  # area of ward
    st_length = models.FloatField(null=True, blank=True)  # perimeter length
    
    centroid_latitude  = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    centroid_longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)

    def __str__(self):
        return self.lgd_name

# app/models.py
from django.utils import timezone

class CrimeRecord(models.Model):
    CRIME_TYPES = [
        ('theft', 'Theft'),
        ('assault', 'Assault'),
        ('fraud', 'Fraud'),
        ('other', 'Other'),
        ('domestic_violence', 'Domestic Violence'),
        ('kidnapping', 'Kidnapping'),
        ('drug_offense', 'Drug Offense'),
        ('robbery', 'Robbery'),
        ('cheating', 'Cheating'),
        ('cybercrime', 'Cybercrime'),
        ('murder', 'Murder'),
        ('burglary', 'Burglary'),
        ('other', 'Other'),
    ]

    ward = models.ForeignKey(Ward, on_delete=models.CASCADE, related_name='crimes', null=True, blank=True)

    crime_type = models.CharField(max_length=50, choices=CRIME_TYPES, null=True, blank=True)
    date_reported = models.DateField(default=timezone.now)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.crime_type} in {self.ward.lgd_name}"



class TrustedContact(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15)


from django.db import models

class NewsArticle(models.Model):
    """
    Stores raw news articles pulled from external APIs
    and later correlated with crime data.
    """

    title = models.CharField(max_length=300)
    description = models.TextField(blank=True, null=True)
    content = models.TextField(blank=True, null=True)

    source = models.CharField(max_length=150, blank=True, null=True)
    author = models.CharField(max_length=150, blank=True, null=True)
    url = models.URLField()

    published_at = models.DateTimeField()

    # ML / Intelligence Fields
    severity_score = models.FloatField(blank=True, null=True)
    risk_score = models.FloatField(blank=True, null=True)
    confidence = models.FloatField(blank=True, null=True)

    # Location Intelligence
    city = models.CharField(max_length=120, blank=True, null=True)
    state = models.CharField(max_length=120, blank=True, null=True)
    area = models.CharField(max_length=150, blank=True, null=True)

    country = models.CharField(max_length=120, default="India")

    crime_type = models.CharField(max_length=120, blank=True, null=True)

    # Processing Flags
    is_verified = models.BooleanField(default=False)
    is_processed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-published_at"]
        indexes = [
            models.Index(fields=["city"]),
            models.Index(fields=["crime_type"]),
            models.Index(fields=["published_at"]),
        ]

    def __str__(self):
        return self.title

class IntelligenceInsight(models.Model):
    """
    Stores derived intelligence insights from articles + crime data correlation
    """

    article = models.ForeignKey(
        NewsArticle,
        on_delete=models.CASCADE,
        related_name="insights"
    )

    trend_type = models.CharField(max_length=100)  # e.g., "spike", "decline", "stable"
    severity = models.CharField(max_length=50)     # low / medium / high
    summary = models.TextField()

    baseline_avg = models.FloatField()
    recent_count = models.IntegerField()

    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-generated_at"]

    def __str__(self):
        return f"{self.trend_type.upper()} - {self.article.city}"
    
    
class NewsActionInsight(models.Model):
    article = models.ForeignKey(NewsArticle, on_delete=models.CASCADE, related_name="actions")
    user_role = models.CharField(max_length=50)
    action_text = models.TextField()
    priority = models.IntegerField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user_role}: {self.action_text[:40]}"


class NewsCrimeCorrelation(models.Model):
    article = models.OneToOneField(
        NewsArticle,
        on_delete=models.CASCADE,
        related_name="correlation"
    )
    historical_avg = models.FloatField(default=0.0)

    recent_trend = models.IntegerField(
        default=0,
        help_text="Short-term trend indicator (e.g., -1, 0, 1)"
    )

    predicted_risk = models.FloatField(default=0.0)

    deviation_score = models.FloatField(default=0.0)

    matches_prediction = models.BooleanField(
        default=False
    )

    risk_level = models.CharField(max_length=20,default="UNKNOWN")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.article.title} - {self.risk_level}"


####################### SOS ############################


from django.db import models
from django.contrib.auth.models import User


class SOSAlert(models.Model):
    STATUS_CHOICES = [
        ('pending',      'Pending'),
        ('notified',     'Officers Notified'),
        ('acknowledged', 'Officer Acknowledged'),
        ('escalated',    'Escalated to SHO'),
        ('resolved',     'Resolved'),
        ('cancelled',    'Cancelled by Citizen'),
    ]

    # Who triggered it
    citizen = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='sos_alerts'
    )

    # Where
    latitude  = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)
    ward = models.ForeignKey(
        'Ward', on_delete=models.SET_NULL, null=True, blank=True
    )

    # Status lifecycle
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Which officers were notified (many, in case first doesn't respond)
    notified_officers = models.ManyToManyField(
        'userProfile', blank=True, related_name='sos_notifications'
    )

    # Who actually picked it up
    acknowledged_by = models.ForeignKey(
        'userProfile', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='sos_acknowledged'
    )

    # Escalation
    escalated_to = models.ForeignKey(
        'userProfile', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='sos_escalations'
    )

    # Timestamps
    triggered_at     = models.DateTimeField(auto_now_add=True)
    acknowledged_at  = models.DateTimeField(null=True, blank=True)
    escalated_at     = models.DateTimeField(null=True, blank=True)
    resolved_at      = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-triggered_at']

    def __str__(self):
        return f"SOS #{self.id} by {self.citizen.username} — {self.status}"


# home/models.py

from django.db import models

class NewsIntel(models.Model):
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True, null=True)
    content = models.TextField(blank=True, null=True)

    source = models.CharField(max_length=150, blank=True, null=True)
    author = models.CharField(max_length=150, blank=True, null=True)
    threat_escalation = models.CharField(
      max_length=5, default="no",
      help_text="AI prediction: will this escalate in 48h? yes/no"
    )
    similar_pattern_keywords = models.JSONField(
        default=list, blank=True,
        help_text="Keywords for pattern matching across stories"
    )

    url = models.URLField(unique=True)
    image_url = models.URLField(blank=True, null=True)

    published_at = models.DateTimeField(null=True, blank=True)
    insight = models.TextField(null=True, blank=True)
    impact = models.TextField(null=True, blank=True)

    location = models.CharField(max_length=255, null=True, blank=True)
    crime_type = models.CharField(max_length=100, null=True, blank=True)

    summary = models.TextField()
    risk_level = models.CharField(max_length=20)
    suggested_action = models.TextField()

    priority_score = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
    
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
 
 
# ── Status constants ─────────────────────────────────────────────────────────
 
class IncidentStatus:
    PENDING   = 'pending'
    ACCEPTED  = 'accepted'
    ENROUTE   = 'enroute'
    ARRIVED   = 'arrived'
    RESOLVED  = 'resolved'
    REJECTED  = 'rejected'
    ESCALATED = 'escalated'
 
    CHOICES = [
        (PENDING,   'Pending'),
        (ACCEPTED,  'Accepted'),
        (ENROUTE,   'En Route'),
        (ARRIVED,   'Arrived'),
        (RESOLVED,  'Resolved'),
        (REJECTED,  'Rejected'),
        (ESCALATED, 'Escalated'),
    ]
 
    # Valid forward transitions — only these are allowed
    VALID_TRANSITIONS = {
        PENDING:   [ACCEPTED, REJECTED, ESCALATED],
        ACCEPTED:  [ENROUTE,  REJECTED, ESCALATED],
        ENROUTE:   [ARRIVED,  ESCALATED],
        ARRIVED:   [RESOLVED, ESCALATED],
        RESOLVED:  [],   # terminal
        REJECTED:  [],   # terminal
        ESCALATED: [ACCEPTED, RESOLVED],
    }
 
    # Human-readable labels for UI
    LABELS = {
        PENDING:   'Pending',
        ACCEPTED:  'Officer Assigned',
        ENROUTE:   'Officer En Route',
        ARRIVED:   'Officer Arrived',
        RESOLVED:  'Resolved',
        REJECTED:  'Rejected',
        ESCALATED: 'Escalated to SHO',
    }
 
    @classmethod
    def can_transition(cls, from_status, to_status):
        return to_status in cls.VALID_TRANSITIONS.get(from_status, [])
    
class IncidentAlert(models.Model):
 
    # Reporter
    reported_by   = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reported_incidents')
    reporter_name = models.CharField(max_length=100, default='Anonymous')
    reporter_phone = models.CharField(max_length=20, blank=True)
    citizen_latitude  = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    citizen_longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
 
    # Incident details
    incident_text           = models.TextField()
    crime_type              = models.CharField(max_length=60, blank=True)
    severity                = models.CharField(max_length=20, default='medium')
    severity_score          = models.FloatField(default=5.0)
    summary                 = models.TextField(blank=True)
    dispatch_recommendation = models.TextField(blank=True)
    ai_confidence           = models.IntegerField(default=0)
 
    # Escalation analysis
    escalation_probability = models.IntegerField(default=0)
    escalation_reason      = models.TextField(blank=True)
    area_risk_score        = models.FloatField(default=5.0)
 
    # Location
    latitude  = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    ward      = models.CharField(max_length=100, blank=True)
    landmark  = models.CharField(max_length=200, blank=True)
 
    # Assignment
    station          = models.ForeignKey(PoliceStation, on_delete=models.SET_NULL, null=True, blank=True, related_name='incidents')
    assigned_officer = models.ForeignKey(userProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_incidents')
 
    # Escalation
    is_escalated  = models.BooleanField(default=False)
    escalated_to  = models.ForeignKey(userProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='escalated_incidents')
    escalated_at  = models.DateTimeField(null=True, blank=True)
 
    # Status lifecycle
    status = models.CharField(max_length=20, choices=IncidentStatus.CHOICES, default=IncidentStatus.PENDING)
 
    # Lifecycle timestamps
    created_at   = models.DateTimeField(auto_now_add=True)
    accepted_at  = models.DateTimeField(null=True, blank=True)
    enroute_at   = models.DateTimeField(null=True, blank=True)
    arrived_at   = models.DateTimeField(null=True, blank=True)
    resolved_at  = models.DateTimeField(null=True, blank=True)
 
    # Computed metrics (stored for analytics)
    response_time_secs   = models.IntegerField(null=True, blank=True)  # created → accepted
    resolution_time_secs = models.IntegerField(null=True, blank=True)  # created → resolved
 
    # Feedback loop
    ai_correct       = models.BooleanField(null=True, blank=True)
    actual_severity  = models.CharField(max_length=20, blank=True)
    citizen_rating   = models.IntegerField(null=True, blank=True)  # 1-5
    citizen_feedback = models.TextField(blank=True)
 
    class Meta:
        ordering = ['-created_at']
 
    def __str__(self):
        return f"#{self.id} {self.crime_type} ({self.severity}) — {self.status}"
 
    # ── Timestamp helpers ────────────────────────────────────────────────────
 
    STATUS_TIMESTAMP_MAP = {
        IncidentStatus.ACCEPTED: 'accepted_at',
        IncidentStatus.ENROUTE:  'enroute_at',
        IncidentStatus.ARRIVED:  'arrived_at',
        IncidentStatus.RESOLVED: 'resolved_at',
    }
 
    def set_status_timestamp(self, new_status):
        """Auto-set the matching timestamp when status changes."""
        field = self.STATUS_TIMESTAMP_MAP.get(new_status)
        if field and not getattr(self, field):
            setattr(self, field, timezone.now())
 
    def compute_metrics(self):
        """Compute and store response + resolution time."""
        if self.accepted_at:
            self.response_time_secs = int((self.accepted_at - self.created_at).total_seconds())
        if self.resolved_at:
            self.resolution_time_secs = int((self.resolved_at - self.created_at).total_seconds())
 
    def is_expired(self):
        """True if pending for more than 30 seconds without officer response."""
        if self.status == IncidentStatus.PENDING:
            return (timezone.now() - self.created_at).total_seconds() > 30
        return False
 
    @property
    def maps_url(self):
        if self.latitude and self.longitude:
            return f"https://maps.google.com/?q={self.latitude},{self.longitude}"
        return None
 
    @property
    def elapsed_seconds(self):
        return int((timezone.now() - self.created_at).total_seconds())
 
    def to_dict(self):
        """Serialise for JSON API responses."""
        officer = self.assigned_officer
        station = self.station
        return {
            'id':                   self.id,
            'status':               self.status,
            'status_label':         IncidentStatus.LABELS.get(self.status, self.status),
            'crime_type':           self.crime_type,
            'severity':             self.severity,
            'severity_score':       self.severity_score,
            'summary':              self.summary,
            'incident_text':        self.incident_text[:300],
            'ward':                 self.ward,
            'landmark':             self.landmark,
            'latitude':             float(self.latitude)  if self.latitude  else None,
            'longitude':            float(self.longitude) if self.longitude else None,
            'maps_url':             self.maps_url,
            'escalation_probability': self.escalation_probability,
            'escalation_reason':    self.escalation_reason,
            'area_risk_score':      self.area_risk_score,
            'is_escalated':         self.is_escalated,
            'dispatch_recommendation': self.dispatch_recommendation,
            'officer': {
                'id':       officer.id,
                'name':     officer.full_name,
                'phone':    officer.phone,
                'badge':    officer.badge_id,
                'specialty':officer.specialty,
                'seniority':officer.get_seniority_display(),
                'station':  officer.station.name if officer.station else '',
            } if officer else None,
            'station': {
                'name':    station.name,
                'address': station.address,
                'phone':   station.phone,
            } if station else None,
            # Timestamps (ISO strings for JS)
            'created_at':  self.created_at.isoformat(),
            'accepted_at': self.accepted_at.isoformat()  if self.accepted_at  else None,
            'enroute_at':  self.enroute_at.isoformat()   if self.enroute_at   else None,
            'arrived_at':  self.arrived_at.isoformat()   if self.arrived_at   else None,
            'resolved_at': self.resolved_at.isoformat()  if self.resolved_at  else None,
            # Metrics
            'response_time_secs':   self.response_time_secs,
            'resolution_time_secs': self.resolution_time_secs,
            'elapsed_seconds':      self.elapsed_seconds,
        }
 
 
# ── IncidentTimeline ─────────────────────────────────────────────────────────
 
class IncidentTimeline(models.Model):
    """One row per status change — immutable audit log."""
    alert     = models.ForeignKey(IncidentAlert, on_delete=models.CASCADE, related_name='timeline')
    status    = models.CharField(max_length=20, choices=IncidentStatus.CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
    actor     = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    note      = models.TextField(blank=True)
 
    class Meta:
        ordering = ['timestamp']
 
    def __str__(self):
        return f"Alert #{self.alert_id} → {self.status} at {self.timestamp:%H:%M:%S}"
 
    def to_dict(self):
        return {
            'status':       self.status,
            'status_label': IncidentStatus.LABELS.get(self.status, self.status),
            'timestamp':    self.timestamp.isoformat(),
            'timestamp_fmt':self.timestamp.strftime('%d %b %Y, %I:%M %p'),
            'actor':        self.actor.get_full_name() if self.actor else 'System',
            'note':         self.note,
        }
 

 
 
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