from flask import Flask, render_template, request, jsonify, redirect, url_for
from pymongo import MongoClient
from datetime import datetime
import os
from bson import ObjectId

app = Flask(__name__)

# MongoDB Atlas connection
# Replace with your actual MongoDB Atlas connection string
MONGO_URI = "mongodb+srv://atharvagoliwar23:ErHbkndToW4rSvui@cluster0.yqtedoj.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

try:
    client = MongoClient(MONGO_URI)
    db = client.code_db  # Database name
    collection = db.code_snippets   # Collection name
    
    # Test the connection
    client.admin.command('ping')
    print("Successfully connected to MongoDB Atlas!")
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_code():
    try:
        # Get form data
        name = request.form.get('name', '').strip()
        code = request.form.get('code', '').strip()
        
        # Validation
        if not name:
            return jsonify({'error': 'Name is required'}), 400
        if not code:
            return jsonify({'error': 'Code is required'}), 400
        
        # Create document to insert
        document = {
            'name': name,
            'code': code,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        # Insert into MongoDB
        result = collection.insert_one(document)
        
        return jsonify({
            'success': True,
            'message': 'Code uploaded successfully!',
            'id': str(result.inserted_id)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/snippets', methods=['GET'])
def get_snippets():
    try:
        # Get all snippets from MongoDB
        snippets = list(collection.find().sort('created_at', -1))
        
        # Convert ObjectId to string for JSON serialization
        for snippet in snippets:
            snippet['_id'] = str(snippet['_id'])
            snippet['created_at'] = snippet['created_at'].isoformat()
            snippet['updated_at'] = snippet['updated_at'].isoformat()
        
        return jsonify({'snippets': snippets})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/snippet/<snippet_id>', methods=['GET'])
def get_snippet(snippet_id):
    try:
        snippet = collection.find_one({'_id': ObjectId(snippet_id)})
        
        if not snippet:
            return jsonify({'error': 'Snippet not found'}), 404
        
        # Convert ObjectId to string
        snippet['_id'] = str(snippet['_id'])
        snippet['created_at'] = snippet['created_at'].isoformat()
        snippet['updated_at'] = snippet['updated_at'].isoformat()
        
        return jsonify(snippet)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/view')
def view_snippets():
    return render_template('view.html')

@app.route('/delete/<snippet_id>', methods=['DELETE'])
def delete_snippet(snippet_id):
    try:
        result = collection.delete_one({'_id': ObjectId(snippet_id)})
        
        if result.deleted_count == 1:
            return jsonify({'success': True, 'message': 'Snippet deleted successfully'})
        else:
            return jsonify({'error': 'Snippet not found'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)