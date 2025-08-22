"""Google Cloud Pub/Sub client for Helios Autonomous Store"""

import asyncio
import json
import time
from typing import Any, Callable, Dict, List, Optional, Union
from google.cloud import pubsub_v1
from google.api_core import retry
from loguru import logger


class PubSubClient:
    """Google Cloud Pub/Sub client for event-driven communication"""
    
    def __init__(self, project_id: str, credentials_path: Optional[str] = None):
        """Initialize Pub/Sub client"""
        self.project_id = project_id
        self.credentials_path = credentials_path
        
        # Initialize clients
        if credentials_path:
            self.publisher_client = pubsub_v1.PublisherClient.from_service_account_file(credentials_path)
            self.subscriber_client = pubsub_v1.SubscriberClient.from_service_account_file(credentials_path)
        else:
            self.publisher_client = pubsub_v1.PublisherClient()
            self.subscriber_client = pubsub_v1.SubscriberClient()
        
        # Topic and subscription cache
        self._topics = {}
        self._subscriptions = {}
        
        logger.info(f"🔌 Pub/Sub client initialized for project: {project_id}")
    
    async def create_topic(self, topic_name: str) -> str:
        """Create a new topic"""
        try:
            topic_path = self.publisher_client.topic_path(self.project_id, topic_name)
            topic = self.publisher_client.create_topic(name=topic_path)
            self._topics[topic_name] = topic_path
            logger.info(f"✅ Created topic: {topic_name}")
            return topic_path
        except Exception as e:
            logger.error(f"❌ Failed to create topic {topic_name}: {e}")
            raise
    
    async def create_subscription(self, topic_name: str, subscription_name: str) -> str:
        """Create a new subscription"""
        try:
            topic_path = self.publisher_client.topic_path(self.project_id, topic_name)
            subscription_path = self.subscriber_client.subscription_path(self.project_id, subscription_name)
            
            subscription = self.subscriber_client.create_subscription(
                name=subscription_path,
                topic=topic_path
            )
            
            self._subscriptions[subscription_name] = subscription_path
            logger.info(f"✅ Created subscription: {subscription_name} for topic: {topic_name}")
            return subscription_path
        except Exception as e:
            logger.error(f"❌ Failed to create subscription {subscription_name}: {e}")
            raise
    
    async def publish_message(
        self, 
        topic_name: str, 
        message: Union[str, Dict[str, Any]], 
        attributes: Optional[Dict[str, str]] = None
    ) -> str:
        """Publish a message to a topic"""
        try:
            topic_path = self._topics.get(topic_name)
            if not topic_path:
                topic_path = self.publisher_client.topic_path(self.project_id, topic_name)
                self._topics[topic_name] = topic_path
            
            # Convert message to string if it's a dict
            if isinstance(message, dict):
                message_data = json.dumps(message).encode("utf-8")
            else:
                message_data = str(message).encode("utf-8")
            
            # Prepare attributes
            message_attributes = attributes or {}
            message_attributes.update({
                "timestamp": str(int(time.time())),
                "source": "helios-autonomous-store"
            })
            
            # Publish with retry logic
            future = self.publisher_client.publish(
                topic_path,
                data=message_data,
                **message_attributes
            )
            
            message_id = future.result()
            logger.debug(f"📤 Published message {message_id} to topic {topic_name}")
            return message_id
            
        except Exception as e:
            logger.error(f"❌ Failed to publish message to topic {topic_name}: {e}")
            raise
    
    async def publish_batch(
        self, 
        topic_name: str, 
        messages: List[Union[str, Dict[str, Any]]], 
        attributes: Optional[Dict[str, str]] = None
    ) -> List[str]:
        """Publish multiple messages in batch"""
        try:
            topic_path = self._topics.get(topic_name)
            if not topic_path:
                topic_path = self.publisher_client.topic_path(self.project_id, topic_name)
                self._topics[topic_name] = topic_path
            
            futures = []
            message_ids = []
            
            for message in messages:
                if isinstance(message, dict):
                    message_data = json.dumps(message).encode("utf-8")
                else:
                    message_data = str(message).encode("utf-8")
                
                # Prepare attributes
                message_attributes = attributes or {}
                message_attributes.update({
                    "timestamp": str(int(time.time())),
                    "source": "helios-autonomous-store"
                })
                
                future = self.publisher_client.publish(
                    topic_path,
                    data=message_data,
                    **message_attributes
                )
                futures.append(future)
            
            # Wait for all messages to be published
            for future in futures:
                message_id = future.result()
                message_ids.append(message_id)
            
            logger.info(f"📤 Published {len(message_ids)} messages to topic {topic_name}")
            return message_ids
            
        except Exception as e:
            logger.error(f"❌ Failed to publish batch to topic {topic_name}: {e}")
            raise
    
    async def subscribe(
        self, 
        subscription_name: str, 
        callback: Callable[[Dict[str, Any]], None],
        timeout: int = 60
    ) -> None:
        """Subscribe to a subscription and process messages"""
        try:
            subscription_path = self._subscriptions.get(subscription_name)
            if not subscription_path:
                subscription_path = self.subscriber_client.subscription_path(self.project_id, subscription_name)
                self._subscriptions[subscription_name] = subscription_path
            
            def message_callback(message):
                try:
                    # Parse message data
                    data = message.data.decode("utf-8")
                    try:
                        parsed_data = json.loads(data)
                    except json.JSONDecodeError:
                        parsed_data = {"raw_data": data}
                    
                    # Add message metadata
                    parsed_data.update({
                        "message_id": message.message_id,
                        "publish_time": message.publish_time.isoformat(),
                        "attributes": dict(message.attributes)
                    })
                    
                    # Process message
                    callback(parsed_data)
                    
                    # Acknowledge message
                    message.ack()
                    logger.debug(f"✅ Processed message {message.message_id}")
                    
                except Exception as e:
                    logger.error(f"❌ Error processing message {message.message_id}: {e}")
                    # Nack message to retry
                    message.nack()
            
            # Start listening
            logger.info(f"🎧 Starting subscription to {subscription_name}")
            streaming_pull_future = self.subscriber_client.subscribe(
                subscription_path,
                callback=message_callback
            )
            
            # Wait for timeout or cancellation
            try:
                streaming_pull_future.result(timeout=timeout)
            except Exception as e:
                streaming_pull_future.cancel()
                logger.info(f"🛑 Subscription {subscription_name} cancelled: {e}")
                
        except Exception as e:
            logger.error(f"❌ Failed to subscribe to {subscription_name}: {e}")
            raise
    
    async def create_workflow_topics(self) -> Dict[str, str]:
        """Create standard workflow topics for Helios"""
        topics = {
            "trend-discovered": "Trend discovery events",
            "analysis-complete": "Analysis completion events", 
            "content-ready": "Content generation events",
            "publication-success": "Publication success events",
            "publication-failure": "Publication failure events",
            "quality-gate-passed": "Quality gate events",
            "performance-update": "Performance metric updates"
        }
        
        created_topics = {}
        for topic_name, description in topics.items():
            try:
                topic_path = await self.create_topic(topic_name)
                created_topics[topic_name] = topic_path
                logger.info(f"✅ Created workflow topic: {topic_name} - {description}")
            except Exception as e:
                logger.warning(f"⚠️  Topic {topic_name} may already exist: {e}")
        
        return created_topics
    
    async def publish_workflow_event(
        self, 
        event_type: str, 
        event_data: Dict[str, Any],
        priority: str = "normal"
    ) -> str:
        """Publish a workflow event with standard attributes"""
        attributes = {
            "event_type": event_type,
            "priority": priority,
            "workflow_id": event_data.get("workflow_id", "unknown"),
            "agent": event_data.get("agent", "unknown")
        }
        
        return await self.publish_message(event_type, event_data, attributes)
    
    def close(self):
        """Close client connections"""
        try:
            self.publisher_client.close()
            self.subscriber_client.close()
            logger.info("🔌 Pub/Sub client connections closed")
        except Exception as e:
            logger.warning(f"⚠️  Error closing Pub/Sub connections: {e}")


# Async context manager wrapper
class AsyncPubSubClient:
    """Async context manager for Pub/Sub client"""
    
    def __init__(self, project_id: str, credentials_path: Optional[str] = None):
        self.client = PubSubClient(project_id, credentials_path)
    
    async def __aenter__(self):
        return self.client
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.client.close()
