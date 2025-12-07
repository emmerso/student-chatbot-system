from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
import requests
import os
from dotenv import load_dotenv
from googletrans import Translator
import json
from typing import Any, Text, Dict, List


# Load environment variables - FIXED PATH
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)

# Enhanced debug prints
print(f"Loading .env from: {env_path}")
print(f"File exists: {os.path.exists(env_path)}")
serpapi_key = os.getenv('SERPAPI_KEY')
print(f"SERPAPI_KEY loaded: {bool(serpapi_key)}")
if serpapi_key:
    print(f"SERPAPI_KEY (masked): {serpapi_key[:8]}...{serpapi_key[-4:]}")

# -------------------------
# TRANSLATOR
# -------------------------
translator = Translator()

class ActionMultilingual(Action):
    def name(self):
        return "action_multilingual"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: dict):

        user_msg = tracker.latest_message.get('text')

        try:
            detected_lang = translator.detect(user_msg).lang
            translated_to_en = translator.translate(user_msg, dest='en').text

            bot_reply = f"You said (in English): {translated_to_en}"
            final_reply = translator.translate(bot_reply, dest=detected_lang).text

            dispatcher.utter_message(text=final_reply)
        except Exception as e:
            print(f"Translation error: {e}")
            dispatcher.utter_message(text=user_msg)

        return []


