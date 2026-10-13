# 브랜치와 테스트

개발 흐름은 `feature/* → dev → prd`다. GitHub 기본 브랜치는 `dev`이며 `main`은 이전 이력으로 보존한다. 새 개발과 배포에 `main`을 사용하지 않는다.

| 브랜치 | 역할 | 병합 대상 |
| --- | --- | --- |
| `feature/<기능명>` | 한 기능 또는 수정 | PR로 `dev` |
| `dev` | 기능 통합·로컬 테스트 | 검증 후 PR로 `prd` |
| `prd` | 운영에 배포할 버전 | 운영 서버 준비 후 배포 |

```sh
git switch dev
git pull --ff-only
git switch -c feature/my-feature
# 기능 구현 후
git add <변경한 파일>
git commit -m "feat: add my feature"
git push -u origin feature/my-feature
```

GitHub에서 `feature/my-feature → dev` PR을 만들고 `Branch policy`와 `Validate` 검사를 통과한 뒤 merge commit으로 병합한다. `dev → prd`도 merge commit을 사용해 두 장기 브랜치의 공통 이력을 유지한다. 기능 브랜치에서 `prd`로 직접 병합하지 않는다. `dev`와 `prd`는 직접 push·force push·삭제를 막고 PR과 두 필수 검사를 요구한다. 혼자 작업할 수 있도록 별도 승인 리뷰 수는 0이다.

CI는 ARM64 runner에서 고정 의존성, 프런트 빌드, 배포 설정, 격리 Redis/API/7일 만료와 실제 Kafka→Spark→Redis→HTTP 경로를 검증한다. 정적 지리 번들은 같은 커밋에 포함하므로 CI나 런타임에 지리 원본을 다시 다운로드하지 않는다.

`dev`에서 실행할 때는 README의 준비·검증·실행 명령을 따른다. 테스트 뒤 로컬 Compose 서비스를 유지하므로 `http://localhost:8080`에서 확인할 수 있다. `prd` 병합은 운영 후보를 확정하는 것이며 현재 서버 배포를 실행하지 않는다. OCI/K3s 서버는 아직 없고 자동 배포 자격 증명도 설정하지 않았다. 서버 준비 후 [운영 문서](operations.md)의 ARM64 이미지·K3s 절차를 연결한다.

