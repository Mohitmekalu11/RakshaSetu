from django.db import models

# Create your models here.
from django.db import models

class SafetyKnowledge(models.Model):
    incident_type = models.CharField(max_length=100)
    immediate_steps = models.TextField()
    evidence_to_collect = models.TextField()
    safety_measures = models.TextField()

    def __str__(self):
        return self.incident_type


class Helpline(models.Model):
    name = models.CharField(max_length=100)
    number = models.CharField(max_length=20)
    category = models.CharField(max_length=100)

    def __str__(self):
        return self.name
