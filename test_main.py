from main import parse_top_news, truncate_kakao_text

# 001=연합뉴스(주요), 082=비주요 언론사, 순서상 082가 먼저 나와도 001이 우선돼야 함
SAMPLE_HTML = """
<a href="https://n.news.naver.com/article/082/0001397816?ntype=RANKING" class="list_title nclicks('RBP.rnknws')" data-nlog-area="content.ranking.article" data-nlog-params="{&#034;rank&#034;:1,&#034;article_id&#034;:&#034;z&#034;}">비주요 언론사 1위 기사</a>
<a href="https://n.news.naver.com/article/001/0016301777?ntype=RANKING" class="list_title nclicks('RBP.rnknws')" data-nlog-area="content.ranking.article" data-nlog-params="{&#034;rank&#034;:1,&#034;article_id&#034;:&#034;x&#034;}">연합뉴스 1위 기사 &amp; 제목</a>
<a href="https://n.news.naver.com/article/001/0016301778?ntype=RANKING" class="list_title nclicks('RBP.rnknws')" data-nlog-area="content.ranking.article" data-nlog-params="{&#034;rank&#034;:2,&#034;article_id&#034;:&#034;y&#034;}">연합뉴스 2위 기사(제외되어야 함)</a>
"""


def test_major_press_prioritized_over_document_order():
    articles = parse_top_news(SAMPLE_HTML, count=1)
    assert len(articles) == 1
    assert articles[0]["title"] == "연합뉴스 1위 기사 & 제목"


def test_falls_back_to_non_major_press_when_needed():
    articles = parse_top_news(SAMPLE_HTML, count=2)
    assert len(articles) == 2
    assert articles[1]["url"].endswith("0001397816?ntype=RANKING")


def test_truncate_kakao_text_respects_limit():
    long_text = "가" * 300
    result = truncate_kakao_text(long_text)
    assert len(result) <= 200
    short_text = "짧은 텍스트"
    assert truncate_kakao_text(short_text) == short_text


if __name__ == "__main__":
    test_major_press_prioritized_over_document_order()
    test_falls_back_to_non_major_press_when_needed()
    test_truncate_kakao_text_respects_limit()
    print("OK")
