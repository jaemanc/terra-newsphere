# 공개 배포 보안

공개 뉴스 조회에는 로그인/JWT/API 키를 요구하지 않는다. 브라우저에 공용 API 키를 넣는 것은 접근 통제가 아니다. 사용자 계정이나 관리자 쓰기 API는 현재 없다.

## 서비스 인증과 격리

Redis 7.4.11을 사용하고 default 사용자를 비활성화한다. 서비스마다 별개의 256-bit 무작위 비밀번호와 ACL 사용자(api, collector, processor, health)를 사용한다. API는 기사 조회와 만료 인덱스 정리만, collector는 최초 수집 시각/쿨다운만, processor는 뉴스 및 인덱스 갱신과 기존 Lua 로딩/실행만, health는 ping만 허용한다. Lua는 적재에 필요하므로 전체 차단하지 않는다. 관리자 CONFIG/FLUSH/ACL 명령은 서비스에 허용하지 않는다.

비밀번호는 `python3 scripts/security_setup.py`로 한 번 생성한다. `.runtime/security`는 Git/Docker build context에서 제외되고 기존 비밀번호는 덮어쓰지 않는다. 호스트 디렉터리는 0700이며 Compose bind secrets의 서로 다른 UID가 읽을 수 있도록 내부 파일은 0444다. 실제 비밀번호는 Compose secrets 또는 K3s Secret의 파일로만 마운트한다. env에는 사용자명·파일 경로만 둔다. 비밀번호를 Git, CLI 인자, 프런트 빌드 변수에 넣지 않는다.

Compose는 web-entry / storage / ingestion 네트워크를 분리하며 frontend에는 Redis/Kafka 네트워크나 비밀번호가 없다. K3s는 기본 ingress/egress를 거부하고 nginx→API, API/collector/Spark→Redis, collector/Spark/init→Kafka만 허용한다. collector의 인터넷 HTTPS와 DNS만 추가 허용하며 사설 IP·클라우드 메타데이터 IP로의 인터넷 egress는 제외한다. K3s CNI가 정책을 실제 집행하는지 배포 후 검증한다.

Kafka는 단일 VM 내부 전용 네트워크에 있으며 현재 SASL/TLS 인증은 추가하지 않는다. 외부 공개 포트, 서로 다른 호스트, 신뢰할 수 없는 공유 namespace로 확장할 때는 SASL/TLS와 브로커 ACL이 필요하다. Redis 연결도 현재 단일 VM 내부 TCP이며 인증은 암호화가 아니다. 외부 네트워크로 이동하면 TLS가 필요하다.

## 반복 호출과 브라우저 보호

로컬과 K3s 모두 모든 HTTP 경로를 nginx로 통과시킨다. `/api`도 Traefik→nginx→FastAPI 경로다. 따라서 Kubernetes API 직결로 제한을 우회하지 않는다.

nginx의 `/api/`는 IP별 5 requests/s + burst 20, 전체 40 requests/s + burst 40, 전체 동시 요청 32 / IP별 8을 제한한다. 초과하면 429다. 시간·body 크기도 제한하고 FastAPI의 Redis 연결은 최대 32개다. 비율은 초기 보수적인 값이며 동일 NAT 사용자가 많으면 정상 트래픽을 측정해 조절한다.

외부가 제공한 X-Forwarded-For는 그대로 믿지 않는다. K3s nginx는 설정된 Traefik Pod CIDR만 신뢰하며 기본 K3s CIDR 10.42.0.0/16을 사용한다. 클러스터 CIDR이 다르면 `TRUSTED_PROXY_CIDR`을 바꾼다. Traefik ingress는 kube-system의 traefik 라벨 Pod만 허용한다. Traefik의 외부 forwardedHeaders.insecure는 켜지 않는다. CDN 사용 시 확인된 CDN IP만 Traefik trustedIPs로 지정해야 한다.

