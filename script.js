class AutoQuestionSolver {
    constructor() {
        this.csrftoken = this.getCookie('csrftoken');
        this.questionElements = Array.from(document.querySelectorAll('.box.box-default.question'));
        this.solvedCount = 0;
        this.totalCount = 0;
    }

    getCookie(name) {
        return document.cookie.split(`; ${name}=`).pop().split(';').shift();
    }

    extractQuestions() {
        return this.questionElements.map((questionEl, index) => ({
            question: questionEl.querySelector('h3.box-title').textContent.trim(),
            index: index + 1,
            answers: Array.from(questionEl.querySelectorAll('.box-body p .qv')).map(answerEl => ({
                text: answerEl.textContent.trim(),
                position: answerEl.closest('p').querySelector('input').value 
            }))
        }));
    }

    async solveBatch() {
        const questionsData = this.extractQuestions();
        this.totalCount = questionsData.length;
        
        console.log(`AI ga ${this.totalCount} ta savol yuborilmoqda...`);
        this.showStatus(`AI ${this.totalCount} ta savolni yechmoqda...`);

        try {
            const response = await fetch("https://unco.pythonanywhere.com/ai-solve/", {
                method: "POST",
                body: JSON.stringify(questionsData),
                headers: {
                    "Content-type": "application/json; charset=UTF-8",
                    "X-CSRFToken": this.csrftoken
                }
            });

            if (!response.ok) {
                throw new Error(`Server xatosi: ${response.status}`);
            }

            const result = await response.json();
            this.processResults(result);
            
        } catch (error) {
            console.error('AI yechim xatosi:', error);
            this.showStatus(`Xato: ${error.message}`, 'error');
        }
    }

    processResults(result) {
        const solutions = result.solutions || [];
        this.solvedCount = result.solved_count || 0;
        
        console.log(`AI natijasi: ${this.solvedCount}/${this.totalCount} ta savol yechildi`);
        
        solutions.forEach((solution, index) => {
            if (index < this.questionElements.length) {
                const questionEl = this.questionElements[index];
                this.applySolution(questionEl, solution);
            }
        });

        this.showFinalStatus(result);
        this.autoSelectAnswers(solutions);
    }

    applySolution(questionEl, solution) {
        const questionTitle = questionEl.querySelector('h3.box-title');
        const originalText = questionTitle.textContent.trim();
        
        if (solution.solved && solution.answer) {
            // To'g'ri javob topilgan
            questionTitle.innerHTML = `✅ ${originalText}`;
            questionEl.style.borderLeft = "5px solid blue";
            questionEl.setAttribute("title", 
                `Javob: ${solution.answer} (${solution.confidence} ishonch, ${solution.source})`);
            
            // Avtomatik javob tanlash
            this.selectAnswer(questionEl, solution.answer);
            
        } else {
            // Javob topilmagan
            questionTitle.innerHTML = `❌ ${originalText}`;
            questionEl.style.borderLeft = "5px solid red";
            questionEl.setAttribute("title", `Yechilmadi: ${solution.message || 'Noma\\lum xato'}`);
        }
    }

    selectAnswer(questionEl, answerPosition) {
        try {
            // To'g'ri input elementini topish va tanlash
            const inputs = questionEl.querySelectorAll('input[type="radio"], input[type="checkbox"]');
            
            for (let input of inputs) {
                if (input.value === answerPosition) {
                    input.checked = true;
                    input.dispatchEvent(new Event('change', { bubbles: true }));
                    
                    // Visual indicator qo'shish
                    const parentP = input.closest('p');
                    if (parentP) {
                        parentP.style.backgroundColor = '#d4edda';
                        parentP.style.border = '2px solid #28a745';
                        parentP.style.borderRadius = '5px';
                    }
                    
                    console.log(`Savol ${questionEl.querySelector('h3.box-title').textContent.slice(0, 50)}... uchun javob ${answerPosition} tanlandi`);
                    break;
                }
            }
        } catch (error) {
            console.error('Javob tanlashda xato:', error);
        }
    }

    autoSelectAnswers(solutions) {
        let selectedCount = 0;
        
        solutions.forEach((solution, index) => {
            if (solution.solved && solution.answer && index < this.questionElements.length) {
                setTimeout(() => {
                    this.selectAnswer(this.questionElements[index], solution.answer);
                    selectedCount++;
                }, index * 100); // Har bir javobni 100ms oraliqda tanlash
            }
        });
        
        setTimeout(() => {
            console.log(`Jami ${selectedCount} ta javob avtomatik tanlandi`);
            this.showStatus(`✅ ${selectedCount} ta javob avtomatik tanlandi!`, 'success');
        }, solutions.length * 100 + 500);
    }

    showStatus(message, type = 'info') {
        // Status ko'rsatish
        let statusDiv = document.getElementById('ai-status');
        if (!statusDiv) {
            statusDiv = document.createElement('div');
            statusDiv.id = 'ai-status';
            statusDiv.style.cssText = `
                position: fixed; top: 20px; right: 20px; z-index: 9999;
                padding: 15px; border-radius: 8px; font-weight: bold;
                max-width: 300px; box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            `;
            document.body.appendChild(statusDiv);
        }
        
        const colors = {
            'info': 'background: #17a2b8; color: white;',
            'success': 'background: #28a745; color: white;',
            'error': 'background: #dc3545; color: white;'
        };
        
        statusDiv.style.cssText += colors[type] || colors['info'];
        statusDiv.textContent = message;
        
        if (type === 'success' || type === 'error') {
            setTimeout(() => statusDiv.remove(), 5000);
        }
    }

    showFinalStatus(result) {
        const successRate = result.success_rate || '0%';
        const message = `🎯 AI natijasi:
${result.solved_count}/${result.total_questions} ta savol yechildi
Muvaffaqiyat darajasi: ${successRate}`;
        
        console.log(message);
        this.showStatus(message, 'success');
    }

    // Avtomatik ishga tushurish
    start() {
        if (this.questionElements.length === 0) {
            this.showStatus('Savollar topilmadi!', 'error');
            return;
        }
        
        console.log('🤖 AI Question Solver ishga tushdi!');
        this.showStatus('🤖 AI Question Solver ishga tushdi!');
        
        setTimeout(() => {
            this.solveBatch();
        }, 1000);
    }
}

// Avtomatik ishga tushurish
document.addEventListener('DOMContentLoaded', function() {
    const solver = new AutoQuestionSolver();
    
    // Sahifa to'liq yuklangandan so'ng AI ni ishga tushurish
    setTimeout(() => {
        solver.start();
    }, 2000);
    
    // Manual ishga tushurish tugmasi qo'shish
    const startButton = document.createElement('button');
    startButton.textContent = '🤖 AI bilan yech';
    startButton.style.cssText = `
        position: fixed; bottom: 20px; right: 20px; z-index: 9999;
        padding: 15px 25px; background: #007bff; color: white;
        border: none; border-radius: 8px; font-size: 16px;
        cursor: pointer; box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    `;
    startButton.onclick = () => solver.start();
    document.body.appendChild(startButton);
});
