import os
from typing import Optional


class ConfigurationError(Exception):
    '''Raised when configuration is invalid or missing required values'''
    pass


class Config:
    '''Application configuration with environment variable validation'''

    # Database configuration
    DATABASE_URL: str
    
    # Placeholder credentials that should never be used in production
    INSECURE_PLACEHOLDERS = [
        'postgresql+asyncpg://user:password@localhost',
        'postgresql+asyncpg://user:password@l',
        'postgresql://user:password@localhost',
        'user:password',
    ]

    def __init__(self):
        '''Initialize configuration and validate required settings'''
        self._load_database_config()
        self._validate_configuration()

    def _load_database_config(self) -> None:
        '''Load database configuration from environment variables'''
        self.DATABASE_URL = os.getenv('DATABASE_URL', '')

    def _validate_configuration(self) -> None:
        '''Validate that all required configuration is present and secure'''
        if not self.DATABASE_URL:
            raise ConfigurationError(
                'DATABASE_URL environment variable is required but not set. '
                'Please set DATABASE_URL in your environment or .env file.'
            )

        # Check for insecure placeholder credentials
        for placeholder in self.INSECURE_PLACEHOLDERS:
            if placeholder in self.DATABASE_URL:
                raise ConfigurationError(
                    f'DATABASE_URL contains insecure placeholder credentials. '
                    f'Please set a valid database connection string. '
                    f'See .env.example for the required format.'
                )

        # Validate URL format
        if not self.DATABASE_URL.startswith(('postgresql://', 'postgresql+asyncpg://')):
            raise ConfigurationError(
                'DATABASE_URL must start with "postgresql://" or "postgresql+asyncpg://". '
                f'Got: {self.DATABASE_URL[:20]}...'
            )

    @classmethod
    def load(cls) -> 'Config':
        '''Load and return validated configuration instance'''
        return cls()


# Global configuration instance
config: Optional[Config] = None


def get_config() -> Config:
    '''Get or create the global configuration instance'''
    global config
    if config is None:
        config = Config.load()
    return config
