import pandas as pd
import numpy as np
import random
from langdetect import detect, DetectorFactory, LangDetectException # Correctly import LangDetectException
from collections import defaultdict
import re
import os 

# Ensure reproducibility for langdetect (important for consistent synthetic data generation)
# Note: For real-world use, you might remove this line to allow for more natural randomness
DetectorFactory.seed = 0 

# --- Configuration for AI Module ---
# Risk values for intents
RISK_SCORES = {
    'violence': 0.90,
    'break_in': 0.95,
    'harassment': 0.75,
    'suspicious_activity': 0.60,
    'medical_emergency': 0.95,
    'information_request': 0.20
}

# Shadow speech keywords/phrases (simplified for hackathon)
SHADOW_SPEECH_KEYWORDS = [
    "I don't feel safe", "Someone is outside", "He's here", "Something is wrong",
    "Please come quickly", "I can't really explain", "It's complicated",
    "Something happened", "It feels weird", "I'm worried", "I need help but I can't say",
    "मुझे ठीक नहीं लग रहा है" # Hindi for "I don't feel well/safe"
]

# Emotion/Distress keywords
EMOTION_KEYWORDS = {
    'panic': ['help', 'oh my god', 'fast', 'now', 'quickly', 'jaldi', 'madad'],
    'fear': ['scared', 'afraid', 'terrified', 'bhaya', 'darr'],
    'uncertainty': ['not sure', 'confused', 'don\'t know', 'kya ho gaya'],
    'hesitation': ['um', 'uh', 'actually', 'well'],
    'vague': ['something', 'it', 'weird', 'problem', 'complicated']
}

# Dialect-specific keywords (simplified for demonstration)
# In a real scenario, this would be much more extensive and use embeddings.
KANNADA_DIALECT_KEYWORDS = {
    'Mysuru/Bengaluru': ['ಅಯ್ಯೋ', 'ಏನು ನಡೀತಾ ಇದೆ'], # Ayyo, enu naditaa ide - Oh no, what's happening?
    'Dharwad/North Karnataka': ['ಹಂಗ ಅಂದ್ರೆ', 'ಏನಪ್ಪಾ'], # Hanga andre - What do you mean?, Enappa - What is it?
    'Mangaluru/Coastal': ['ಏನ್ ಮಾಡೋದು', 'ಮೂರ್ತಿ'], # En maadodu - What to do?, Murti (common name but used for illustrative purpose)
    'Rural Mysore': ['ನನಗೆ ಭಯ ಆಗ್ತಿದೆ'], # Nanage bhaya agtide - I'm scared
    # Add more as needed for other dialects
}

