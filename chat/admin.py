from .models import models
from django.contrib import admin
from .models import Notification
from django.db.models import Count, Avg
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    Conversation, ChatFeedback, UnansweredQuestion, 
    FAQ, UserLanguagePreference, ChatAnalytics
)
from .models import (
    MentalHealthResource, MentalHealthTrigger, 
    MentalHealthInteraction, CrisisAlert
)
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'user', 'detected_language', 'short_message', 
        'confidence_score', 'is_fallback', 'has_feedback', 'timestamp'
    ]
    list_filter = ['detected_language', 'is_fallback', 'timestamp', 'intent']
    search_fields = ['user_message', 'bot_response', 'user__username']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'
    
    def short_message(self, obj):
        return obj.user_message[:50] + '...' if len(obj.user_message) > 50 else obj.user_message
    short_message.short_description = 'User Message'
    
    def has_feedback(self, obj):
        count = obj.feedback.count()
        if count > 0:
            return format_html('<span style="color: green;">✓ {}</span>', count)
        return format_html('<span style="color: gray;">—</span>')
    has_feedback.short_description = 'Feedback'
    
    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(request, extra_context)
        
        # Add summary statistics
        total_conversations = Conversation.objects.count()
        fallback_conversations = Conversation.objects.filter(is_fallback=True).count()
        avg_confidence = Conversation.objects.filter(
            confidence_score__isnull=False
        ).aggregate(avg=Avg('confidence_score'))['avg']
        
        positive_feedback = ChatFeedback.objects.filter(
            models.Q(is_helpful=True) | models.Q(star_rating__gte=4)
        ).count()
        
        response.context_data['summary'] = {
            'total_conversations': total_conversations,
            'fallback_rate': f"{(fallback_conversations/total_conversations*100):.1f}%" if total_conversations > 0 else "0%",
            'avg_confidence': f"{avg_confidence:.2f}" if avg_confidence else "N/A",
            'positive_feedback': positive_feedback
        }
        
        return response

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'message', 'scheduled_time', 'is_sent', 'is_read')
    list_filter = ('scheduled_time', 'is_sent', 'is_read')
    
    # Hide is_sent from the form
    exclude = ("is_sent",)

@admin.register(ChatFeedback)
class ChatFeedbackAdmin(admin.ModelAdmin):
    list_display = [
        'conversation_id', 'feedback_type', 'rating_display', 
        'is_helpful', 'has_text', 'timestamp'
    ]
    list_filter = ['feedback_type', 'is_helpful', 'star_rating', 'timestamp']
    search_fields = ['feedback_text', 'conversation__user_message']
    readonly_fields = ['timestamp', 'user_agent', 'ip_address']
    
    def rating_display(self, obj):
        if obj.star_rating:
            stars = '★' * obj.star_rating + '☆' * (5 - obj.star_rating)
            return format_html('<span title="{}/5 stars">{}</span>', obj.star_rating, stars)
        return '—'
    rating_display.short_description = 'Rating'
    
    def has_text(self, obj):
        return bool(obj.feedback_text.strip())
    has_text.boolean = True
    has_text.short_description = 'Has Text'

@admin.register(UnansweredQuestion)
class UnansweredQuestionAdmin(admin.ModelAdmin):
    list_display = [
        'short_question', 'detected_language', 'frequency_count',
        'confidence_score', 'is_processed', 'converted_to_faq', 'last_asked'
    ]
    list_filter = ['detected_language', 'is_processed', 'converted_to_faq', 'last_asked']
    search_fields = ['user_message', 'admin_notes']
    actions = ['convert_to_faq', 'mark_as_processed']
    
    def short_question(self, obj):
        return obj.user_message[:60] + '...' if len(obj.user_message) > 60 else obj.user_message
    short_question.short_description = 'Question'
    
    def convert_to_faq(self, request, queryset):
        count = 0
        for question in queryset:
            if not question.converted_to_faq:
                # Create FAQ entry
                FAQ.objects.create(
                    question=question.user_message,
                    answer="[Please add appropriate answer]",
                    language=question.detected_language,
                    created_from_unanswered=question,
                    created_by=request.user
                )
                question.converted_to_faq = True
                question.is_processed = True
                question.save()
                count += 1
        
        self.message_user(request, f"Successfully converted {count} questions to FAQs")
    convert_to_faq.short_description = "Convert selected questions to FAQs"
    
    def mark_as_processed(self, request, queryset):
        count = queryset.update(is_processed=True)
        self.message_user(request, f"Marked {count} questions as processed")
    mark_as_processed.short_description = "Mark as processed"

