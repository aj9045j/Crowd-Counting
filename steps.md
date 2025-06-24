
## to start zookeeper
./bin/zookeeper-server-start.sh ./config/zookeeper.properties

## to start server
./bin/kafka-server-start.sh ./config/server.properties

## to create
bin/kafka-topics.sh --create \
  --topic crowd-frames \
  --bootstrap-server ajay:9092, deepak:9092\
  --partitions 3 \
  --replication-factor 2
  
## to delete
  bin/kafka-topics.sh --delete \
  --topic crowd-frames \
  --bootstrap-server node1-ip:9092, deepak:9092


# to clear logs
rm -rf /tmp/kafka-logs/crowd-frames-*

# to start producer
./bin/kafka-console-producer.sh \
  --topic crowd-frames \
  --bootstrap-server ajay:9092

# to start consumer
./bin/kafka-console-consumer.sh \
  --topic camera-stream \
  --from-beginning \
  --bootstrap-server  ajay:9092

## export
export HADOOP_CONF_DIR=/hadoop-3.4.0/etc/hadoop
export YARN_CONF_DIR=/hadoop-3.4.0/etc/hadoop


# to spark submit
spark-submit \
  --master yarn \
  --deploy-mode client \
  --name SmartCrowdMonitor-KafkaToHDFS \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1 \
  --conf spark.hadoop.fs.defaultFS=hdfs://ajay:8020 \
  --conf spark.sql.warehouse.dir=hdfs://ajay:8020/crowd_counting/warehouse \
  --conf spark.serializer=org.apache.spark.serializer.KryoSerializer \
  --conf spark.sql.adaptive.enabled=true \
  --conf spark.sql.streaming.metricsEnabled=true \
  --conf spark.yarn.appMasterEnv.PYSPARK_PYTHON=./ENV/venv/bin/python \
  --conf spark.executorEnv.PYSPARK_PYTHON=./ENV/venv/bin/python \
  --py-files wheels/*.whl,\
  --executor-memory 6G \
  --executor-cores 2 \
  --num-executors 10 \
  --driver-memory 6G \
  process_v2.py \
    --kafka-servers ajay:9092 \
    --kafka-topic crowd-frames \
    --hdfs-base-path hdfs://ajay:8020/crowd_counting \
    --checkpoint-path hdfs://ajay:8020/crowd_counting/checkpoints \
    --store-images True


## to create wheel
pip wheel -r requirements.txt -w wheels/


  sudo apt-get update
  sudo apt-get install python3-distutils


# working
spark-submit   --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0   --master yarn   --deploy-mode cluster   --num-executors 1   --executor-cores 2   --executor-memory 3g   --driver-memory 1g   --conf spark.executor.memoryOverhead=512m   process.py





1. create a code that take the camera feeds and then send that to the kafka 
2. create some load balancner that handle handle that and according to that it give node t o process the crows count using the yolo 
3. After that also in evry node run the yolo that process the crowd count and store them in hdfs frames or image in the jpg format with correct boundary box and crowd count in image.


sudo apt-get update
sudo apt-get install python3-tk


pip install PyQt5
