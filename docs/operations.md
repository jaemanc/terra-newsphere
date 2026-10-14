# 단일 OCI ARM64 서버 운영

## 배포 전 준비

대상은 OCI A1 ARM64, Ubuntu 26.04 LTS, 단일 노드 K3s다. VM의 실제 CPU/RAM/디스크를 확인해 설정을 조정한다. 현재 컨테이너 limit는 API 256MiB, 수집기 256MiB, Redis 384MiB, Kafka 1GiB, Spark 2GiB, frontend 128MiB다. 이는 초기 설정값이며 K3s·OS·페이지 캐시와 이미지 빌드 작업의 추가 공간/메모리가 필요하다. 실제 서버에서 프로파일링하기 전 용량 보장을 의미하지 않는다.

이미지를 다른 ARM64 빌드 머신이나 CI에서 준비하면 서버의 빌드 부하를 줄일 수 있다. 아래는 로컬 태그를 준비하는 예다. 패키지 설치와 지도 가공 후 실행한다.

```sh
docker buildx build --platform linux/arm64 --load -t terra-newsphere-api:0.1.0 --build-arg ROLE=api -f deploy/docker/python.Dockerfile .
docker buildx build --platform linux/arm64 --load -t terra-newsphere-collector:0.1.0 --build-arg ROLE=collector -f deploy/docker/python.Dockerfile .
docker buildx build --platform linux/arm64 --load -t terra-newsphere-spark:0.1.0 -f spark/Dockerfile .
docker buildx build --platform linux/arm64 --load -t terra-newsphere-frontend:0.1.0 -f frontend/Dockerfile .
docker save -o terra-images.tar terra-newsphere-api:0.1.0 terra-newsphere-collector:0.1.0 terra-newsphere-spark:0.1.0 terra-newsphere-frontend:0.1.0
# 위 tar를 VM으로 전달한 후 실행
sudo k3s ctr images import terra-images.tar
```

배포 이미지 태그는 고정하며 Spark와 Kafka 커넥터는 4.0.2다. 기본 이미지의 ARM64 manifest와 Python/Java 네이티브 의존성은 실제 ARM64 빌드·실행으로 확인한다. 로컬 x86 실행 성공을 ARM64 검증으로 대신하지 않는다. apt의 Java 보안 패키지는 빌드 시 저장소 버전을 사용하므로 실제 릴리스 이미지는 digest로도 고정해야 한다.

## 도메인·TLS와 K3s

`deploy/k3s/ingress.yaml`의 `news.example.com`을 실제 도메인으로 변경한다. TLS 인증서와 키를 준비하고 `terra-tls` Secret을 해당 namespace에 만든다. 비밀 파일은 저장소에 넣지 않는다.

```sh
kubectl create namespace terra-newsphere
kubectl -n terra-newsphere create secret tls terra-tls --cert=/path/to/fullchain.pem --key=/path/to/privkey.pem
kubectl apply -k deploy/k3s
kubectl -n terra-newsphere wait --for=condition=complete job/kafka-init --timeout=180s
kubectl -n terra-newsphere get pods
```

K3s 기본 Traefik과 local-path StorageClass를 전제로 한다. ingress에는 HTTPS 설정을 두고, HTTP에서 HTTPS로의 리다이렉트와 HSTS는 포함된 Traefik Middleware에서 설정한다. OCI 방화벽은 웹 80/443과 필요한 관리 접근만 열고 Kafka/Redis 포트는 열지 않는다. NetworkPolicy는 기본 ingress/egress를 거부하고 필요한 서비스 연결만 허용한다. 모든 웹/API는 Traefik→nginx를 거쳐 호출 제한을 적용한다. Redis ACL Secret과 TLS 준비는 [보안 문서](security.md)를 따른다. 설치한 CNI가 NetworkPolicy를 실제 적용하는지도 확인한다.

RSS는 `collector/rss-policy.json`과 `RSS_URLS`에 운영자가 확인한 피드를 설정한다. 피드별 `event_locations`는 해당 피드가 특정 보도 지역을 보장할 때만 지정하고 출판사 위치로 대체하지 않는다. 썸네일은 `allow_thumbnails: true`로 사용 권한을 확인한 피드에만 허용한다. 현재 별도 유료 API 키는 필요 없다. 추가 키는 Kubernetes Secret/env로 전달한다.

## 보존·재시작

