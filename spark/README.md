# Spark

PySpark와 Kafka 커넥터를 모두 `4.0.2`로 고정한다. Java 17, Scala 2.13 커넥터를 사용하며 `local[1]` 한 프로세스로 실행한다.

`main.py`는 Kafka를 Structured Streaming으로 읽고 제한된 배치를 순차 검증·저장한다. `foreachBatch` 재실행 시 Redis Lua가 중복과 만료 연장을 막는다. 잘못된 입력은 내용 없이 거부 건수만 기록하고, Redis 장애는 배치를 실패시켜 재시도한다.

체크포인트는 별도 지속 볼륨에 저장한다. Spark UI, 다중 executor, master 서비스는 없다. 커넥터는 이미지 빌드 때 받아 런타임 Ivy 캐시에 포함한다.
