"""매일 네이버 인기 뉴스 TOP5를 Gemini로 요약해 카카오톡(나에게 보내기)으로 전송."""
import html
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

NAVER_RANKING_URL = "https://news.naver.com/main/ranking/popularDay.naver"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key}"
KAKAO_TOKEN_URL = "https://kauth.kakao.com/oauth/token"
KAKAO_SEND_URL = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
KAKAO_TEXT_LIMIT = 200

# ponytail: 네이버 랭킹 페이지의 현재 마크업에 맞춘 정규식. 네이버가 구조를 바꾸면 깨짐 -> 이때만 갱신.
TITLE_PATTERN = re.compile(
    r'<a href="(?P<url>[^"]+)" class="list_title[^"]*" data-nlog-area="[^"]*" '
    r'data-nlog-params="\{&#034;rank&#034;:(?P<rank>\d+)[^}]*\}">(?P<title>[^<]+)</a>'
)

# 네이버 랭킹 페이지의 언론사 노출 순서는 요청마다 바뀜(노출 공정성 로직으로 추정) ->
# "화면에 먼저 뜨는 언론사"를 집으면 실행할 때마다 완전히 다른 언론사가 나옴.
# 그래서 주요 언론사를 직접 고정하고 그 언론사의 1위 기사만 뽑는다.
MAJOR_PRESS_IDS = [
    "001",  # 연합뉴스
    "023",  # 조선일보
    "025",  # 중앙일보
    "056",  # KBS
    "055",  # SBS
]


def http_get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read()


def _urlopen_json(req):
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{req.full_url} -> HTTP {e.code}: {e.read().decode('utf-8', 'replace')}") from None


def http_post_json(url, payload, headers=None):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json", **(headers or {})}
    )
    return _urlopen_json(req)


def http_post_form(url, fields, headers=None):
    data = urllib.parse.urlencode(fields).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded", **(headers or {})}
    )
    return _urlopen_json(req)


def parse_top_news(page_html, count=5):
    """주요 언론사(MAJOR_PRESS_IDS)의 1위 기사를 우선 추출, 모자라면 다른 언론사로 채움."""
    rank1_by_press, press_order = {}, []
    for m in TITLE_PATTERN.finditer(page_html):
        if m.group("rank") != "1":
            continue
        url = m.group("url")
        press = url.split("/article/")[1].split("/")[0]
        if press not in rank1_by_press:
            rank1_by_press[press] = {"title": html.unescape(m.group("title")).strip(), "url": url}
            press_order.append(press)

    picked, articles = set(), []
    for press in MAJOR_PRESS_IDS + press_order:
        if press in picked or press not in rank1_by_press:
            continue
        picked.add(press)
        articles.append(rank1_by_press[press])
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
    dry_run = "--dry-run" in sys.argv

    gemini_key = os.environ["GEMINI_API_KEY"]

    articles = fetch_top_news(5)
    if not articles:
        raise SystemExit("네이버 랭킹 페이지에서 기사를 찾지 못함 (마크업 변경 가능성)")

    for article in articles:
        article["summary"] = summarize(article["title"], article["url"], gemini_key)

    if dry_run:
        print("=== DRY RUN: 카카오톡 전송 없이 요약만 확인 ===\n")
        for i, article in enumerate(articles, 1):
            print(f"{i}. {article['title']}\n{article['summary']}\n{article['url']}\n")
        return

    kakao_rest_key = os.environ["KAKAO_REST_API_KEY"]
    kakao_refresh_token = os.environ["KAKAO_REFRESH_TOKEN"]
    access_token = refresh_kakao_access_token(kakao_rest_key, kakao_refresh_token)

    for i, article in enumerate(articles, 1):
        try:
            send_kakao_message(access_token, article, i)
            print(f"[전송완료] {article['title']}")
        except RuntimeError as e:
            print(f"[전송실패] {article['title']}: {e}")


if __name__ == "__main__":
    main()
