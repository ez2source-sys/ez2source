from app import app

# Import the full routes but with mobile header fix applied
import routes  # Import routes to register them with the app  
import routes_mobile  # Import mobile PWA routes

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return {'status': 'healthy', 'service': 'Ez2source', 'version': '1.0'}, 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
