from dockai.health_checker import detect_health_endpoint, detect_port

def test_detect_health_endpoint_express():
    """Test health endpoint detection in Express.js code"""
    file_contents = """
    const express = require('express');
    const app = express();
    
    app.get('/health', (req, res) => {
        res.status(200).json({ status: 'ok' });
    });
    
    app.listen(3000);
    """
    
    result = detect_health_endpoint(file_contents, "Node.js/Express")
    assert result is not None
    endpoint, port = result
    assert endpoint == "/health"
    assert port == 3000

def test_detect_health_endpoint_flask():
    """Test health endpoint detection in Flask code"""
    file_contents = """
    from flask import Flask
    app = Flask(__name__)
    
    @app.route('/healthz')
    def health():
        return {'status': 'healthy'}
    
    if __name__ == '__main__':
        app.run(port=5000)
    """
    
    result = detect_health_endpoint(file_contents, "Python/Flask")
    assert result is not None
    endpoint, port = result
    assert endpoint == "/healthz"
    assert port == 5000

def test_detect_health_endpoint_go():
    """Test health endpoint detection in Go code"""
    file_contents = """
    package main
    
    import (
        "net/http"
    )
    
    func main() {
        http.HandleFunc("/health", healthHandler)
        http.ListenAndServe(":8080", nil)
    }
    """
    
    result = detect_health_endpoint(file_contents, "Go")
    assert result is not None
    endpoint, port = result
    assert endpoint == "/health"
    assert port == 8080

def test_detect_health_endpoint_no_endpoint():
    """Test when no health endpoint is found"""
    file_contents = """
    const express = require('express');
    const app = express();
    
    app.get('/', (req, res) => {
        res.send('Hello');
    });
    """
    
    result = detect_health_endpoint(file_contents, "Node.js/Express")
    # Should return default for Node.js
    assert result is not None
    endpoint, port = result
    assert endpoint == "/health"
    assert port == 3000

def test_detect_port_various_patterns():
    """Test port detection with various patterns"""
    
    # Node.js pattern
    assert detect_port("server.listen(3000)", "Node.js") == 3000
    
    # Go pattern
    assert detect_port("http.ListenAndServe(\":8080\", nil)", "Go") == 8080
    
    # Generic pattern
    assert detect_port("port: 5000", "Python") == 5000
    
    # ENV pattern
    assert detect_port("PORT=9000", "Unknown") == 9000
    
    # Flask pattern
    assert detect_port("app.run(port=5000)", "Flask") == 5000

def test_detect_port_fallback():
    """Test port detection fallback to defaults"""
    
    # No port found, should use stack default
    assert detect_port("", "Node.js") == 3000
    assert detect_port("", "Python") == 8000
    assert detect_port("", "Go") == 8080
    assert detect_port("", "Unknown") == 8080  # Ultimate fallback
