import cv2
import json
import base64
import time
from kafka import KafkaProducer
from datetime import datetime
import threading
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MultiWebcamKafkaStreamer:
    def __init__(self, ip_webcam_urls, kafka_bootstrap_servers, kafka_topic, initial_frames_per_minute=60, include_pc_webcam=False, pc_webcam_index=0):
        """
        Initialize the multi-webcam to Kafka streamer
        
        Args:
            ip_webcam_urls (list): List of IP webcam URLs
            kafka_bootstrap_servers (str): Kafka server address (e.g., 'localhost:9092')
            kafka_topic (str): Kafka topic name
            initial_frames_per_minute (int): Initial frames per minute to send from each camera
            include_pc_webcam (bool): Whether to include PC's webcam feed
            pc_webcam_index (int): Index of PC webcam (usually 0 for default camera)
        """
        self.ip_webcam_urls = ip_webcam_urls
        self.kafka_topic = kafka_topic
        self.frames_per_minute = initial_frames_per_minute
        self.include_pc_webcam = include_pc_webcam
        self.pc_webcam_index = pc_webcam_index
        self.running = False
        
        # Initialize Kafka producer
        self.producer = KafkaProducer(
            bootstrap_servers=[kafka_bootstrap_servers],
            key_serializer=lambda x: str(x).encode('utf-8'),
            value_serializer=lambda x: json.dumps(x).encode('utf-8'),
            max_request_size=15728640,  # 15MB for large images
            buffer_memory=33554432,     # 32MB buffer
            batch_size=16384
        )
        
        # Initialize video captures for each camera
        self.cameras = {}
        self.camera_threads = {}
        
    def connect_cameras(self):
        """Connect to all IP webcams and optionally PC webcam"""
        connected_count = 0
        
        # Connect to IP webcams
        for i, url in enumerate(self.ip_webcam_urls):
            try:
                cap = cv2.VideoCapture(url)
                if cap.isOpened():
                    self.cameras[f'ip_camera_{i}'] = {
                        'capture': cap,
                        'url': url,
                        'camera_id': i,
                        'camera_type': 'ip_camera',
                        'last_frame_time': 0
                    }
                    logger.info(f"Successfully connected to IP camera {i} at {url}")
                    connected_count += 1
                else:
                    logger.error(f"Failed to connect to IP camera {i} at {url}")
            except Exception as e:
                logger.error(f"Error connecting to IP camera {i} at {url}: {e}")
        
        # Connect to PC webcam if enabled
        if self.include_pc_webcam:
            try:
                pc_cap = cv2.VideoCapture(self.pc_webcam_index)
                if pc_cap.isOpened():
                    self.cameras['pc_webcam'] = {
                        'capture': pc_cap,
                        'url': f'PC_Webcam_Index_{self.pc_webcam_index}',
                        'camera_id': len(self.ip_webcam_urls),  # Assign next available ID
                        'camera_type': 'pc_webcam',
                        'last_frame_time': 0
                    }
                    logger.info(f"Successfully connected to PC webcam (index {self.pc_webcam_index})")
                    connected_count += 1
                else:
                    logger.error(f"Failed to connect to PC webcam (index {self.pc_webcam_index})")
            except Exception as e:
                logger.error(f"Error connecting to PC webcam: {e}")
        
        total_cameras = len(self.ip_webcam_urls) + (1 if self.include_pc_webcam else 0)
        logger.info(f"Connected to {connected_count} out of {total_cameras} cameras")
        return connected_count > 0
    
    def set_frames_per_minute(self, new_frames_per_minute):
        """Change the frame rate dynamically for all cameras"""
        if new_frames_per_minute > 0:
            self.frames_per_minute = new_frames_per_minute
            logger.info(f"Frame rate changed to {self.frames_per_minute} frames per minute for all cameras")
        else:
            logger.warning("Frames per minute must be greater than 0")
    
    def capture_and_send_frame(self, camera_name, camera_info):
        """Capture a frame from a specific camera and send it to Kafka"""
        cap = camera_info['capture']
        if not cap or not cap.isOpened():
            return False
            
        ret, frame = cap.read()
        if not ret:
            logger.warning(f"Failed to capture frame from {camera_name}")
            return False
        
        try:
            # Encode frame to JPEG
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            
            # Convert to base64 string
            frame_base64 = base64.b64encode(buffer).decode('utf-8')
            
            # Create simplified message payload - only essential data
            message = {
                'timestamp': datetime.now().isoformat(),
                'camera_id': camera_info['camera_id'],
                'frame_data': frame_base64,
                'frame_size': len(buffer)
            }
            
            # Send to Kafka with camera_id as key for partitioning
            future = self.producer.send(
                self.kafka_topic, 
                key=camera_info['camera_id'],  # Use camera_id as partition key
                value=message
            )
            
            # Optional: wait for confirmation (can be removed for better performance)
            # future.get(timeout=1)
            
            logger.debug(f"Frame sent from {camera_name} with key {camera_info['camera_id']}")
            return True
        except Exception as e:
            logger.error(f"Error sending frame from {camera_name} to Kafka: {e}")
            return False
    
    def stream_camera(self, camera_name, camera_info):
        """Stream frames from a specific camera"""
        logger.info(f"Starting stream for {camera_name} at {self.frames_per_minute} frames per minute")
        
        # Calculate interval between frames (in seconds)
        frame_interval = 60.0 / self.frames_per_minute
        last_frame_time = 0
        
        while self.running:
            current_time = time.time()
            
            # Check if it's time to send the next frame
            if current_time - last_frame_time >= frame_interval:
                if self.capture_and_send_frame(camera_name, camera_info):
                    last_frame_time = current_time
                    # Update frame interval in case frames_per_minute changed
                    frame_interval = 60.0 / self.frames_per_minute
                else:
                    # If frame capture fails, try to reconnect
                    logger.warning(f"Frame capture failed for {camera_name}, attempting to reconnect...")
                    time.sleep(5)
                    try:
                        camera_info['capture'].release()
                        
                        # Reconnect based on camera type
                        if camera_info['camera_type'] == 'pc_webcam':
                            new_cap = cv2.VideoCapture(self.pc_webcam_index)
                        else:
                            new_cap = cv2.VideoCapture(camera_info['url'])
                            
                        if new_cap.isOpened():
                            camera_info['capture'] = new_cap
                            logger.info(f"Reconnected to {camera_name}")
                        else:
                            logger.error(f"Failed to reconnect to {camera_name}")
                    except Exception as e:
                        logger.error(f"Error reconnecting to {camera_name}: {e}")
            
            # Small sleep to prevent busy waiting
            time.sleep(0.1)
    
    def start_streaming(self):
        """Start the streaming process for all cameras"""
        if not self.connect_cameras():
            logger.error("No cameras connected. Exiting.")
            return
        
        self.running = True
        logger.info(f"Starting streams to Kafka topic '{self.kafka_topic}' at {self.frames_per_minute} frames per minute")
        
        # Start a thread for each camera
        for camera_name, camera_info in self.cameras.items():
            thread = threading.Thread(
                target=self.stream_camera, 
                args=(camera_name, camera_info),
                daemon=True
            )
            thread.start()
            self.camera_threads[camera_name] = thread
        
        logger.info(f"Started {len(self.camera_threads)} camera streaming threads")
    
    def stop_streaming(self):
        """Stop the streaming process for all cameras"""
        self.running = False
        
        # Release all camera captures
        for camera_name, camera_info in self.cameras.items():
            if camera_info['capture']:
                camera_info['capture'].release()
        
        # Close Kafka producer
        self.producer.close()
        logger.info("All camera streams stopped")
    
    def get_status(self):
        """Get current status of all cameras"""
        total_cameras = len(self.ip_webcam_urls) + (1 if self.include_pc_webcam else 0)
        status = {
            'total_cameras': total_cameras,
            'connected_cameras': len(self.cameras),
            'frames_per_minute': self.frames_per_minute,
            'streaming': self.running,
            'pc_webcam_enabled': self.include_pc_webcam,
            'cameras': []
        }
        
        for camera_name, camera_info in self.cameras.items():
            status['cameras'].append({
                'name': camera_name,
                'id': camera_info['camera_id'],
                'type': camera_info['camera_type'],
                'url': camera_info['url'],
                'connected': camera_info['capture'].isOpened() if camera_info['capture'] else False
            })
        
        return status

