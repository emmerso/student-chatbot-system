from .mental_health_service import MentalHealthDetectionService
from django.shortcuts import render
from django.http import JsonResponse
from django.utils import timezone
from .models import Notification
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods
from django.db.models import Q, F
import requests
import json
import logging
from difflib import SequenceMatcher

from .translator import translator
from .mental_health_service import MentalHealthDetectionService
from .models import (
    Conversation, ChatFeedback, UnansweredQuestion, FAQ, 
    MentalHealthResource, MentalHealthInteraction
)

logger = logging.getLogger(__name__)

def chatbot(request):
    return render(request, "chat/index.html")

@csrf_exempt
def multilingual_chat(request):
    """
    Enhanced multilingual chat endpoint with mental health detection and feedback tracking
    """
    if request.method == "POST":
        try:
            # Handle both JSON and form data
            if request.content_type == 'application/json':
                data = json.loads(request.body)
                user_message = data.get("message", "").strip()
            else:
                user_message = request.POST.get("message", "").strip()
            
            if not user_message:
                return JsonResponse({"error": "No message provided"}, status=400)
            
            # Get session ID and user info for tracking
            session_id = request.session.session_key or f"anon_{request.META.get('REMOTE_ADDR', 'unknown')}"
            user = request.user if request.user.is_authenticated else None
            client_ip = get_client_ip(request)
            
            # Detect user's language
            user_language = translator.detect_language(user_message)
            logger.info(f"Detected language: {user_language} for message: {user_message}")
            
            # MENTAL HEALTH CHECK - Priority 1 (Highest Priority)
            mental_health_service = MentalHealthDetectionService()
            mental_health_analysis = mental_health_service.analyze_message(user_message, user_language)
            
            if mental_health_analysis['concern_level'] != 'none':
                logger.info(f"Mental health concern detected: {mental_health_analysis['concern_level']}")
                
                # Create mental health response
                mental_health_response = mental_health_service.format_resource_response(
                    mental_health_analysis['recommended_resources'], 
                    user_language
                )
                
                # Create conversation record
                conversation = Conversation.objects.create(
                    user=user,
                    session_id=session_id,
                    user_message=user_message,
                    bot_response=mental_health_response,
                    detected_language=user_language,
                    confidence_score=mental_health_analysis['confidence'],
                    intent="mental_health_support",
                    is_fallback=False
                )
                
                # Create mental health interaction record
                mental_health_service.create_mental_health_interaction(
                    conversation, user, session_id, mental_health_analysis, client_ip
                )
                
                # Update resource usage counts
                for resource in mental_health_analysis['recommended_resources']:
                    resource.usage_count = F('usage_count') + 1
                    resource.save()
                
                return JsonResponse({
                    'response': mental_health_response,
                    'detected_language': user_language,
                    'conversation_id': conversation.id,
                    'mental_health_detected': True,
                    'concern_level': mental_health_analysis['concern_level'],
                    'confidence_score': mental_health_analysis['confidence'],
                    'source': 'mental_health_support'
                })
            
            # Check if this is a similar question to existing FAQs - Priority 2
            faq_response = check_faq_match(user_message, user_language)
            if faq_response:
                # Create conversation record
                conversation = Conversation.objects.create(
                    user=user,
                    session_id=session_id,
                    user_message=user_message,
                    bot_response=faq_response,
                    detected_language=user_language,
                    confidence_score=0.95,
                    intent="faq_match",
                    is_fallback=False
                )
                
                return JsonResponse({
                    'response': faq_response,
                    'detected_language': user_language,
                    'conversation_id': conversation.id,
                    'confidence_score': 0.95,
                    'source': 'faq'
                })
            
            # Translate user message to English for Rasa processing (if needed) - Priority 3
            message_for_rasa = user_message
            if user_language != 'en':
                message_for_rasa = translator.translate_text(user_message, 'en')
                logger.info(f"Translated for Rasa: {message_for_rasa}")
            
            # Send to Rasa
            try:
                rasa_response = requests.post(
                    "http://localhost:5005/webhooks/rest/webhook",
                    json={"sender": session_id, "message": message_for_rasa},
                    timeout=10
                )
                
                if rasa_response.status_code == 200:
                    rasa_data = rasa_response.json()
                    
                    logger.info(f"Full Rasa response: {rasa_data}")
                    
                    if rasa_data and len(rasa_data) > 0:
                        # ============================================
                        # FIX: Combine all text responses from Rasa
                        # ============================================
                        bot_reply_parts = []
                        for response_item in rasa_data:
                            if 'text' in response_item:
                                bot_reply_parts.append(response_item['text'])
                        
                        # Join all parts with newlines
                        bot_reply = '\n\n'.join(bot_reply_parts) if bot_reply_parts else 'Sorry, I did not understand.'
                        
                        logger.info(f"Combined bot reply: {bot_reply}")
                        
                        # Extract Rasa metadata if available
                        confidence_score = None
                        intent = None
                        is_fallback = False
                        
                        # Try to extract intent and confidence if available in response
                        if isinstance(rasa_data[0], dict):
                            metadata = rasa_data[0].get('metadata', {})
                            confidence_score = metadata.get('confidence')
                            intent = metadata.get('intent')
                        
                        # Check if this looks like a fallback response
                        fallback_phrases = [
                            "sorry, i did not understand",
                            "i'm not sure i understand", 
                            "could you please rephrase",
                            "i didn't get that",
                            "i don't understand",
                            "can you rephrase"
                        ]
                        is_fallback = any(phrase in bot_reply.lower() for phrase in fallback_phrases)
                        
                        # Translate bot response to user's language
                        if user_language != 'en':
                            bot_reply = translator.translate_text(bot_reply, user_language)
                            logger.info(f"Translated response: {bot_reply}")
                        
                        # Create conversation record
                        conversation = Conversation.objects.create(
                            user=user,
                            session_id=session_id,
                            user_message=user_message,
                            bot_response=bot_reply,
                            detected_language=user_language,
                            confidence_score=confidence_score,
                            intent=intent,
                            is_fallback=is_fallback
                        )
                        
                        # If it's a fallback or low confidence, add to unanswered questions
                        if is_fallback or (confidence_score and confidence_score < 0.5):
                            handle_unanswered_question(
                                user_message, user_language, session_id,
                                confidence_score, intent, bot_reply
                            )
                        
                        return JsonResponse({
                            'response': bot_reply,
                            'detected_language': user_language,
                            'original_message': user_message,
                            'translated_input': message_for_rasa if user_language != 'en' else None,
                            'conversation_id': conversation.id,
                            'confidence_score': confidence_score,
                            'intent': intent,
                            'is_fallback': is_fallback
                        })
                    else:
                        # Empty response from Rasa - treat as unanswered
                        fallback_msg = get_fallback_message(user_language)
                        
                        conversation = Conversation.objects.create(
                            user=user,
                            session_id=session_id,
                            user_message=user_message,
                            bot_response=fallback_msg,
                            detected_language=user_language,
                            confidence_score=0.0,
                            intent="empty_response",
                            is_fallback=True
                        )
                        
                        handle_unanswered_question(
                            user_message, user_language, session_id,
                            0.0, "empty_response", fallback_msg
                        )
                        
                        return JsonResponse({
                            'response': fallback_msg,
                            'detected_language': user_language,
                            'conversation_id': conversation.id,
                            'confidence_score': 0.0,
                            'is_fallback': True
                        })
                else:
                    logger.error(f"Rasa server error: {rasa_response.status_code}")
                    raise requests.exceptions.RequestException(f"Rasa server error: {rasa_response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Rasa connection error: {e}")
                
                # Fallback response in user's language
                fallback_msg = get_connection_error_message(user_language)
                
                conversation = Conversation.objects.create(
                    user=user,
                    session_id=session_id,
                    user_message=user_message,
                    bot_response=fallback_msg,
                    detected_language=user_language,
                    confidence_score=0.0,
                    intent="connection_error",
                    is_fallback=True
                )
                
                return JsonResponse({
                    'response': fallback_msg,
                    'detected_language': user_language,
                    'conversation_id': conversation.id,
                    'error': 'rasa_connection_error',
                    'confidence_score': 0.0,
                    'is_fallback': True
                })
                
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON format'}, status=400)
        except Exception as e:
            logger.error(f"Multilingual chat error: {e}")
            return JsonResponse({
                'error': 'Internal server error',
                'response': 'Sorry, something went wrong. Please try again.'
            }, status=500)
    
    return JsonResponse({'error': 'Only POST method allowed'}, status=405)