# -------------------------
# MAIN HYBRID ACTION
# -------------------------
class ActionAnswerWUAQuestion(Action):
    def name(self):
        return "action_answer_wua_question"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: dict):

        query = tracker.latest_message.get("text")
        intent = tracker.latest_message.get("intent", {}).get("name", "")

        # --- trained responses dictionary ---
        trained_responses = {
            "ask_about_wua": (
                "**About Women's University in Africa (WUA)**\n\n"
                "WUA is Zimbabwe's first private university dedicated to women's empowerment through education.\n"
                "Founded in 2002, it has graduated thousands of women leaders across sectors."
            ),
            "ask_admission": (
                "**Admission Requirements**\n\n"
                "- 5 O'Levels including English\n"
                "- 2 A'Levels or equivalent\n"
                "- Mature entry for candidates 25+ years\n\n"
                "Contact admissions@wua.ac.zw for details."
            ),
            "ask_fees_payment": (
                "**Fees & Payment**\n\n"
                "- Semester or yearly payments\n"
                "- Scholarships & bursaries available\n\n"
                "Email: finance@wua.ac.zw"
            ),
            "ask_contact_info": (
                "**Contact WUA**\n\n"
                "Phone: +263-4-369-739\n"
                "Email: info@wua.ac.zw\n"
                "Website: www.wua.ac.zw"
            ),
            "ask_faculties": (
                "**Faculties at WUA**\n\n"
                "- Management & Entrepreneurship Sciences\n"
                "- Social & Gender Transformative Sciences\n"
                "- Agriculture & Environmental Sciences\n"
                "- Health Sciences\n"
                "- Science & Technology"
            ),
        }

        # Step 1: trained response
        if intent in trained_responses:
            dispatcher.utter_message(text=trained_responses[intent])
            return []

        # Step 2: fallback to SerpAPI
        serpapi_key = os.getenv("SERPAPI_KEY")
        
        print(f"\n=== SerpAPI Debug Info ===")
        print(f"Query: {query}")
        print(f"Intent: {intent}")
        print(f"API Key present: {bool(serpapi_key)}")
        
        if not serpapi_key:
            print("ERROR: SERPAPI_KEY not found in environment")
            dispatcher.utter_message(
                text="I couldn't find that in my knowledge base, and search is unavailable right now."
            )
            return []

        params = {
            "engine": "google",
            "q": f"site:wua.ac.zw {query}",
            "api_key": serpapi_key,
            "num": 3
        }

        print(f"Search query: {params['q']}")

        try:
            response = requests.get("https://serpapi.com/search", params=params, timeout=10)
            
            print(f"SerpAPI Status Code: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            
            # Check if request was successful
            if response.status_code != 200:
                print(f"ERROR: Non-200 status code")
                print(f"Response text: {response.text}")
                dispatcher.utter_message(
                    text="I had trouble searching. Please try again or contact info@wua.ac.zw"
                )
                return []
            
            # Parse JSON
            try:
                data = response.json()
                print(f"JSON parsed successfully")
                print(f"Response keys: {data.keys()}")
            except json.JSONDecodeError as je:
                print(f"JSON Decode Error: {je}")
                print(f"Raw response: {response.text[:500]}")
                dispatcher.utter_message(text="Sorry, I received an invalid response. Please try again.")
                return []

            # Check for errors in response
            if "error" in data:
                print(f"API Error: {data['error']}")
                dispatcher.utter_message(text="Sorry, there was an issue with the search service.")
                return []

            # Process results
            if "organic_results" in data and len(data["organic_results"]) > 0:
                results = data["organic_results"][:2]
                print(f"Found {len(results)} results")
                
                # Build complete message
                message_parts = ["Here's what I found on the WUA website:\n"]
                
                for idx, res in enumerate(results, 1):
                    title = res.get('title', 'No title')
                    snippet = res.get('snippet', 'No description available')
                    link = res.get('link', '')
                    
                    message_parts.append(f"\n{idx}. {title}")
                    message_parts.append(f"{snippet}")
                    message_parts.append(f"Link: {link}\n")
                
                message = "\n".join(message_parts)
                print(f"Complete message length: {len(message)}")
                print(f"Complete message:\n{message}")
                dispatcher.utter_message(text=message)
            else:
                print("No organic results found")
                print(f"Full response data: {json.dumps(data, indent=2)[:500]}")
                dispatcher.utter_message(
                    text="I couldn't find anything specific on the WUA site. Could you rephrase or ask about admissions, fees, or courses?"
                )

        except requests.exceptions.Timeout:
            print("ERROR: Request timeout")
            dispatcher.utter_message(text="The search request timed out. Please try again.")
        except requests.exceptions.RequestException as e:
            print(f"Request error: {type(e).__name__}: {e}")
            dispatcher.utter_message(text="Sorry, I had trouble connecting to the search service.")
        except Exception as e:
            print(f"Unexpected error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            dispatcher.utter_message(text="Sorry, I had trouble looking that up. Please try again later.")

        return []


# -------------------------
# CONTACT INFO
# -------------------------
class ActionProvideContactInfo(Action):
    def name(self):
        return "action_provide_contact_info"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: dict):

        department = tracker.get_slot("department")
        if department and department.lower() == "admissions":
            dispatcher.utter_message(text="Admissions Office: admissions@wua.ac.zw")
        else:
            dispatcher.utter_message(text="Main Office: info@wua.ac.zw | +263-4-369-739")
        return []
    
 
# Mock Student Database
STUDENT_DATABASE = {
    "alice johnson": {
        "student_id": "WUA001",
        "gpa": 3.85,
        "assignments": [
            {"name": "Python Project", "score": 92, "due_date": "2025-10-20"},
            {"name": "Database Design", "score": 88, "due_date": "2025-10-25"},
        ],
        "courses": ["Data Science 101", "Web Development", "Database Systems"],
        "grades": {"DS101": "A", "WD201": "B+", "DBS301": "A-"}
    },
    "jane doe": {
        "student_id": "WUA002",
        "gpa": 3.92,
        "assignments": [
            {"name": "Business Plan", "score": 95, "due_date": "2025-10-22"},
            {"name": "Financial Analysis", "score": 90, "due_date": "2025-10-28"},
        ],
        "courses": ["Business Management", "Entrepreneurship", "Finance"],
        "grades": {"BM101": "A", "ENT201": "A", "FIN301": "A-"}
    },
}

class ActionGetStudentInfo(Action):
    def name(self):
        return "action_get_student_info"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: dict):

        # Get student name from slot
        student_name = tracker.get_slot("student_name")
        query = tracker.latest_message.get("text", "").lower()

        if not student_name:
            dispatcher.utter_message(
                text="To access your records, please provide your full name for authentication."
            )
            return []

        # Normalize name for lookup
        name_key = student_name.lower().strip()

        # Check if student exists
        if name_key not in STUDENT_DATABASE:
            dispatcher.utter_message(
                text=f"Sorry, no student record found for '{student_name}'. Please check the name and try again."
            )
            return []

        # Get student data
        student = STUDENT_DATABASE[name_key]

        # Route to specific info based on query
        if "gpa" in query or "grade" in query:
            dispatcher.utter_message(
                text=f"**{student_name.title()} - GPA & Grades**\n\n"
                     f"Overall GPA: {student['gpa']}\n\n"
                     f"Course Grades:\n"
                     + "\n".join([f"- {course}: {grade}" for course, grade in student['grades'].items()])
            )
        elif "assignment" in query:
            assignments_text = "\n".join([
                f"- {a['name']}: {a['score']}/100 (Due: {a['due_date']})"
                for a in student['assignments']
            ])
            dispatcher.utter_message(
                text=f"**{student_name.title()} - Assignments**\n\n{assignments_text}"
            )
        elif "course" in query:
            courses_text = "\n".join([f"- {course}" for course in student['courses']])
            dispatcher.utter_message(
                text=f"**{student_name.title()} - Enrolled Courses**\n\n{courses_text}"
            )
        else:
            # Default: show full summary
            dispatcher.utter_message(
                text=f"**{student_name.title()} - Academic Summary**\n\n"
                     f"Student ID: {student['student_id']}\n"
                     f"GPA: {student['gpa']}\n"
                     f"Courses: {len(student['courses'])}\n\n"
                     f"Ask me about: GPA, assignments, or courses for more details."
            )

        return []    
    