# static/js/search.js

class SearchManager {
    constructor() {
        this.form = document.querySelector('#searchForm');
        this.resultsContainer = document.querySelector('#results');
        this.progressBar = document.querySelector('#progressBar');
        this.statusMessage = document.querySelector('#statusMessage');
        this.searchButton = document.querySelector('#searchButton');
        
        this.bindEvents();
    }

    bindEvents() {
        this.form.addEventListener('submit', this.handleSubmit.bind(this));
    }

    async handleSubmit(event) {
        event.preventDefault();
        
        const formData = new FormData(this.form);
        const searchData = {
            url: formData.get('url'),
            search_term: formData.get('search_term'),
            max_pages: formData.get('max_pages')
        };

        try {
            this.setLoading(true);
            
            const response = await fetch('/search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(searchData)
            });

            const data = await response.json();
            
            if (data.status === 'success') {
                this.initWebSocket(data.search_id);
            } else {
                this.showError(data.message);
            }
            
        } catch (error) {
            this.showError('An error occurred while starting the search');
            console.error(error);
        }
    }

    initWebSocket(searchId) {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const ws = new WebSocket(`${protocol}//${window.location.host}/ws/${searchId}`);
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.updateProgress(data);
            
            if (data.current_status === 'completed') {
                this.loadResults(searchId);
            } else if (data.current_status === 'error') {
                this.showError(data.error || 'Search failed');
            }
        };

        ws.onerror = () => {
            this.showError('WebSocket connection error');
        };
    }

    async loadResults(searchId) {
        try {
            const response = await fetch(`/results/${searchId}`);
            const data = await response.json();
            
            if (data.status === 'success') {
                this.displayResults(data.results);
            } else {
                this.showError(data.message);
            }
        } catch (error) {
            this.showError('Error loading results');
            console.error(error);
        } finally {
            this.setLoading(false);
        }
    }

    displayResults(results) {
        this.resultsContainer.innerHTML = results.map(result => `
            <div class="result">
                <h3>${this.escapeHtml(result.title)}</h3>
                <p class="result-context">${this.highlightSearchTerm(result.context)}</p>
                <p><strong>URL:</strong> <a href="${result.url}" target="_blank">${result.url}</a></p>
                <p><strong>Relevance:</strong> ${result.relevance.toFixed(2)}</p>
            </div>
        `).join('');
    }

    updateProgress(data) {
        this.progressBar.style.width = `${data.progress}%`;
        this.statusMessage.textContent = this.getStatusMessage(data.current_status);
    }

    setLoading(loading) {
        this.searchButton.disabled = loading;
        this.progressBar.style.display = loading ? 'block' : 'none';
    }

    showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error';
        errorDiv.textContent = message;
        this.form.insertAdjacentElement('beforebegin', errorDiv);
        
        setTimeout(() => errorDiv.remove(), 5000);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    highlightSearchTerm(text) {
        const searchTerm = this.form.querySelector('[name="search_term"]').value;
        const regex = new RegExp(`(${searchTerm})`, 'gi');
        return text.replace(regex, '<mark>$1</mark>');
    }

    getStatusMessage(status) {
        const messages = {
            'waiting': 'Preparing search...',
            'searching': 'Searching pages...',
            'completed': 'Search completed!',
            'error': 'An error occurred'
        };
        return messages[status] || 'Processing...';
    }
}

// Initialize search manager
document.addEventListener('DOMContentLoaded', () => {
    new SearchManager();
});
