class XScraperError(Exception):
    pass


class AuthenticationError(XScraperError):
    pass


class SessionExpiredError(AuthenticationError):
    pass


class InvalidCredentialsError(AuthenticationError):
    pass


class RateLimitError(XScraperError):
    
    def __init__(self, message: str = "Twitter rate limit exceeded", retry_after: int = 0):
        super().__init__(message)
        self.retry_after = retry_after


class BotDetectionError(XScraperError):
    pass


class NetworkError(XScraperError):
    pass


class ProxyError(NetworkError):
    pass


class PageLoadError(NetworkError):
    pass


class ScrapingError(XScraperError):
    pass


class TweetExtractionError(ScrapingError):
    pass


class NoTweetsFoundError(ScrapingError):
    pass


class ConfigurationError(XScraperError):
    pass


class InvalidConfigError(ConfigurationError):
    pass


class MissingConfigError(ConfigurationError):
    pass


class AIAnalysisError(XScraperError):
    pass


class CheckpointError(XScraperError):
    pass

