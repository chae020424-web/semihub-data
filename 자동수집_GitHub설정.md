# 노트북을 꺼 둬도 자동으로 수집하기 (GitHub Actions)

GitHub의 서버가 6시간마다(한국시간 0·6·12·18시경) 뉴스·채용공고를 대신 수집해 저장소에 올려 둡니다.
노트북은 서버(`start_semihub.cmd`)를 켜는 순간(그리고 켜 두는 동안 1시간마다) 그 최신 데이터를 받아옵니다.

## 한 번만 하는 설정
1. GitHub에서 새 저장소를 만듭니다. (이름 예: `semihub-data`, **Public**, README 추가 체크 안 함)
2. 저장소 이름(`계정/저장소`)을 Claude에게 알려 주면 코드와 현재 데이터를 올려 줍니다.
3. 저장소 → **Actions** 탭 → 안내가 나오면 "I understand my workflows, go ahead and enable them" 을 누릅니다.
4. Actions → 「SEMI-HUB 자동 수집」 → **Run workflow** 로 한 번 직접 실행해서 초록색 체크가 뜨는지 확인합니다.
5. 노트북의 `remote_config.json` 에 저장소 이름이 들어 있으면 연결 끝입니다. 서버를 다시 켜면 검은 창에 `GitHub 동기화: synced` 가 나옵니다.

## 선택
- **AI 분석도 자동으로**: 저장소 → Settings → Secrets and variables → Actions → New repository secret → 이름 `GEMINI_API_KEY`, 값은 본인 키. (GitHub이 암호화해서 보관하며 화면에 보이지 않습니다.)
- **비공개 저장소로 쓰려면**: 읽기 전용 토큰을 만들어 노트북에서 `setx SEMIHUB_GH_TOKEN "토큰"` 으로 저장합니다.

## 알아둘 점
- 저장소가 **Public** 이므로 올라가는 건 뉴스·채용공고·코드뿐입니다. 내 프로필, 지원 현황, 카카오 키·토큰, 백업은 `.gitignore` 로 제외되어 절대 올라가지 않습니다.
- GitHub 스케줄은 몇 분~수십 분 늦게 돌 수 있고, 저장소에 60일 동안 아무 활동이 없으면 GitHub이 스케줄을 멈출 수 있습니다(Actions 탭에서 다시 켜기).
- 카톡 알림은 노트북이 켜져 서버가 데이터를 받은 시점에 전송됩니다.
- GitHub 서버에서 일부 기업 사이트가 접속을 막을 수 있습니다. 그 경우 Actions 로그와 앱의 「수집 현황」에 실패로 표시되고, 노트북에서 직접 수집하면 됩니다.
- 노트북에서 「최신 뉴스 수집」 버튼은 그대로 노트북에서 직접 수집합니다.