- Redis RDB/AOF와 뉴스 백업은 비활성이다. Redis 재시작 시 뉴스는 사라진다. Kafka의 남아 있는 입력은 원래 수집 시각을 사용해 다시 넣을 수 있다.
- Kafka 로그는 토픽 기준 24시간 또는 512MiB 한도이며 로그 PVC는 2GiB다. 크기 한도는 파티션별이고 현재 파티션은 한 개다. 세그먼트 정리 지연과 OS 디스크 여유를 고려한다.
- Spark checkpoint PVC는 1GiB다. 처리기는 하나만 실행하고 `Recreate` 교체로 같은 체크포인트를 동시에 쓰는 일을 막는다. 현재 stateful aggregation을 두지 않아 체크포인트는 주로 offset/commit 정보다. 복구에 필요한 현재 파일을 임의 삭제하지 않는다.
- PySpark가 Redis 장애로 실패하면 컨테이너 재시작 후 같은 체크포인트에서 재시도한다. Kafka 입력이 먼저 삭제됐다면 `failOnDataLoss=true`로 조용한 누락 대신 실패한다. 운영자가 수집 복구 범위를 결정한 후에만 체크포인트를 재설정한다.
- 뉴스 전체의 엄격한 삭제 범위에는 Kafka 로그·스냅샷, 체크포인트 metadata, 컨테이너 로그와 호스트 백업도 포함될 수 있다. 데이터 본문을 로그에 남기지 않으며 VM 전체 스냅샷을 뉴스 백업처럼 유지하지 않는다. 정적 지리와 앱 코드만 별도 보관한다.
- 단일 VM 장애는 전체 서비스 중단이다. 이 구성에는 복제나 고가용성 보장이 없다.

K3s/컨테이너 로그 크기도 제한한다. Kafka·체크포인트 디스크와 Redis 사용량, API 지연을 기본 CLI로 확인하고, 측정 결과가 필요할 때만 모니터링 도구를 추가한다.

## 검증 기록

실제로 수행한 검증 결과는 `docs/implementation-progress.md`에 기록한다. 이 문서의 배포 예는 클라우드 배포 완료를 뜻하지 않는다.

## Vercel 사용 범위

Hobby의 2 vCPU / 8GB / 32GB는 빌드 머신 사양이다. 같은 사양의 상시 VM을 받는 것이 아니다. React/Cesium과 번들 정적 지리는 Vercel에 배포할 수 있다. FastAPI도 Vercel Function으로 배포할 수 있지만 서버리스 실행에 맞는 진입점·Redis 연결·정적 매핑 번들 구성이 필요하다. 현재 프로젝트 기본 배치는 Oracle Cloud/K3s로 유지한다. [Hobby 공식 사양](https://vercel.com/docs/plans/hobby), [빌드 산출물 제공 방식](https://vercel.com/docs/builds/configure-a-build), [FastAPI 지원](https://vercel.com/docs/frameworks/backend/fastapi).

Vercel Functions의 Hobby 실행 한도는 현재 2GB / 1 vCPU, Fluid Compute 기준 최대 300초다. 지속 실행하는 Kafka 브로커·Redis 서버·Spark 스트리밍 프로세스를 이 구조 그대로 함수로 배포할 수 없다. [공식 함수 한도](https://vercel.com/docs/functions/limitations).

Services/Container Runtime beta로 여러 웹 서비스를 같은 Vercel 프로젝트에 둘 수 있다. 그러나 컨테이너도 HTTP 요청을 받는 함수이며 함수 한도가 적용되고 무요청 시 축소된다. Kafka/Redis TCP 서버와 지속 Spark 소비자를 상시 VM처럼 실행하는 배치는 이 모델에 맞지 않는다. Redis는 Marketplace의 외부 Redis Cloud/Upstash 연동을 사용할 수 있다. [Container Runtime](https://vercel.com/docs/functions/runtimes/container), [Marketplace Storage](https://vercel.com/docs/marketplace-storage).

프런트만 배포한다면 root directory는 `frontend`, build는 `npm run build`, output은 `dist`다. 단, 현재 지리 생성은 아직 완료되지 않았고 `/api`를 Oracle HTTPS API로 연결하는 라우팅도 별도 설정해야 한다. 이것은 배포 방식 설명이며 현재 Vercel 배포나 라우팅 변경을 수행한 것은 아니다. Hobby는 개인·비상업 용도와 월별 전송량/요청 한도 안에서 사용한다.