@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = [
        'short_question', 'language', 'category', 'usage_count',
        'is_active', 'created_at', 'created_by'
    ]
    list_filter = ['language', 'category', 'is_active', 'created_at']
    search_fields = ['question', 'answer', 'keywords', 'category']
    readonly_fields = ['usage_count', 'created_at', 'updated_at']
    
    def short_question(self, obj):
        return obj.question[:50] + '...' if len(obj.question) > 50 else obj.question
    short_question.short_description = 'Question'
    
    def save_model(self, request, obj, form, change):
        if not change:  # New object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(UserLanguagePreference)
class UserLanguagePreferenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'preferred_language', 'auto_detect']
    list_filter = ['preferred_language', 'auto_detect']
    search_fields = ['user__username', 'user__email']

@admin.register(ChatAnalytics)
class ChatAnalyticsAdmin(admin.ModelAdmin):
    list_display = [
        'date', 'total_conversations', 'success_rate', 
        'feedback_ratio', 'language_breakdown'
    ]
    list_filter = ['date']
    readonly_fields = ['date']
    
    def success_rate(self, obj):
        if obj.total_conversations > 0:
            rate = (obj.successful_responses / obj.total_conversations) * 100
            return f"{rate:.1f}%"
        return "0%"
    success_rate.short_description = 'Success Rate'
    
    def feedback_ratio(self, obj):
        total_feedback = obj.positive_feedback + obj.negative_feedback
        if total_feedback > 0:
            positive_rate = (obj.positive_feedback / total_feedback) * 100
            return f"{positive_rate:.1f}% positive"
        return "No feedback"
    feedback_ratio.short_description = 'Feedback Ratio'
    
    def language_breakdown(self, obj):
        total = obj.english_conversations + obj.shona_conversations
        if total > 0:
            en_percent = (obj.english_conversations / total) * 100
            sn_percent = (obj.shona_conversations / total) * 100
            return f"EN: {en_percent:.0f}%, SN: {sn_percent:.0f}%"
        return "No data"
    language_breakdown.short_description = 'Languages'