def main():
    # Configuration - Add your camera URLs here
    IP_WEBCAM_URLS = [
        "http://192.168.28.130:8080/video",  # Camera 1
        # Add more camera URLs as needed
    ]
    
    KAFKA_BOOTSTRAP_SERVERS = "ajay:9092"          # Replace with your Kafka server
    KAFKA_TOPIC = "camera-stream"                       # Replace with your desired topic name
    INITIAL_FRAMES_PER_MINUTE = 30                    # Initial frames per minute (1 frame per second)
    
    # PC Webcam Configuration
    INCLUDE_PC_WEBCAM = True                            # Set to True to include PC webcam feed
    PC_WEBCAM_INDEX = 0                                 # Usually 0 for default camera, try 1, 2, etc. if needed
    
    # Create streamer instance
    streamer = MultiWebcamKafkaStreamer(
        ip_webcam_urls=IP_WEBCAM_URLS,
        kafka_bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        kafka_topic=KAFKA_TOPIC,
        initial_frames_per_minute=INITIAL_FRAMES_PER_MINUTE,
        include_pc_webcam=INCLUDE_PC_WEBCAM,
        pc_webcam_index=PC_WEBCAM_INDEX
    )
    
    # Start streaming in separate threads
    streaming_thread = threading.Thread(target=streamer.start_streaming)
    streaming_thread.daemon = True
    streaming_thread.start()
    
    # Wait a moment for cameras to initialize
    time.sleep(2)
    
    # Interactive control loop
    try:
        print("\n=== Multi-Camera Kafka Streamer ===")
        print("Available commands:")
        print("  fpm <number> - Change frames per minute (e.g., 'fpm 120' for 2 frames per second)")
        print("  status - Show current status of all cameras")
        print("  stop - Stop streaming")
        print("  help - Show this help message")
        print()
        
        while True:
            command = input("Enter command: ").strip().lower()
            
            if command == "stop":
                streamer.stop_streaming()
                break
            elif command == "status":
                status = streamer.get_status()
                print(f"\n--- Status ---")
                print(f"Total cameras configured: {status['total_cameras']}")
                print(f"Connected cameras: {status['connected_cameras']}")
                print(f"Frames per minute: {status['frames_per_minute']}")
                print(f"PC webcam enabled: {status['pc_webcam_enabled']}")
                print(f"Streaming: {status['streaming']}")
                print("\nCamera details:")
                for cam in status['cameras']:
                    cam_type = "📱 IP Camera" if cam['type'] == 'ip_camera' else "💻 PC Webcam"
                    connection_status = '✓ Connected' if cam['connected'] else '✗ Disconnected'
                    print(f"  {cam['name']}: {connection_status} - {cam_type} - {cam['url']}")
                print()
            elif command.startswith("fpm "):
                try:
                    new_fpm = int(command.split()[1])
                    streamer.set_frames_per_minute(new_fpm)
                    print(f"Frame rate changed to {new_fpm} frames per minute")
                except (IndexError, ValueError):
                    print("Invalid frames per minute value. Use: fpm <number>")
            elif command == "help":
                print("\nAvailable commands:")
                print("  fpm <number> - Change frames per minute")
                print("  status - Show current status")
                print("  stop - Stop streaming")
                print("  help - Show this help message")
            else:
                print("Unknown command. Type 'help' for available commands.")
                
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        streamer.stop_streaming()

if __name__ == "__main__":
    main()