import json
import base64
import cv2
import numpy as np
from kafka import KafkaConsumer
from ultralytics import YOLO
import threading
import queue
import time
import logging
from hdfs import InsecureClient
from collections import deque, defaultdict
import os
import sys
from datetime import datetime, timedelta

# Simple plotting libraries (lightweight alternatives)
try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    import plotly.offline as pyo
    PLOTTING_BACKEND = 'plotly'
except ImportError:
    try:
        import matplotlib.pyplot as plt
        import matplotlib
        matplotlib.use('Agg')  # Non-interactive backend
        PLOTTING_BACKEND = 'matplotlib'
    except ImportError:
        PLOTTING_BACKEND = 'text'

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleRealTimePlotter:
    """
    Enhanced real-time plotter with camera-specific visualization
    """
    def __init__(self, max_points=100):
        self.max_points = max_points
        
        # Camera-specific data storage
        self.camera_data = defaultdict(lambda: {
            'processing_times': deque(maxlen=max_points),
            'crowd_counts': deque(maxlen=max_points),
            'timestamps': deque(maxlen=max_points),
            'total_frames': 0,
            'start_time': time.time()
        })
        
        # Overall performance metrics
        self.overall_stats = {
            'total_frames': 0,
            'start_time': time.time(),
            'last_update': time.time(),
            'active_cameras': set()
        }
        
        # Color mapping for cameras
        self.camera_colors = [
            'lime', 'cyan', 'orange', 'magenta', 'yellow', 'red', 
            'blue', 'green', 'purple', 'pink', 'brown', 'gray'
        ]
        
        logger.info(f"📊 Using plotting backend: {PLOTTING_BACKEND}")
    
    def add_data_point(self, processing_time, crowd_count, camera_id, timestamp=None):
        """Add new data point for plotting with camera ID"""
        if timestamp is None:
            timestamp = datetime.now()
        
        # Add to camera-specific data
        cam_data = self.camera_data[camera_id]
        cam_data['processing_times'].append(processing_time)
        cam_data['crowd_counts'].append(crowd_count)
        cam_data['timestamps'].append(timestamp)
        cam_data['total_frames'] += 1
        
        # Update overall stats
        self.overall_stats['total_frames'] += 1
        self.overall_stats['active_cameras'].add(camera_id)
        
        # Update plots every 10 seconds
        if time.time() - self.overall_stats['last_update'] > 10:
            self.update_plots()
            self.overall_stats['last_update'] = time.time()
    
    def get_camera_color(self, camera_id):
        """Get consistent color for camera"""
        camera_list = sorted(list(self.overall_stats['active_cameras']))
        try:
            idx = camera_list.index(camera_id)
            return self.camera_colors[idx % len(self.camera_colors)]
        except ValueError:
            return 'gray'
    
    def update_plots(self):
        """Update plots based on available backend"""
        if PLOTTING_BACKEND == 'plotly':
            self._update_plotly()
        elif PLOTTING_BACKEND == 'matplotlib':
            self._update_matplotlib()
        else:
            self._update_text()
    
    def _update_plotly(self):
        """Create interactive web-based plots using Plotly with camera separation"""
        try:
            if not self.camera_data:
                return
            
            # Filter cameras with sufficient data
            active_cameras = [cam_id for cam_id, data in self.camera_data.items() 
                            if len(data['processing_times']) >= 2]
            
            if not active_cameras:
                return
            
            # Create subplots - 2x2 grid
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=('Processing Time by Camera', 'Crowd Count by Camera', 
                              'FPS by Camera', 'Camera Statistics'),
                specs=[[{"secondary_y": False}, {"secondary_y": False}],
                       [{"secondary_y": False}, {"type": "table"}]]
            )
            
            # Process each camera
            for i, camera_id in enumerate(sorted(active_cameras)):
                cam_data = self.camera_data[camera_id]
                color = self.get_camera_color(camera_id)
                
                times_list = list(cam_data['processing_times'])
                counts_list = list(cam_data['crowd_counts'])
                fps_list = [1.0/t if t > 0 else 0 for t in times_list]
                
                # Processing Time plot
                fig.add_trace(
                    go.Scatter(
                        y=times_list, 
                        mode='lines+markers', 
                        name=f'Camera {camera_id} - Processing Time',
                        line=dict(color=color),
                        legendgroup=f'camera_{camera_id}'
                    ),
                    row=1, col=1
                )
                
                # Crowd Count plot
                fig.add_trace(
                    go.Scatter(
                        y=counts_list, 
                        mode='lines+markers', 
                        name=f'Camera {camera_id} - Crowd Count',
                        line=dict(color=color, dash='dot'),
                        legendgroup=f'camera_{camera_id}'
                    ),
                    row=1, col=2
                )
                
                # FPS plot
                fig.add_trace(
                    go.Scatter(
                        y=fps_list, 
                        mode='lines+markers', 
                        name=f'Camera {camera_id} - FPS',
                        line=dict(color=color, dash='dash'),
                        legendgroup=f'camera_{camera_id}'
                    ),
                    row=2, col=1
                )
            
            # Create comprehensive statistics table
            stats_data = [['Camera ID', 'Frames', 'Avg Processing', 'Avg Crowd', 'Avg FPS', 'Max Crowd', 'Last Update']]
            
            for camera_id in sorted(active_cameras):
                cam_data = self.camera_data[camera_id]
                times_list = list(cam_data['processing_times'])
                counts_list = list(cam_data['crowd_counts'])
                fps_list = [1.0/t if t > 0 else 0 for t in times_list]
                
                avg_processing = np.mean(times_list) if times_list else 0
                avg_crowd = np.mean(counts_list) if counts_list else 0
                avg_fps = np.mean(fps_list) if fps_list else 0
                max_crowd = max(counts_list) if counts_list else 0
                last_update = cam_data['timestamps'][-1].strftime('%H:%M:%S') if cam_data['timestamps'] else 'N/A'
                
                stats_data.append([
                    str(camera_id),
                    str(cam_data['total_frames']),
                    f'{avg_processing:.3f}s',
                    f'{avg_crowd:.1f}',
                    f'{avg_fps:.1f}',
                    str(max_crowd),
                    last_update
                ])
            
            # Add overall statistics
            total_uptime = time.time() - self.overall_stats['start_time']
            stats_data.extend([
                ['---', '---', '---', '---', '---', '---', '---'],
                ['OVERALL', str(self.overall_stats['total_frames']), 
                 f'{total_uptime:.0f}s uptime', f'{len(active_cameras)} cameras', 
                 '', '', datetime.now().strftime('%H:%M:%S')]
            ])
            
            fig.add_trace(
                go.Table(
                    header=dict(
                        values=stats_data[0], 
                        fill_color='darkblue',
                        font=dict(color='white', size=12, family='DejaVu Sans, Arial, sans-serif')
                    ),
                    cells=dict(
                        values=list(zip(*stats_data[1:])), 
                        fill_color='lightblue',
                        font=dict(color='#222', size=11, family='DejaVu Sans, Arial, sans-serif')
                    )
                ),
                row=2, col=2
            )
            
            # Update layout
            fig.update_layout(
                title=f'Multi-Camera Crowd Counting Dashboard - {len(active_cameras)} Active Cameras',
                height=900,
                template='plotly_dark',
                showlegend=True,
                legend=dict(
                    orientation="v",
                    yanchor="top",
                    y=1,
                    xanchor="left",
                    x=1.02
                )
            )
            
            # Update axis labels
            fig.update_xaxes(title_text="Frame Index", row=1, col=1)
            fig.update_yaxes(title_text="Processing Time (s)", row=1, col=1)
            fig.update_xaxes(title_text="Frame Index", row=1, col=2)
            fig.update_yaxes(title_text="Crowd Count", row=1, col=2)
            fig.update_xaxes(title_text="Frame Index", row=2, col=1)
            fig.update_yaxes(title_text="FPS", row=2, col=1)
            
            # Save to HTML file
            filename = 'multi_camera_crowd_dashboard.html'
            pyo.plot(fig, filename=filename, auto_open=False)
            logger.info(f"📊 Multi-camera dashboard updated: {filename}")
            
        except Exception as e:
            logger.error(f"Plotly update error: {e}")
    
    def _update_matplotlib(self):
        """Create static plots using matplotlib with camera separation"""
        try:
            active_cameras = [cam_id for cam_id, data in self.camera_data.items() 
                            if len(data['processing_times']) >= 2]
            
            if not active_cameras:
                return
            
            # Create figure with subplots
            fig, axes = plt.subplots(2, 2, figsize=(15, 10))
            fig.suptitle(f'Multi-Camera Crowd Counting Analytics - {len(active_cameras)} Cameras', fontsize=16)
            
            # Color map for cameras
            colors = plt.cm.tab10(np.linspace(0, 1, len(active_cameras)))
            
            for i, camera_id in enumerate(sorted(active_cameras)):
                cam_data = self.camera_data[camera_id]
                color = colors[i]
                
                times_list = list(cam_data['processing_times'])
                counts_list = list(cam_data['crowd_counts'])
                fps_list = [1.0/t if t > 0 else 0 for t in times_list]
                
                # Processing time
                axes[0,0].plot(times_list, color=color, marker='o', markersize=3, 
                              label=f'Camera {camera_id}', linewidth=2)
                
                # Crowd count
                axes[0,1].plot(counts_list, color=color, marker='s', markersize=3, 
                              label=f'Camera {camera_id}', linewidth=2)
                
                # FPS
                axes[1,0].plot(fps_list, color=color, marker='^', markersize=3, 
                              label=f'Camera {camera_id}', linewidth=2)
            
            # Configure subplots
            axes[0,0].set_title('Processing Time by Camera')
            axes[0,0].set_ylabel('Processing Time (s)')
            axes[0,0].set_xlabel('Frame Index')
            axes[0,0].grid(True, alpha=0.3)
            axes[0,0].legend()
            
            axes[0,1].set_title('Crowd Count by Camera')
            axes[0,1].set_ylabel('Crowd Count')
            axes[0,1].set_xlabel('Frame Index')
            axes[0,1].grid(True, alpha=0.3)
            axes[0,1].legend()
            
            axes[1,0].set_title('FPS by Camera')
            axes[1,0].set_ylabel('FPS')
            axes[1,0].set_xlabel('Frame Index')
            axes[1,0].grid(True, alpha=0.3)
            axes[1,0].legend()
            
            # Statistics text
            axes[1,1].axis('off')
            axes[1,1].set_title('Camera Statistics')
            
            stats_text = [f"📊 MULTI-CAMERA STATISTICS"]
            stats_text.append(f"Active Cameras: {len(active_cameras)}")
            stats_text.append(f"Total Frames: {self.overall_stats['total_frames']}")
            
            uptime = time.time() - self.overall_stats['start_time']
            stats_text.append(f"System Uptime: {timedelta(seconds=int(uptime))}")
            stats_text.append("")
            
            # Per camera stats
            for camera_id in sorted(active_cameras):
                cam_data = self.camera_data[camera_id]
                times_list = list(cam_data['processing_times'])
                counts_list = list(cam_data['crowd_counts'])
                
                avg_processing = np.mean(times_list) if times_list else 0
                avg_crowd = np.mean(counts_list) if counts_list else 0
                max_crowd = max(counts_list) if counts_list else 0
                
                stats_text.append(f"Camera {camera_id}:")
                stats_text.append(f"  Frames: {cam_data['total_frames']}")
                stats_text.append(f"  Avg Processing: {avg_processing:.3f}s")
                stats_text.append(f"  Avg Crowd: {avg_crowd:.1f}")
                stats_text.append(f"  Max Crowd: {max_crowd}")
                stats_text.append("")
            
            # Display stats
            for i, text in enumerate(stats_text):
                y_pos = 0.95 - i * 0.05
                if y_pos < 0:
                    break
                weight = 'bold' if text.startswith('📊') or text.startswith('Camera') else 'normal'
                axes[1,1].text(0.05, y_pos, text, fontsize=9, weight=weight, 
                              transform=axes[1,1].transAxes, family='monospace')
            
            plt.tight_layout()
            filename = 'multi_camera_crowd_dashboard.png'
            plt.savefig(filename, dpi=120, bbox_inches='tight')
            plt.close()
            logger.info(f"📊 Multi-camera dashboard saved: {filename}")
            
        except Exception as e:
            logger.error(f"Matplotlib update error: {e}")
    
    def _update_text(self):
        """Enhanced text-based statistics output with camera separation"""
        if not self.camera_data:
            return
        
        active_cameras = list(self.camera_data.keys())
        uptime = time.time() - self.overall_stats['start_time']
        
        print("\n" + "="*70)
        print("📊 MULTI-CAMERA CROWD COUNTING STATISTICS")
        print("="*70)
        print(f"System Uptime: {timedelta(seconds=int(uptime))}")
        print(f"Active Cameras: {len(active_cameras)}")
        print(f"Total Frames Processed: {self.overall_stats['total_frames']}")
        print(f"Last Update: {datetime.now().strftime('%H:%M:%S')}")
        print("-"*70)
        
        for camera_id in sorted(active_cameras):
            cam_data = self.camera_data[camera_id]
            times_list = list(cam_data['processing_times'])
            counts_list = list(cam_data['crowd_counts'])
            
            if not times_list:
                continue
                
            avg_processing = np.mean(times_list)
            avg_crowd = np.mean(counts_list)
            avg_fps = 1.0 / avg_processing if avg_processing > 0 else 0
            max_crowd = max(counts_list)
            current_crowd = counts_list[-1] if counts_list else 0
            
            print(f"📹 CAMERA ID: {camera_id}")
            print(f"   Frames Processed: {cam_data['total_frames']}")
            print(f"   Average Processing Time: {avg_processing:.3f}s")
            print(f"   Average FPS: {avg_fps:.1f}")
            print(f"   Average Crowd Count: {avg_crowd:.1f}")
            print(f"   Current Crowd Count: {current_crowd}")
            print(f"   Maximum Crowd Count: {max_crowd}")
            
            if cam_data['timestamps']:
                last_update = cam_data['timestamps'][-1].strftime('%H:%M:%S')
                print(f"   Last Update: {last_update}")
            print("-"*35)
        
        print("="*70)