# --- Deliverable 1: Synthetic Dataset Generation (Code) ---
def generate_synthetic_data(num_rows=200):
    intents = list(RISK_SCORES.keys())
    languages = ['English', 'Kannada', 'Hindi', 'Hinglish', 'Code-Switched'] 
    kannada_dialects = list(KANNADA_DIALECT_KEYWORDS.keys()) + ['Standard Kannada'] # Add standard for variation

    data = []
    for _ in range(num_rows):
        # Base transcript elements
        base_phrases = [
            "What is the helpline number?", "How does this service work?", "Can I get some information?",
            "I have a general question.", "I saw a thief!", "My house is broken into!",
            "Someone is trying to hurt me!", "I'm being attacked!", "He's hitting me!",
            "There's a fire!", "I'm bleeding heavily!", "I need an ambulance now!",
            "It's not good here.", "There's a problem.", "He's here.", "Someone is outside."
        ]
        
        # Shadow speech/distress modifiers
        shadow_phrases = [
            "", random.choice(SHADOW_SPEECH_KEYWORDS),
            "Um...", "Actually...", "I'm not sure...", "I can't really explain.",
            "Oh my god!", "Help!", "Please help me, jaldi!", "I'm so scared!"
        ]
        
        # Code-switched elements (using placeholders for Hindi/Kannada)
        kannada_placeholders = {
            "I'm worried": "ಭಯ ಆಗ್ತಿದೆ ನನಗೆ", # bhaya agtide nanage
            "What is happening": "ಏನು ನಡೀತಾ ಇದೆ" # enu naditaa ide
        }
        hindi_placeholders = {
            "I need help": "मदद चाहिए", # madad chahiye
            "Who is here": "कौन है", # kaun hai
            "What happened": "क्या हो गया" # kya ho gaya
        }

        # Select primary language and dialect for generation purposes
        detected_language = random.choice(languages)
        
        # Determine detected_dialect for synthetic data to match language choices
        if detected_language == 'Kannada':
            detected_dialect = random.choice(kannada_dialects)
        elif detected_language == 'Hindi':
            detected_dialect = 'Standard Hindi'
        elif detected_language == 'English':
            detected_dialect = 'Standard English'
        elif detected_language == 'Hinglish':
            detected_dialect = 'Hinglish'
        else: # Code-Switched
            if random.random() < 0.5:
                detected_dialect = 'Kannada-English'
            else:
                detected_dialect = 'Hindi-English'
            
        
        transcript_parts = [random.choice(base_phrases)]
        
        if random.random() < 0.6: # Add shadow/distress elements
            shadow_mod = random.choice(shadow_phrases)
            if shadow_mod: # Ensure the chosen modifier isn't an empty string
                transcript_parts.append(shadow_mod)
        
        if detected_language == 'Code-Switched':
            if 'Kannada' in detected_dialect:
                k_phrase_key = random.choice(list(kannada_placeholders.keys()))
                transcript_parts.append(f"{k_phrase_key}, [Kannada: {kannada_placeholders[k_phrase_key]}]")
            else: # Hindi-English
                h_phrase_key = random.choice(list(hindi_placeholders.keys()))
                transcript_parts.append(f"{h_phrase_key}, [Hindi: {hindi_placeholders[h_phrase_key]}]")
        elif detected_language == 'Hinglish':
            if random.random() < 0.5:
                h_phrase_key = random.choice(list(hindi_placeholders.keys()))
                # Simplified Hinglish construction
                transcript_parts.append(f"{h_phrase_key.split(' ')[0]} {hindi_placeholders[h_phrase_key]}, I don't know.") 
            else:
                transcript_parts.append("Kya ho gaya, I don't know.")

        transcript = ". ".join(filter(None, transcript_parts)).strip()
        transcript = re.sub(r'\s{2,}', ' ', transcript) # Clean up extra spaces

        # Simulate other AI outputs
        intent = random.choice(intents)
        confidence = round(random.uniform(0.4, 0.99), 2)
        urgency = round(random.uniform(0.1, 0.99), 2)
        
        # Determine shadow speech presence
        shadow_speech = any(keyword.lower() in transcript.lower() for keyword in SHADOW_SPEECH_KEYWORDS) or \
                        (random.random() < 0.2 and intent != 'information_request' and confidence < 0.7) # Simulate implicit
        
        # Determine emotion (simplified)
        emotion = 'calm'
        if urgency > 0.8 or any(k in transcript.lower() for k in EMOTION_KEYWORDS['panic']):
            emotion = 'panic'
        elif shadow_speech or any(k in transcript.lower() for k in EMOTION_KEYWORDS['fear']):
            emotion = 'fear'
        elif confidence < 0.6 or any(k in transcript.lower() for k in EMOTION_KEYWORDS['uncertainty']):
            emotion = 'uncertainty'
        elif any(k in transcript.lower() for k in EMOTION_KEYWORDS['hesitation']):
            emotion = 'hesitation'
        elif any(k in transcript.lower() for k in EMOTION_KEYWORDS['vague']):
            emotion = 'vague'

        risk = RISK_SCORES[intent]
        score = round((1 - confidence) * risk, 4)

        emergency_percentage = int(np.interp(urgency * risk, [0, 0.95], [10, 100]))
        if shadow_speech and emergency_percentage < 40:
            emergency_percentage += random.randint(10, 20) # Boost for shadow speech
            emergency_percentage = min(emergency_percentage, 100)

        # Decision logic
        decision = "PROCEED"
        if urgency > 0.8:
            decision = "ESCALATE"
        elif score > 0.5:
            decision = "ESCALATE"
        elif score > 0.25:
            decision = "CONFIRM"
        
        reasoning = "Synthetic data based reasoning"

        data.append({
            "transcript": transcript,
            "detected_language": detected_language,
            "detected_dialect": detected_dialect,
            "intent": intent,
            "confidence": confidence,
            "urgency": urgency,
            "risk": risk,
            "score": score,
            "emergency_percentage": emergency_percentage,
            "shadow_speech_flag": shadow_speech,
            "emotion": emotion,
            "expected_decision": decision,
            "reasoning": reasoning
        })
    
    df = pd.DataFrame(data)
    return df

# --- Deliverable 2: Modular Python Code (AI Module) ---

