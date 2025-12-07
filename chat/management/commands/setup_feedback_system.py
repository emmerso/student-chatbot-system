from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from chat.models import FAQ  # Replace 'chat' with your actual app name

class Command(BaseCommand):
    help = 'Set up initial FAQ data for the feedback system'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Setting up feedback system...'))

        # Sample FAQ data in English
        english_faqs = [
            {
                'question': 'How do I register for courses?',
                'answer': 'You can register for courses through the student portal. Log in with your student ID and password, then navigate to Course Registration.',
                'category': 'Registration',
                'keywords': 'register, course, registration, enroll, enrollment'
            },
            {
                'question': 'What are the library hours?',
                'answer': 'The library is open Monday-Friday 8:00 AM to 10:00 PM, Saturday 9:00 AM to 6:00 PM, and Sunday 12:00 PM to 8:00 PM.',
                'category': 'Campus Services',
                'keywords': 'library, hours, time, open, close'
            },
            {
                'question': 'How do I access my grades?',
                'answer': 'You can access your grades through the student portal. Go to Academic Records > View Grades to see your current and past semester grades.',
                'category': 'Academics',
                'keywords': 'grades, marks, results, academic, transcript'
            },
            {
                'question': 'Where is the student support center?',
                'answer': 'The Student Support Center is located in Building A, Ground Floor, Room 105. Office hours are Monday-Friday 8:00 AM to 5:00 PM.',
                'category': 'Campus Services',
                'keywords': 'support, help, assistance, building, location'
            },
            {
                'question': 'How do I pay my fees?',
                'answer': 'You can pay fees online through the student portal, at the bank using your student number, or at the bursar office in cash or card.',
                'category': 'Finance',
                'keywords': 'fees, payment, pay, money, bursar, finance'
            }
        ]

        # Sample FAQ data in Shona
        shona_faqs = [
            {
                'question': 'Ndinonyoresa sei makosi?',
                'answer': 'Unogona kunyoresa makosi kuburikidza neStudent Portal. Pinda neStudent ID yako nepassword, wobva waenda kuCourse Registration.',
                'category': 'Registration',
                'keywords': 'nyoresa, kosi, registration, enroll'
            },
            {
                'question': 'Nguva dzei dzinoshanda library?',
                'answer': 'Library inoshanda Muvhuro kusvika Chishanu 8:00 mangwanani kusvika 10:00 madekwana, Mugovera 9:00 mangwanani kusvika 6:00 madekwana, uye Svondo 12:00 masikati kusvika 8:00 madekwana.',
                'category': 'Campus Services',
                'keywords': 'library, nguva, time, vhura, vhara'
            },
            {
                'question': 'Ndinoona sei grades dzangu?',
                'answer': 'Unogona kuona grades dzako kuburikidza neStudent Portal. Enda kuAcademic Records > View Grades kuti uone grades dzako dzezvino nedziakare.',
                'category': 'Academics',
                'keywords': 'grades, marks, mibvunzo, academic'
            },
            {
                'question': 'Iri kupi Student Support Center?',
                'answer': 'Student Support Center iri muBuilding A, Ground Floor, Room 105. Office hours ndiMuvhuro kusvika Chishanu 8:00 mangwanani kusvika 5:00 madekwana.',
                'category': 'Campus Services',
                'keywords': 'support, rubatsiro, building, location'
            }
        ]

        # Create English FAQs
        english_count = 0
        for faq_data in english_faqs:
            faq, created = FAQ.objects.get_or_create(
                question=faq_data['question'],
                language='en',
                defaults={
                    'answer': faq_data['answer'],
                    'category': faq_data['category'],
                    'keywords': faq_data['keywords'],
                    'is_active': True
                }
            )
            if created:
                english_count += 1
                self.stdout.write(f"Created English FAQ: {faq.question[:50]}...")

        # Create Shona FAQs
        shona_count = 0
        for faq_data in shona_faqs:
            faq, created = FAQ.objects.get_or_create(
                question=faq_data['question'],
                language='sn',
                defaults={
                    'answer': faq_data['answer'],
                    'category': faq_data['category'],
                    'keywords': faq_data['keywords'],
                    'is_active': True
                }
            )
            if created:
                shona_count += 1
                self.stdout.write(f"Created Shona FAQ: {faq.question[:50]}...")

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {english_count} English FAQs and {shona_count} Shona FAQs'
            )
        )