CSP, nosniff, frame deny, referrer/permission 정책을 nginx에서 제공한다. Cesium과 동적 스타일 호환을 위해 CSP에 script unsafe-eval / style unsafe-inline은 남아 있다. unsafe-inline 스크립트는 허용하지 않는다. API docs/openapi는 비활성화한다. Python/프런트/Redis는 non-root, 불필요한 capability 제거, privilege escalation 금지, 임시 영역 외 read-only 설정이다. Spark/Kafka는 런타임 파일 생성 때문에 전체 파일시스템 read-only를 강제하지 않는다. K3s 서비스 계정 토큰은 마운트하지 않는다.

수집 응답은 해제된 본문 기준 4MiB, GKG pointer는 16KiB로 제한한다. 다른 HTTPS origin으로 redirect하면 요청 전 거부한다. GKG ZIP은 기존 16MiB/행·파일 한도를 유지하며 redirect를 따르지 않는다.

## HTTPS와 도메인

소유한 도메인이 있으면 하위 도메인(예: news.example.com)을 쓰면 된다. 새 독립 도메인은 등록업체에서 구매/갱신하고 DNS A/AAAA를 VM IP에 연결한다. 인증서는 Let's Encrypt로 무료 발급·갱신할 수 있어 유료 SSL 구매가 필수는 아니다. 사용자 제공 인증서를 `terra-tls` Secret으로 넣는 현재 방식을 유지한다. 갱신은 발급 도구의 timer/cron과 Secret 갱신을 함께 구성해야 한다.

실제 도메인으로 Ingress를 교체하고 다음을 실행한다. 개인키 파일은 저장소 밖의 0600 파일로 관리한다.

```sh
python3 scripts/security_setup.py
kubectl create namespace terra-newsphere
kubectl -n terra-newsphere create secret generic terra-redis-auth \
  --from-file=.runtime/security/redis_api \
  --from-file=.runtime/security/redis_collector \
  --from-file=.runtime/security/redis_processor \
  --from-file=.runtime/security/redis_health
kubectl -n terra-newsphere create secret tls terra-tls \
  --cert=/path/to/fullchain.pem --key=/path/to/privkey.pem
kubectl apply -k deploy/k3s
```

Traefik Middleware가 HTTP를 HTTPS로 redirect하고 HTTPS 응답에 HSTS를 적용한다. HTTP redirect와 발급 도구의 HTTP-01 검증에는 80, HTTPS에는 443이 필요하다. SSH/K3s 관리 포트는 관리 IP/VPN에만 허용하고 Redis/Kafka는 외부에 열지 않는다. 실제 도메인·VM·인증서가 아직 없으므로 HTTPS가 실서버에서 작동했다고 주장하지 않는다.

## DDoS 한계와 앞단 보호

서버의 요청 제한은 반복 조회와 애플리케이션 과부하를 줄이지만, 회선을 채우는 대규모 분산 공격까지 막을 수는 없다. Cloudflare의 프록시/DDoS 보호처럼 서버 앞단에서 트래픽을 차단하는 서비스를 사용한다. 무료 플랜에도 DDoS 보호가 있으며 고급 기능은 플랜별 차이가 있다. 실제 계정 연결/구매는 수행하지 않는다.

CDN을 사용하면 DNS proxy를 활성화하고 TLS는 Full (strict)로 설정한다. 원본 VM의 80/443은 확인된 CDN 주소 범위로만 제한해 원본 IP 직결을 막는다. HTTP-01 발급과 제한이 충돌하면 DNS-01로 발급하거나 검증 경로를 명시적으로 허용한다. `/api/*`는 캐시하지 않고 뉴스 만료를 존중한다. 클라이언트 IP 헤더를 신뢰할 범위를 설정하지 않으면 전체 사용자에게 하나의 IP 제한이 걸릴 수 있다.

## 검증

`python scripts/verify.py --containers`의 마지막 단계에서 파이프라인과 `check_security.py`를 함께 확인한다. 인증 없는 Redis 거부, 계정별 금지 명령, frontend의 Redis/Kafka 연결 차단, 보안 헤더, 조작된 X-Forwarded-For를 포함한 429와 회복을 확인한다. 테스트는 로컬의 제한된 요청만 보낸다. Python/npm 알려진 취약점은 릴리스마다 재검사하고 ARM64 이미지를 검증한다.
