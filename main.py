"""매일 네이버 인기 뉴스 TOP5를 Gemini로 요약해 카카오톡(나에게 보내기)으로 전송."""
import html
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

NAVER_RANKING_URL = "https://news.naver.com/main/ranking/popularDay.naver"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={key}"
KAKAO_TOKEN_URL = "https://kauth.kakao.com/oauth/token"
KAKAO_SEND_URL = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
KAKAO_TEXT_LIMIT = 200

# ponytail: 네이버 랭킹 페이지의 현재 마크업에 맞춘 정규식. 네이버가 구조를 바꾸면 깨짐 -> 이때만 갱신.
TITLE_PATTERN = re.compile(
    r'<a href="(?P<url>[^"]+)" class="list_title[^"]*" data-nlog-area="[^"]*" '
    r'data-nlog-params="\{&#034;rank&#034;:(?P<rank>\d+)[^}]*\}">(?P<title>[^<]+)</a>'
)


def http_get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read()


def http_post_json(url, payload, headers=None):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json", **(headers or {})}
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read())


def http_post_form(url, fields, headers=None):
    data = urllib.parse.urlencode(fields).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded", **(headers or {})}
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read())


def parse_top_news(page_html, count=5):
    """언론사별 랭킹 1위 기사를 언론사가 나온 순서대로 최대 count개 추출."""
    seen_press, articles = set(), []
    for m in TITLE_PATTERN.finditer(page_html):
        if m.group("rank") != "1":
            continue
        url = m.group("url")
        press = url.split("/article/")[1].split("/")[0]
        if press in seen_press:
            continue
        seen_press.add(press)
        articles.append({"title": html.unescape(m.group("title")).strip(), "url": url})
        if len(articles) >= count:
            break
    return articles


def fetch_top_news(count=5):
    page = http_get(NAVER_RANKING_URL, headers={"User-Agent": "Mozilla/5.0"}).decode(
        "euc-kr", errors="replace"
    )
    return parse_top_news(page, count)


def summarize(title, url, api_key):
    prompt = (
        "다음 뉴스 제목을 한국어 한 문장으로 핵심만 요약해줘. 군더더기 없이 사실만.\n"
        f"제목: {title}"
    )
    resp = http_post_json(
        GEMINI_URL.format(key=api_key),
        {"contents": [{"parts": [{"text": prompt}]}]},
    )
    return resp["candidates"][0]["content"]["parts"][0]["text"].strip()


def truncate_kakao_text(text, limit=KAKAO_TEXT_LIMIT):
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def refresh_kakao_access_token(rest_api_key, refresh_token):
    resp = http_post_form(
        KAKAO_TOKEN_URL,
        {
            "grant_type": "refresh_token",
            "client_id": rest_api_key,
            "refresh_token": refresh_token,
        },
    )
    return resp["access_token"]


def send_kakao_message(access_token, article, index):
    text = truncate_kakao_text(f"{index}. {article['title']}\n{article['summary']}")
    template = {
        "object_type": "text",
        "text": text,
        "link": {"web_url": article["url"], "mobile_web_url": article["url"]},
    }
    http_post_form(
        KAKAO_SEND_URL,
        {"template_object": json.dumps(template, ensure_ascii=False)},
        headers={"Authorization": f"Bearer {access_token}"},
    )


def main():
    gemini_key = os.environ["GEMINI_API_KEY"]
    kakao_rest_key = os.environ["KAKAO_REST_API_KEY"]
    kakao_refresh_token = os.environ["KAKAO_REFRESH_TOKEN"]

    articles = fetch_top_news(5)
    if not articles:
        raise SystemExit("네이버 랭킹 페이지에서 기사를 찾지 못함 (마크업 변경 가능성)")

    for article in articles:
        article["summary"] = summarize(article["title"], article["url"], gemini_key)

    access_token = refresh_kakao_access_token(kakao_rest_key, kakao_refresh_token)

    for i, article in enumerate(articles, 1):
        try:
            send_kakao_message(access_token, article, i)
            print(f"[전송완료] {article['title']}")
        except urllib.error.HTTPError as e:
            print(f"[전송실패] {article['title']}: {e.read().decode('utf-8', 'replace')}")


if __name__ == "__main__":
    main()
