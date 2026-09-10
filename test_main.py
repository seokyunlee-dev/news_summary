from main import parse_top_news, truncate_kakao_text

SAMPLE_HTML = """
<a href="https://n.news.naver.com/article/214/0001523236?ntype=RANKING" class="list_title nclicks('RBP.rnknws')" data-nlog-area="content.ranking.article" data-nlog-params="{&#034;rank&#034;:1,&#034;article_id&#034;:&#034;x&#034;}">첫번째 뉴스 &amp; 제목</a>
<a href="https://n.news.naver.com/article/214/0001523237?ntype=RANKING" class="list_title nclicks('RBP.rnknws')" data-nlog-area="content.ranking.article" data-nlog-params="{&#034;rank&#034;:2,&#034;article_id&#034;:&#034;y&#034;}">같은 언론사 2위 기사(제외되어야 함)</a>
<a href="https://n.news.naver.com/article/082/0001397816?ntype=RANKING" class="list_title nclicks('RBP.rnknws')" data-nlog-area="content.ranking.article" data-nlog-params="{&#034;rank&#034;:1,&#034;article_id&#034;:&#034;z&#034;}">두번째 언론사 1위 기사</a>
"""


def test_parse_skips_non_rank1_and_dedupes_press():
    articles = parse_top_news(SAMPLE_HTML, count=5)
    assert len(articles) == 2, articles
    assert articles[0]["title"] == "첫번째 뉴스 & 제목"
    assert articles[1]["url"].endswith("0001397816?ntype=RANKING")


def test_parse_respects_count():
    articles = parse_top_news(SAMPLE_HTML, count=1)
    assert len(articles) == 1


def test_truncate_kakao_text_respects_limit():
    long_text = "가" * 300
    result = truncate_kakao_text(long_text)
    assert len(result) <= 200
    short_text = "짧은 텍스트"
    assert truncate_kakao_text(short_text) == short_text


if __name__ == "__main__":
    test_parse_skips_non_rank1_and_dedupes_press()
    test_parse_respects_count()
    test_truncate_kakao_text_respects_limit()
    print("OK")
