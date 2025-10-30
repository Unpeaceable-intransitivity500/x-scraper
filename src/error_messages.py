class ErrorMessages:
    AUTH_FAILED = "Authentication failed. Please check your credentials."
    SESSION_EXPIRED = "Twitter session has expired. Please refresh your session."
    INVALID_CREDENTIALS = "Invalid username, email, or password."
    COOKIES_EXPIRED = "Saved cookies have expired. A new login is required."
    
    RATE_LIMIT_HIT = "Twitter rate limit exceeded."
    RATE_LIMIT_WAIT = "Rate limit reached. Waiting {seconds}s before retry..."
    
    BOT_DETECTED = "Twitter has detected automated behavior."
    BOT_PREVENTION_ADVICE = "Increase delays or use a residential proxy to avoid detection."
    CAPTCHA_REQUIRED = "CAPTCHA challenge detected. Manual intervention required."
    
    CONNECTION_FAILED = "Network connection failed."
    PROXY_CONNECTION_FAILED = "Failed to connect through proxy: {proxy}"
    PAGE_LOAD_TIMEOUT = "Page load timed out after {seconds}s."
    NAVIGATION_FAILED = "Failed to navigate to {url}"
    
    NO_TWEETS_FOUND = "No tweets found in the expected location."
    TWEET_EXTRACTION_FAILED = "Failed to extract tweet data from response."
    SCRAPING_INTERRUPTED = "Scraping was interrupted."
    SCROLL_LIMIT_REACHED = "Maximum scroll attempts reached without finding new tweets."
    
    CONFIG_FILE_MISSING = "Configuration file not found: {path}"
    CONFIG_PARSE_ERROR = "Failed to parse configuration file: {error}"
    MISSING_REQUIRED_CONFIG = "Required configuration missing: {key}"
    INVALID_CONFIG_VALUE = "Invalid configuration value for {key}: {value}"
    
    CHECKPOINT_LOAD_FAILED = "Failed to load checkpoint for @{username}"
    CHECKPOINT_SAVE_FAILED = "Failed to save checkpoint for @{username}"
    
    AI_ANALYSIS_FAILED = "AI analysis failed: {error}"
    AI_PROVIDER_ERROR = "Error communicating with AI provider: {provider}"
    AI_QUOTA_EXCEEDED = "AI API quota exceeded."
    
    UNEXPECTED_ERROR = "An unexpected error occurred: {error}"
    INITIALIZATION_FAILED = "Failed to initialize {component}: {error}"
    CLEANUP_FAILED = "Failed to cleanup {component}: {error}"
    
    @staticmethod
    def format(template: str, **kwargs) -> str:
        return template.format(**kwargs)