class SpashtAIAgent:
    def __init__(self):
        self.candidate_labels = [
            "harassment", "violence", "suspicious_activity",
            "break_in", "medical_emergency", "information_request"
        ]
        self.risk_scores = RISK_SCORES
        self.shadow_speech_keywords = SHADOW_SPEECH_KEYWORDS
        self.emotion_keywords = EMOTION_KEYWORDS
        self.kannada_dialect_keywords = KANNADA_DIALECT_KEYWORDS

    def _detect_language(self, text):
        """
        Detects language using langdetect with improved robustness and fallback
        for code-switching and short texts.
        """
        if not text.strip(): # Handle empty strings
            return 'Unknown'
        
        text_lower = text.lower()
        
        try:
            lang = detect(text)
            
            # --- Heuristics for Code-Switching/Hinglish detection ---
            # These are based on common Indic words/phrases used in English context
            common_indic_words = ['jaldi', 'kya ho gaya', 'madad', 'sir', 'madam', 'bhai', 'behen', 'aur', 'kya', 'nahi', 'toh', 'acha', 'bas', 'tension', 'ok', 'haan', 'acha']
            
            if lang == 'en':
                if any(kw in text_lower for kw in common_indic_words):
                    return 'Hinglish' 
                return 'English'
            elif lang == 'kn':
                # Check for English words within Kannada context
                if any(kw in text_lower for kw in ['help', 'sir', 'madam', 'oh my god', 'problem', 'worried', 'please', 'why', 'what', 'how', 'tension', 'ok']):
                    return 'Code-Switched' 
                return 'Kannada'
            elif lang == 'hi':
                # Check for English words within Hindi context
                if any(kw in text_lower for kw in ['help', 'sir', 'madam', 'oh my god', 'problem', 'worried', 'please', 'why', 'what', 'how', 'tension', 'ok']):
                    return 'Code-Switched' 
                return 'Hindi'
            else:
                return lang # Return langdetect's prediction for other languages
                
        except LangDetectException:
            # Fallback logic if langdetect fails (e.g., very short text, ambiguous)
            # Prioritize common code-switching indicators
            if any(kw in text_lower for kw in common_indic_words):
                return 'Hinglish' # Best guess for Hinglish-like if langdetect failed
            
            # Then common Indic words for Kannada/Hindi
            if any(kw in text_lower for kw in ['ಏನು', 'ನನಗೆ', 'ಭಯ', 'ನಡೀತಾ', 'ಹೇಗೆ']): # Common Kannada words
                return 'Kannada'
            if any(kw in text_lower for kw in ['क्या', 'मदद', 'है', 'नहीं', 'करो', 'मुझे']): # Common Hindi words
                return 'Hindi'
            
            # Generic English fallback (most common expected language in emergency calls)
            if any(kw in text_lower for kw in ['help', 'please', 'emergency', 'worry', 'problem', 'fire', 'attack', 'safe']):
                return 'English' 
            return 'Unknown' # Ultimate fallback if nothing specific is found

    def _detect_dialect(self, text, detected_language):
        """Simulates dialect detection for Kannada or assigns standard for others."""
        if detected_language == 'Kannada':
            for dialect, keywords in self.kannada_dialect_keywords.items():
                if any(kw.lower() in text.lower() for kw in keywords):
                    return dialect
            return 'Standard Kannada' # Fallback if no specific dialect keywords found
        elif detected_language == 'Hinglish':
            return 'Hinglish'
        elif 'English' in detected_language: # Catches English and Code-Switched (English dominant)
            return 'Standard English'
        elif 'Hindi' in detected_language: # Catches Hindi and Code-Switched (Hindi dominant)
            return 'Standard Hindi'
        return 'Unknown' # Default for other languages or true Code-Switched (no specific dialect logic)

    def _extract_intent(self, text):
        """
        Simulates intent extraction using zero-shot classification principles.
        For hackathon, prioritizes keyword matching.
        """
        text_lower = text.lower()
        
        # Prioritized keyword matching for specific intents (including Indic examples)
        # Added more Indic keywords for better coverage
        if 'violence' in text_lower or 'attack' in text_lower or 'hit' in text_lower or 'hurt me' in text_lower or 'मार' in text_lower or 'ಹೊಡೆ' in text_lower or 'ಹಲ್ಲೆ' in text_lower or 'ದಾಳಿ' in text_lower or 'ಹಾನಿ' in text_lower:
            return 'violence', random.uniform(0.8, 0.95)
        if 'break in' in text_lower or 'broken into' in text_lower or 'thief' in text_lower or 'ಚೋರ' in text_lower or 'ಕಳ್ಳ' in text_lower or 'ಕಳ್ಳತನ' in text_lower or 'ಒಳಗೆ' in text_lower:
            return 'break_in', random.uniform(0.8, 0.95)
        if 'harass' in text_lower or 'threat' in text_lower or 'uncomfortable' in text_lower or 'ತೊಂದರೆ' in text_lower or 'ಪೀಡಿಸು' in text_lower or 'ಕಿರುಕುಳ' in text_lower or 'ಧಮಕಿ' in text_lower or 'ಬೆದರಿಕೆ' in text_lower:
            return 'harassment', random.uniform(0.7, 0.9)
        if 'suspicious' in text_lower or 'outside' in text_lower or 'not safe' in text_lower or 'wrong' in text_lower or 'ವಿಚಿತ್ರ' in text_lower or 'ಸಮಸ್ಯೆ' in text_lower or 'ಅಪಾಯ' in text_lower or 'ಸಂದೇಹ' in text_lower:
            return 'suspicious_activity', random.uniform(0.6, 0.85)
        if 'ambulance' in text_lower or 'bleeding' in text_lower or 'medical' in text_lower or 'emergency' in text_lower or 'ರಕ್ತ' in text_lower or 'ಆಸ್ಪತ್ರೆ' in text_lower or 'ಪ್ರಥಮ ಚಿಕಿತ್ಸೆ' in text_lower or 'ಜೀವರಕ್ಷಕ' in text_lower or 'ಸ್ವಾಸ್ಥ್ಯ' in text_lower:
            return 'medical_emergency', random.uniform(0.85, 0.98)
        if 'information' in text_lower or 'question' in text_lower or 'how does it work' in text_lower or 'ಪ್ರಶ್ನೆ' in text_lower or 'ಮಾಹಿತಿ' in text_lower or 'ಹೇಗೆ' in text_lower or 'ವಿವರ' in text_lower:
            return 'information_request', random.uniform(0.5, 0.7)
        
        # Fallback to simple heuristic if no strong keywords matched
        if len(text.split()) > 5:
            return 'information_request', random.uniform(0.4, 0.6) # Default to info if unclear but longer
        return 'information_request', random.uniform(0.3, 0.5) # Even lower confidence for very short unclear texts

    def _detect_shadow_speech(self, text):
        """Detects implicit danger using keywords."""
        text_lower = text.lower()
        for keyword in self.shadow_speech_keywords:
            if keyword.lower() in text_lower:
                return True
        return False

    def _detect_emotion_and_urgency(self, text):
        """
        Detects emotion and estimates urgency.
        In a real setting, this would involve acoustic features (librosa, SpeechBrain)
        and more sophisticated NLP.
        """
        text_lower = text.lower()
        urgency_score = 0.0
        detected_emotion = 'calm'
        
        # Keyword-based urgency and emotion
        for emotion, keywords in self.emotion_keywords.items():
            for kw in keywords:
                if kw in text_lower:
                    if emotion == 'panic':
                        urgency_score = max(urgency_score, random.uniform(0.8, 0.99))
                        detected_emotion = 'panic'
                    elif emotion == 'fear' and urgency_score < 0.8:
                        urgency_score = max(urgency_score, random.uniform(0.6, 0.85))
                        if detected_emotion != 'panic': detected_emotion = 'fear'
                    elif emotion == 'hesitation' and urgency_score < 0.6:
                        urgency_score = max(urgency_score, random.uniform(0.4, 0.6))
                        if detected_emotion == 'calm': detected_emotion = 'hesitation'
                    elif emotion == 'uncertainty' and urgency_score < 0.7:
                        urgency_score = max(urgency_score, random.uniform(0.5, 0.7))
                        if detected_emotion == 'calm' or detected_emotion == 'hesitation': detected_emotion = 'uncertainty'
                    elif emotion == 'vague' and urgency_score < 0.7:
                        urgency_score = max(urgency_score, random.uniform(0.45, 0.75))
                        if detected_emotion == 'calm' or detected_emotion == 'hesitation' or detected_emotion == 'uncertainty': detected_emotion = 'vague'
        
        # If no strong keywords, base on length or general sentiment (mock)
        if urgency_score == 0.0:
            if len(text.split()) < 5:
                urgency_score = random.uniform(0.1, 0.3)
            else:
                urgency_score = random.uniform(0.2, 0.5)
        
        return round(urgency_score, 2), detected_emotion

    def process_call(self, transcript):
        """
        Main inference pipeline for a single call transcript segment.
        This function takes a transcript segment and performs a full analysis.
        For simulating a conversation, you'll call this function for each conversational turn.
        """
        # 1. Preprocessing (minimal for hackathon)
        processed_transcript = transcript.strip()

        # 2. Language Detection
        detected_language = self._detect_language(processed_transcript)

        # 3. Dialect Detection (simplified)
        detected_dialect = self._detect_dialect(processed_transcript, detected_language)

        # 4. Intent Extraction
        intent, intent_confidence = self._extract_intent(processed_transcript)

        # 5. Shadow Speech Detection
        shadow_speech = self._detect_shadow_speech(processed_transcript)

        # 6. Emotion & Urgency Detection
        urgency, emotion = self._detect_emotion_and_urgency(processed_transcript)

        # 7. Confidence (overall, combines intent and urgency)
        # This is a simplified heuristic for hackathon
        # Lower urgency should ideally lead to higher confidence in 'normal' interpretation
        overall_confidence = (intent_confidence + (1 - urgency)) / 2 
        overall_confidence = round(max(0.01, min(0.99, overall_confidence)), 2)


        # 8. Emergency Severity Percentage
        risk = self.risk_scores.get(intent, 0.2) # Default to low risk if intent is unknown
        
        # Calculate a base severity from risk and urgency - THIS IS THE CRITICAL LINE
        base_severity = (risk * 0.7 + urgency * 0.3) * 100 
        
        # Adjust for shadow speech and low confidence
        if shadow_speech and base_severity < 70:
            base_severity += random.randint(10, 25) # Boost for hidden danger
        if overall_confidence < 0.6 and base_severity < 80:
            base_severity += random.randint(5, 15) # Boost for uncertainty
            
        emergency_percentage = int(max(10, min(100, base_severity))) # Ensure bounds

        # 9. Risk × Confidence Reasoning
        # 'risk' variable is already correctly retrieved above
        score = round((1 - overall_confidence) * risk, 4)

        # 10. Decision Logic
        decision = "PROCEED"
        reasoning = []

        if urgency > 0.8:
            decision = "ESCALATE"
            reasoning.append("High urgency detected.")
        elif score > 0.5:
            decision = "ESCALATE"
            reasoning.append(f"Risk-Confidence score ({score:.2f}) indicates high severity.")
        elif score > 0.25:
            decision = "CONFIRM"
            reasoning.append(f"Risk-Confidence score ({score:.2f}) suggests confirmation needed.")
        else:
            reasoning.append("Low immediate risk detected.")
        
        if shadow_speech:
            reasoning.append("Implicit danger (shadow speech) detected.")
        if overall_confidence < 0.5:
            reasoning.append("Low confidence in interpretation.")
        if detected_language == 'Code-Switched':
            reasoning.append("Code-switched language detected, potential for nuance.")
        
        final_reasoning = ". ".join(reasoning) + "." if reasoning else "Analysis complete."

        output = {
            "transcript": transcript,
            "detected_language": detected_language,
            "detected_dialect": detected_dialect,
            "intent": intent,
            "confidence": overall_confidence,
            "urgency": urgency,
            "risk": risk, # Include the calculated risk score for clarity
            "score": score,
            "emergency_percentage": emergency_percentage,
            "shadow_speech": shadow_speech,
            "emotion": emotion,
            "decision": decision,
            "reasoning": final_reasoning
        }
        return output


