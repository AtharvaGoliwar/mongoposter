import pymongo
import pyperclip
import time
import threading
from pymongo import MongoClient
from datetime import datetime, timedelta
from bson import ObjectId
import logging
from typing import Dict, Any, Optional, List

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MongoDBPollingMonitor:
    def __init__(self, connection_string: str, database_name: str, collection_name: str, poll_interval: int = 2):
        """
        Initialize MongoDB polling monitor (works without replica sets)
        
        Args:
            connection_string: MongoDB connection string
            database_name: Name of the database to monitor
            collection_name: Name of the collection to monitor
            poll_interval: Polling interval in seconds (default: 2)
        """
        self.connection_string = connection_string
        self.database_name = database_name
        self.collection_name = collection_name
        self.poll_interval = poll_interval
        self.client = None
        self.db = None
        self.collection = None
        self.is_monitoring = False
        self.last_check_time = None
        self.processed_ids = set()
        
    def connect(self) -> bool:
        """Establish connection to MongoDB"""
        try:
            self.client = MongoClient(self.connection_string)
            self.db = self.client[self.database_name]
            self.collection = self.db[self.collection_name]
            
            # Test connection
            self.client.admin.command('ping')
            logger.info(f"Connected to MongoDB: {self.database_name}.{self.collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            return False
    
    def preserve_code_formatting(self, text: str) -> str:
        """
        Preserve code indentation and formatting
        
        Args:
            text: Raw text that may contain code
            
        Returns:
            Formatted text with preserved indentation
        """
        if not text:
            return ""
        
        # Preserve original line breaks and indentation
        lines = text.splitlines()
        formatted_lines = []
        
        for line in lines:
            # Don't strip leading whitespace to preserve indentation
            formatted_lines.append(line.rstrip())  # Only strip trailing whitespace
        
        return '\n'.join(formatted_lines)
    
    def extract_text_content(self, document: Dict[Any, Any]) -> Optional[str]:
        """
        Extract text content from document with various field names
        
        Args:
            document: MongoDB document
            
        Returns:
            Extracted text content or None
        """
        # Common field names for text content
        text_fields = ['text', 'content', 'code', 'message', 'body', 'data', 'value', 'snippet']
        
        for field in text_fields:
            if field in document and document[field]:
                text_content = str(document[field])
                return self.preserve_code_formatting(text_content)
        
        # If no specific text field found, try to extract from nested objects
        for key, value in document.items():
            if key.startswith('_'):  # Skip MongoDB internal fields
                continue
                
            if isinstance(value, str) and len(value) > 10:  # Assume longer strings are content
                return self.preserve_code_formatting(value)
            elif isinstance(value, dict):
                nested_text = self.extract_text_content(value)
                if nested_text:
                    return nested_text
        
        return None
    
    def copy_to_clipboard(self, text: str) -> bool:
        """
        Copy text to clipboard with error handling
        
        Args:
            text: Text to copy to clipboard
            
        Returns:
            True if successful, False otherwise
        """
        try:
            pyperclip.copy(text)
            logger.info(f"Copied {len(text)} characters to clipboard")
            return True
        except Exception as e:
            logger.error(f"Failed to copy to clipboard: {e}")
            return False
    
    def get_new_documents(self) -> List[Dict[Any, Any]]:
        """
        Get new documents since last check
        
        Returns:
            List of new documents
        """
        try:
            query = {}
            
            # Use timestamp-based filtering if available
            if self.last_check_time:
                # Try different timestamp field names
                timestamp_fields = ['timestamp', 'created_at', 'createdAt', 'date_created', '_id']
                
                for field in timestamp_fields:
                    if field == '_id':
                        # Use ObjectId timestamp (works for all documents)
                        last_object_id = ObjectId.from_datetime(self.last_check_time)
                        query = {'_id': {'$gt': last_object_id}}
                        break
                    else:
                        # Check if field exists in collection
                        sample_doc = self.collection.find_one({field: {'$exists': True}})
                        if sample_doc:
                            query = {field: {'$gt': self.last_check_time}}
                            break
            
            # Get documents
            cursor = self.collection.find(query).sort('_id', -1).limit(100)
            new_documents = list(cursor)
            
            # Filter out already processed documents
            filtered_docs = []
            for doc in new_documents:
                doc_id = doc['_id']
                if doc_id not in self.processed_ids:
                    filtered_docs.append(doc)
                    self.processed_ids.add(doc_id)
            
            return filtered_docs
            
        except Exception as e:
            logger.error(f"Error getting new documents: {e}")
            return []
    
    def process_document(self, document: Dict[Any, Any]) -> None:
        """
        Process a new document
        
        Args:
            document: MongoDB document to process
        """
        try:
            logger.info(f"Processing document ID: {document['_id']}")
            
            # Extract text content
            text_content = self.extract_text_content(document)
            
            if text_content:
                logger.info(f"Extracted text content: {len(text_content)} characters")
                
                # Copy to clipboard
                if self.copy_to_clipboard(text_content):
                    logger.info("Successfully copied code to clipboard with preserved formatting")
                    
                    # Optional: Print first few lines for verification
                    preview_lines = text_content.split('\n')[:3]
                    logger.info(f"Preview: {preview_lines}")
                else:
                    logger.error("Failed to copy to clipboard")
            else:
                logger.info("No text content found in document")
                
        except Exception as e:
            logger.error(f"Error processing document: {e}")
    
    def poll_for_changes(self) -> None:
        """Poll MongoDB for new documents"""
        try:
            new_documents = self.get_new_documents()
            
            if new_documents:
                logger.info(f"Found {len(new_documents)} new documents")
                
                # Process documents in reverse order (oldest first)
                for document in reversed(new_documents):
                    self.process_document(document)
                    
            # Update last check time
            self.last_check_time = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Error in polling: {e}")
    
    def start_monitoring(self) -> None:
        """Start monitoring MongoDB changes using polling"""
        if not self.connect():
            return
        
        try:
            self.is_monitoring = True
            self.last_check_time = datetime.utcnow() - timedelta(seconds=5)  # Start 5 seconds ago
            
            logger.info(f"Started polling MongoDB every {self.poll_interval} seconds...")
            
            while self.is_monitoring:
                self.poll_for_changes()
                time.sleep(self.poll_interval)
                
        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")
        except Exception as e:
            logger.error(f"Error in monitoring: {e}")
        finally:
            self.stop_monitoring()
    
    def start_monitoring_background(self) -> threading.Thread:
        """Start monitoring in a background thread"""
        monitor_thread = threading.Thread(target=self.start_monitoring, daemon=True)
        monitor_thread.start()
        logger.info("Monitor started in background thread")
        return monitor_thread
    
    def stop_monitoring(self) -> None:
        """Stop monitoring and cleanup resources"""
        self.is_monitoring = False
        
        if self.client:
            try:
                self.client.close()
                logger.info("MongoDB connection closed")
            except Exception as e:
                logger.error(f"Error closing MongoDB connection: {e}")

# Enhanced version with additional features
class EnhancedPollingMonitor(MongoDBPollingMonitor):
    def __init__(self, connection_string: str, database_name: str, collection_name: str, 
                 poll_interval: int = 2, filters: Dict[str, Any] = None):
        super().__init__(connection_string, database_name, collection_name, poll_interval)
        self.filters = filters or {}
        self.stats = {
            'documents_processed': 0,
            'texts_copied': 0,
            'start_time': None
        }
    
    def get_new_documents(self) -> List[Dict[Any, Any]]:
        """Enhanced version with filtering support"""
        try:
            query = self.filters.copy()
            
            # Add timestamp filtering
            if self.last_check_time:
                last_object_id = ObjectId.from_datetime(self.last_check_time)
                query['_id'] = {'$gt': last_object_id}
            
            cursor = self.collection.find(query).sort('_id', -1).limit(100)
            new_documents = list(cursor)
            
            # Filter out already processed documents
            filtered_docs = []
            for doc in new_documents:
                doc_id = doc['_id']
                if doc_id not in self.processed_ids:
                    filtered_docs.append(doc)
                    self.processed_ids.add(doc_id)
            
            return filtered_docs
            
        except Exception as e:
            logger.error(f"Error getting new documents: {e}")
            return []
    
    def process_document(self, document: Dict[Any, Any]) -> None:
        """Enhanced processing with statistics"""
        super().process_document(document)
        self.stats['documents_processed'] += 1
        
        # Update stats if text was copied
        text_content = self.extract_text_content(document)
        if text_content:
            self.stats['texts_copied'] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get monitoring statistics"""
        if self.stats['start_time']:
            runtime = datetime.utcnow() - self.stats['start_time']
            self.stats['runtime_seconds'] = runtime.total_seconds()
        
        return self.stats.copy()
    
    def start_monitoring(self) -> None:
        """Enhanced monitoring with statistics"""
        self.stats['start_time'] = datetime.utcnow()
        super().start_monitoring()

def main():
    """Main function to run the polling monitor"""
    
    # Configuration
    MONGODB_URI = "abc"
    DATABASE_NAME = "db"
    COLLECTION_NAME = "collection"# Update with your collection name
    POLL_INTERVAL = 2  # Check every 2 seconds
    
    # Optional filters
    filters = {
        'type': 'code',  # Only monitor documents with type='code'
        # 'language': 'python'  # Only monitor Python code
    }
    
    # Create and start monitor
    monitor = EnhancedPollingMonitor(
        MONGODB_URI, 
        DATABASE_NAME, 
        COLLECTION_NAME, 
        POLL_INTERVAL,
        filters
    )
    
    try:
        monitor.start_monitoring()
    except KeyboardInterrupt:
        print("\nShutting down monitor...")
        monitor.stop_monitoring()
        
        # Print statistics
        stats = monitor.get_stats()
        print(f"\nMonitoring Statistics:")
        print(f"Documents processed: {stats['documents_processed']}")
        print(f"Texts copied: {stats['texts_copied']}")
        print(f"Runtime: {stats.get('runtime_seconds', 0):.1f} seconds")

def run_background_example():
    """Example of running monitor in background"""
    
    MONGODB_URI = "mongodb+srv://atharvagoliwar23:ErHbkndToW4rSvui@cluster0.yqtedoj.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    DATABASE_NAME = "code_db"
    COLLECTION_NAME = "code_snippets"
    
    monitor = MongoDBPollingMonitor(MONGODB_URI, DATABASE_NAME, COLLECTION_NAME, poll_interval=3)
    
    # Start in background
    monitor_thread = monitor.start_monitoring_background()
    
    try:
        # Your main application code here
        while True:
            time.sleep(1)
            # You can check stats periodically
            # stats = monitor.get_stats()
            # print(f"Processed: {stats['documents_processed']} documents")
            
    except KeyboardInterrupt:
        print("Stopping background monitor...")
        monitor.stop_monitoring()
        monitor_thread.join(timeout=5)

if __name__ == "__main__":
    # Run main monitor
    main()
    
    # Or run background example
    # run_background_example()