@admin.register(MentalHealthResource)
class MentalHealthResourceAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'resource_type', 'urgency_level', 'available_247', 
        'languages_supported', 'usage_count', 'is_active'
    ]
    list_filter = ['resource_type', 'urgency_level', 'available_247', 'is_active', 'location_specific']
    search_fields = ['title', 'description', 'keywords']
    readonly_fields = ['usage_count', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'resource_type', 'urgency_level')
        }),
        ('Contact Information', {
            'fields': ('phone_number', 'email', 'website_url', 'address')
        }),
        ('Availability', {
            'fields': ('hours_of_operation', 'available_247')
        }),
        ('Targeting', {
            'fields': ('languages_supported', 'location_specific', 'keywords')
        }),
        ('Status', {
            'fields': ('is_active', 'is_verified', 'usage_count')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related()

@admin.register(MentalHealthTrigger)
class MentalHealthTriggerAdmin(admin.ModelAdmin):
    list_display = [
        'trigger_phrase', 'language', 'concern_level', 
        'resource_count', 'is_active', 'created_at'
    ]
    list_filter = ['concern_level', 'language', 'is_active']
    search_fields = ['trigger_phrase', 'custom_response']
    filter_horizontal = ['suggested_resources']
    
    def resource_count(self, obj):
        count = obj.suggested_resources.count()
        return format_html('<span class="badge">{}</span>', count)
    resource_count.short_description = 'Resources'

@admin.register(MentalHealthInteraction)
class MentalHealthInteractionAdmin(admin.ModelAdmin):
    list_display = [
        'timestamp', 'concern_level', 'session_id', 'user',
        'follow_up_status', 'crisis_alert_status'
    ]
    list_filter = [
        'concern_level', 'requires_follow_up', 'follow_up_completed', 
        'timestamp', 'trigger_used__concern_level'
    ]
    search_fields = ['session_id', 'user__username', 'follow_up_notes']
    readonly_fields = ['timestamp', 'ip_address']
    filter_horizontal = ['resources_provided']
    
    actions = ['mark_follow_up_completed']
    
    def follow_up_status(self, obj):
        if not obj.requires_follow_up:
            return format_html('<span style="color: gray;">Not Required</span>')
        elif obj.follow_up_completed:
            return format_html('<span style="color: green;">✓ Completed</span>')
        else:
            return format_html('<span style="color: orange;">⚠ Pending</span>')
    follow_up_status.short_description = 'Follow-up'
    
    def crisis_alert_status(self, obj):
        if hasattr(obj, 'crisisalert'):
            alert = obj.crisisalert
            color_map = {
                'new': 'red',
                'acknowledged': 'orange', 
                'contacted': 'blue',
                'resolved': 'green',
                'escalated': 'purple'
            }
            color = color_map.get(alert.status, 'gray')
            return format_html(
                '<span style="color: {};">🚨 {}</span>', 
                color, alert.get_status_display()
            )
        return '-'
    crisis_alert_status.short_description = 'Crisis Alert'
    
    def mark_follow_up_completed(self, request, queryset):
        count = queryset.update(follow_up_completed=True)
        self.message_user(request, f"Marked {count} interactions as follow-up completed")
    mark_follow_up_completed.short_description = "Mark follow-up as completed"

@admin.register(CrisisAlert)
class CrisisAlertAdmin(admin.ModelAdmin):
    list_display = [
        'created_at', 'status', 'session_display', 'concern_level',
        'acknowledged_by', 'response_time'
    ]
    list_filter = ['status', 'created_at', 'mental_health_interaction__concern_level']
    search_fields = ['alert_message', 'response_notes', 'mental_health_interaction__session_id']
    readonly_fields = ['created_at', 'mental_health_interaction']
    
    actions = ['mark_acknowledged', 'mark_contacted', 'mark_resolved']
    
    def session_display(self, obj):
        return obj.mental_health_interaction.session_id[:20] + '...' if len(obj.mental_health_interaction.session_id) > 20 else obj.mental_health_interaction.session_id
    session_display.short_description = 'Session'
    
    def concern_level(self, obj):
        level = obj.mental_health_interaction.concern_level
        color_map = {'crisis': 'red', 'high': 'orange', 'moderate': 'blue', 'low': 'green'}
        color = color_map.get(level, 'gray')
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, level.upper())
    concern_level.short_description = 'Concern Level'
    
    def response_time(self, obj):
        if obj.acknowledged_at:
            delta = obj.acknowledged_at - obj.created_at
            if delta.total_seconds() < 3600:  # Less than 1 hour
                return format_html('<span style="color: green;">{} min</span>', int(delta.total_seconds() / 60))
            else:
                return format_html('<span style="color: orange;">{:.1f} hours</span>', delta.total_seconds() / 3600)
        return format_html('<span style="color: red;">Not acknowledged</span>')
    response_time.short_description = 'Response Time'
    
    def mark_acknowledged(self, request, queryset):
        from django.utils import timezone
        count = queryset.filter(status='new').update(
            status='acknowledged',
            acknowledged_by=request.user,
            acknowledged_at=timezone.now()
        )
        self.message_user(request, f"Marked {count} alerts as acknowledged")
    mark_acknowledged.short_description = "Mark as acknowledged"
    
    def mark_contacted(self, request, queryset):
        count = queryset.update(status='contacted')
        self.message_user(request, f"Marked {count} alerts as contacted")
    mark_contacted.short_description = "Mark as contacted"
    
    def mark_resolved(self, request, queryset):
        from django.utils import timezone
        count = queryset.update(status='resolved', resolved_at=timezone.now())
        self.message_user(request, f"Marked {count} alerts as resolved")
    mark_resolved.short_description = "Mark as resolved"
    
    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(request, extra_context)
        
        # Add crisis alert summary
        new_alerts = CrisisAlert.objects.filter(status='new').count()
        pending_alerts = CrisisAlert.objects.filter(status__in=['new', 'acknowledged']).count()
        
        response.context_data['crisis_summary'] = {
            'new_alerts': new_alerts,
            'pending_alerts': pending_alerts
        }
        
        return response

# Customize the admin site for mental health section
class MentalHealthAdminSection:
    """Custom admin section for mental health features"""
    
    @staticmethod
    def get_crisis_alerts_count():
        return CrisisAlert.objects.filter(status='new').count()
    
    @staticmethod
    def get_pending_followups_count():
        return MentalHealthInteraction.objects.filter(
            requires_follow_up=True,
            follow_up_completed=False
        ).count()
# Custom admin site customization
admin.site.site_header = "Womens University in Africa Chatbot Admin"
admin.site.site_title = "Chatbot Admin Portal"
admin.site.index_title = "Welcome to Chatbot Administration"