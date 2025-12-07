from django.core.management.base import BaseCommand
from chat.models import MentalHealthResource, MentalHealthTrigger  # Replace 'chat' with your app name

class Command(BaseCommand):
    help = 'Set up initial mental health resources and triggers'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Setting up mental health resources...'))

        # Crisis/Emergency Resources
        crisis_resources = [
            {
                'title': 'National Emergency Services',
                'description': 'Immediate emergency response for life-threatening situations',
                'resource_type': 'emergency',
                'urgency_level': 'immediate',
                'phone_number': '999',
                'available_247': True,
                'languages_supported': 'en,sn',
                'location_specific': 'Zimbabwe',
                'keywords': 'emergency, crisis, suicide, immediate danger, urgent help'
            },
            {
                'title': 'Zimbabwe Crisis Helpline',
                'description': 'Crisis counseling and immediate support for mental health emergencies',
                'resource_type': 'hotline',
                'urgency_level': 'immediate',
                'phone_number': '+263 4 700 505',
                'available_247': True,
                'languages_supported': 'en,sn',
                'location_specific': 'Zimbabwe',
                'keywords': 'crisis, helpline, suicide prevention, immediate support'
            },
            {
                'title': 'Parirenyatwa Hospital Emergency',
                'description': 'Major hospital with 24/7 emergency psychiatric services',
                'resource_type': 'emergency',
                'urgency_level': 'immediate',
                'phone_number': '+263 4 791 631',
                'address': 'Mazowe Street, Harare',
                'available_247': True,
                'languages_supported': 'en,sn',
                'location_specific': 'Harare, Zimbabwe',
                'keywords': 'hospital, emergency, psychiatric, medical emergency'
            }
        ]

        # Counseling and Support Services
        counseling_resources = [
            {
                'title': 'University Counseling Center',
                'description': 'Free counseling services for university students',
                'resource_type': 'campus',
                'urgency_level': 'general',
                'phone_number': '+263 4 303211',
                'email': 'counseling@university.ac.zw',
                'address': 'Student Services Building, Ground Floor',
                'hours_of_operation': 'Monday-Friday 8:00 AM - 5:00 PM',
                'languages_supported': 'en,sn',
                'keywords': 'counseling, therapy, student support, mental health services'
            },
            {
                'title': 'Samaritans Zimbabwe',
                'description': 'Confidential emotional support for people in distress',
                'resource_type': 'hotline',
                'urgency_level': 'urgent',
                'phone_number': '+263 4 722 000',
                'email': 'samaritans@zol.co.zw',
                'available_247': True,
                'languages_supported': 'en,sn',
                'location_specific': 'Zimbabwe',
                'keywords': 'emotional support, confidential, distress, listening ear'
            },
            {
                'title': 'Friendship Bench',
                'description': 'Community-based mental health support program',
                'resource_type': 'counseling',
                'urgency_level': 'general',
                'website_url': 'https://www.friendshipbenchzimbabwe.org',
                'languages_supported': 'en,sn',
                'location_specific': 'Zimbabwe',
                'keywords': 'community support, friendship bench, mental health, local support'
            },
            {
                'title': 'Zimbabwe National Association for Mental Health (ZNAMH)',
                'description': 'Support and advocacy for mental health issues',
                'resource_type': 'external',
                'urgency_level': 'general',
                'phone_number': '+263 4 703 891',
                'email': 'znamh@znamh.co.zw',
                'website_url': 'http://www.znamh.co.zw',
                'languages_supported': 'en,sn',
                'location_specific': 'Zimbabwe',
                'keywords': 'mental health association, advocacy, support groups'
            }
        ]

        # Online and Self-Help Resources
        online_resources = [
            {
                'title': 'Crisis Text Line',
                'description': 'Free crisis support via text message',
                'resource_type': 'online',
                'urgency_level': 'urgent',
                'phone_number': 'Text HOME to 741741',
                'available_247': True,
                'languages_supported': 'en',
                'keywords': 'text support, crisis text, messaging support'
            },
            {
                'title': 'Mental Health America Resources',
                'description': 'Comprehensive mental health information and screening tools',
                'resource_type': 'online',
                'urgency_level': 'preventive',
                'website_url': 'https://www.mhanational.org',
                'languages_supported': 'en',
                'keywords': 'mental health information, screening, self-help'
            },
            {
                'title': 'Headspace App',
                'description': 'Guided meditation and mindfulness app',
                'resource_type': 'app',
                'urgency_level': 'preventive',
                'website_url': 'https://www.headspace.com',
                'languages_supported': 'en',
                'keywords': 'meditation, mindfulness, stress relief, mental wellness'
            }
        ]

        # Create all resources
        all_resources = crisis_resources + counseling_resources + online_resources
        created_count = 0

        for resource_data in all_resources:
            resource, created = MentalHealthResource.objects.get_or_create(
                title=resource_data['title'],
                defaults=resource_data
            )
            if created:
                created_count += 1
                self.stdout.write(f"Created resource: {resource.title}")

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} mental health resources')
        )

        # Create Mental Health Triggers
        triggers_data = [
            # Crisis level triggers (English)
            {'phrase': 'want to kill myself', 'language': 'en', 'level': 'crisis'},
            {'phrase': 'going to end my life', 'language': 'en', 'level': 'crisis'},
            {'phrase': 'suicide', 'language': 'en', 'level': 'crisis'},
            {'phrase': 'want to die', 'language': 'en', 'level': 'crisis'},
            {'phrase': 'harm myself', 'language': 'en', 'level': 'crisis'},
            {'phrase': 'hurt myself', 'language': 'en', 'level': 'crisis'},
            
            # Crisis level triggers (Shona)
            {'phrase': 'ndinoda kuzviuraya', 'language': 'sn', 'level': 'crisis'},
            {'phrase': 'ndinoda kufa', 'language': 'sn', 'level': 'crisis'},
            {'phrase': 'ndinoda kuzvirwadza', 'language': 'sn', 'level': 'crisis'},
            
            # High concern triggers (English)
            {'phrase': 'severely depressed', 'language': 'en', 'level': 'high'},
            {'phrase': 'panic attacks', 'language': 'en', 'level': 'high'},
            {'phrase': 'cant cope anymore', 'language': 'en', 'level': 'high'},
            {'phrase': 'feeling hopeless', 'language': 'en', 'level': 'high'},
            {'phrase': 'severe anxiety', 'language': 'en', 'level': 'high'},
            {'phrase': 'mental breakdown', 'language': 'en', 'level': 'high'},
            
            # High concern triggers (Shona)
            {'phrase': 'kushushikana kwakanyanya', 'language': 'sn', 'level': 'high'},
            {'phrase': 'kusina tariro', 'language': 'sn', 'level': 'high'},
            {'phrase': 'kurwara mupfungwa', 'language': 'sn', 'level': 'high'},
            
            # Moderate concern triggers (English)
            {'phrase': 'feeling sad', 'language': 'en', 'level': 'moderate'},
            {'phrase': 'very stressed', 'language': 'en', 'level': 'moderate'},
            {'phrase': 'overwhelmed', 'language': 'en', 'level': 'moderate'},
            {'phrase': 'having trouble sleeping', 'language': 'en', 'level': 'moderate'},
            {'phrase': 'family problems', 'language': 'en', 'level': 'moderate'},
            {'phrase': 'relationship issues', 'language': 'en', 'level': 'moderate'},
            
            # Moderate concern triggers (Shona)
            {'phrase': 'ndiri kushungurudzika', 'language': 'sn', 'level': 'moderate'},
            {'phrase': 'ndiri kuneta', 'language': 'sn', 'level': 'moderate'},
            {'phrase': 'matambudziko emhuri', 'language': 'sn', 'level': 'moderate'},
        ]

        trigger_created_count = 0
        for trigger_data in triggers_data:
            trigger, created = MentalHealthTrigger.objects.get_or_create(
                trigger_phrase=trigger_data['phrase'],
                language=trigger_data['language'],
                defaults={
                    'concern_level': trigger_data['level'],
                    'is_active': True
                }
            )
            if created:
                trigger_created_count += 1
                self.stdout.write(f"Created trigger: {trigger.trigger_phrase} ({trigger.concern_level})")

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {trigger_created_count} mental health triggers')
        )

        # Link triggers to appropriate resources
        self._link_triggers_to_resources()

        self.stdout.write(
            self.style.SUCCESS('Mental health system setup completed successfully!')
        )

    def _link_triggers_to_resources(self):
        """Link triggers to appropriate resources based on concern level"""
        
        # Get resources by urgency level
        crisis_resources = MentalHealthResource.objects.filter(urgency_level='immediate')
        urgent_resources = MentalHealthResource.objects.filter(urgency_level='urgent')
        general_resources = MentalHealthResource.objects.filter(urgency_level='general')
        
        # Link crisis triggers to crisis resources
        crisis_triggers = MentalHealthTrigger.objects.filter(concern_level='crisis')
        for trigger in crisis_triggers:
            trigger.suggested_resources.set(crisis_resources)
        
        # Link high concern triggers to urgent and crisis resources
        high_triggers = MentalHealthTrigger.objects.filter(concern_level='high')
        for trigger in high_triggers:
            trigger.suggested_resources.set(list(crisis_resources) + list(urgent_resources))
        
        # Link moderate triggers to general and urgent resources
        moderate_triggers = MentalHealthTrigger.objects.filter(concern_level='moderate')
        for trigger in moderate_triggers:
            trigger.suggested_resources.set(list(urgent_resources) + list(general_resources))
        
        self.stdout.write("Linked triggers to appropriate resources")