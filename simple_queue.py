#!/usr/bin/env python3
import time
import json
from datetime import datetime, timedelta
from queue_processor import QueueProcessor

class SimpleQueue:
    def __init__(self):
        # Initialize the queue processor
        self.processor = QueueProcessor()
        self.processor.start()
        print("Queue processor started")
        
    def schedule_task(self, function, params=None, delay_minutes=0):
        """
        Schedule a function to run after a specified delay
        
        Args:
            function: The function to run
            params: Dictionary of parameters to pass to the function
            delay_minutes: Minutes to wait before running the task
            
        Returns:
            task_id: ID of the scheduled task
        """
        # Generate a unique task type based on the function name
        task_type = f"custom_task_{function.__name__}"
        
        # Register the function as a handler for this task type
        self.processor.register_task_handler(task_type, lambda params: function(**params))
        
        # Calculate the scheduled time
        scheduled_time = datetime.now() + timedelta(minutes=delay_minutes)
        
        # Add the task to the queue
        task_id = self.processor.add_task(
            task_type=task_type,
            parameters=params or {},
            scheduled_time=scheduled_time
        )
        
        print(f"Task scheduled: {function.__name__} will run at {scheduled_time}")
        return task_id
    
    def stop(self):
        """Stop the queue processor"""
        self.processor.stop()
        print("Queue processor stopped")

# Example usage
if __name__ == "__main__":
    # Create the simple queue
    queue = SimpleQueue()
    
    # Define some example functions
    def send_notification(user_id, message):
        print(f"Sending notification to user {user_id}: {message}")
        # Your notification logic here
        return True
    
    def process_data(data_file, process_type="standard"):
        print(f"Processing data from {data_file} using {process_type} method")
        # Your data processing logic here
        return True
    
    # Schedule tasks with different delays
    queue.schedule_task(
        send_notification, 
        {"user_id": 123, "message": "Your report is ready!"}, 
        delay_minutes=2
    )
    
    queue.schedule_task(
        process_data, 
        {"data_file": "sales_data.csv", "process_type": "detailed"}, 
        delay_minutes=5
    )
    
    try:
        # Keep the script running
        print("Queue is running. Press Ctrl+C to stop.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        queue.stop() 