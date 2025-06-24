# 🏙️ Smart Crowd Monitoring System

A real-time, distributed crowd counting and monitoring system that processes multiple camera feeds using YOLO object detection, Apache Kafka for stream processing, and HDFS for data storage. The system provides real-time analytics and visualization capabilities for crowd monitoring applications.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Monitoring & Analytics](#monitoring--analytics)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## 🎯 Overview

The Smart Crowd Monitoring System is designed for real-time crowd analysis in various environments such as:
- **Public Spaces**: Parks, squares, and gathering areas
- **Transportation Hubs**: Airports, train stations, bus terminals
- **Event Venues**: Stadiums, concert halls, conference centers
- **Retail Spaces**: Shopping malls, stores, markets
- **Security Applications**: Surveillance and crowd control

The system leverages modern technologies to provide scalable, reliable, and real-time crowd counting capabilities.

## ✨ Features

### 🎥 Multi-Camera Support
- **IP Camera Integration**: Support for multiple IP cameras
- **Local Webcam Support**: Integration with local computer webcams
- **Dynamic Camera Management**: Hot-plugging and reconnection capabilities
- **Load Balancing**: Distributed processing across multiple nodes

### 🤖 AI-Powered Detection
- **YOLO v8 Integration**: State-of-the-art object detection
- **Real-time Processing**: Sub-second response times
- **Bounding Box Visualization**: Visual annotations on processed frames
- **Crowd Density Analysis**: Accurate people counting algorithms

### 📊 Real-time Analytics
- **Live Dashboard**: Interactive web-based monitoring interface
- **Performance Metrics**: Processing time, FPS, and accuracy tracking
- **Camera-specific Analytics**: Individual camera performance monitoring
- **Historical Data**: Time-series analysis and trending

### 🚀 Scalable Architecture
- **Apache Kafka**: Distributed streaming platform
- **HDFS Integration**: Scalable data storage
- **Multi-node Processing**: Horizontal scaling capabilities
- **Fault Tolerance**: Automatic recovery and redundancy

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Camera Feeds  │    │   IP Cameras    │    │  Local Webcams  │
│                 │    │                 │    │                 │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────▼─────────────┐
                    │    Camera Feed Producer   │
                    │     (camera_feed.py)      │
                    └─────────────┬─────────────┘
                                 │
                    ┌─────────────▼─────────────┐
                    │      Apache Kafka         │
                    │   (crowd-frames topic)    │
                    └─────────────┬─────────────┘
                                 │
                    ┌─────────────▼─────────────┐
                    │   Crowd Counting Consumer │
                    │   (kafka_consumer.py)     │
                    └─────────────┬─────────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
┌─────────▼─────────┐  ┌─────────▼─────────┐  ┌─────────▼─────────┐
│   YOLO Detection  │  │  HDFS Storage     │  │  Real-time Plot   │
│                   │  │                   │  │                   │
└───────────────────┘  └───────────────────┘  └───────────────────┘
```

### Core Components

1. **Camera Feed Producer** (`camera_feed.py`)
   - Manages multiple camera connections
   - Streams video frames to Kafka
   - Handles camera failures and reconnections

2. **Crowd Counting Consumer** (`kafka_consumer.py`)
   - Processes incoming video frames
   - Performs YOLO-based crowd detection
   - Stores annotated frames in HDFS
   - Generates real-time analytics

3. **Real-time Dashboard** (`multi_camera_crowd_dashboard.html`)
   - Interactive web interface
   - Live performance monitoring
   - Camera-specific analytics

## 📋 Prerequisites

### System Requirements
- **OS**: Linux (Ubuntu 18.04+ recommended)
- **Python**: 3.8 or higher
- **Memory**: Minimum 8GB RAM (16GB+ recommended)
- **Storage**: 50GB+ available space
- **Network**: Stable internet connection for IP cameras

### Required Software
- **Apache Kafka** (2.13+)
- **Apache Zookeeper** (3.6+)
- **Apache Hadoop HDFS** (3.4+)
- **Apache Spark** (3.5+) (optional, for advanced processing)

## 🚀 Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd Crowd-Counting
```

### 2. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Download YOLO Model
```bash
# The yolov8n.pt model should be automatically downloaded
# If not, download it manually:
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt
```

### 5. Setup Apache Kafka
```bash
# Download and extract Kafka
wget https://downloads.apache.org/kafka/3.5.1/kafka_2.13-3.5.1.tgz
tar -xzf kafka_2.13-3.5.1.tgz
cd kafka_2.13-3.5.1

# Start Zookeeper
./bin/zookeeper-server-start.sh ./config/zookeeper.properties

# In a new terminal, start Kafka
./bin/kafka-server-start.sh ./config/server.properties

# Create the required topic
./bin/kafka-topics.sh --create \
  --topic crowd-frames \
  --bootstrap-server localhost:9092 \
  --partitions 3 \
  --replication-factor 1
```

### 6. Setup HDFS (Optional)
```bash
# Configure HDFS environment
export HADOOP_CONF_DIR=/path/to/hadoop/etc/hadoop
export YARN_CONF_DIR=/path/to/hadoop/etc/hadoop
```

## ⚙️ Configuration

### Camera Configuration
Edit the camera URLs in `camera_feed.py`:

```python
# Example configuration
ip_webcam_urls = [
    "http://192.168.1.100:8080/video",
    "http://192.168.1.101:8080/video",
    "rtsp://192.168.1.102:554/stream1"
]

# Include local webcam
include_pc_webcam = True
pc_webcam_index = 0
```

### Kafka Configuration
```python
# Kafka settings
kafka_bootstrap_servers = "localhost:9092"
kafka_topic = "crowd-frames"
```

### HDFS Configuration
```python
# HDFS settings
hdfs_url = "http://localhost:9870"
hdfs_user = "hdfs"
base_path = "/crowd_counting"
```

## 🎮 Usage

### 1. Start the Camera Producer
```bash
python camera_feed.py
```

### 2. Start the Crowd Counting Consumer
```bash
python kafka_consumer.py
```

### 3. Access the Dashboard
Open `multi_camera_crowd_dashboard.html` in your web browser.

### 4. Monitor Performance
The system provides real-time metrics including:
- Processing time per frame
- Crowd count per camera
- FPS (Frames Per Second)
- System performance statistics

## 📚 API Documentation

### Camera Feed Producer API

#### `MultiWebcamKafkaStreamer`
Main class for managing camera feeds and Kafka streaming.

**Methods:**
- `connect_cameras()`: Establish connections to all cameras
- `start_streaming()`: Begin streaming frames to Kafka
- `stop_streaming()`: Stop all camera streams
- `set_frames_per_minute(rate)`: Adjust streaming rate

### Crowd Counting Consumer API

#### `CrowdCountingPipeline`
Main class for processing Kafka messages and performing crowd detection.

**Methods:**
- `process_kafka_messages()`: Main processing loop
- `detect_and_count_crowd(frame)`: Perform YOLO detection
- `save_to_hdfs(frame, metadata)`: Store processed frames
- `start_pipeline()`: Initialize and start the pipeline

## 📊 Monitoring & Analytics

### Real-time Metrics
- **Processing Time**: Time taken to process each frame
- **Crowd Count**: Number of people detected per frame
- **FPS**: Frames processed per second
- **Camera Status**: Connection status and health

### Performance Optimization
- **Batch Processing**: Efficient handling of multiple frames
- **Memory Management**: Optimized buffer usage
- **Network Optimization**: Compressed frame transmission
- **Load Balancing**: Distributed processing across nodes

## 🔧 Troubleshooting

### Common Issues

#### Camera Connection Problems
```bash
# Check camera accessibility
curl -I http://camera-ip:port/video

# Verify network connectivity
ping camera-ip
```

#### Kafka Connection Issues
```bash
# Check Kafka status
./bin/kafka-topics.sh --list --bootstrap-server localhost:9092

# Verify topic exists
./bin/kafka-topics.sh --describe --topic crowd-frames --bootstrap-server localhost:9092
```

#### YOLO Model Issues
```bash
# Verify model file exists
ls -la yolov8n.pt

# Check model file integrity
file yolov8n.pt
```

### Performance Tuning

#### Memory Optimization
```python
# Adjust buffer sizes in camera_feed.py
max_request_size=15728640  # 15MB
buffer_memory=33554432     # 32MB
```

#### Processing Rate Adjustment
```python
# Modify frames per minute
streamer.set_frames_per_minute(30)  # 30 FPM for better performance
```

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
python -m pytest tests/

# Code formatting
black .
flake8 .
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Ultralytics**: For the YOLO v8 implementation
- **Apache Kafka**: For the streaming platform
- **OpenCV**: For computer vision capabilities
- **Plotly**: For interactive visualizations

## 📞 Support

For support and questions:
- Create an issue on GitHub
- Check the troubleshooting section
- Review the documentation

---

**Note**: This system is designed for research and development purposes. For production deployment, additional security measures and error handling should be implemented.
 
