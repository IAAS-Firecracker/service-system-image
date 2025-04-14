#!/usr/bin/env python3
import os
import json
import logging
import pika
from datetime import datetime
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class SystemImagePublisher:
    """
    A utility class to handle RabbitMQ connections and publishing messages
    for the service-system-image application.
    """
    
    def __init__(self):
        """Initialize the RabbitMQ connection and channel."""
        self.connection = None
        self.channel = None
        self.exchange_name = os.getenv('SERVICE_SYSTEM_IMAGE_EXCHANGE', 'system-image-exchange')
        # Queue name for this service
        self.queue_name = f"{self.exchange_name}-system-image-queue"
        self.host = os.getenv('RABBITMQ_HOST', 'localhost')
        self.port = int(os.getenv('RABBITMQ_PORT', 5672))
        self.user = os.getenv('RABBITMQ_USER', 'guest')
        self.password = os.getenv('RABBITMQ_PASSWORD', 'guest')
        
    def connect(self):
        """Establish connection to RabbitMQ server and set up the exchange."""
        try:
            # Create connection parameters
            credentials = pika.PlainCredentials(self.user, self.password)
            parameters = pika.ConnectionParameters(
                host=self.host,
                port=self.port,
                credentials=credentials,
                heartbeat=600,
                blocked_connection_timeout=300
            )
            
            # Establish connection
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            
            # Declare a fanout exchange
            self.channel.exchange_declare(
                exchange=self.exchange_name,
                exchange_type='fanout',
                durable=True
            )
            
            logger.info(f"Successfully connected to RabbitMQ and declared exchange: {self.exchange_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {str(e)}")
            return False
    
    def publish_system_image_event(self, action, system_image_data):
        """
        Publish a system image event to the exchange.
        
        Args:
            action (str): The action performed (create, update, delete)
            system_image_data (dict): The system image data
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.connection or self.connection.is_closed:
            if not self.connect():
                return False
        
        try:
            # Prepare the message
            message = {
                'action': action,
                'timestamp': str(datetime.now()),
                'data': system_image_data
            }
            
            # Convert to JSON
            message_json = json.dumps(message)
            
            # Publish the message
            self.channel.basic_publish(
                exchange=self.exchange_name,
                routing_key='',  # Not needed for fanout exchange
                body=message_json,
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                    content_type='application/json'
                )
            )
            
            logger.info(f"Published {action} event for System Image: {system_image_data.get('id', 'new')}")
            return True
        except Exception as e:
            logger.error(f"Failed to publish message: {str(e)}")
            return False
    
    def close(self):
        """Close the RabbitMQ connection."""
        if self.connection and not self.connection.is_closed:
            self.connection.close()
            logger.info("RabbitMQ connection closed")

# Create a singleton instance
system_image_publisher = SystemImagePublisher()