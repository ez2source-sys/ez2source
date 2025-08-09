// Enhanced Autocomplete for Interview AI Assistance
class InterviewAutocomplete {
    constructor() {
        this.topicSuggestions = [
            'Java', 'Python', 'JavaScript', 'React', 'Node.js', 'SQL', 
            'Data Structures', 'Algorithms', 'System Design', 'Machine Learning',
            'Angular', 'Vue.js', 'Spring Boot', 'Django', 'Flask', 'Express.js',
            'MongoDB', 'PostgreSQL', 'MySQL', 'Redis', 'AWS', 'Docker', 
            'Kubernetes', 'Git', 'Linux', 'C++', 'C#', '.NET', 'PHP',
            'Ruby', 'Go', 'Rust', 'Swift', 'Kotlin', 'TypeScript',
            'REST APIs', 'GraphQL', 'Microservices', 'DevOps', 'CI/CD',
            'Testing', 'Cybersecurity', 'Blockchain', 'Cloud Computing',
            'Web Development', 'Mobile Development', 'Game Development',
            'Data Science', 'Artificial Intelligence', 'Deep Learning',
            'Computer Networks', 'Operating Systems', 'Database Design'
        ];
        
        this.difficultySuggestions = ['Easy', 'Medium', 'Hard'];
        
        this.init();
    }
    
    init() {
        this.setupTopicAutocomplete();
        this.setupDifficultyAutocomplete();
    }
    
    setupTopicAutocomplete() {
        const input = document.getElementById('topicInput');
        const container = this.createAutocompleteContainer(input, 'topic');
        
        input.addEventListener('input', (e) => {
            this.showSuggestions(e.target, this.topicSuggestions, container);
        });
        
        input.addEventListener('blur', () => {
            setTimeout(() => container.style.display = 'none', 200);
        });
        
        input.addEventListener('focus', (e) => {
            if (e.target.value) {
                this.showSuggestions(e.target, this.topicSuggestions, container);
            }
        });
    }
    
    setupDifficultyAutocomplete() {
        const input = document.getElementById('difficultyInput');
        const container = this.createAutocompleteContainer(input, 'difficulty');
        
        input.addEventListener('input', (e) => {
            this.showSuggestions(e.target, this.difficultySuggestions, container);
        });
        
        input.addEventListener('blur', () => {
            setTimeout(() => container.style.display = 'none', 200);
        });
        
        input.addEventListener('focus', (e) => {
            this.showSuggestions(e.target, this.difficultySuggestions, container);
        });
    }
    
    createAutocompleteContainer(input, type) {
        const container = document.createElement('div');
        container.className = 'autocomplete-suggestions';
        container.id = `${type}-suggestions`;
        container.style.cssText = `
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: white;
            border: 1px solid #dee2e6;
            border-top: none;
            border-radius: 0 0 10px 10px;
            max-height: 200px;
            overflow-y: auto;
            z-index: 1000;
            display: none;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        `;
        
        input.parentNode.style.position = 'relative';
        input.parentNode.appendChild(container);
        
        return container;
    }
    
    showSuggestions(input, suggestions, container) {
        const value = input.value.toLowerCase();
        
        if (!value) {
            container.style.display = 'none';
            return;
        }
        
        const filtered = suggestions.filter(item => 
            item.toLowerCase().includes(value)
        );
        
        if (filtered.length === 0) {
            container.style.display = 'none';
            return;
        }
        
        container.innerHTML = '';
        
        filtered.forEach(item => {
            const div = document.createElement('div');
            div.className = 'autocomplete-item';
            div.textContent = item;
            div.style.cssText = `
                padding: 10px 15px;
                cursor: pointer;
                border-bottom: 1px solid #f8f9fa;
                transition: background-color 0.2s;
                color: #495057;
            `;
            
            div.addEventListener('mouseenter', () => {
                div.style.backgroundColor = '#f8f9fa';
            });
            
            div.addEventListener('mouseleave', () => {
                div.style.backgroundColor = 'transparent';
            });
            
            div.addEventListener('click', () => {
                input.value = item;
                container.style.display = 'none';
                input.focus();
            });
            
            container.appendChild(div);
        });
        
        container.style.display = 'block';
    }
}

// Initialize autocomplete when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new InterviewAutocomplete();
});