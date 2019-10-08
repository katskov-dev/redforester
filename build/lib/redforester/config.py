class Config():
    BASIC_URL = ""
    PROTOCOL= ""


class ProductionConfig(Config):
    BASIC_URL = "app.redforester.com"
    PROTOCOL = "http"

class DevelopmentConfig(Config):
    BASIC_URL = "app.test.redforester.com"
    PROTOCOL = "https"


PRODUCTION_CONFIG = ProductionConfig()
DEVELOPMENT_CONFIG = DevelopmentConfig()