class CrowdCountingPipeline:
    def __init__(self, kafka_config, hdfs_config, model_path='yolov8n.pt'):
        """Initialize the enhanced crowd counting pipeline with multi-camera support"""
        self.kafka_config = kafka_config
        self.hdfs_config = hdfs_config
        
        # Initialize YOLOv8 model
        self.model = YOLO(model_path)
        
        # Initialize HDFS client
        self.hdfs_client = InsecureClient(
            hdfs_config['namenode_url'], 
            user=hdfs_config.get('user', 'ajay')
        )
        
        # Initialize enhanced plotter with camera support
        self.plotter = SimpleRealTimePlotter(max_points=200)
        
        # Control flags
        self.running = False
        
        # Enhanced performance tracking per camera
        self.camera_stats = defaultdict(lambda: {
            'total_frames': 0,
            'total_processing_time': 0,
            'start_time': time.time(),
            'last_crowd_count': 0
        })
        
        # Initialize HDFS directories
        self._initialize_hdfs_directories()

    def _initialize_hdfs_directories(self):
        """Initialize HDFS directories for storing results"""
        try:
            base_path = self.hdfs_config['base_path']
            images_path = f"{base_path}/images"
            metadata_path = f"{base_path}/metadata"
            
            self.hdfs_config['images_path'] = images_path
            self.hdfs_config['metadata_path'] = metadata_path
            
            # Create directories
            for path in [base_path, images_path, metadata_path]:
                try:
                    self.hdfs_client.makedirs(path)
                    logger.info(f"✅ Created HDFS directory: {path}")
                except Exception as e:
                    if "already exists" in str(e).lower():
                        logger.info(f"✅ HDFS directory exists: {path}")
                    else:
                        logger.warning(f"⚠️  HDFS directory issue: {path} - {e}")
            
        except Exception as e:
            logger.error(f"❌ HDFS initialization error: {e}")

    def decode_frame_data(self, frame_data_b64):
        """Decode base64 frame data to OpenCV image"""
        try:
            frame_bytes = base64.b64decode(frame_data_b64)
            nparr = np.frombuffer(frame_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            return frame
        except Exception as e:
            logger.error(f"Error decoding frame: {e}")
            return None

    def detect_and_count_crowd(self, frame):
        """Perform crowd detection and counting using YOLOv8"""
        try:
            results = self.model(frame)
            crowd_count = 0
            detection_boxes = []
            
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        if int(box.cls[0]) == 0:  # Person class
                            crowd_count += 1
                            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                            confidence = box.conf[0].cpu().numpy()
                            
                            detection_boxes.append({
                                'bbox': [int(x1), int(y1), int(x2), int(y2)],
                                'confidence': float(confidence)
                            })
            
            annotated_frame = self.draw_annotations(frame.copy(), detection_boxes, crowd_count)
            return annotated_frame, crowd_count, detection_boxes
            
        except Exception as e:
            logger.error(f"Error in crowd detection: {e}")
            return frame, 0, []

    def draw_annotations(self, frame, detection_boxes, crowd_count):
        """Draw bounding boxes and crowd count on frame"""
        # Draw bounding boxes
        for detection in detection_boxes:
            bbox = detection['bbox']
            confidence = detection['confidence']
            
            cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0, 255, 0), 2)
            label = f"Person: {confidence:.2f}"
            cv2.putText(frame, label, (bbox[0], bbox[1] - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        # Draw crowd count
        count_text = f"Crowd Count: {crowd_count}"
        cv2.putText(frame, count_text, (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
        # Add timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, timestamp, (10, frame.shape[0] - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return frame

    def save_to_hdfs(self, annotated_frame, metadata):
        """Save results to HDFS"""
        try:
            timestamp = metadata.get('timestamp', 'unknown_time')
            camera_id = metadata.get('camera_id', 'unknown')
            crowd_count = metadata.get('crowd_count', 0)
            
            # Create filename
            timestamp_clean = timestamp.replace(':', '-').replace('.', '-').replace(' ', '_')
            base_filename = f"camera_{camera_id}_{timestamp_clean}_{crowd_count}_people"
            
            # Save image
            image_path = f"{self.hdfs_config['images_path']}/{base_filename}.jpg"
            encode_success, buffer = cv2.imencode('.jpg', annotated_frame)
            
            if encode_success:
                with self.hdfs_client.write(image_path, overwrite=True) as writer:
                    writer.write(buffer.tobytes())
            
            # Save metadata
            metadata_path = f"{self.hdfs_config['metadata_path']}/{base_filename}.json"
            metadata_json = json.dumps(metadata, indent=2, default=str)
            
            with self.hdfs_client.write(metadata_path, overwrite=True) as writer:
                writer.write(metadata_json.encode('utf-8'))
            
            return True
            
        except Exception as e:
            logger.error(f"HDFS save error: {e}")
            return False

    def process_kafka_messages(self):
        """Process messages from Kafka consumer with enhanced camera tracking"""
        consumer = KafkaConsumer(
            self.kafka_config['topic'],
            group_id='yolo-cluster',
            bootstrap_servers=self.kafka_config['bootstrap_servers'],
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='latest'
        )
        
        logger.info("🚀 Starting Kafka consumer with multi-camera visualization...")
        
        for message in consumer:
            if not self.running:
                break
                
            try:
                data = message.value
                timestamp = data.get('timestamp')
                camera_id = data.get('camera_id', 'unknown')
                frame_data = data.get('frame_data')
                
                # Record processing start time
                start_time = time.time()
                
                # Decode and process frame
                frame = self.decode_frame_data(frame_data)
                if frame is None:
                    continue
                
                # Perform crowd detection
                annotated_frame, crowd_count, detection_boxes = self.detect_and_count_crowd(frame)
                
                # Calculate processing time
                processing_time = time.time() - start_time
                
                # Add data point to plotter with camera ID
                self.plotter.add_data_point(processing_time, crowd_count, camera_id)
                
                # Update camera-specific stats
                cam_stats = self.camera_stats[camera_id]
                cam_stats['total_frames'] += 1
                cam_stats['total_processing_time'] += processing_time
                cam_stats['last_crowd_count'] = crowd_count
                
                # Prepare enhanced metadata
                metadata = {
                    'timestamp': timestamp,
                    'camera_id': camera_id,
                    'crowd_count': crowd_count,
                    'processing_time': processing_time,
                    'detection_boxes': detection_boxes,
                    'processed_at': datetime.now().isoformat(),
                    'frame_number': cam_stats['total_frames'],
                    'camera_avg_processing_time': cam_stats['total_processing_time'] / cam_stats['total_frames']
                }
                
                # Save to HDFS (async)
                threading.Thread(
                    target=self.save_to_hdfs, 
                    args=(annotated_frame, metadata),
                    daemon=True
                ).start()
                
                # Enhanced logging every 10 frames per camera
                if cam_stats['total_frames'] % 10 == 0:
                    avg_processing_time = cam_stats['total_processing_time'] / cam_stats['total_frames']
                    logger.info(f"📹 Camera {camera_id} | "
                              f"Frames: {cam_stats['total_frames']} | "
                              f"Avg: {avg_processing_time:.3f}s | "
                              f"Current: {crowd_count} people | "
                              f"FPS: {1/processing_time:.1f}")
                
            except Exception as e:
                logger.error(f"Error processing message: {e}")
        
        consumer.close()

    def start_pipeline(self):
        """Start the enhanced pipeline with multi-camera support"""
        self.running = True
        
        logger.info("🎬 Starting Enhanced Multi-Camera Crowd Counting Pipeline...")
        logger.info(f"📊 Visualization: {PLOTTING_BACKEND}")
        
        # Start Kafka consumer in separate thread
        kafka_thread = threading.Thread(target=self.process_kafka_messages)
        kafka_thread.daemon = True
        kafka_thread.start()
        
        # Run main loop with enhanced camera tracking
        try:
            while self.running:
                active_cameras = list(self.camera_stats.keys())
                if active_cameras:
                    total_frames = sum(stats['total_frames'] for stats in self.camera_stats.values())
                    uptime = time.time() - min(stats['start_time'] for stats in self.camera_stats.values())
                    
                    # Create status line showing all cameras
                    camera_status = []
                    for cam_id in sorted(active_cameras):
                        stats = self.camera_stats[cam_id]
                        avg_time = stats['total_processing_time'] / stats['total_frames'] if stats['total_frames'] > 0 else 0
                        camera_status.append(f"Cam{cam_id}:{stats['last_crowd_count']}p({avg_time:.2f}s)")
                    
                    status_line = f"📊 {len(active_cameras)} cameras | Total frames: {total_frames} | " + " | ".join(camera_status)
                    print(f"\r{status_line[:150]}...", end='', flush=True)
                
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("\n🛑 Stopping multi-camera pipeline...")
            self.running = False

def main():
    """Main function to run the enhanced multi-camera crowd counting pipeline"""
    # Configuration
    kafka_config = {
        'bootstrap_servers': ['ajay:9092'],
        'topic': 'camera-stream'
    }
    
    hdfs_config = {
        'namenode_url': 'http://ajay:9870',
        'base_path': '/crowd_counting_results',
        'user': 'ajay'
    }
    
    # Initialize and start pipeline
    try:
        pipeline = CrowdCountingPipeline(kafka_config, hdfs_config)
        
        # Show available plotting options
        if PLOTTING_BACKEND == 'plotly':
            logger.info("📊 Multi-camera Plotly dashboard will be saved as 'multi_camera_crowd_dashboard.html'")
        elif PLOTTING_BACKEND == 'matplotlib':
            logger.info("📊 Multi-camera Matplotlib dashboard will be saved as 'multi_camera_crowd_dashboard.png'")
        else:
            logger.info("📊 Using enhanced text output for multi-camera statistics")
        
        pipeline.start_pipeline()
        
    except Exception as e:
        logger.error(f"❌ Failed to start pipeline: {e}")
        logger.info("💡 Check HDFS permissions and Kafka connectivity")
        logger.info("💡 Install plotting libraries: pip install plotly")

if __name__ == "__main__":
    main()