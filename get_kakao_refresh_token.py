"""
최초 1회, 로컬에서 직접 실행해서 KAKAO_REFRESH_TOKEN을 발급받는 스크립트.

사전 준비 (https://developers.kakao.com):
  1. 앱 생성 후 REST API 키를 아래 REST_API_KEY에 입력.
  2. [카카오 로그인] 활성화, Redirect URI에 http://localhost:8000 등록.
  3. [카카오 로그인 > 동의항목]에서 "카카오톡 메시지 전송"(talk_message) 활성화.
     (개인 앱은 팀원 등록 없이 본인 계정으로 바로 사용 가능)

실행: python get_kakao_refresh_token.py
출력되는 KAKAO_REST_API_KEY / KAKAO_REFRESH_TOKEN을 GitHub repo Secrets에 등록.
"""
import json
import urllib.error
import urllib.parse
import urllib.request

REST_API_KEY = "여기에_REST_API_키_입력"
REDIRECT_URI = "http://localhost:8000"


def main():
    if REST_API_KEY.startswith("여기에"):
        raise SystemExit("REST_API_KEY를 먼저 입력하세요.")

    auth_url = "https://kauth.kakao.com/oauth/authorize?" + urllib.parse.urlencode(
        {
            "client_id": REST_API_KEY,
            "redirect_uri": REDIRECT_URI,
            "response_type": "code",
            "scope": "talk_message",
        }
    )
    print("1) 아래 URL을 브라우저에 열고 로그인 후 동의하세요:\n")
    print(auth_url)
    print("\n2) 리디렉션된 주소창 URL에서 'code=' 뒤의 값을 복사하세요.")
    code = input("\ncode: ").strip()

    data = urllib.parse.urlencode(
        {
            "grant_type": "authorization_code",
            "client_id": REST_API_KEY,
            "redirect_uri": REDIRECT_URI,
            "code": code,
        }
    ).encode()
    req = urllib.request.Request(
        "https://kauth.kakao.com/oauth/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(req) as resp:
            token = json.load(resp)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"토큰 발급 실패: {e.read().decode('utf-8', 'replace')}")

    print("\n=== 아래 값을 GitHub repo Settings > Secrets and variables > Actions 에 등록 ===")
    print("KAKAO_REST_API_KEY:", REST_API_KEY)
    print("KAKAO_REFRESH_TOKEN:", token["refresh_token"])
    print("\n(refresh_token 유효기간 약 60일. 만료되면 이 스크립트를 다시 실행)")


if __name__ == "__main__":
    main()
