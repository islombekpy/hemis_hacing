import json
import os
import re
import openai
from typing import List, Dict, Any, Optional
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
import logging
from dotenv import load_dotenv
# Logging sozlamalari
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("ai_question_service.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
openai.api_key = OPENAI_API_KEY

class SmartAIQuestionSolver:
    def __init__(self):
        self.success_rate = 0
        self.total_questions = 0
        
    def analyze_and_solve_question(self, question: str, answer_options: List[Dict[str, Any]]) -> Dict[str, Any]:
        """AI yordamida savolni tahlil qilib, to'g'ri javobni topish"""
        try:
            # Javob variantlarini formatlash
            options_formatted = []
            for opt in answer_options:
                options_formatted.append(f"Variant {opt['position']}: {opt['text']}")
            
            options_text = "\n".join(options_formatted)
            
            # AI uchun maxsus prompt tayyorlash
            system_prompt = """Siz professional test yechuvchi AI assistantsiz. Sizning vazifangiz:
1. Savolni diqqat bilan o'qing va tahlil qiling
2. Har bir javob variantini baholang
3. Eng to'g'ri javobni tanlang
4. Faqat javob raqamini (1, 2, 3, 4, 5) qaytaring
5. Hech qanday qo'shimcha matn yozmang, faqat raqam

Agar savol matematik bo'lsa - hisoblang
Agar savol mantiqiy bo'lsa - tahlil qiling  
Agar savol bilim asosida bo'lsa - eng to'g'ri variantni tanlang"""

            user_prompt = f"""Quyidagi savolga eng to'g'ri javobni tanlang:

SAVOL: {question}

JAVOB VARIANTLARI:
{options_text}

TO'G'RI JAVOB RAQAMI:"""

            # AI ga so'rov yuborish
            response = openai.ChatCompletion.create(
                model="gpt-4",  # Eng kuchli model
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=5,
                temperature=0,  # Eng aniq javob uchun
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0
            )
            
            ai_answer = response.choices[0].message.content.strip()
            
            # Javobni tozalash va tekshirish
            cleaned_answer = re.findall(r'\d+', ai_answer)
            if cleaned_answer:
                answer_number = cleaned_answer[0]
                
                # Javob raqami mavjudligini tekshirish
                valid_positions = [opt['position'] for opt in answer_options]
                if answer_number in valid_positions:
                    logger.info(f"AI SUCCESS: Question solved, answer: {answer_number}")
                    self.success_rate += 1
                    return {
                        "success": True,
                        "answer": answer_number,
                        "confidence": "high",
                        "source": "AI-GPT4"
                    }
            
            logger.warning(f"AI gave invalid answer: {ai_answer}")
            return {"success": False, "error": "Invalid AI response"}
            
        except Exception as e:
            logger.error(f"AI request failed: {str(e)}")
            return {"success": False, "error": str(e)}
        
        finally:
            self.total_questions += 1

    def get_backup_answer(self, question: str, answer_options: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Backup AI yordamida savolni yechish (GPT-3.5)"""
        try:
            options_text = "\n".join([f"{opt['position']}: {opt['text']}" for opt in answer_options])
            
            prompt = f"""Savol: {question}

Variantlar:
{options_text}

Eng to'g'ri javob raqami (faqat raqam):"""

            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Siz test savollarini yechadigan AI assistantsiz. Faqat javob raqamini qaytaring."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=3,
                temperature=0.1
            )
            
            backup_answer = response.choices[0].message.content.strip()
            cleaned_answer = re.findall(r'\d+', backup_answer)
            
            if cleaned_answer:
                answer_number = cleaned_answer[0]
                valid_positions = [opt['position'] for opt in answer_options]
                if answer_number in valid_positions:
                    return {
                        "success": True,
                        "answer": answer_number,
                        "confidence": "medium",
                        "source": "AI-GPT3.5"
                    }
            
            return {"success": False, "error": "Backup AI failed"}
            
        except Exception as e:
            logger.error(f"Backup AI failed: {str(e)}")
            return {"success": False, "error": f"Backup failed: {str(e)}"}

    def smart_guess(self, question: str, answer_options: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aqlli taxmin (oxirgi imkoniyat)"""
        try:
            # Eng uzun javobni tanlash (ko'pincha to'g'ri bo'ladi)
            longest_option = max(answer_options, key=lambda x: len(x['text']))
            
            # Agar matematik savol bo'lsa, raqamli javobni tanlash
            if any(char.isdigit() for char in question):
                for opt in answer_options:
                    if any(char.isdigit() for char in opt['text']):
                        return {
                            "success": True,
                            "answer": opt['position'],
                            "confidence": "low",
                            "source": "Smart-Guess-Math"
                        }
            
            return {
                "success": True,
                "answer": longest_option['position'],
                "confidence": "low",
                "source": "Smart-Guess-Length"
            }
            
        except Exception as e:
            logger.error(f"Smart guess failed: {str(e)}")
            return {"success": False, "error": "All methods failed"}

    def solve_question(self, question: str, answer_options: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Savolni yechish uchun asosiy metod"""
        
        # 1-usul: GPT-4 bilan
        result = self.analyze_and_solve_question(question, answer_options)
        if result["success"]:
            return result
            
        logger.warning("GPT-4 failed, trying GPT-3.5...")
        
        # 2-usul: GPT-3.5 bilan
        result = self.get_backup_answer(question, answer_options)
        if result["success"]:
            return result
            
        logger.warning("GPT-3.5 failed, using smart guess...")
        
        # 3-usul: Aqlli taxmin
        result = self.smart_guess(question, answer_options)
        return result

    def process_questions_batch(self, questions_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Bir nechta savolni bir vaqtda yechish"""
        responses = []
        
        for item in questions_data:
            question_text = item.get("question", "")
            answer_options = item.get("answers", [])
            question_index = item.get("index", 0)
            
            if not question_text or not answer_options:
                responses.append({
                    "question_index": question_index,
                    "question": question_text,
                    "status": "error",
                    "message": "Savol yoki javoblar mavjud emas",
                    "answer": "-"
                })
                continue
            
            # Savolni yechish
            result = self.solve_question(question_text, answer_options)
            
            if result["success"]:
                responses.append({
                    "question_index": question_index,
                    "question": question_text[:100] + "..." if len(question_text) > 100 else question_text,
                    "status": "success",
                    "answer": result["answer"],
                    "confidence": result["confidence"],
                    "source": result["source"],
                    "solved": True
                })
            else:
                responses.append({
                    "question_index": question_index,
                    "question": question_text[:100] + "..." if len(question_text) > 100 else question_text,
                    "status": "failed",
                    "message": result.get("error", "Noma'lum xato"),
                    "answer": "-",
                    "solved": False
                })
        
        # Statistika
        successful = sum(1 for r in responses if r.get("solved", False))
        total = len(responses)
        logger.info(f"Batch completed: {successful}/{total} questions solved successfully")
        
        return responses

# Global AI solver instance
ai_solver = SmartAIQuestionSolver()

@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def solve_questions_ai(request) -> JsonResponse:
    """AI yordamida savollarni yechish endpoint"""
    if request.method == "OPTIONS":
        response = JsonResponse({})
        response = _add_cors_headers(response)
        return response
        
    try:
        data = json.loads(request.body.decode("utf-8"))
        
        if not isinstance(data, list):
            logger.warning("Invalid input format: not an array")
            return JsonResponse({"error": "Ma'lumot array formatida bo'lishi kerak"}, status=400)

        if not data:
            return JsonResponse({"error": "Bo'sh array yuborildi"}, status=400)

        # AI yordamida savollarni yechish
        solutions = ai_solver.process_questions_batch(data)
        
        response_data = {
            "status": "completed",
            "total_questions": len(solutions),
            "solved_count": sum(1 for s in solutions if s.get("solved", False)),
            "success_rate": f"{(sum(1 for s in solutions if s.get('solved', False)) / len(solutions) * 100):.1f}%",
            "solutions": solutions
        }
        
        response = JsonResponse(response_data, safe=False)
        response = _add_cors_headers(response)
        
        return response
        
    except json.JSONDecodeError:
        logger.error("JSON parsing error")
        return JsonResponse({"error": "Noto'g'ri JSON format"}, status=400)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return JsonResponse({"error": f"Xato: {str(e)}"}, status=500)

def _add_cors_headers(response):
    response["Access-Control-Allow-Origin"] = "*"  # Barcha domenlar uchun ruxsat
    response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response["Access-Control-Allow-Headers"] = "Content-Type, X-CSRFToken, Accept"
    return response

