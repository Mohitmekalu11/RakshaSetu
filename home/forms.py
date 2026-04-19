from django import forms
from .models import userProfile




class ProfileForm(forms.ModelForm):
    class Meta:
        model = userProfile
        fields = ['bio', 'about', 'location', 'contact', 'profile_image']
        widgets = {
            'skills': forms.CheckboxSelectMultiple(),  # Allow multiple skill selection
        }

# from django import forms
# from .models import OfficerFeedback

# class OfficerFeedbackForm(forms.ModelForm):
#     rating = forms.ChoiceField(
#         choices=[(i, f"{i} ★") for i in range(1, 6)],
#         widget=forms.RadioSelect,
#         label="Your Rating"
#     )
#     comment = forms.CharField(
#         widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Optional comment…'}),
#         required=False,
#         label="Comment"
#     )

#     class Meta:
#         model = OfficerFeedback
#         fields = ['rating', 'comment']
        
        
"""
forms_additions.py → paste these into your existing home/forms.py
"""

from django import forms
from .models import OfficerFeedback, InvestigationReport


class OfficerFeedbackForm(forms.ModelForm):
    rating = forms.ChoiceField(
        choices=[(i, f"{i} Star{'s' if i > 1 else ''}") for i in range(1, 6)],
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Rate the officer's service"
    )
    comment = forms.CharField(
        widget=forms.Textarea(attrs={
            "rows": 3,
            "placeholder": "Share your experience (optional)...",
            "class": "form-control",
        }),
        required=False,
        label="Comments"
    )

    class Meta:
        model  = OfficerFeedback
        fields = ["rating", "comment"]


class InvestigationReportForm(forms.ModelForm):
    """
    Filed by the officer before requesting SHO approval.
    Forces the officer to document what was actually done — real-world practice.
    """
    summary = forms.CharField(
        widget=forms.Textarea(attrs={
            "rows": 4,
            "placeholder": "Summarise the findings of your investigation...",
            "class": "form-control",
        }),
        label="Investigation Summary",
    )
    action_taken = forms.CharField(
        widget=forms.Textarea(attrs={
            "rows": 4,
            "placeholder": "List every action taken: witness interviews, site visits, arrests, etc.",
            "class": "form-control",
        }),
        label="Actions Taken",
    )
    evidence_notes = forms.CharField(
        widget=forms.Textarea(attrs={
            "rows": 3,
            "placeholder": "Note the physical/digital evidence collected and its current custody...",
            "class": "form-control",
        }),
        label="Evidence Notes",
        required=False,
    )

    class Meta:
        model  = InvestigationReport
        fields = ["summary", "action_taken", "evidence_notes"]