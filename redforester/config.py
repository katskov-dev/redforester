class Config():
    BASIC_URL = ""
    PROTOCOL= ""


class ProductionConfig(Config):
    BASIC_URL = "app.redforester.com"
    PROTOCOL = "http"

class DevelopmentConfig(Config):
    BASIC_URL = "188.68.16.188"
    PROTOCOL = "http"


PRODUCTION_CONFIG = ProductionConfig()
DEVELOPMENT_CONFIG = DevelopmentConfig()