@csrf_exempt
@require_http_methods(["POST"])
def submit_feedback(request):
    """
    Handle feedback submission from users
    """
    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST.dict()
        
        conversation_id = data.get('conversation_id')
        feedback_type = data.get('feedback_type')
        
        if not conversation_id:
            return JsonResponse({'error': 'Conversation ID is required'}, status=400)
        
        try:
            conversation = Conversation.objects.get(id=conversation_id)
        except Conversation.DoesNotExist:
            return JsonResponse({'error': 'Conversation not found'}, status=404)
        
        # Get or create feedback record
        feedback, created = ChatFeedback.objects.get_or_create(
            conversation=conversation,
            feedback_type=feedback_type,
            defaults={
                'user': request.user if request.user.is_authenticated else None,
                'session_id': conversation.session_id,
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'ip_address': get_client_ip(request)
            }
        )
        
        # Update feedback based on type
        if feedback_type == 'thumbs':
            feedback.is_helpful = data.get('is_helpful', True)
        elif feedback_type == 'stars':
            star_rating = data.get('star_rating')
            if star_rating and 1 <= int(star_rating) <= 5:
                feedback.star_rating = int(star_rating)
            else:
                return JsonResponse({'error': 'Invalid star rating'}, status=400)
        elif feedback_type == 'helpful':
            feedback.is_helpful = data.get('is_helpful', True)
        elif feedback_type == 'detailed':
            feedback.feedback_text = data.get('feedback_text', '')
            feedback.star_rating = data.get('star_rating')
            feedback.is_helpful = data.get('is_helpful')
        
        feedback.save()
        
        # If negative feedback and this was a fallback, increase priority of unanswered question
        if (feedback.is_helpful == False or (feedback.star_rating and feedback.star_rating <= 2)) and conversation.is_fallback:
            try:
                unanswered = UnansweredQuestion.objects.get(
                    user_message=conversation.user_message,
                    detected_language=conversation.detected_language
                )
                unanswered.frequency_count = F('frequency_count') + 1
                unanswered.save()
            except UnansweredQuestion.DoesNotExist:
                pass
        
        return JsonResponse({
            'success': True,
            'message': 'Feedback submitted successfully',
            'feedback_id': feedback.id
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON format'}, status=400)
    except Exception as e:
        logger.error(f"Feedback submission error: {e}")
        return JsonResponse({'error': 'Failed to submit feedback'}, status=500)

def check_faq_match(user_message, language):
    """
    Check if user message matches any existing FAQ
    """
    try:
        faqs = FAQ.objects.filter(language=language, is_active=True)
        
        # First try exact similarity matching
        for faq in faqs:
            similarity = SequenceMatcher(None, user_message.lower(), faq.question.lower()).ratio()
            if similarity > 0.7:
                # Increment usage count
                faq.usage_count = F('usage_count') + 1
                faq.save()
                return faq.answer
        
        # Then try keyword matching
        for faq in faqs:
            if faq.keywords:
                keywords = [k.strip().lower() for k in faq.keywords.split(',')]
                message_words = user_message.lower().split()
                if any(keyword in message_words for keyword in keywords):
                    faq.usage_count = F('usage_count') + 1
                    faq.save()
                    return faq.answer
        
        return None
    except Exception as e:
        logger.error(f"FAQ matching error: {e}")
        return None

def handle_unanswered_question(user_message, language, session_id, confidence_score, intent, bot_response):
    """
    Handle unanswered questions by storing or updating frequency
    """
    try:
        # Check if similar question already exists
        unanswered, created = UnansweredQuestion.objects.get_or_create(
            user_message=user_message,
            detected_language=language,
            defaults={
                'session_id': session_id,
                'confidence_score': confidence_score,
                'intent': intent,
                'bot_response': bot_response,
                'frequency_count': 1
            }
        )
        
        if not created:
            # Increase frequency count
            unanswered.frequency_count = F('frequency_count') + 1
            unanswered.confidence_score = confidence_score
            unanswered.bot_response = bot_response
            unanswered.save()
            
    except Exception as e:
        logger.error(f"Error handling unanswered question: {e}")

def get_fallback_message(language):
    """Get appropriate fallback message based on language"""
    messages = {
        'en': "I'm sorry, I couldn't understand that. Could you please rephrase your question?",
        'sn': "Pamusoroi, handina kunzwisisa izvozvo. Mungandipindure muimwe nzira here?"
    }
    return messages.get(language, messages['en'])

def get_connection_error_message(language):
    """Get appropriate connection error message based on language"""
    messages = {
        'en': "I'm sorry, I'm having trouble connecting right now. Please try again.",
        'sn': "Pamusoroi, ndiri kunetsa kubatana izvozvi. Edza zvakare."
    }
    return messages.get(language, messages['en'])

def get_client_ip(request):
    """Get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def fetch_notifications(request):
    now = timezone.now()

    # Scheduled notifications to send (polling)
    notifications_to_send = Notification.objects.filter(
        scheduled_time__lte=now,
        is_sent=False
    )
    notifications_to_send.update(is_sent=True)

    # All notifications for UI
    all_notifications = Notification.objects.all().order_by('-scheduled_time')

    # If user clicked the bell, mark all as read
    if request.GET.get('mark_read') == '1':
        all_notifications.update(is_read=True)

    # Build JSON response
    data = [
        {
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "is_read": n.is_read
        }
        for n in all_notifications
    ]
    return JsonResponse({"notifications": data})

def rasa_proxy(request):
    """
    Keep the original rasa_proxy for backward compatibility
    """
    if request.method == "POST":
        user_message = request.POST.get("message", "").strip()
        if not user_message:
            return JsonResponse({"error": "No message provided"}, status=400)

        try:
            rasa_response = requests.post(
                "http://localhost:5005/webhooks/rest/webhook",
                json={"sender": "user123", "message": user_message},
                timeout=5
            )
            data = rasa_response.json()
        except requests.exceptions.RequestException as e:
            return JsonResponse({"error": str(e)}, status=500)

        return JsonResponse(data, safe=False)

    return JsonResponse({"error": "POST request required"}, status=405)

# from django.shortcuts import render
# from django.http import JsonResponse
# from django.views.decorators.csrf import csrf_exempt
# import requests
# import json
# import logging
# from .translator import translator

# logger = logging.getLogger(__name__)

# def chatbot(request):
#     return render(request, "chat/index.html")

# @csrf_exempt
# def multilingual_chat(request):
#     """
#     Multilingual chat endpoint that handles language detection and translation
#     """
#     if request.method == "POST":
#         try:
#             # Handle both JSON and form data
#             if request.content_type == 'application/json':
#                 data = json.loads(request.body)
#                 user_message = data.get("message", "").strip()
#             else:
#                 user_message = request.POST.get("message", "").strip()
            
#             if not user_message:
#                 return JsonResponse({"error": "No message provided"}, status=400)
            
#             # Detect user's language
#             user_language = translator.detect_language(user_message)
#             logger.info(f"Detected language: {user_language} for message: {user_message}")
            
#             # Translate user message to English for Rasa processing (if needed)
#             message_for_rasa = user_message
#             if user_language != 'en':
#                 message_for_rasa = translator.translate_text(user_message, 'en')
#                 logger.info(f"Translated for Rasa: {message_for_rasa}")
            
#             # Send to Rasa
#             try:
#                 rasa_response = requests.post(
#                     "http://localhost:5005/webhooks/rest/webhook",
#                     json={"sender": "user123", "message": message_for_rasa},
#                     timeout=10
#                 )
                
#                 if rasa_response.status_code == 200:
#                     rasa_data = rasa_response.json()
                    
#                     if rasa_data and len(rasa_data) > 0:
#                         # Get bot response
#                         bot_reply = rasa_data[0].get('text', 'Sorry, I did not understand.')
                        
#                         # Translate bot response to user's language
#                         if user_language != 'en':
#                             bot_reply = translator.translate_text(bot_reply, user_language)
#                             logger.info(f"Translated response: {bot_reply}")
                        
#                         return JsonResponse({
#                             'response': bot_reply,
#                             'detected_language': user_language,
#                             'original_message': user_message,
#                             'translated_input': message_for_rasa if user_language != 'en' else None
#                         })
#                     else:
#                         # Empty response from Rasa
#                         fallback_msg = "I'm sorry, I couldn't understand that."
#                         if user_language != 'en':
#                             fallback_msg = translator.translate_text(fallback_msg, user_language)
                        
#                         return JsonResponse({
#                             'response': fallback_msg,
#                             'detected_language': user_language
#                         })
#                 else:
#                     logger.error(f"Rasa server error: {rasa_response.status_code}")
#                     raise requests.exceptions.RequestException(f"Rasa server error: {rasa_response.status_code}")
                    
#             except requests.exceptions.RequestException as e:
#                 logger.error(f"Rasa connection error: {e}")
                
#                 # Fallback response in user's language
#                 fallback_msg = "I'm sorry, I'm having trouble connecting right now. Please try again."
#                 if user_language != 'en':
#                     fallback_msg = translator.translate_text(fallback_msg, user_language)
                
#                 return JsonResponse({
#                     'response': fallback_msg,
#                     'detected_language': user_language,
#                     'error': 'rasa_connection_error'
#                 })
                
#         except json.JSONDecodeError:
#             return JsonResponse({'error': 'Invalid JSON format'}, status=400)
#         except Exception as e:
#             logger.error(f"Multilingual chat error: {e}")
#             return JsonResponse({
#                 'error': 'Internal server error',
#                 'response': 'Sorry, something went wrong. Please try again.'
#             }, status=500)
    
#     return JsonResponse({'error': 'Only POST method allowed'}, status=405)

# def rasa_proxy(request):
#     """
#     Keep the original rasa_proxy for backward compatibility
#     """
#     if request.method == "POST":
#         user_message = request.POST.get("message", "").strip()
#         if not user_message:
#             return JsonResponse({"error": "No message provided"}, status=400)

#         try:
#             rasa_response = requests.post(
#                 "http://localhost:5005/webhooks/rest/webhook",
#                 json={"sender": "user123", "message": user_message},
#                 timeout=5
#             )
#             data = rasa_response.json()
#         except requests.exceptions.RequestException as e:
#             return JsonResponse({"error": str(e)}, status=500)

#         return JsonResponse(data, safe=False)

#     return JsonResponse({"error": "POST request required"}, status=405)