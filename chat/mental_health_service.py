import re
import logging
from typing import List, Dict, Tuple, Optional
from django.db.models import Q
from .models import MentalHealthTrigger, MentalHealthResource, MentalHealthInteraction, CrisisAlert

logger = logging.getLogger(__name__)

class MentalHealthDetectionService:
    """Service for detecting mental health concerns and providing appropriate resources"""
    
    def __init__(self):
        self.crisis_keywords = {
            'en': [
                'suicide', 'kill myself', 'end my life', 'want to die', 
                'harm myself', 'hurt myself', 'self harm', 'cutting',
                'overdose', 'pills', 'jump', 'hanging', 'weapon'
            ],
            'sn': [
                'kuzviuraya', 'kufira', 'ndinoda kufa', 'ndoda kuzviuraya',
                'kuzvirwadza', 'kurwadza', 'mafuta', 'mishonga'
            ]
        }
        
        self.high_concern_keywords = {
            'en': [
                'depression', 'depressed', 'anxiety', 'anxious', 'panic',
                'hopeless', 'worthless', 'alone', 'isolated', 'empty',
                'overwhelmed', 'stressed', 'trauma', 'ptsd', 'abuse',
                'addiction', 'substance', 'alcohol', 'drugs', 'cutting'
            ],
            'sn': [
                'kushushikana', 'kusuruvara', 'kutya', 'kurwara mupfungwa',
                'kushaiwa tariro', 'kusina basa', 'kusina vanhu', 'kusurukirwa'
            ]
        }
        
        self.moderate_concern_keywords = {
            'en': [
                'sad', 'worried', 'stressed', 'upset', 'frustrated',
                'angry', 'confused', 'tired', 'exhausted', 'burnt out',
                'relationship problems', 'family issues', 'academic stress'
            ],
            'sn': [
                'kushungurudzika', 'kunetseka', 'kushatirwa', 'kutsamwa',
                'kukanganisika', 'kuneta', 'matambudziko emhuri'
            ]
        }

    def analyze_message(self, message: str, language: str = 'en') -> Dict:
        """
        Analyze a message for mental health concerns
        Returns: {
            'concern_level': str,
            'triggers_found': List[str],
            'confidence': float,
            'recommended_resources': List[MentalHealthResource]
        }
        """
        message_lower = message.lower()
        result = {
            'concern_level': 'none',
            'triggers_found': [],
            'confidence': 0.0,
            'recommended_resources': []
        }
        
        # Check for crisis keywords first (highest priority)
        crisis_matches = self._check_keywords(message_lower, self.crisis_keywords.get(language, []))
        if crisis_matches:
            result['concern_level'] = 'crisis'
            result['triggers_found'].extend(crisis_matches)
            result['confidence'] = 0.9
            result['recommended_resources'] = self._get_crisis_resources(language)
            return result
        
        # Check database triggers
        db_trigger = self._check_database_triggers(message, language)
        if db_trigger:
            result['concern_level'] = db_trigger.concern_level
            result['triggers_found'].append(db_trigger.trigger_phrase)
            result['confidence'] = 0.8
            result['recommended_resources'] = list(db_trigger.suggested_resources.filter(is_active=True))
            return result
        
        # Check high concern keywords
        high_matches = self._check_keywords(message_lower, self.high_concern_keywords.get(language, []))
        if high_matches:
            result['concern_level'] = 'high'
            result['triggers_found'].extend(high_matches)
            result['confidence'] = 0.7
            result['recommended_resources'] = self._get_resources_by_level('high', language)
            return result
        
        # Check moderate concern keywords
        moderate_matches = self._check_keywords(message_lower, self.moderate_concern_keywords.get(language, []))
        if moderate_matches:
            result['concern_level'] = 'moderate'
            result['triggers_found'].extend(moderate_matches)
            result['confidence'] = 0.6
            result['recommended_resources'] = self._get_resources_by_level('moderate', language)
            return result
        
        return result
    
    def _check_keywords(self, message: str, keywords: List[str]) -> List[str]:
        """Check if any keywords are present in the message"""
        found = []
        for keyword in keywords:
            if re.search(r'\b' + re.escape(keyword) + r'\b', message, re.IGNORECASE):
                found.append(keyword)
        return found
    
    def _check_database_triggers(self, message: str, language: str) -> Optional[MentalHealthTrigger]:
        """Check message against database triggers"""
        triggers = MentalHealthTrigger.objects.filter(
            language=language, 
            is_active=True
        ).order_by('concern_level')  # Crisis first
        
        message_lower = message.lower()
        for trigger in triggers:
            if re.search(r'\b' + re.escape(trigger.trigger_phrase.lower()) + r'\b', message_lower):
                return trigger
        
        return None
    
    def _get_crisis_resources(self, language: str) -> List[MentalHealthResource]:
        """Get immediate crisis resources"""
        return list(MentalHealthResource.objects.filter(
            urgency_level='immediate',
            is_active=True,
            languages_supported__icontains=language
        ).order_by('available_247', 'title')[:3])
    
    def _get_resources_by_level(self, urgency_level: str, language: str) -> List[MentalHealthResource]:
        """Get resources by urgency level"""
        urgency_mapping = {
            'high': ['urgent', 'immediate'],
            'moderate': ['general', 'urgent'],
            'low': ['general', 'preventive']
        }
        
        levels = urgency_mapping.get(urgency_level, ['general'])
        return list(MentalHealthResource.objects.filter(
            urgency_level__in=levels,
            is_active=True,
            languages_supported__icontains=language
        ).order_by('urgency_level', 'usage_count')[:5])
    
    def create_mental_health_interaction(self, conversation, user, session_id, analysis_result, ip_address=None):
        """Create a record of mental health interaction"""
        interaction = MentalHealthInteraction.objects.create(
            conversation=conversation,
            user=user,
            session_id=session_id,
            concern_level=analysis_result['concern_level'],
            ip_address=ip_address
        )
        
        # Add resources provided
        if analysis_result['recommended_resources']:
            interaction.resources_provided.set(analysis_result['recommended_resources'])
        
        # Create crisis alert if needed
        if analysis_result['concern_level'] == 'crisis':
            self._create_crisis_alert(interaction, analysis_result)
        
        # Set follow-up requirement for high concern
        if analysis_result['concern_level'] in ['crisis', 'high']:
            interaction.requires_follow_up = True
            interaction.save()
        
        return interaction
    
    def _create_crisis_alert(self, interaction: MentalHealthInteraction, analysis_result: Dict):
        """Create a crisis alert for immediate attention"""
        alert_message = (
            f"CRISIS ALERT: User session {interaction.session_id} has expressed "
            f"concerning language indicating immediate risk. "
            f"Triggers: {', '.join(analysis_result['triggers_found'])}. "
            f"Immediate intervention may be required."
        )
        
        CrisisAlert.objects.create(
            mental_health_interaction=interaction,
            alert_message=alert_message
        )
        
        # Log for immediate attention
        logger.critical(f"CRISIS ALERT CREATED: Session {interaction.session_id}")
    
    def format_resource_response(self, resources: List[MentalHealthResource], language: str = 'en') -> str:
        """Format mental health resources into a user-friendly response"""
        if not resources:
            return self._get_fallback_response(language)
        
        # Crisis resources get special formatting
        crisis_resources = [r for r in resources if r.urgency_level == 'immediate']
        if crisis_resources:
            return self._format_crisis_response(crisis_resources, language)
        
        # Regular resources
        return self._format_regular_response(resources, language)
    
    def _format_crisis_response(self, resources: List[MentalHealthResource], language: str) -> str:
        """Format crisis-level response with immediate help"""
        if language == 'sn':
            response = ("🚨 KUKURUMIDZIRA: Kana uri munzvimbo yenjodzi, fona 999 kana uende ku"
                       "chipatara chakare.\n\nZvimwe zvinokubatsira:\n\n")
        else:
            response = ("🚨 URGENT: If you're in immediate danger, call 999 or go to your nearest "
                       "emergency room.\n\nImmediate support available:\n\n")
        
        for resource in resources:
            response += self._format_single_resource(resource, language, is_crisis=True)
        
        if language == 'sn':
            response += "\n💙 Unokosheswa uye uko kusina wega. Rubatsiro ruripo."
        else:
            response += "\n💙 You matter and you're not alone. Help is available."
        
        return response
    
    def _format_regular_response(self, resources: List[MentalHealthResource], language: str) -> str:
        """Format regular mental health response"""
        if language == 'sn':
            response = "Ndinzwisisa kuti unogona kutambudzika. Heano zvinokubatsira:\n\n"
        else:
            response = "I understand you might be going through a difficult time. Here are some resources that can help:\n\n"
        
        for resource in resources:
            response += self._format_single_resource(resource, language)
        
        if language == 'sn':
            response += "\n💚 Rangarira kuti kutsvaga rubatsiro hakusi urombo. Una simba."
        else:
            response += "\n💚 Remember, seeking help is a sign of strength, not weakness."
        
        return response
    
    def _format_single_resource(self, resource: MentalHealthResource, language: str, is_crisis: bool = False) -> str:
        """Format a single resource for display"""
        resource_text = f"📞 **{resource.title}**\n"
        
        if resource.phone_number:
            if language == 'sn':
                resource_text += f"   Nhare: {resource.phone_number}\n"
            else:
                resource_text += f"   Phone: {resource.phone_number}\n"
        
        if resource.available_247:
            if language == 'sn':
                resource_text += "   ⏰ Inoshanda mazuva ose, nguva dzose\n"
            else:
                resource_text += "   ⏰ Available 24/7\n"
        elif resource.hours_of_operation:
            if language == 'sn':
                resource_text += f"   ⏰ Nguva: {resource.hours_of_operation}\n"
            else:
                resource_text += f"   ⏰ Hours: {resource.hours_of_operation}\n"
        
        if resource.description:
            resource_text += f"   ℹ️ {resource.description}\n"
        
        if resource.website_url:
            resource_text += f"   🌐 {resource.website_url}\n"
        
        resource_text += "\n"
        return resource_text
    
    def _get_fallback_response(self, language: str) -> str:
        """Get fallback response when no specific resources are available"""
        if language == 'sn':
            return ("Ndinzwisisa kuti unogona kushungurudzika. Zvisinei kana ndisina "
                   "rubatsiro chakamira rurikuda, ndinokurudzira kuti utaure nemunhu "
                   "waunoda kana mushandi weutano.")
        else:
            return ("I understand you might be going through something difficult. "
                   "While I don't have specific resources immediately available, "
                   "I encourage you to speak with someone you trust or a healthcare professional.")