from firecrawl import FirecrawlApp

class crawl:
    def __init__(self):
        self.app = FirecrawlApp(api_key="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")

    def crawl_url(self, url):
        crawl_status = self.app.crawl_url(
            url,
            params={
                'limit': 100,
                'scrapeOptions': {'formats': ['markdown', 'html']}
            },
            poll_interval=30
        )
        return crawl_status['data'][0]['html']