# --- Sample Test Cases and Execution (Conversational Simulation) ---
if __name__ == "__main__":
    # Generate the synthetic dataset
    print("Generating synthetic dataset...")
    synthetic_df = generate_synthetic_data(num_rows=100) # Reduced for quick output
    print("Synthetic Dataset (first 5 rows):")
    print(synthetic_df.head())

    # Initialize the AI Agent
    ai_agent = SpashtAIAgent()

    print("\n--- Emergency Call Simulation (SPASHT AI Module) ---")
    print("Enter transcript segments from the caller. Type 'exit' to end the call.")
    print("----------------------------------------------------\n")

    call_transcript_history = [] # To keep a log of the conversation

    while True:
        caller_input = input("Caller says: ")

        # Exit condition
        if caller_input.lower() == "exit":
            print("\n--- Call Ended ---")
            print("Full Call History:")
            for i, segment in enumerate(call_transcript_history):
                print(f"[{i+1}] {segment}")
            break

        if not caller_input.strip():
            print("Agent: Please say something.")
            continue

        call_transcript_history.append(caller_input)

        # Process the current transcript segment
        result = ai_agent.process_call(caller_input)

        print("\n--- AI Module Analysis ---")
        for key, value in result.items():
            # Format output for better readability
            if isinstance(value, float):
                print(f"{key}: {value:.2f}")
            else:
                print(f"{key}: {value}")
        print("----------------------------------------------------\n")

