from django.contrib import admin
from django.urls import path,include
from .views import solve_questions_ai
urlpatterns = [
    path('ai-solve/', solve_questions_ai, name='ai_solve'), 
]
