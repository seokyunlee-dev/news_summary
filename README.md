# news_summary

매일 아침 네이버 랭킹 뉴스(주요 언론사 5곳의 1위 기사)를 Gemini로 한 줄 요약해서 카카오톡 "나에게 보내기"로 전송하는 GitHub Actions 자동화.

- 뉴스 소스: 네이버 뉴스 랭킹(`news.naver.com/main/ranking/popularDay.naver`)에서 연합뉴스/조선일보/중앙일보/KBS/SBS 5개 언론사의 1위 기사
- 요약: Google Gemini API (`gemini-2.5-flash`)
- 전송: 카카오톡 메시지 API (나에게 보내기)
- 실행: 매일 07:00 KST, GitHub Actions cron

## 동작 방식

1. [main.py](main.py)가 네이버 랭킹 페이지 HTML을 받아서 정규식으로 언론사별 1위 기사(제목+링크)를 파싱
2. 각 기사 제목을 Gemini에 보내 한 문장 요약
3. 카카오 refresh_token으로 access_token을 갱신하고, 기사마다 카카오톡 메시지(제목+요약+링크)를 전송

언론사 5곳은 [main.py](main.py)의 `MAJOR_PRESS_IDS`에 고정돼 있음 (네이버 랭킹 페이지의 언론사 노출 순서가 요청마다 바뀌어서, 고정하지 않으면 실행할 때마다 완전히 다른 언론사가 뽑힘).

## 로컬 실행

```powershell
$env:GEMINI_API_KEY="..."
$env:KAKAO_REST_API_KEY="..."
$env:KAKAO_REFRESH_TOKEN="..."

py main.py             # 실제로 카카오톡 전송까지 실행
py main.py --dry-run   # 카카오톡 전송 없이 요약 결과만 콘솔에 출력 (환각 확인용)
py test_main.py        # 파싱/텍스트 자르기 로직 자체 검증
```

## 최초 설정 (카카오 refresh_token 발급)

카카오톡 전송은 최초 1회 로컬에서 OAuth 로그인을 해야 함 (자동화 불가한 수동 단계).

1. [카카오 디벨로퍼스](https://developers.kakao.com)에서 앱 생성 (사업자 등록 불필요, 개인 테스트 앱으로 충분)
2. 앱 설정 > 플랫폼 > Web에 아래 도메인 등록 (메시지 링크 버튼이 동작하려면 필요)
   ```
   https://news.naver.com
   https://n.news.naver.com
   ```
3. 카카오 로그인 활성화, Redirect URI에 `http://localhost:8000` 등록
4. 카카오 로그인 > 동의항목에서 "카카오톡 메시지 전송"(talk_message) 활성화
5. 보안 탭에서 Client Secret이 켜져 있으면 꺼두기 (안 그러면 토큰 발급 시 `KOE010` 에러)
6. [get_kakao_refresh_token.py](get_kakao_refresh_token.py)에 REST API 키를 넣고 실행:
   ```powershell
   py get_kakao_refresh_token.py
   ```
   출력된 `KAKAO_REST_API_KEY`, `KAKAO_REFRESH_TOKEN` 값을 확보

## GitHub Secrets 등록

레포 Settings > Secrets and variables > Actions에 아래 3개 등록:

- `GEMINI_API_KEY`
- `KAKAO_REST_API_KEY`
- `KAKAO_REFRESH_TOKEN`

등록 후 Actions 탭에서 `Daily Kakao News Summary` 워크플로를 수동 실행(`workflow_dispatch`)해서 테스트 가능.

## 알려진 제약

- refresh_token 유효기간은 약 60일. 만료되면 `get_kakao_refresh_token.py`를 다시 실행해서 재발급.
- 네이버 랭킹 페이지의 HTML 마크업이 바뀌면 [main.py](main.py)의 `TITLE_PATTERN` 정규식이 깨짐.
- 5개 언론사가 같은 사건을 다루면 요약이 겹칠 수 있음 (현재는 그대로 둠).
