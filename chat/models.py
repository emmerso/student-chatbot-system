from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class Notification(models.Model):
    title = models.CharField(max_length=200)
    message = models.TextField()
    scheduled_time = models.DateTimeField(default=timezone.now)
    is_sent = models.BooleanField(default=False)
    is_read = models.BooleanField(default=False)  # Tracks unread notifications

    def __str__(self):
        return self.title


class Conversation(models.Model):
    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('sn', 'Shona'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_id = models.CharField(max_length=100, null=True, blank=True)
    user_message = models.TextField()
    bot_response = models.TextField()
    detected_language = models.CharField(max_length=2, choices=LANGUAGE_CHOICES, default='en')
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # New fields for tracking bot performance
    confidence_score = models.FloatField(null=True, blank=True, help_text="Rasa confidence score")
    intent = models.CharField(max_length=100, null=True, blank=True, help_text="Detected intent from Rasa")
    is_fallback = models.BooleanField(default=False, help_text="Was this a fallback response?")
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"Conversation ({self.detected_language}) - {self.timestamp}"

class ChatFeedback(models.Model):
    """Store user feedback on bot responses"""
    RATING_CHOICES = [
        (1, 'Very Poor'),
        (2, 'Poor'),
        (3, 'Average'),
        (4, 'Good'),
        (5, 'Excellent')
    ]
    
    FEEDBACK_TYPE_CHOICES = [
        ('thumbs', 'Thumbs Up/Down'),
        ('stars', 'Star Rating'),
        ('helpful', 'Helpful/Not Helpful'),
        ('detailed', 'Detailed Feedback')
    ]
    
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='feedback')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_id = models.CharField(max_length=100, null=True, blank=True)
    
    # Feedback data
    feedback_type = models.CharField(max_length=20, choices=FEEDBACK_TYPE_CHOICES)
    is_helpful = models.BooleanField(null=True, blank=True)  # For thumbs up/down
    star_rating = models.IntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    feedback_text = models.TextField(blank=True, help_text="Optional detailed feedback")
    
    # Metadata
    timestamp = models.DateTimeField(auto_now_add=True)
    user_agent = models.CharField(max_length=500, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        unique_together = ['conversation', 'feedback_type']  # Prevent duplicate feedback
    
    def __str__(self):
        if self.star_rating:
            return f"Feedback: {self.star_rating}/5 stars"
        elif self.is_helpful is not None:
            return f"Feedback: {'Helpful' if self.is_helpful else 'Not Helpful'}"
        return f"Feedback: {self.feedback_type}"

class UnansweredQuestion(models.Model):
    """Store questions that the bot couldn't answer properly"""
    user_message = models.TextField()
    detected_language = models.CharField(max_length=2, choices=Conversation.LANGUAGE_CHOICES, default='en')
    session_id = models.CharField(max_length=100, null=True, blank=True)
    
    # Context information
    confidence_score = models.FloatField(null=True, blank=True)
    intent = models.CharField(max_length=100, null=True, blank=True)
    bot_response = models.TextField(help_text="The response that was given")
    
    # Processing status
    is_processed = models.BooleanField(default=False)
    converted_to_faq = models.BooleanField(default=False)
    admin_notes = models.TextField(blank=True)
    
    # Frequency tracking
    frequency_count = models.IntegerField(default=1, help_text="How many times this question was asked")
    first_asked = models.DateTimeField(auto_now_add=True)
    last_asked = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-frequency_count', '-last_asked']
    
    def __str__(self):
        return f"Unanswered ({self.frequency_count}x): {self.user_message[:50]}..."

class FAQ(models.Model):
    """Store frequently asked questions and their answers"""
    question = models.TextField(help_text="The question in its original form")
    answer = models.TextField()
    language = models.CharField(max_length=2, choices=Conversation.LANGUAGE_CHOICES, default='en')
    
    # Categorization
    category = models.CharField(max_length=100, blank=True, help_text="e.g., Registration, Academics, Campus Life")
    keywords = models.CharField(max_length=500, blank=True, help_text="Comma-separated keywords for search")
    
    # Metadata
    is_active = models.BooleanField(default=True)
    created_from_unanswered = models.ForeignKey(
        UnansweredQuestion, 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        help_text="If this FAQ was created from an unanswered question"
    )
    usage_count = models.IntegerField(default=0, help_text="How many times this FAQ was served")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['-usage_count', 'category']
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"
    
    def __str__(self):
        return f"FAQ ({self.language}): {self.question[:50]}..."

class UserLanguagePreference(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    preferred_language = models.CharField(
        max_length=2, 
        choices=Conversation.LANGUAGE_CHOICES, 
        default='en'
    )
    auto_detect = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.preferred_language}"

class ChatAnalytics(models.Model):
    """Store analytics data for admin dashboard"""
    date = models.DateField(auto_now_add=True)
    total_conversations = models.IntegerField(default=0)
    successful_responses = models.IntegerField(default=0)
    fallback_responses = models.IntegerField(default=0)
    positive_feedback = models.IntegerField(default=0)
    negative_feedback = models.IntegerField(default=0)
    
    # Language breakdown
    english_conversations = models.IntegerField(default=0)
    shona_conversations = models.IntegerField(default=0)
    
    # Common intents (stored as JSON)
    top_intents = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-date']
        unique_together = ['date']
    
    def __str__(self):
        return f"Analytics for {self.date}"
    
class MentalHealthResource(models.Model):
    """Store mental health resources and emergency contacts"""
    RESOURCE_TYPES = [
        ('emergency', 'Emergency Contact'),
        ('counseling', 'Counseling Service'),
        ('hotline', 'Crisis Hotline'),
        ('online', 'Online Resource'),
        ('campus', 'Campus Service'),
        ('external', 'External Service'),
        ('self_help', 'Self-Help Resource'),
        ('app', 'Mobile App'),
        ('book', 'Reading Material'),
        ('video', 'Video Resource')
    ]
    
    URGENCY_LEVELS = [
        ('immediate', 'Immediate Crisis'),
        ('urgent', 'Urgent Support'),
        ('general', 'General Support'),
        ('preventive', 'Preventive Care')
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    resource_type = models.CharField(max_length=20, choices=RESOURCE_TYPES)
    urgency_level = models.CharField(max_length=20, choices=URGENCY_LEVELS, default='general')
    
    # Contact information
    phone_number = models.CharField(max_length=50, blank=True, help_text="Include country code if international")
    email = models.EmailField(blank=True)
    website_url = models.URLField(blank=True)
    address = models.TextField(blank=True)
    
    # Availability
    hours_of_operation = models.CharField(max_length=200, blank=True)
    available_247 = models.BooleanField(default=False)
    
    # Languages and location
    languages_supported = models.CharField(
        max_length=100, 
        default='en', 
        help_text="Comma-separated language codes (en, sn, etc.)"
    )
    location_specific = models.CharField(
        max_length=100, 
        blank=True,
        help_text="Specific to country/region (e.g., 'Zimbabwe', 'Harare')"
    )
    
    # Metadata
    is_verified = models.BooleanField(default=True, help_text="Has this resource been verified as legitimate?")
    is_active = models.BooleanField(default=True)
    usage_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Keywords for matching
    keywords = models.TextField(
        blank=True,
        help_text="Keywords that trigger this resource (comma-separated)"
    )
    
    class Meta:
        ordering = ['urgency_level', '-is_active', 'title']
    
    def __str__(self):
        return f"{self.title} ({self.get_resource_type_display()})"
    
    def get_languages_list(self):
        return [lang.strip() for lang in self.languages_supported.split(',')]

class MentalHealthTrigger(models.Model):
    """Keywords and phrases that indicate mental health concerns"""
    CONCERN_LEVELS = [
        ('crisis', 'Crisis - Immediate Intervention'),
        ('high', 'High Concern'),
        ('moderate', 'Moderate Concern'),
        ('low', 'Low Concern')
    ]
    
    trigger_phrase = models.CharField(max_length=200, unique=True)
    language = models.CharField(max_length=2, choices=Conversation.LANGUAGE_CHOICES, default='en')
    concern_level = models.CharField(max_length=20, choices=CONCERN_LEVELS)
    
    # Response configuration
    suggested_resources = models.ManyToManyField(MentalHealthResource, blank=True)
    custom_response = models.TextField(
        blank=True,
        help_text="Custom response for this trigger (optional)"
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['concern_level', 'language', 'trigger_phrase']
    
    def __str__(self):
        return f"{self.trigger_phrase} ({self.get_concern_level_display()})"

class MentalHealthInteraction(models.Model):
    """Log mental health related interactions for follow-up"""
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_id = models.CharField(max_length=100)
    
    # Detected concern
    trigger_used = models.ForeignKey(MentalHealthTrigger, on_delete=models.SET_NULL, null=True)
    concern_level = models.CharField(
        max_length=20, 
        choices=MentalHealthTrigger.CONCERN_LEVELS,
        default='low'
    )
    
    # Resources provided
    resources_provided = models.ManyToManyField(MentalHealthResource, blank=True)
    
    # Follow-up tracking
    requires_follow_up = models.BooleanField(default=False)
    follow_up_completed = models.BooleanField(default=False)
    follow_up_notes = models.TextField(blank=True)
    
    # Metadata
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"Mental Health Interaction - {self.concern_level} - {self.timestamp}"

class CrisisAlert(models.Model):
    """Store crisis-level interactions for immediate attention"""
    STATUS_CHOICES = [
        ('new', 'New Alert'),
        ('acknowledged', 'Acknowledged'),
        ('contacted', 'User Contacted'),
        ('resolved', 'Resolved'),
        ('escalated', 'Escalated to Professional')
    ]
    
    mental_health_interaction = models.ForeignKey(MentalHealthInteraction, on_delete=models.CASCADE)
    alert_message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    
    # Response tracking
    acknowledged_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    response_notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Crisis Alert - {self.status} - {self.created_at}"